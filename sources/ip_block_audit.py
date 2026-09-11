#!/usr/bin/env python3
#
# ip_block_audit.py - audit 02_ip_block.json for inconsistent fields.
#
# The block records carry source fields (the RIR delegation record), fields
# derived from them (the range, the prefix, the UUID, the assigned flag), and
# a verbatim RDAP answer with a summary drawn from it. Redundancy is useful
# only while the parts agree, so every derived field is checked against the
# field it came from.
#
# Two kinds of finding, and they mean different things:
#
#   error - an internal contradiction. A derived field disagrees with its
#           source, so one of the two is wrong: a defect in the data or the
#           code that wrote it.
#   note  - separate sources disagree. The delegation record says one thing
#           and RDAP says another. That is not a defect; it is the project's
#           subject matter, and it is reported so the map can show it.
#
# Usage:
#   python3 sources/ip_block_audit.py
#   python3 sources/ip_block_audit.py --example 10
#   python3 sources/ip_block_audit.py --quiet      (counts only)
#
"""Audit the collected address blocks for inconsistent fields."""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ip_block_collect import NAMESPACE_BLOCK, block_uuid_make  # noqa: E402
from ip_probe_generate import probe_format, probe_parse  # noqa: E402

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent

COUNT_EXAMPLE_DEFAULT = 5
STATUS_ASSIGNED = frozenset(("allocated", "assigned"))

TEXT_NAMESPACE_HISTORICAL = "https://labs.bannister.us/ip_telescope/block"

TEXT_SERVICE_OF_REGISTRY = {
    "afrinic": "rdap.afrinic.net",
    "apnic": "rdap.apnic.net",
    "arin": "rdap.arin.net",
    "lacnic": "rdap.lacnic.net",
    "ripencc": "rdap.db.ripe.net",
}

TEXT_EVENT_ROLE = ("registrant", "administrative", "technical")


class Findings:
    """Collect findings by check, with countable examples."""

    def __init__(self, count_example: int) -> None:
        self.count_example = count_example
        self.dict_count: collections.Counter[str] = collections.Counter()
        self.dict_example: dict[str, list[str]] = collections.defaultdict(list)

    def error(self, text_check: str, text_example: str) -> None:
        """Record an internal contradiction."""
        self.dict_count[f"error: {text_check}"] += 1
        list_example = self.dict_example[f"error: {text_check}"]
        if len(list_example) < self.count_example:
            list_example.append(text_example)

    def note(self, text_check: str, text_example: str) -> None:
        """Record a disagreement between sources."""
        self.dict_count[f"note: {text_check}"] += 1
        list_example = self.dict_example[f"note: {text_check}"]
        if len(list_example) < self.count_example:
            list_example.append(text_example)

    def report(self, flag_quiet: bool) -> int:
        """Print the findings and return the number of errors."""
        count_error = sum(
            value_count
            for text_check, value_count in self.dict_count.items()
            if text_check.startswith("error")
        )
        for text_check in sorted(self.dict_count):
            print(f"{self.dict_count[text_check]:8}  {text_check}")
        if not flag_quiet:
            print()
            for text_check in sorted(self.dict_example):
                print(f"{text_check}:")
                for text_example in self.dict_example[text_check]:
                    print(f"    {text_example}")
        return count_error


def prefix_expected(value_start: int, value_size: int) -> str | None:
    """Return the honest CIDR of a block, or None when it is not one.

    A block is a CIDR only when the size is a power of two *and* the start
    address is aligned to that size. A record of 256 addresses starting at
    2.2.2.128 is not 2.2.2.128/24: that string names a different range.
    """
    if 0 == value_size & (value_size - 1):
        if 0 == value_start & (value_size - 1):
            value_bits = value_size.bit_length() - 1
            return f"{probe_format(value_start)}/{32 - value_bits}"
    return None


def summary_organization_read(document_rdap: dict | None) -> str | None:
    """Return the organization the summary should have extracted."""
    if not isinstance(document_rdap, dict):
        return None
    for dict_entity in document_rdap.get("entities", []):
        if not isinstance(dict_entity, dict):
            continue
        for text_role in dict_entity.get("roles", []):
            if text_role in TEXT_EVENT_ROLE:
                dict_vcard = dict_entity.get("vcardArray")
                if isinstance(dict_vcard, list) and 2 <= len(dict_vcard):
                    for list_field in dict_vcard[1]:
                        if isinstance(list_field, list) and "fn" == list_field[0]:
                            return list_field[3]
    return None


