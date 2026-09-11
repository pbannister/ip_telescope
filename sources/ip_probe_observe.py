#!/usr/bin/env python3
#
# ip_probe_observe.py - phase 3: HTTP GET every ip_probe that no operator holds.
#
# Input:
#   <data>/04_ip_probe.json
#       The probes that are not inside an operator-held RIR block: the
#       addresses where no ordinary service should answer at all.
# Output:
#   <data>/05_ip_probe_http.json
#       Run parameters, outcome counts, and one observation per address.
#
# An observation records the outcome class, the HTTP status when there was
# one, the response headers, a digest of the response body, and the elapsed
# time. The body itself is not kept; only its length, digest, and a short
# prefix, so that a surprising answer is visible without storing payloads.
#
# Usage:
#   python3 sources/ip_probe_observe.py --limit 100
#   python3 sources/ip_probe_observe.py --thread 128 --timeout 3
#
"""Observe the unassigned ip_probe addresses over HTTP (phase 3)."""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime
import errno
import hashlib
import http.client
import json
import pathlib
import socket
import sys
import time

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent

PORT_DEFAULT = 80
COUNT_THREAD_DEFAULT = 64
SECONDS_TIMEOUT_DEFAULT = 3.0
COUNT_BODY_LIMIT = 65536
COUNT_PREFIX_LIMIT = 256

TEXT_USER_AGENT = "IP_telescope/0.1 (probe observation; contact via project owner)"

OUTCOME_RESPONSE = "http_response"
OUTCOME_REFUSED = "connect_refused"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_UNREACHABLE_NETWORK = "network_unreachable"
OUTCOME_UNREACHABLE_HOST = "host_unreachable"
OUTCOME_RESET = "connection_reset"
OUTCOME_PROTOCOL = "protocol_error"
OUTCOME_OTHER = "error"

HEADER_KEEP = ("server", "content-type", "content-length", "location", "date", "via")


def observation_outcome(error_probe: BaseException) -> str:
    """Classify a failure into an outcome name."""
    if isinstance(error_probe, (socket.timeout, TimeoutError)):
        return OUTCOME_TIMEOUT
    if isinstance(error_probe, ConnectionRefusedError):
        return OUTCOME_REFUSED
    if isinstance(error_probe, ConnectionResetError):
        return OUTCOME_RESET
    if isinstance(error_probe, http.client.HTTPException):
        return OUTCOME_PROTOCOL
    if isinstance(error_probe, OSError):
        if errno.ENETUNREACH == error_probe.errno:
            return OUTCOME_UNREACHABLE_NETWORK
        if errno.EHOSTUNREACH == error_probe.errno:
            return OUTCOME_UNREACHABLE_HOST
        if errno.ETIMEDOUT == error_probe.errno:
            return OUTCOME_TIMEOUT
        if errno.ECONNREFUSED == error_probe.errno:
            return OUTCOME_REFUSED
        if errno.ECONNRESET == error_probe.errno:
            return OUTCOME_RESET
    return OUTCOME_OTHER


def observation_probe(text_address: str, value_port: int, value_timeout: float) -> dict:
    """Return the observation document for one address."""
    moment_start = time.monotonic()
    document_observation = {
        "address": text_address,
        "outcome": OUTCOME_OTHER,
        "http_status": None,
        "header": {},
        "body_bytes": 0,
        "body_sha256": None,
        "body_prefix": None,
        "body_truncated": False,
        "elapsed_ms": 0,
        "error": None,
    }
    connection_probe = None
    try:
        connection_probe = http.client.HTTPConnection(
            text_address, value_port, timeout=value_timeout
        )
        connection_probe.request("GET", "/", headers={"User-Agent": TEXT_USER_AGENT})
        response_probe = connection_probe.getresponse()
        bytes_body = response_probe.read(COUNT_BODY_LIMIT)
        bytes_extra = response_probe.read(1)
        text_body = bytes_body.decode("utf-8", errors="replace")
        document_observation["outcome"] = OUTCOME_RESPONSE
        document_observation["http_status"] = response_probe.status
        document_observation["header"] = {
            text_name.lower(): text_value
            for text_name, text_value in response_probe.getheaders()
            if text_name.lower() in HEADER_KEEP
        }
        document_observation["body_bytes"] = len(bytes_body) + len(bytes_extra)
        document_observation["body_sha256"] = hashlib.sha256(bytes_body).hexdigest()
        document_observation["body_prefix"] = text_body[:COUNT_PREFIX_LIMIT]
        document_observation["body_truncated"] = 0 < len(bytes_extra)
    except BaseException as error_probe:  # noqa: BLE001 - every failure is data
        document_observation["outcome"] = observation_outcome(error_probe)
        document_observation["error"] = f"{type(error_probe).__name__}: {error_probe}"[
            :256
        ]
    finally:
        if connection_probe is not None:
            try:
                connection_probe.close()
            except Exception:  # noqa: BLE001 - closing must not mask the result
                pass
    document_observation["elapsed_ms"] = int(1000 * (time.monotonic() - moment_start))
    return document_observation


