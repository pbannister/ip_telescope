#!/usr/bin/env python3
#
# ip_probe_generate.py - phase 1: generate the ip_probe list.
#
# An ip_probe is an IPv4 address that
#   * has four prime octets, and
#   * is valid for routing across the Internet.
#
# "Valid for routing" here means globally reachable unicast: the address is
# not inside an IANA special-purpose block that is private, loopback,
# link-local, shared, documentation, benchmark, multicast, reserved, or
# broadcast.
#
# Only three excluded blocks intersect the four-prime-octet space:
#   127.0.0.0/8   loopback    - 127 is a prime first octet
#   224.0.0.0/4   multicast   - prime first octets 227, 229, 233, 239
#   240.0.0.0/4   reserved    - prime first octets 241, 251
# Every other excluded block begins at a composite first octet, so no
# four-prime address can fall inside it. The exclusion list is kept whole
# anyway, so the rule reads as the routing rule it is.
#
# Output (default): dataflow.out/01_ip_probe.json
#   A JSON array of dotted-quad strings, ascending, one address per line.
#
# Usage:
#   python3 sources/ip_probe_generate.py --output dataflow.out/01_ip_probe.json
#   python3 sources/ip_probe_generate.py --count-only
#   python3 sources/ip_probe_generate.py --first 1000 --output /tmp/sample.json
#   python3 sources/ip_probe_generate.py --verify dataflow.out/01_ip_probe.json
#
"""Generate and verify the ip_probe list (phase 1)."""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Iterator

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH_OUTPUT_DEFAULT = PATH_REPOSITORY_ROOT / "dataflow.out" / "01_ip_probe.json"

BITS_OCTET = 8
COUNT_OCTET = 4
VALUE_OCTET_MAX = 255

# 54 primes in 0..255; 54**4 four-prime addresses, less the 7 first-octet
# classes that are not routable (127, 227, 229, 233, 239, 241, 251), each
# costing 54**3 addresses: 8503056 - 1102248.
COUNT_PROBE_EXPECTED = 54**COUNT_OCTET - 7 * 54 ** (COUNT_OCTET - 1)

# IANA IPv4 Special-Purpose Address Registry entries that are not globally
# reachable unicast, ordered by prefix.
PREFIX_EXCLUDED = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "255.255.255.255/32",
)


def octet_prime_list() -> list[int]:
    """Return every prime value of an octet, ascending."""
    is_prime = [True] * (VALUE_OCTET_MAX + 1)
    is_prime[0] = False
    is_prime[1] = False
    value = 2
    while value * value <= VALUE_OCTET_MAX:
        if is_prime[value]:
            multiple = value * value
            while multiple <= VALUE_OCTET_MAX:
                is_prime[multiple] = False
                multiple += value
        value += 1
    return [value for value in range(VALUE_OCTET_MAX + 1) if is_prime[value]]


OCTET_PRIME = tuple(octet_prime_list())


def prefix_parse(text_prefix: str) -> tuple[int, int]:
    """Return (mask, network) for a prefix such as '224.0.0.0/4'."""
    text_address, text_length = text_prefix.split("/")
    value_length = int(text_length)
    value_network = 0
    for text_octet in text_address.split("."):
        value_network = (value_network << BITS_OCTET) | int(text_octet)
    value_mask = ((1 << value_length) - 1) << (COUNT_OCTET * BITS_OCTET - value_length)
    return value_mask, value_network & value_mask


def exclusion_tables() -> tuple[frozenset[int], dict[int, tuple[tuple[int, int], ...]]]:
    """Return (whole first octets, narrow blocks by first octet).

    A block of length 8 or shorter covers whole first octets, so it is
    filtered by first octet alone. A narrower block is kept for an exact
    check of the addresses that survive the first filter.
    """
    octet_excluded: set[int] = set()
    prefix_narrow: dict[int, list[tuple[int, int]]] = {}
    for text_prefix in PREFIX_EXCLUDED:
        value_mask, value_network = prefix_parse(text_prefix)
        value_length = bin(value_mask).count("1")
        if value_length <= BITS_OCTET:
            value_first = value_network >> (3 * BITS_OCTET)
            value_count = 1 << (BITS_OCTET - value_length)
            for offset in range(value_count):
                octet_excluded.add(value_first + offset)
        else:
            value_first = value_network >> (3 * BITS_OCTET)
            prefix_narrow.setdefault(value_first, []).append(
                (value_mask, value_network)
            )
    return frozenset(octet_excluded), {
        value_first: tuple(block_list)
        for value_first, block_list in prefix_narrow.items()
    }


OCTET_FIRST_EXCLUDED, PREFIX_NARROW_BY_FIRST = exclusion_tables()


def probe_is_valid(value_address: int) -> bool:
    """Return True when the address has four prime octets and is routable."""
    value_rest = value_address
    for _ in range(COUNT_OCTET):
        if (value_rest & VALUE_OCTET_MAX) not in OCTET_PRIME_SET:
            return False
        value_rest >>= BITS_OCTET
    value_first = value_address >> (3 * BITS_OCTET)
    if value_first in OCTET_FIRST_EXCLUDED:
        return False
    for value_mask, value_network in PREFIX_NARROW_BY_FIRST.get(value_first, ()):
        if value_address & value_mask == value_network:
            return False
    return True


OCTET_PRIME_SET = frozenset(OCTET_PRIME)


