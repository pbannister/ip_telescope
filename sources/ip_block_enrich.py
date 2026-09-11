#!/usr/bin/env python3
#
# ip_block_enrich.py - phase 2 enrichment: add RIR RDAP metadata to blocks.
#
# The delegation files publish block boundaries and status. RDAP publishes
# the registry object behind a block: its handle, name, parent, type,
# country, organization, events, and remarks.
#
# For every block in <data>/02_ip_block.json this program asks the
# authoritative RDAP service for the block start address and stores the
# response verbatim under an "rdap" key, next to a small summary. Answers
# are cached in dataflow.out/raw/RDAP-CACHE.jsonl, so an interrupted or repeated run
# does not ask the registries twice.
#
# Usage:
#   python3 sources/ip_block_enrich.py
#   python3 sources/ip_block_enrich.py --limit 20 --rate 2
#   python3 sources/ip_block_enrich.py --refresh
#
"""Add RIR RDAP metadata to the collected address blocks (phase 2)."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent

URL_BOOTSTRAP = "https://data.iana.org/rdap/ipv4.json"
FILE_BOOTSTRAP = "RDAP-BOOTSTRAP-IPV4.json"
FILE_CACHE = "RDAP-CACHE.jsonl"

TEXT_USER_AGENT = "IP_telescope/0.1 (block enrichment; contact via project owner)"
COUNT_WORKER_DEFAULT = 8
VALUE_RATE_DEFAULT = 5.0
SECONDS_TIMEOUT_DEFAULT = 15.0
COUNT_RETRY = 3
SECONDS_RETRY_DEFAULT = 30.0
SECONDS_RETRY_MAX = 120.0
COUNT_PROGRESS = 500
COUNT_SERVICE_FAILURE = 3


class ServiceGate:
    """Stop asking a registry service that keeps failing.

    A registry endpoint can be unreachable while the others answer (AFRINIC
    was, on 2026-09-10). Without a gate, every block behind that service
    costs the full retry budget and the run stalls for hours. The blocks are
    recorded as unanswered instead, and a later run tries them again
    because an unanswered address is not treated as cached.
    """

    def __init__(self, count_limit: int) -> None:
        self.count_limit = count_limit
        self.lock = threading.Lock()
        self.dict_count: dict[str, int] = {}
        self.dict_reason: dict[str, str] = {}
        self.set_blocked: set[str] = set()

    def is_blocked(self, text_service: str) -> bool:
        """Return True when the service is closed."""
        with self.lock:
            return text_service in self.set_blocked

    def reason_get(self, text_service: str) -> str:
        """Return why the service was closed."""
        with self.lock:
            return self.dict_reason.get(text_service, "unknown")

    def record(self, text_service: str, flag_ok: bool, text_reason: str) -> None:
        """Record one outcome, closing the service after too many failures."""
        with self.lock:
            if flag_ok:
                self.dict_count.pop(text_service, None)
                return
            count_failure = self.dict_count.get(text_service, 0) + 1
            self.dict_count[text_service] = count_failure
            self.dict_reason[text_service] = text_reason
            if (
                self.count_limit <= count_failure
                and text_service not in self.set_blocked
            ):
                self.set_blocked.add(text_service)
                print(
                    f"enrich: service closed after {count_failure} failures "
                    f"({text_reason}): {text_service}"
                )


class RateLimiter:
    """Keep requests to a steady rate across threads."""

    def __init__(self, value_rate: float) -> None:
        self.seconds_interval = 0.0 if 0.0 >= value_rate else 1.0 / value_rate
        self.lock = threading.Lock()
        self.moment_next = 0.0

    def wait(self) -> None:
        """Block until the next request is allowed."""
        with self.lock:
            moment_now = time.monotonic()
            seconds_delay = max(0.0, self.moment_next - moment_now)
            self.moment_next = max(moment_now, self.moment_next) + self.seconds_interval
        if 0.0 < seconds_delay:
            time.sleep(seconds_delay)


def bootstrap_service_read(
    path_directory_raw: pathlib.Path,
) -> list[tuple[int, int, str]]:
    """Return (mask, network, service) from the IANA RDAP bootstrap."""
    path_file = path_directory_raw / FILE_BOOTSTRAP
    if not path_file.is_file():
        path_directory_raw.mkdir(parents=True, exist_ok=True)
        request_bootstrap = urllib.request.Request(
            URL_BOOTSTRAP, headers={"User-Agent": TEXT_USER_AGENT}
        )
        with urllib.request.urlopen(
            request_bootstrap, timeout=SECONDS_TIMEOUT_DEFAULT
        ) as response:
            path_file.write_bytes(response.read())
    with open(path_file, "r", encoding="utf-8") as file_bootstrap:
        document = json.load(file_bootstrap)
    list_service: list[tuple[int, int, str]] = []
    for list_prefix, list_url in document["services"]:
        for text_prefix in list_prefix:
            text_network, text_length = text_prefix.split("/")
            value_length = int(text_length)
            value_network = 0
            for text_octet in text_network.split("."):
                value_network = (value_network << 8) | int(text_octet)
            value_mask = ((1 << value_length) - 1) << (32 - value_length)
            list_service.append((value_mask, value_network & value_mask, list_url[0]))
    return list_service


def service_choose(
    value_address: int,
    list_service: list[tuple[int, int, str]],
    text_service_force: str | None,
) -> str | None:
    """Return the RDAP service for an address."""
    if text_service_force is not None:
        return text_service_force
    for value_mask, value_network, text_service in list_service:
        if value_address & value_mask == value_network:
            return text_service
    return None


def rdap_query(text_service: str, text_address: str, value_timeout: float) -> dict:
    """Return one RDAP answer as a cache record."""
    moment_now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    text_url = f"{text_service.rstrip('/')}/ip/{text_address}"
    record_answer = {
        "address": text_address,
        "service": text_service,
        "status": None,
        "fetched_at": moment_now,
        "document": None,
        "error": None,
        "retry_after": None,
    }
    request_rdap = urllib.request.Request(
        text_url,
        headers={"User-Agent": TEXT_USER_AGENT, "Accept": "application/rdap+json"},
    )
    try:
        with urllib.request.urlopen(
            request_rdap, timeout=value_timeout
        ) as response_rdap:
            record_answer["status"] = response_rdap.status
            record_answer["document"] = json.loads(response_rdap.read().decode("utf-8"))
    except urllib.error.HTTPError as error_http:
        record_answer["status"] = error_http.code
        record_answer["error"] = f"HTTPError: {error_http.code}"
        # A 429 or 503 carries the wait the registry wants; honor it.
        text_retry = (
            error_http.headers.get("Retry-After") if error_http.headers else None
        )
        if text_retry:
            try:
                record_answer["retry_after"] = float(text_retry)
            except ValueError:
                record_answer["retry_after"] = None
    except (urllib.error.URLError, TimeoutError, OSError) as error_url:
        record_answer["error"] = f"{type(error_url).__name__}: {error_url}"[:256]
    except json.JSONDecodeError as error_json:
        record_answer["error"] = f"JSONDecodeError: {error_json}"[:256]
    return record_answer


@dataclasses.dataclass(slots=True)
class EnrichOptions:
    """Everything one enrichment run needs."""

    path_directory_data: pathlib.Path
    path_directory_raw: pathlib.Path
    count_worker: int
    count_retry: int
    count_progress: int
    seconds_retry: float
    seconds_timeout: float
    value_rate: float
    count_limit: int | None
    flag_refresh: bool
    flag_retry_failed: bool
    flag_cache_only: bool
    text_service_force: str | None


def rdap_query_retry(
    text_service: str,
    text_address: str,
    options: EnrichOptions,
    limiter_rate: RateLimiter,
) -> dict:
    """Query RDAP, retrying a rate limit or a transport failure."""
    record_answer = {}
    count_try = 0
    while count_try < options.count_retry:
        count_try += 1
        limiter_rate.wait()
        record_answer = rdap_query(text_service, text_address, options.seconds_timeout)
        text_status = record_answer["status"]
        # A real answer is anything but a rate limit or a transport failure:
        # 404 means the registry holds no object for the address, which is
        # itself worth recording.
        if text_status not in (429, 503, None):
            return record_answer
        if count_try < options.count_retry:
            # The registry may state its own wait; a registry that is asked
            # too often answers 429 and means it.
            seconds_wait = record_answer.get("retry_after") or options.seconds_retry
            time.sleep(min(seconds_wait, SECONDS_RETRY_MAX))
    return record_answer


def rdap_query_gated(
    text_service: str,
    text_address: str,
    options: EnrichOptions,
    limiter_rate: RateLimiter,
    gate_service: ServiceGate,
) -> dict:
    """Query RDAP unless the service is closed, and report the outcome."""
    if gate_service.is_blocked(text_service):
        return {
            "address": text_address,
            "service": text_service,
            "status": None,
            "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "document": None,
            "error": f"service closed: {gate_service.reason_get(text_service)}",
        }
    record_answer = rdap_query_retry(text_service, text_address, options, limiter_rate)
    text_status = record_answer["status"]
    # A rate limit counts against the service: three in a row mean this run
    # should stop asking, and a later, slower run can try again. The blocks
    # are recorded without a status, so they are not treated as answered.
    if 429 == text_status or 503 == text_status:
        gate_service.record(text_service, False, f"rate limited with {text_status}")
    else:
        gate_service.record(text_service, text_status is not None, "no answer")
    return record_answer


def summary_read(document_rdap: dict | None) -> dict:
    """Return the few RDAP facts worth reading at a glance."""
    if not isinstance(document_rdap, dict):
        return {}
    dict_summary = {
        "handle": document_rdap.get("handle"),
        "name": document_rdap.get("name"),
        "type": document_rdap.get("type"),
        "parent_handle": document_rdap.get("parentHandle"),
        "start_address": document_rdap.get("startAddress"),
        "end_address": document_rdap.get("endAddress"),
        "country": document_rdap.get("country"),
        "organization": None,
        "event": {},
    }
    for dict_event in document_rdap.get("events", []):
        if isinstance(dict_event, dict) and dict_event.get("eventAction"):
            dict_summary["event"][dict_event["eventAction"]] = dict_event.get(
                "eventDate"
            )
    for dict_entity in document_rdap.get("entities", []):
        if not isinstance(dict_entity, dict):
            continue
        for text_role in dict_entity.get("roles", []):
            if text_role in ("registrant", "administrative", "technical"):
                dict_vcard = dict_entity.get("vcardArray")
                if isinstance(dict_vcard, list) and 2 <= len(dict_vcard):
                    for list_field in dict_vcard[1]:
                        if isinstance(list_field, list) and "fn" == list_field[0]:
                            dict_summary["organization"] = list_field[3]
                            return dict_summary
    return dict_summary


def cache_failure_read(path_directory_raw: pathlib.Path) -> dict[str, str]:
    """Return the last recorded failure reason per address.

    The cache keeps every attempt, including the ones that failed. When a work
    product is rebuilt in cache-only mode there is no new attempt to report, so
    the previous reason is carried forward rather than replaced with a blank.
    """
    path_file = path_directory_raw / FILE_CACHE
    dict_failure: dict[str, str] = {}
    if not path_file.is_file():
        return dict_failure
    with open(path_file, "r", encoding="utf-8") as file_cache:
        for text_line in file_cache:
            text_line = text_line.strip()
            if not text_line:
                continue
            try:
                record_answer = json.loads(text_line)
            except json.JSONDecodeError:
                continue
            if record_answer.get("status") is None and record_answer.get("error"):
                dict_failure[record_answer["address"]] = record_answer["error"]
    return dict_failure


def cache_read(path_directory_raw: pathlib.Path) -> dict[str, dict]:
    """Return the cached RDAP answers, keyed by address.

    Only records that carry a real answer count as cached. A record without
    a status is a transport failure, and a record with 429 or 503 is a rate
    limit; neither is an answer, so a later run tries that address again.
    """
    path_file = path_directory_raw / FILE_CACHE
    dict_cache: dict[str, dict] = {}
    if not path_file.is_file():
        return dict_cache
    with open(path_file, "r", encoding="utf-8") as file_cache:
        for text_line in file_cache:
            text_line = text_line.strip()
            if not text_line:
                continue
            try:
                record_answer = json.loads(text_line)
            except json.JSONDecodeError:
                continue
            if record_answer.get("status") in (None, 429, 503):
                dict_cache.pop(record_answer["address"], None)
                continue
            dict_cache[record_answer["address"]] = record_answer
    return dict_cache


def answer_map_build(
    list_address: list[str],
    list_service: list[tuple[int, int, str]],
    limiter_rate: RateLimiter,
    gate_service: ServiceGate,
    options: EnrichOptions,
    path_file_cache: pathlib.Path,
) -> dict[str, dict]:
    """Ask the registries about these addresses, or record the gap.

    Cache-only mode asks nothing: the answers are already known, and the point
    is to rebuild a work product's annotations without spending another round
    of registry queries. A block with no cached answer is recorded as
    unanswered, exactly as a failed query would have left it.
    """
    dict_new: dict[str, dict] = {}
    if options.flag_cache_only:
        dict_failure = cache_failure_read(options.path_directory_raw)
        for text_address in list_address:
            dict_new[text_address] = {
                "address": text_address,
                "service": service_choose(
                    address_value(text_address),
                    list_service,
                    options.text_service_force,
                ),
                "status": None,
                "fetched_at": None,
                "document": None,
                "error": "not asked this pass; last attempt: "
                + dict_failure.get(text_address, "no answer recorded"),
            }
        print(f"enrich: cache only; {len(dict_new)} block(s) left unanswered")
        return dict_new

    with open(path_file_cache, "a", encoding="utf-8") as file_cache:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=options.count_worker
        ) as executor_pool:
            dict_future = {}
            for text_address in list_address:
                text_service = service_choose(
                    address_value(text_address),
                    list_service,
                    options.text_service_force,
                )
                if text_service is None:
                    record_answer = {
                        "address": text_address,
                        "service": None,
                        "status": None,
                        "fetched_at": None,
                        "document": None,
                        "error": "no RDAP service for address",
                    }
                    dict_new[text_address] = record_answer
                    file_cache.write(json.dumps(record_answer, ensure_ascii=True) + "\n")
                    continue
                dict_future[
                    executor_pool.submit(
                        rdap_query_gated,
                        text_service,
                        text_address,
                        options,
                        limiter_rate,
                        gate_service,
                    )
                ] = text_address
            count_done = 0
            for future_query in concurrent.futures.as_completed(dict_future):
                record_answer = future_query.result()
                dict_new[record_answer["address"]] = record_answer
                file_cache.write(json.dumps(record_answer, ensure_ascii=True) + "\n")
                file_cache.flush()
                count_done += 1
                if 0 == count_done % options.count_progress:
                    print(f"enrich: queried {count_done}/{len(list_address)}")
    return dict_new


def enrich(options: EnrichOptions) -> dict[str, int]:
    """Add RDAP metadata to every block and return the answer counts."""
    path_block = options.path_directory_data / "02_ip_block.json"
    if not path_block.is_file():
        raise FileNotFoundError(f"missing block file: {path_block}")
    with open(path_block, "r", encoding="utf-8") as file_block:
        list_block = json.load(file_block)

    path_file_cache = options.path_directory_raw / FILE_CACHE
    list_service = (
        []
        if options.text_service_force
        else bootstrap_service_read(options.path_directory_raw)
    )
    dict_cache = {} if options.flag_refresh else cache_read(options.path_directory_raw)
    limiter_rate = RateLimiter(options.value_rate)
    gate_service = ServiceGate(COUNT_SERVICE_FAILURE)

    # Which blocks need attention:
    #   --refresh        every block, asking the registries again
    #   --retry-failed   blocks whose last answer was a failure or a rate limit
    #   default          only blocks that carry no RDAP record at all
    # A block already annotated is left alone, so a default run over finished
    # work asks nothing and writes nothing.
    list_target = []
    for document_block in list_block:
        document_rdap = document_block.get("rdap")
        if options.flag_refresh or document_rdap is None:
            list_target.append(document_block)
        elif options.flag_retry_failed and document_rdap.get("status") in (
            None,
            429,
            503,
        ):
            list_target.append(document_block)
    if options.count_limit is not None:
        list_target = list_target[: options.count_limit]
    list_address = [
        document_block["rir_record"]["start"]
        for document_block in list_target
        if document_block["rir_record"]["start"] not in dict_cache
    ]
    print(
        f"enrich: blocks={len(list_block)} cached={len(dict_cache)} "
        f"target={len(list_target)} query={len(list_address)}"
    )

    dict_new: dict[str, dict] = {}
    options.path_directory_raw.mkdir(parents=True, exist_ok=True)
    dict_new = answer_map_build(
        list_address, list_service, limiter_rate, gate_service, options, path_file_cache
    )

    dict_cache.update(dict_new)
    count_status: dict[str, int] = {}
    count_applied = 0
    count_changed = 0
    for document_block in list_block:
        text_address = document_block["rir_record"]["start"]
        record_answer = dict_cache.get(text_address)
        if record_answer is None:
            continue
        if "rdap" not in document_block:
            count_applied += 1
        document_rdap_new = {
            "query": text_address,
            "service": record_answer["service"],
            "status": record_answer["status"],
            "fetched_at": record_answer["fetched_at"],
            "error": record_answer["error"],
            "summary": summary_read(record_answer["document"]),
            "document": record_answer["document"],
        }
        if document_block.get("rdap") != document_rdap_new:
            count_changed += 1
        document_block["rdap"] = document_rdap_new
        text_key = str(record_answer["status"]) if record_answer["status"] else "error"
        count_status[text_key] = count_status.get(text_key, 0) + 1

    # Nothing was asked and nothing new was applied, so the block file already
    # holds this answer set. Rewriting 165 MB to change nothing is waste.
    if not options.flag_refresh and 0 == len(dict_new) and 0 == count_changed:
        return {
            "reuse": "yes",
            "block": len(list_block),
            "queried": 0,
            **count_status,
        }

    with open(path_block, "w", encoding="utf-8") as file_block:
        json.dump(list_block, file_block, indent=4, ensure_ascii=True)
        file_block.write("\n")

    dict_result = {
        "block": len(list_block),
        "queried": len(list_address),
        "applied": count_applied,
        "changed": count_changed,
        **count_status,
    }
    if gate_service.set_blocked:
        dict_result["service_closed"] = ",".join(sorted(gate_service.set_blocked))
    return dict_result


def address_value(text_address: str) -> int:
    """Return the integer value of a dotted-quad address."""
    value_address = 0
    for text_octet in text_address.split("."):
        value_address = (value_address << 8) | int(text_octet)
    return value_address


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Add RIR RDAP metadata to the collected address blocks (phase 2)."
    )
    parser_arguments.add_argument(
        "--data-directory",
        type=pathlib.Path,
        default=PATH_REPOSITORY_ROOT / "dataflow.out",
    )
    parser_arguments.add_argument(
        "--raw-directory",
        type=pathlib.Path,
        default=PATH_REPOSITORY_ROOT / "dataflow.out" / "raw",
    )
    parser_arguments.add_argument("--thread", type=int, default=COUNT_WORKER_DEFAULT)
    parser_arguments.add_argument("--rate", type=float, default=VALUE_RATE_DEFAULT)
    parser_arguments.add_argument(
        "--timeout", type=float, default=SECONDS_TIMEOUT_DEFAULT
    )
    parser_arguments.add_argument("--retry", type=int, default=COUNT_RETRY)
    parser_arguments.add_argument(
        "--retry-wait", type=float, default=SECONDS_RETRY_DEFAULT
    )
    parser_arguments.add_argument("--limit", type=int, default=None)
    parser_arguments.add_argument(
        "--service",
        default=None,
        help="RDAP base URL to use instead of the IANA bootstrap",
    )
    parser_arguments.add_argument(
        "--refresh",
        action="store_true",
        help="ignore the cache and query every block again",
    )
    parser_arguments.add_argument(
        "--retry-failed",
        action="store_true",
        help="ask again for blocks whose last answer was a failure or a rate limit",
    )
    parser_arguments.add_argument(
        "--cache-only",
        action="store_true",
        help="apply the cached answers and ask the registries nothing",
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    options = EnrichOptions(
        path_directory_data=arguments_parsed.data_directory,
        path_directory_raw=arguments_parsed.raw_directory,
        count_worker=arguments_parsed.thread,
        count_retry=arguments_parsed.retry,
        count_progress=COUNT_PROGRESS,
        seconds_retry=arguments_parsed.retry_wait,
        seconds_timeout=arguments_parsed.timeout,
        value_rate=arguments_parsed.rate,
        count_limit=arguments_parsed.limit,
        flag_refresh=arguments_parsed.refresh,
        flag_retry_failed=arguments_parsed.retry_failed,
        flag_cache_only=arguments_parsed.cache_only,
        text_service_force=arguments_parsed.service,
    )

    try:
        dict_count = enrich(options)
    except (FileNotFoundError, ValueError) as error_enrich:
        print(f"enrich: FAIL: {error_enrich}", file=sys.stderr)
        return 1

    for text_key, value_count in dict_count.items():
        print(f"enrich: {text_key}={value_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
