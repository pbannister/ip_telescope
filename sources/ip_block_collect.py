#!/usr/bin/env python3
#
# ip_block_collect.py - phase 2: map ip_probe addresses onto RIR address blocks.
#
# Inputs:
#   dataflow.out/raw/delegated-<registry>-extended-latest
#       The five RIR delegation files (ARIN, RIPE NCC, APNIC, LACNIC,
#       AFRINIC) in extended record format:
#       registry|country|type|start|value|date|status|extension...
#   <data>/01_ip_probe.json
#       The phase 1 probe list.
#
# Outputs, written to the data directory:
#   02_ip_block.json   every RIR address block that contains at least one
#                      ip_probe, with the RIR record kept verbatim, the
#                      derived range, and an assigned UUID.
#   03_ip_probe.json   [address, block_uuid] for every probe inside an
#                      assigned block (status allocated or assigned).
#   04_ip_probe.json   every probe not inside an assigned block: the
#                      addresses that no RIR has handed to an operator.
#
# A block UUID is derived (UUID version 5) from the registry, the start
# address, and the size, so a block keeps its UUID across runs.
#
# Usage:
#   python3 sources/ip_block_collect.py
#   python3 sources/ip_block_collect.py --raw-directory dataflow.out/raw --data-directory data
#
"""Collect RIR address blocks for the ip_probe list (phase 2)."""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
import uuid
from typing import Iterator

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ip_probe_generate import probe_count_read, probe_format, probe_parse  # noqa: E402

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent

REGISTRY_ALL = ("afrinic", "apnic", "arin", "lacnic", "ripencc")
FILE_RAW_TEMPLATE = "delegated-{registry}-extended-latest"

# A record with one of these statuses names an operator; anything else
# (available, reserved) is space no operator holds.
STATUS_ASSIGNED = frozenset(("allocated", "assigned"))

# Namespace for block UUIDs. The URL is a stable project name, not a
# fetched resource.
NAMESPACE_BLOCK = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://labs.bannister.us/IP_telescope/block"
)


@dataclasses.dataclass(slots=True)
class BlockRecord:
    """One RIR delegation record, with its derived range and UUID."""

    text_registry: str
    text_country: str
    text_type: str
    text_start: str
    text_date: str
    text_status: str
    tuple_extension: tuple[str, ...]
    value_size: int
    value_start: int
    value_end: int
    text_uuid: str

    @property
    def is_assigned(self) -> bool:
        """Return True when an operator holds the block."""
        return self.text_status in STATUS_ASSIGNED

    def document(self, count_probe: int) -> dict:
        """Return the JSON document for this block.

        Only source facts and the join key are stored. The end address, the
        prefix, and the opaque id were once written here as well; they are
        functions of the fields below, and a stored derivation can drift, so
        readers compute them with block_address_end and block_prefix_text.
        """
        return {
            "block_uuid": self.text_uuid,
            "probe_count": count_probe,
            "assigned": self.is_assigned,
            "rir_record": {
                "registry": self.text_registry,
                "country": self.text_country,
                "type": self.text_type,
                "start": self.text_start,
                "value": self.value_size,
                "date": self.text_date,
                "status": self.text_status,
                "extensions": list(self.tuple_extension),
            },
        }


def block_address_end(value_start: int, value_size: int) -> int:
    """Return the last address of a block."""
    return value_start + value_size - 1


def block_prefix_text(value_start: int, value_size: int) -> str | None:
    """Return the CIDR prefix, when the block really is one.

    A power-of-two size is not enough: the start address must also be aligned
    to that size. A record of 1,048,576 addresses starting at 13.168.0.0 is
    not 13.168.0.0/12, because that string names 13.160.0.0-13.175.255.255, a
    different range. Such a block is described by its start and end addresses
    instead.
    """
    if 1 > value_size:
        return None
    if 0 == value_size & (value_size - 1):
        if 0 == value_start & (value_size - 1):
            value_bits = value_size.bit_length() - 1
            return f"{probe_format(value_start)}/{32 - value_bits}"
    return None


def block_uuid_make(text_registry: str, value_start: int, value_size: int) -> str:
    """Return the stable UUID of a block."""
    text_name = f"{text_registry}|{probe_format(value_start)}|{value_size}"
    return str(uuid.uuid5(NAMESPACE_BLOCK, text_name))


def block_records_read(path_directory_raw: pathlib.Path) -> list[BlockRecord]:
    """Read every IPv4 record of every RIR delegation file, sorted by start."""
    list_block: list[BlockRecord] = []
    for text_registry in REGISTRY_ALL:
        path_file = path_directory_raw / FILE_RAW_TEMPLATE.format(
            registry=text_registry
        )
        if not path_file.is_file():
            raise FileNotFoundError(f"missing delegation file: {path_file}")
        with open(path_file, "r", encoding="ascii", errors="replace") as file_raw:
            for text_line in file_raw:
                if text_line.startswith("#"):
                    continue
                field = text_line.rstrip("\n").split("|")
                if 7 > len(field) or "ipv4" != field[2]:
                    continue
                value_size = int(field[4])
                value_start = probe_parse(field[3])
                list_block.append(
                    BlockRecord(
                        text_registry=field[0],
                        text_country=field[1],
                        text_type=field[2],
                        text_start=field[3],
                        text_date=field[5],
                        text_status=field[6],
                        tuple_extension=tuple(field[7:]),
                        value_size=value_size,
                        value_start=value_start,
                        value_end=value_start + value_size - 1,
                        text_uuid=block_uuid_make(field[0], value_start, value_size),
                    )
                )
    list_block.sort(key=lambda record: record.value_start)
    return list_block