def summary_event_read(document_rdap: dict | None) -> dict:
    """Return the events map the summary should have extracted."""
    if not isinstance(document_rdap, dict):
        return {}
    dict_event = {}
    for dict_item in document_rdap.get("events", []):
        if isinstance(dict_item, dict) and dict_item.get("eventAction"):
            dict_event[dict_item["eventAction"]] = dict_item.get("eventDate")
    return dict_event


def audit(path_block: pathlib.Path, count_example: int) -> tuple[Findings, dict]:
    """Audit every block record and return the findings and a summary."""
    with open(path_block, "r", encoding="utf-8") as file_block:
        list_block = json.load(file_block)

    findings = Findings(count_example)
    dict_count = collections.Counter()
    set_uuid: set[str] = set()
    value_previous_end = -1
    list_start = []

    for document_block in list_block:
        text_uuid = document_block.get("block_uuid")
        document_rir = document_block.get("rir_record", {})
        document_derived = document_block.get("derived", {})
        document_rdap = document_block.get("rdap", {})
        text_registry = document_rir.get("registry", "")
        text_start = document_rir.get("start", "")
        value_size = document_rir.get("value")
        value_start = probe_parse(text_start)
        list_start.append((value_start, value_size, text_uuid))

        # --- the record itself -------------------------------------------
        if "ipv4" != document_rir.get("type"):
            findings.error(
                "rir_record.type is not ipv4",
                f"{text_uuid} {text_start} type={document_rir.get('type')!r}",
            )
        if not isinstance(value_size, int) or 1 > value_size:
            findings.error(
                "rir_record.value is not a positive count",
                f"{text_uuid} {text_start} value={value_size!r}",
            )
            continue
        if 1 > document_block.get("probe_count", 0):
            findings.error(
                "probe_count is zero on a collected block",
                f"{text_uuid} {text_start}",
            )

        # --- fields derived from the record ------------------------------
        value_end = value_start + value_size - 1
        text_end_expected = probe_format(value_end)
        if text_end_expected != document_derived.get("address_end"):
            findings.error(
                "derived.address_end disagrees with start+value",
                f"{text_uuid} {text_start} value={value_size} "
                f"stored={document_derived.get('address_end')} expected={text_end_expected}",
            )
        text_prefix_expected = prefix_expected(value_start, value_size)
        if text_prefix_expected != document_derived.get("prefix"):
            findings.error(
                "derived.prefix is not the block's real CIDR",
                f"{text_uuid} {text_start} value={value_size} "
                f"stored={document_derived.get('prefix')!r} expected={text_prefix_expected!r}",
            )
        text_uuid_expected = block_uuid_make(text_registry, value_start, value_size)
        if text_uuid_expected != text_uuid:
            # The UUID namespace string changed on 2026-09-11, after these
            # blocks were written, so the historical namespace is accepted as
            # a note rather than an error. Any other mismatch is a defect.
            text_uuid_historical = str(
                uuid.uuid5(
                    uuid.uuid5(uuid.NAMESPACE_URL, TEXT_NAMESPACE_HISTORICAL),
                    f"{text_registry}|{text_start}|{value_size}",
                )
            )
            if text_uuid_historical == text_uuid:
                findings.note(
                    "block_uuid predates the namespace rename of 2026-09-11",
                    f"{text_uuid} {text_start}",
                )
            else:
                findings.error(
                    "block_uuid is not the UUID of registry|start|value",
                    f"{text_uuid} {text_start} expected={text_uuid_expected}",
                )
        if text_uuid in set_uuid:
            findings.error("block_uuid is duplicated", f"{text_uuid} {text_start}")
        set_uuid.add(text_uuid)
        flag_assigned_expected = document_rir.get("status") in STATUS_ASSIGNED
        if flag_assigned_expected is not document_block.get("assigned"):
            findings.error(
                "assigned disagrees with the record status",
                f"{text_uuid} {text_start} status={document_rir.get('status')!r} "
                f"stored={document_block.get('assigned')}",
            )
        list_extension = document_rir.get("extensions") or [""]
        text_opaque = list_extension[0] if list_extension else ""
        if text_opaque.startswith("opaque-id="):
            text_opaque = text_opaque.split("=", 1)[1]
        if text_opaque != document_derived.get("opaque_id", ""):
            findings.error(
                "derived.opaque_id disagrees with rir_record.extensions",
                f"{text_uuid} {text_start} stored={document_derived.get('opaque_id')!r} "
                f"extension={list_extension[0]!r}",
            )

        # --- RDAP: the wrapper against the document ----------------------
        text_status = document_rdap.get("status")
        document_document = document_rdap.get("document")
        if document_rdap:
            if document_rdap.get("query") != text_start:
                findings.error(
                    "rdap.query is not the block start address",
                    f"{text_uuid} {text_start} query={document_rdap.get('query')}",
                )
            if 200 == text_status and not isinstance(document_document, dict):
                findings.error(
                    "rdap.status is 200 but the document is missing",
                    f"{text_uuid} {text_start}",
                )
            if 200 != text_status and document_document is not None:
                findings.error(
                    "rdap.document is present without a 200 status",
                    f"{text_uuid} {text_start} status={text_status}",
                )
            dict_summary = document_rdap.get("summary") or {}
            if isinstance(document_document, dict):
                for text_key, text_field in (
                    ("handle", "handle"),
                    ("name", "name"),
                    ("type", "type"),
                    ("parent_handle", "parentHandle"),
                    ("start_address", "startAddress"),
                    ("end_address", "endAddress"),
                    ("country", "country"),
                ):
                    if dict_summary.get(text_key) != document_document.get(text_field):
                        findings.error(
                            f"rdap.summary.{text_key} disagrees with the document",
                            f"{text_uuid} {text_start} summary={dict_summary.get(text_key)!r} "
                            f"document={document_document.get(text_field)!r}",
                        )
                if dict_summary.get("organization") != summary_organization_read(document_document):
                    findings.error(
                        "rdap.summary.organization disagrees with the document entities",
                        f"{text_uuid} {text_start} summary={dict_summary.get('organization')!r} "
                        f"entities={summary_organization_read(document_document)!r}",
                    )
                if (dict_summary.get("event") or {}) != summary_event_read(document_document):
                    findings.error(
                        "rdap.summary.event disagrees with the document events",
                        f"{text_uuid} {text_start}",
                    )
            elif dict_summary:
                findings.error(
                    "rdap.summary is present without a document",
                    f"{text_uuid} {text_start}",
                )

        # --- separate sources that disagree (notes, not defects) ---------
        text_service = document_rdap.get("service")
        if text_service:
            text_host = text_service.split("/")[2] if "//" in text_service else text_service
            text_host_expected = TEXT_SERVICE_OF_REGISTRY.get(text_registry)
            if text_host_expected and text_host != text_host_expected:
                findings.note(
                    "the RDAP service is not the delegation registry's service",
                    f"{text_uuid} {text_start} registry={text_registry} service={text_host}",
                )
        dict_summary = document_rdap.get("summary") or {}
        if 200 == text_status:
            if dict_summary.get("start_address") != text_start:
                findings.note(
                    "RDAP answered with a parent object, not this block",
                    f"{text_uuid} {text_start}-{document_derived.get('address_end')} "
                    f"rdap={dict_summary.get('start_address')}-{dict_summary.get('end_address')}",
                )
            text_country_rir = document_rir.get("country") or ""
            text_country_rdap = dict_summary.get("country") or ""
            if text_country_rir and text_country_rdap and text_country_rir != text_country_rdap:
                findings.note(
                    "the delegation country and the RDAP country differ",
                    f"{text_uuid} {text_start} delegation={text_country_rir} rdap={text_country_rdap}",
                )
            if not dict_summary.get("name"):
                findings.note(
                    "the RDAP object has no name",
                    f"{text_uuid} {text_start} handle={dict_summary.get('handle')!r}",
                )
        for text_key, value_count in (
            ("rdap status 200", 1 if 200 == text_status else 0),
            ("rdap status 404", 1 if 404 == text_status else 0),
            ("rdap unanswered", 1 if text_status is None else 0),
            ("assigned", 1 if document_block.get("assigned") else 0),
            ("unassigned", 1 if not document_block.get("assigned") else 0),
        ):
            dict_count[text_key] += value_count
        dict_count[f"status {document_rir.get('status')}"] += 1

    # --- the collection as a whole --------------------------------------
    list_start.sort(key=lambda item: item[0])
    for index_block in range(1, len(list_start)):
        value_previous_start, value_previous_size, text_previous_uuid = list_start[index_block - 1]
        value_start, value_size, text_uuid = list_start[index_block]
        if value_start <= value_previous_start + value_previous_size - 1:
            findings.error(
                "blocks overlap",
                f"{text_previous_uuid} and {text_uuid} both cover {probe_format(value_start)}",
            )
    return findings, dict_count