def probe_iter(count_limit: int | None = None) -> Iterator[int]:
    """Yield ip_probe addresses as integers, ascending."""
    count_emitted = 0
    for value_first in OCTET_PRIME:
        if value_first in OCTET_FIRST_EXCLUDED:
            continue
        block_list = PREFIX_NARROW_BY_FIRST.get(value_first, ())
        for value_second in OCTET_PRIME:
            for value_third in OCTET_PRIME:
                value_base = (
                    (value_first << (3 * BITS_OCTET))
                    | (value_second << (2 * BITS_OCTET))
                    | (value_third << BITS_OCTET)
                )
                for value_fourth in OCTET_PRIME:
                    value_address = value_base | value_fourth
                    if any(
                        value_address & value_mask == value_network
                        for value_mask, value_network in block_list
                    ):
                        continue
                    yield value_address
                    count_emitted += 1
                    if count_limit is not None and count_limit <= count_emitted:
                        return


def probe_format(value_address: int) -> str:
    """Return the dotted-quad text of an address."""
    return ".".join(
        str((value_address >> shift) & VALUE_OCTET_MAX) for shift in (24, 16, 8, 0)
    )


def probe_parse(text_address: str) -> int:
    """Return the integer value of a dotted-quad address."""
    value_address = 0
    for text_octet in text_address.split("."):
        value_address = (value_address << BITS_OCTET) | int(text_octet)
    return value_address


def probe_count_read(path_probe: pathlib.Path) -> Iterator[int]:
    """Yield the addresses of a generated probe file, one line at a time."""
    with open(path_probe, "r", encoding="ascii") as file_probe:
        for text_line in file_probe:
            text_item = text_line.strip().rstrip(",").strip().strip('"')
            if not text_item or text_item in ("[", "]"):
                continue
            yield probe_parse(text_item)


def probe_write(path_probe: pathlib.Path, count_limit: int | None = None) -> int:
    """Write a probe file and return the number of addresses written."""
    path_probe.parent.mkdir(parents=True, exist_ok=True)
    count_written = 0
    with open(path_probe, "w", encoding="ascii") as file_probe:
        file_probe.write("[\n")
        for value_address in probe_iter(count_limit):
            if 0 < count_written:
                file_probe.write(",\n")
            file_probe.write(f'    "{probe_format(value_address)}"')
            count_written += 1
        file_probe.write("\n]\n")
    return count_written


def probe_verify(
    path_probe: pathlib.Path, count_limit: int | None = None
) -> tuple[int, int, int]:
    """Verify a probe file; return (count, first, last) or raise ValueError."""
    count_read = 0
    value_previous = -1
    value_first = -1
    value_last = -1
    for value_address in probe_count_read(path_probe):
        if not probe_is_valid(value_address):
            raise ValueError(
                f"not a routable four-prime address: {probe_format(value_address)}"
            )
        if value_address <= value_previous:
            raise ValueError(f"address not ascending: {probe_format(value_address)}")
        if count_read == 0:
            value_first = value_address
        value_previous = value_address
        value_last = value_address
        count_read += 1
    if count_limit is not None:
        if count_read != count_limit:
            raise ValueError(f"expected {count_limit} addresses, found {count_read}")
    elif count_read != COUNT_PROBE_EXPECTED:
        raise ValueError(
            f"expected {COUNT_PROBE_EXPECTED} addresses, found {count_read}"
        )
    return count_read, value_first, value_last


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Generate or verify the ip_probe list (phase 1)."
    )
    parser_arguments.add_argument(
        "--output",
        type=pathlib.Path,
        default=PATH_OUTPUT_DEFAULT,
        help="probe file to write (default: dataflow.out/01_ip_probe.json)",
    )
    parser_arguments.add_argument(
        "--count-only",
        action="store_true",
        help="print the number of ip_probe addresses and write nothing",
    )
    parser_arguments.add_argument(
        "--first",
        type=int,
        default=None,
        metavar="COUNT",
        help="write or expect only the first COUNT addresses",
    )
    parser_arguments.add_argument(
        "--verify",
        type=pathlib.Path,
        default=None,
        metavar="FILE",
        help="verify a probe file instead of writing one",
    )
    parser_arguments.add_argument(
        "--refresh",
        action="store_true",
        help="write the file again even when it already exists",
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    if arguments_parsed.count_only:
        print(sum(1 for _ in probe_iter(arguments_parsed.first)))
        return 0

    if arguments_parsed.verify is not None:
        try:
            count_read, value_first, value_last = probe_verify(
                arguments_parsed.verify, arguments_parsed.first
            )
        except ValueError as error_verify:
            print(f"verify: FAIL: {error_verify}", file=sys.stderr)
            return 1
        print(
            f"verify: PASS count={count_read} "
            f"first={probe_format(value_first)} last={probe_format(value_last)}"
        )
        return 0

    # A work product that already exists is verified and kept, not rewritten:
    # the file is the result of the phase, and regenerating it costs the same
    # as checking it.
    if not arguments_parsed.refresh and arguments_parsed.output.is_file():
        try:
            count_read, value_first, value_last = probe_verify(
                arguments_parsed.output, arguments_parsed.first
            )
        except ValueError as error_reuse:
            print(f"reuse: {arguments_parsed.output} failed verification: {error_reuse}")
            print("reuse: regenerating")
        else:
            print(
                f"reuse: {arguments_parsed.output} count={count_read} "
                f"first={probe_format(value_first)} last={probe_format(value_last)}"
            )
            return 0

    count_written = probe_write(arguments_parsed.output, arguments_parsed.first)
    print(f"write: {arguments_parsed.output} count={count_written}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