def probe_block_iter(
    list_block: list[BlockRecord], path_probe: pathlib.Path
) -> Iterator[tuple[int, BlockRecord | None]]:
    """Yield (probe, containing block) for every probe, ascending.

    Blocks are disjoint and sorted, so one pointer walks them alongside the
    ascending probe list.
    """
    index_block = 0
    count_block = len(list_block)
    for value_probe in probe_count_read(path_probe):
        while (
            index_block < count_block
            and list_block[index_block].value_end < value_probe
        ):
            index_block += 1
        record_block = None
        if index_block < count_block:
            record_candidate = list_block[index_block]
            if (
                record_candidate.value_start
                <= value_probe
                <= record_candidate.value_end
            ):
                record_block = record_candidate
        yield value_probe, record_block


def collect(
    path_directory_raw: pathlib.Path,
    path_directory_data: pathlib.Path,
    flag_refresh: bool = False,
) -> dict[str, int | str]:
    """Write the phase 2 outputs, or keep the ones that already exist.

    The three files are produced together and are expensive to rebuild; the
    enriched 02 file especially, because it carries every RDAP answer. Pass
    refresh to write them again.
    """
    path_block = path_directory_data / "02_ip_block.json"
    path_assigned = path_directory_data / "03_ip_probe.json"
    path_open = path_directory_data / "04_ip_probe.json"
    list_path_output = (path_block, path_assigned, path_open)
    if not flag_refresh and all(
        path_output.is_file() for path_output in list_path_output
    ):
        return {
            "reuse": "yes",
            **{
                f"file_{path_output.stem}_bytes": path_output.stat().st_size
                for path_output in list_path_output
            },
        }

    list_block = block_records_read(path_directory_raw)
    path_probe = path_directory_data / "01_ip_probe.json"
    if not path_probe.is_file():
        raise FileNotFoundError(
            f"missing probe file: {path_probe}; run scripts/01-probe-generate.sh"
        )

    dict_probe_count: dict[str, int] = {}
    list_block_hit: list[BlockRecord] = []
    count_probe_assigned = 0
    count_probe_open = 0

    with (
        open(path_assigned, "w", encoding="ascii") as file_assigned,
        open(path_open, "w", encoding="ascii") as file_open,
    ):
        file_assigned.write("[\n")
        file_open.write("[\n")
        count_assigned_written = 0
        count_open_written = 0
        for value_probe, record_block in probe_block_iter(list_block, path_probe):
            if record_block is None:
                text_payload = f'    "{probe_format(value_probe)}"'
                if 0 < count_open_written:
                    file_open.write(",\n")
                file_open.write(text_payload)
                count_open_written += 1
                count_probe_open += 1
                continue
            if record_block.text_uuid not in dict_probe_count:
                dict_probe_count[record_block.text_uuid] = 0
                list_block_hit.append(record_block)
            dict_probe_count[record_block.text_uuid] += 1
            if not record_block.is_assigned:
                if 0 < count_open_written:
                    file_open.write(",\n")
                file_open.write(f'    "{probe_format(value_probe)}"')
                count_open_written += 1
                count_probe_open += 1
                continue
            if 0 < count_assigned_written:
                file_assigned.write(",\n")
            file_assigned.write(
                f'    ["{probe_format(value_probe)}", "{record_block.text_uuid}"]'
            )
            count_assigned_written += 1
            count_probe_assigned += 1
        file_assigned.write("\n]\n")
        file_open.write("\n]\n")

    with open(path_block, "w", encoding="ascii") as file_block:
        file_block.write("[\n")
        for index_block, record_block in enumerate(list_block_hit):
            if 0 < index_block:
                file_block.write(",\n")
            document_block = record_block.document(
                dict_probe_count[record_block.text_uuid]
            )
            file_block.write(block_json_text(document_block))
        file_block.write("\n]\n")

    return {
        "block": len(list_block_hit),
        "block_assigned": sum(1 for record in list_block_hit if record.is_assigned),
        "block_open": sum(1 for record in list_block_hit if not record.is_assigned),
        "probe_assigned": count_probe_assigned,
        "probe_open": count_probe_open,
    }


def block_json_text(document_object: dict) -> str:
    """Return one block document as JSON text, indented for the array."""
    text_json = json.dumps(document_object, indent=4, ensure_ascii=True)
    return "\n".join("    " + text_line for text_line in text_json.split("\n"))


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Collect RIR address blocks for the ip_probe list (phase 2)."
    )
    parser_arguments.add_argument(
        "--raw-directory",
        type=pathlib.Path,
        default=PATH_REPOSITORY_ROOT / "dataflow.out" / "raw",
        help="directory holding the RIR delegation files",
    )
    parser_arguments.add_argument(
        "--data-directory",
        type=pathlib.Path,
        default=PATH_REPOSITORY_ROOT / "dataflow.out",
        help="directory holding the phase 1 input and the phase 2 outputs",
    )
    parser_arguments.add_argument(
        "--refresh",
        action="store_true",
        help="write the phase 2 files again even when they already exist",
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    try:
        dict_count = collect(
            arguments_parsed.raw_directory,
            arguments_parsed.data_directory,
            arguments_parsed.refresh,
        )
    except (FileNotFoundError, ValueError) as error_collect:
        print(f"collect: FAIL: {error_collect}", file=sys.stderr)
        return 1

    for text_key, value_count in dict_count.items():
        print(f"collect: {text_key}={value_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