def repair(path_block: pathlib.Path, count_example: int) -> dict[str, int]:
    """Rewrite the derived fields that disagree with their source fields.

    Only fields with one unambiguous correct value are repaired: the end
    address and the prefix, both functions of the record's start and size.
    The UUID is never touched, because the probe-to-block file and the
    characterization refer to it; a UUID that no longer matches its rule is
    reported for a decision, not silently rewritten.
    """
    with open(path_block, "r", encoding="utf-8") as file_block:
        list_block = json.load(file_block)
    dict_change: dict[str, int] = collections.Counter()
    list_example: list[str] = []
    for document_block in list_block:
        document_rir = document_block.get("rir_record", {})
        document_derived = document_block.get("derived", {})
        text_start = document_rir.get("start", "")
        value_size = document_rir.get("value")
        if not isinstance(value_size, int) or 1 > value_size:
            continue
        value_start = probe_parse(text_start)
        text_end_expected = probe_format(value_start + value_size - 1)
        if text_end_expected != document_derived.get("address_end"):
            if len(list_example) < count_example:
                list_example.append(
                    f"{text_start} address_end {document_derived.get('address_end')!r} "
                    f"-> {text_end_expected!r}"
                )
            document_derived["address_end"] = text_end_expected
            dict_change["address_end"] += 1
        text_prefix_expected = prefix_expected(value_start, value_size)
        if text_prefix_expected != document_derived.get("prefix"):
            if len(list_example) < count_example:
                list_example.append(
                    f"{text_start} prefix {document_derived.get('prefix')!r} "
                    f"-> {text_prefix_expected!r}"
                )
            document_derived["prefix"] = text_prefix_expected
            dict_change["prefix"] += 1
    if dict_change:
        with open(path_block, "w", encoding="utf-8") as file_block:
            json.dump(list_block, file_block, indent=4, ensure_ascii=True)
            file_block.write("\n")
        for text_example in list_example:
            print(f"repair: {text_example}")
    return dict(dict_change)


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Audit the collected address blocks for inconsistent fields."
    )
    parser_arguments.add_argument(
        "--data-directory",
        type=pathlib.Path,
        default=PATH_REPOSITORY_ROOT / "dataflow.out",
    )
    parser_arguments.add_argument("--example", type=int, default=COUNT_EXAMPLE_DEFAULT)
    parser_arguments.add_argument("--quiet", action="store_true")
    parser_arguments.add_argument(
        "--repair",
        action="store_true",
        help="rewrite the derived fields that disagree with their source fields",
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    path_block = arguments_parsed.data_directory / "02_ip_block.json"
    if not path_block.is_file():
        print(f"audit: FAIL: missing block file: {path_block}", file=sys.stderr)
        return 1

    print(f"audit: {path_block}")
    if arguments_parsed.repair:
        dict_change = repair(path_block, arguments_parsed.example)
        for text_key, value_count in sorted(dict_change.items()):
            print(f"repair: {text_key}={value_count}")
        if not dict_change:
            print("repair: nothing to repair")
        print()
    findings, dict_count = audit(path_block, arguments_parsed.example)
    count_error = findings.report(arguments_parsed.quiet)
    print()
    for text_key in sorted(dict_count):
        print(f"{dict_count[text_key]:8}  {text_key}")
    print()
    print(f"audit: {count_error} internal contradiction(s)")
    return 1 if count_error else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