def address_list_read(path_probe: pathlib.Path, count_limit: int | None) -> list[str]:
    """Return the target addresses, ascending, at most count_limit of them."""
    list_address: list[str] = []
    with open(path_probe, "r", encoding="ascii") as file_probe:
        for text_line in file_probe:
            text_item = text_line.strip().rstrip(",").strip().strip('"')
            if not text_item or text_item in ("[", "]"):
                continue
            list_address.append(text_item)
            if count_limit is not None and count_limit <= len(list_address):
                break
    return list_address


def observe(
    path_probe: pathlib.Path,
    path_output: pathlib.Path,
    value_port: int,
    count_thread: int,
    value_timeout: float,
    count_limit: int | None,
) -> dict:
    """Probe every target and write the observation document."""
    list_address = address_list_read(path_probe, count_limit)
    moment_start = datetime.datetime.now(datetime.timezone.utc)
    list_observation: list[dict | None] = [None] * len(list_address)
    flag_interrupted = False

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=count_thread
    ) as executor_pool:
        dict_future: dict[concurrent.futures.Future, int] = {
            executor_pool.submit(
                observation_probe, text_address, value_port, value_timeout
            ): index
            for index, text_address in enumerate(list_address)
        }
        try:
            for future_probe in concurrent.futures.as_completed(dict_future):
                index_probe = dict_future[future_probe]
                list_observation[index_probe] = future_probe.result()
        except KeyboardInterrupt:
            flag_interrupted = True
            for future_probe in dict_future:
                future_probe.cancel()
            executor_pool.shutdown(wait=False, cancel_futures=True)

    list_written = [item for item in list_observation if item is not None]
    count_outcome = collections.Counter(item["outcome"] for item in list_written)
    document_output = {
        "observed_at": moment_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parameters": {
            "port": value_port,
            "thread": count_thread,
            "timeout_seconds": value_timeout,
            "target_count": len(list_address),
            "limit": count_limit,
            "interrupted": flag_interrupted,
        },
        "counts": dict(sorted(count_outcome.items())),
        "observations": list_written,
    }
    path_output.parent.mkdir(parents=True, exist_ok=True)
    with open(path_output, "w", encoding="utf-8") as file_output:
        json.dump(document_output, file_output, indent=4, ensure_ascii=True)
        file_output.write("\n")
    return {
        "target": len(list_address),
        "observed": len(list_written),
        **{
            f"outcome_{text_key}": value_count
            for text_key, value_count in count_outcome.items()
        },
    }


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Observe unassigned ip_probe addresses over HTTP (phase 3)."
    )
    parser_arguments.add_argument(
        "--data-directory",
        type=pathlib.Path,
        default=PATH_REPOSITORY_ROOT / "data",
        help="directory holding 04_ip_probe.json and receiving 05_ip_probe_http.json",
    )
    parser_arguments.add_argument(
        "--probe-file",
        type=pathlib.Path,
        default=None,
        help="target address file (default: <data-directory>/04_ip_probe.json)",
    )
    parser_arguments.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="observation file (default: <data-directory>/05_ip_probe_http.json)",
    )
    parser_arguments.add_argument("--port", type=int, default=PORT_DEFAULT)
    parser_arguments.add_argument("--thread", type=int, default=COUNT_THREAD_DEFAULT)
    parser_arguments.add_argument(
        "--timeout", type=float, default=SECONDS_TIMEOUT_DEFAULT
    )
    parser_arguments.add_argument(
        "--limit", type=int, default=None, help="observe at most this many targets"
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    path_probe = (
        arguments_parsed.probe_file
        or arguments_parsed.data_directory / "04_ip_probe.json"
    )
    path_output = (
        arguments_parsed.output
        or arguments_parsed.data_directory / "05_ip_probe_http.json"
    )
    if not path_probe.is_file():
        print(f"observe: FAIL: missing target file: {path_probe}", file=sys.stderr)
        return 1

    dict_count = observe(
        path_probe,
        path_output,
        arguments_parsed.port,
        arguments_parsed.thread,
        arguments_parsed.timeout,
        arguments_parsed.limit,
    )
    for text_key, value_count in dict_count.items():
        print(f"observe: {text_key}={value_count}")
    print(f"observe: wrote {path_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
