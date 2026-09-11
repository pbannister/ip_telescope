#!/usr/bin/env python3
#
# ip_probe_characterize.py - phase 4: gather the evidence that characterizes
# an anomalous ip_probe.
#
# Inputs:
#   <data>/05_ip_probe_http.json   the phase 3 observations; the anomalies are
#                                  the addresses that answered, refused, or
#                                  reset
#   <data>/02_ip_block.json        the blocks, for context and for controls
# Output:
#   <data>/06_ip_probe_characterize.json
#
# The pass probes each anomalous address and, in the same block, a sample of
# control addresses whose octets are not all prime. An incumbent service
# answers on every address in its range; a deliberate exercise answers only
# on the four-prime addresses. That comparison is the sharpest single test
# the project has.
#
# The battery for every address:
#   * HTTP  GET / with the address as Host
#   * HTTP  GET / with an unrelated Host        (catch-all test)
#   * HTTPS GET / with the peer certificate     (identity and consistency)
#   * the reverse DNS name                      (what the address claims)
#   * three TCP connect samples                 (latency, against geography)
#
# This pass records evidence. It does not record verdicts: the expected
# characterization is prompts/features/06-probe-characterization.md and
# documents/07-characterization-theory.md.
#
# Usage:
#   python3 sources/ip_probe_characterize.py
#   python3 sources/ip_probe_characterize.py --control-count 4 --limit 6
#   python3 sources/ip_probe_characterize.py --refresh
#
"""Characterize the anomalous ip_probe addresses (phase 4)."""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime
import hashlib
import http.client
import json
import pathlib
import socket
import ssl
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ip_probe_generate import OCTET_PRIME_SET, probe_format, probe_parse  # noqa: E402

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH_DATA_DEFAULT = PATH_REPOSITORY_ROOT / "dataflow.out"

OUTCOME_ANOMALY = ("http_response", "connect_refused", "connection_reset")

PORT_HTTP_DEFAULT = 80
PORT_HTTPS_DEFAULT = 443
COUNT_CONTROL_DEFAULT = 12
COUNT_ANOMALY_SAMPLE = 12
COUNT_THREAD_DEFAULT = 16
SECONDS_TIMEOUT_DEFAULT = 5.0
COUNT_LATENCY_SAMPLE = 3

TEXT_HOST_UNRELATED = "ip-telescope-probe.invalid"
TEXT_USER_AGENT = "IP_telescope/0.1 (probe characterization; contact via project owner)"

BITS_OCTET = 8
VALUE_OCTET_MAX = 255
COUNT_OCTET = 4

# Light-speed floors, for the "not local folk" hypothesis. A round trip
# cannot be faster than 2d/c, so a measured floor below the quantum rules a
# distance out. A floor that sits on the quantum is a candidate, and only a
# second vantage point can confirm it: a terrestrial server answers more
# slowly to a distant observer, while a lunar one does not care.
KM_PER_SECOND_LIGHT = 299792.458
KM_ALTITUDE_GEOSYNCHRONOUS = 35786.0
KM_DISTANCE_MOON_MEAN = 384400.0
VALUE_QUANTUM_LOW = 0.95
VALUE_QUANTUM_HIGH = 1.30
TEXT_QUANTUM_NONE = "none"
TEXT_QUANTUM_GEOSYNCHRONOUS = "geosynchronous_band"
TEXT_QUANTUM_MOON = "moon_band"


def observation_anomaly_read(path_observation: pathlib.Path) -> dict[str, dict]:
    """Return the phase 3 observations that are anomalies, keyed by address."""
    with open(path_observation, "r", encoding="utf-8") as file_observation:
        document_observation = json.load(file_observation)
    dict_anomaly: dict[str, dict] = {}
    for document_probe in document_observation.get("observations", []):
        if document_probe.get("outcome") in OUTCOME_ANOMALY:
            dict_anomaly[document_probe["address"]] = document_probe
    return dict_anomaly


def block_list_read(path_block: pathlib.Path) -> list[tuple[int, int, dict]]:
    """Return (start, end, document) for every block, sorted by start."""
    with open(path_block, "r", encoding="utf-8") as file_block:
        list_document = json.load(file_block)
    list_block: list[tuple[int, int, dict]] = []
    for document_block in list_document:
        value_start = probe_parse(document_block["rir_record"]["start"])
        value_end = probe_parse(document_block["derived"]["address_end"])
        list_block.append((value_start, value_end, document_block))
    list_block.sort(key=lambda item_block: item_block[0])
    return list_block


def block_find(list_block: list[tuple[int, int, dict]], value_address: int) -> dict | None:
    """Return the block that contains an address, or None."""
    for value_start, value_end, document_block in list_block:
        if value_start <= value_address <= value_end:
            return document_block
    return None


def octet_list_read(value_address: int) -> list[int]:
    """Return the four octets of an address."""
    return [
        (value_address >> shift) & VALUE_OCTET_MAX
        for shift in (24, 16, 8, 0)
    ]


def probe_is_four_prime(value_address: int) -> bool:
    """Return True when all four octets are prime."""
    return all(value_octet in OCTET_PRIME_SET for value_octet in octet_list_read(value_address))


def control_address_map(
    value_start: int,
    value_end: int,
    list_anomaly_value: list[int],
    count_control: int,
    count_anomaly_sample: int,
) -> dict[int, str]:
    """Return control addresses in a block, with the reason each was chosen.

    Two samples answer two different questions:

    * neighbours of the anomalous addresses, at several distances, answer
      "how far does this service extend around an address that answers?"; and
    * a sample spread across the block answers "does anything answer in the
      far parts of the block?".

    A control is never a four-prime address, because the whole point is to
    test the addresses the project would otherwise have ignored.
    """
    dict_control: dict[int, str] = {}

    def control_add(value_candidate: int, text_reason: str) -> None:
        if not (value_start <= value_candidate <= value_end):
            return
        if probe_is_four_prime(value_candidate):
            return
        dict_control.setdefault(value_candidate, text_reason)

    value_step = max(1, len(list_anomaly_value) // count_anomaly_sample)
    for value_anomaly in list_anomaly_value[::value_step]:
        for value_offset in (1, -1, 2, -2, 3, -3, 8, -8, 16, -16, 256, -256, 1024, -1024):
            control_add(value_anomaly + value_offset, f"neighbour{value_offset:+d}")

    value_size = value_end - value_start + 1
    for index_control in range(count_control):
        value_candidate = value_start + int(
            (index_control / max(1, count_control)) * (value_size - 1)
        )
        control_add(value_candidate, "spread")
    return dict_control


def http_read(
    text_address: str,
    value_port: int,
    text_host: str | None,
    value_timeout: float,
    flag_tls: bool,
    flag_verify: bool = True,
) -> dict:
    """Return the answer to one HTTP or HTTPS request."""
    document_answer = {
        "host": text_host or text_address,
        "scheme": "https" if flag_tls else "http",
        "outcome": None,
        "http_status": None,
        "header": {},
        "body_bytes": 0,
        "body_sha256": None,
        "body_prefix": None,
        "elapsed_ms": 0,
        "error": None,
        "certificate": None,
    }
    moment_start = time.monotonic()
    connection_target = None
    try:
        if flag_tls:
            context_tls = (
                ssl.create_default_context()
                if flag_verify
                else ssl._create_unverified_context()  # noqa: SLF001 - deliberate
            )
            connection_target = http.client.HTTPSConnection(
                text_address, value_port, timeout=value_timeout, context=context_tls
            )
        else:
            connection_target = http.client.HTTPConnection(
                text_address, value_port, timeout=value_timeout
            )
        dict_header = {"User-Agent": TEXT_USER_AGENT}
        if text_host is not None:
            dict_header["Host"] = text_host
        # Connect first, so the certificate is captured even when the request
        # that follows fails: the certificate is evidence on its own.
        connection_target.connect()
        if flag_tls and connection_target.sock is not None:
            document_answer["certificate"] = certificate_read(
                connection_target.sock, flag_verify
            )
        connection_target.request("GET", "/", headers=dict_header)
        response_target = connection_target.getresponse()
        bytes_body = response_target.read(65536)
        bytes_extra = response_target.read(1)
        document_answer["outcome"] = "http_response"
        document_answer["http_status"] = response_target.status
        document_answer["header"] = {
            text_name.lower(): text_value
            for text_name, text_value in response_target.getheaders()
        }
        document_answer["body_bytes"] = len(bytes_body) + len(bytes_extra)
        document_answer["body_sha256"] = hashlib.sha256(bytes_body).hexdigest()
        document_answer["body_prefix"] = bytes_body.decode("utf-8", errors="replace")[:256]
    except ssl.SSLCertVerificationError as error_tls:
        document_answer["outcome"] = "certificate_unverified"
        document_answer["error"] = f"{type(error_tls).__name__}: {error_tls}"[:256]
        if flag_verify:
            # Ask again without verification: an unverifiable certificate is
            # evidence, and so is the answer behind it.
            document_second = http_read(
                text_address, value_port, text_host, value_timeout, flag_tls, False
            )
            document_answer["certificate"] = document_second.get("certificate")
            if document_second.get("http_status") is not None:
                for text_key in ("http_status", "header", "body_bytes", "body_sha256", "body_prefix"):
                    document_answer[text_key] = document_second[text_key]
    except ssl.SSLError as error_ssl:
        document_answer["outcome"] = "tls_error"
        document_answer["error"] = f"{type(error_ssl).__name__}: {error_ssl}"[:256]
    except (socket.timeout, TimeoutError):
        document_answer["outcome"] = "timeout"
        document_answer["error"] = "timed out"
    except ConnectionRefusedError:
        document_answer["outcome"] = "connect_refused"
        document_answer["error"] = "connection refused"
    except ConnectionResetError:
        document_answer["outcome"] = "connection_reset"
        document_answer["error"] = "connection reset"
    except http.client.HTTPException as error_protocol:
        document_answer["outcome"] = "protocol_error"
        document_answer["error"] = f"{type(error_protocol).__name__}: {error_protocol}"[:256]
    except OSError as error_socket:
        document_answer["outcome"] = "error"
        document_answer["error"] = f"{type(error_socket).__name__}: {error_socket}"[:256]
    finally:
        if connection_target is not None:
            try:
                connection_target.close()
            except Exception:  # noqa: BLE001 - closing must not mask the result
                pass
    document_answer["elapsed_ms"] = int(1000 * (time.monotonic() - moment_start))
    return document_answer


def certificate_read(socket_tls: ssl.SSLSocket, flag_verify: bool) -> dict:
    """Return the peer certificate as fields, or as little as can be read."""
    document_certificate: dict = {
        "verified": flag_verify,
        "subject": None,
        "issuer": None,
        "not_before": None,
        "not_after": None,
        "subject_alt_name": [],
        "sha256": None,
        "self_signed": None,
        "covers_ip": None,
    }
    bytes_der = None
    try:
        bytes_der = socket_tls.getpeercert(binary_form=True)
    except Exception:  # noqa: BLE001 - some sockets cannot report the chain
        bytes_der = None
    if bytes_der:
        document_certificate["sha256"] = hashlib.sha256(bytes_der).hexdigest()
    dict_decoded = {}
    try:
        dict_decoded = socket_tls.getpeercert() or {}
    except Exception:  # noqa: BLE001 - unverified contexts return nothing here
        dict_decoded = {}
    if not dict_decoded and bytes_der:
        dict_decoded = certificate_decode(bytes_der)
    if dict_decoded:
        tuple_subject = tuple(
            item_field for item_relative in dict_decoded.get("subject", ()) for item_field in item_relative
        )
        tuple_issuer = tuple(
            item_field for item_relative in dict_decoded.get("issuer", ()) for item_field in item_relative
        )
        document_certificate["subject"] = [
            {"name": list(item_field)[0], "value": list(item_field)[1]} for item_field in tuple_subject
        ]
        document_certificate["issuer"] = [
            {"name": list(item_field)[0], "value": list(item_field)[1]} for item_field in tuple_issuer
        ]
        document_certificate["not_before"] = dict_decoded.get("notBefore")
        document_certificate["not_after"] = dict_decoded.get("notAfter")
        document_certificate["subject_alt_name"] = [
            {"type": item_name[0], "value": item_name[1]}
            for item_name in dict_decoded.get("subjectAltName", ())
        ]
        document_certificate["self_signed"] = tuple_subject == tuple_issuer
    return document_certificate


def certificate_decode(bytes_der: bytes) -> dict:
    """Decode a DER certificate with the standard library, when it can."""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=True) as file_pem:
            file_pem.write(ssl.DER_cert_to_PEM_cert(bytes_der))
            file_pem.flush()
            return ssl._ssl._test_decode_cert(file_pem.name)  # noqa: SLF001 - only decoder in the standard library
    except Exception:  # noqa: BLE001 - a certificate that will not decode is still evidence
        return {}


def ptr_read(text_address: str, seconds_timeout: float) -> dict:
    """Return the reverse DNS name of an address, using dig."""
    document_ptr = {"name": None, "names": [], "error": None}
    try:
        result_ptr = subprocess.run(
            ["dig", "+short", "-x", text_address],
            capture_output=True,
            text=True,
            timeout=seconds_timeout,
        )
    except FileNotFoundError:
        document_ptr["error"] = "dig not available"
        return document_ptr
    except subprocess.TimeoutExpired:
        document_ptr["error"] = "dig timed out"
        return document_ptr
    list_name = [
        text_line.strip().rstrip(".")
        for text_line in result_ptr.stdout.splitlines()
        if text_line.strip() and not text_line.startswith(";")
    ]
    document_ptr["names"] = list_name
    document_ptr["name"] = list_name[0] if list_name else None
    return document_ptr


def latency_read(
    text_address: str, value_port: int, value_timeout: float
) -> dict:
    """Return TCP connect samples in milliseconds, and their light-speed band.

    A refused connection is a round trip too, and is recorded as one: the
    measurement is the network, not the service.

    The measurement is one round trip, not a request. A full HTTP exchange
    costs two round trips, so a responder at lunar distance would take about
    5.1 seconds to answer a GET and only 2.6 seconds to complete a connect.
    Reaching past the timeout is indistinguishable from a blackhole, which is
    why the timeout is recorded as the blind spot it is.
    """
    document_latency = {
        "sample_ms": [],
        "ms_min": None,
        "ms_median": None,
        "ms_jitter": None,
        "connected": False,
        "quantum": TEXT_QUANTUM_NONE,
        "ms_floor_geosynchronous": round(
            2000.0 * KM_ALTITUDE_GEOSYNCHRONOUS / KM_PER_SECOND_LIGHT, 1
        ),
        "ms_floor_moon": round(
            2000.0 * KM_DISTANCE_MOON_MEAN / KM_PER_SECOND_LIGHT, 1
        ),
    }
    for _ in range(COUNT_LATENCY_SAMPLE):
        moment_start = time.monotonic()
        try:
            with socket.create_connection((text_address, value_port), timeout=value_timeout):
                document_latency["connected"] = True
        except OSError:
            pass
        document_latency["sample_ms"].append(int(1000 * (time.monotonic() - moment_start)))
    list_sample = sorted(document_latency["sample_ms"])
    if list_sample:
        document_latency["ms_min"] = list_sample[0]
        document_latency["ms_median"] = list_sample[len(list_sample) // 2]
        document_latency["ms_jitter"] = list_sample[-1] - list_sample[0]
        document_latency["quantum"] = latency_quantum_read(list_sample[0])
    return document_latency


def latency_quantum_read(value_min_ms: int) -> str:
    """Name the light-speed band a measured floor falls in, if any.

    The minimum of several samples estimates the propagation floor, because
    jitter only ever adds. A band hit is a candidate for the distance, not
    evidence of it: ordinary long-haul terrestrial paths also sit in the
    geosynchronous band.
    """
    for text_name, value_floor in (
        (TEXT_QUANTUM_GEOSYNCHRONOUS, 2000.0 * KM_ALTITUDE_GEOSYNCHRONOUS / KM_PER_SECOND_LIGHT),
        (TEXT_QUANTUM_MOON, 2000.0 * KM_DISTANCE_MOON_MEAN / KM_PER_SECOND_LIGHT),
    ):
        if value_floor * VALUE_QUANTUM_LOW <= value_min_ms <= value_floor * VALUE_QUANTUM_HIGH:
            return text_name
    return TEXT_QUANTUM_NONE


def address_probe(text_address: str, options: "CharacterizeOptions") -> dict:
    """Run the battery against one address."""
    value_address = probe_parse(text_address)
    document_answer = http_read(
        text_address, options.http_port, None, options.seconds_timeout, False
    )
    document_other = http_read(
        text_address, options.http_port, TEXT_HOST_UNRELATED, options.seconds_timeout, False
    )
    document_secure = http_read(
        text_address, options.https_port, None, options.seconds_timeout, True
    )
    document_observation = {
        "address": text_address,
        "is_probe": probe_is_four_prime(value_address),
        "octet": octet_list_read(value_address),
        "http": document_answer,
        "http_host_other": document_other,
        "https": document_secure,
        "ptr": ptr_read(text_address, options.seconds_timeout),
        "latency": latency_read(text_address, options.http_port, options.seconds_timeout),
    }
    document_observation["signal"] = signal_build(document_observation)
    return document_observation


def signal_build(document_observation: dict) -> dict:
    """Return the objective signals a verdict may rest on."""
    document_http = document_observation["http"]
    document_other = document_observation["http_host_other"]
    document_secure = document_observation["https"]
    document_certificate = document_secure.get("certificate") or {}
    return {
        "answers_http": None is not document_http["http_status"],
        "answers_https": None is not document_secure["http_status"],
        "catch_all": bool(
            None is not document_http["body_sha256"]
            and document_http["body_sha256"] == document_other["body_sha256"]
        ),
        "host_aware": bool(
            None is not document_other["outcome"]
            and document_other["outcome"] != document_http["outcome"]
        ),
        "refused": "connect_refused" == document_http["outcome"],
        "reset": "connection_reset" == document_http["outcome"],
        "certificate_present": bool(document_certificate.get("sha256")),
        "certificate_verified": document_certificate.get("verified"),
        "certificate_self_signed": document_certificate.get("self_signed"),
        "certificate_covers_ip": certificate_covers_ip(
            document_certificate, document_observation["address"]
        ),
        "ptr_present": None is not document_observation["ptr"]["name"],
        "latency_quantum": document_observation["latency"].get("quantum"),
        "latency_ms_min": document_observation["latency"].get("ms_min"),
        "latency_ms_jitter": document_observation["latency"].get("ms_jitter"),
    }


def certificate_covers_ip(document_certificate: dict, text_address: str) -> bool | None:
    """Return whether the certificate names the address."""
    list_alt = document_certificate.get("subject_alt_name")
    if not list_alt:
        return None
    for dict_name in list_alt:
        if text_address == dict_name.get("value"):
            return True
    return False


def characterize(options: "CharacterizeOptions") -> dict:
    """Run the pass and write the result file."""
    path_observation = options.path_data / "05_ip_probe_http.json"
    path_block = options.path_data / "02_ip_block.json"
    path_output = options.path_data / "06_ip_probe_characterize.json"
    for path_required in (path_observation, path_block):
        if not path_required.is_file():
            raise FileNotFoundError(f"missing input file: {path_required}")

    if not options.flag_refresh and path_output.is_file():
        with open(path_output, "r", encoding="utf-8") as file_output:
            document_reuse = json.load(file_output)
        return {
            "reuse": "yes",
            "observed_at": document_reuse.get("observed_at"),
            "observation": len(document_reuse.get("observations", [])),
        }

    dict_anomaly = observation_anomaly_read(path_observation)
    list_block = block_list_read(path_block)

    # Group the anomalies by block, then add controls from the same blocks.
    dict_block_anomaly: dict[str, list[str]] = collections.OrderedDict()
    dict_address_block: dict[str, dict] = {}
    for text_address in sorted(dict_anomaly, key=probe_parse):
        document_block = block_find(list_block, probe_parse(text_address))
        if document_block is None:
            continue
        text_uuid = document_block["block_uuid"]
        dict_block_anomaly.setdefault(text_uuid, []).append(text_address)
        dict_address_block[text_address] = document_block

    list_target: list[str] = []
    dict_role_of: dict[str, str] = {}
    for text_uuid, list_address_anomaly in dict_block_anomaly.items():
        for text_address in list_address_anomaly:
            list_target.append(text_address)
            dict_role_of[text_address] = "anomaly"
        document_block = dict_address_block[list_address_anomaly[0]]
        value_start = probe_parse(document_block["rir_record"]["start"])
        value_end = probe_parse(document_block["derived"]["address_end"])
        dict_control = control_address_map(
            value_start,
            value_end,
            [probe_parse(text_address) for text_address in list_address_anomaly],
            options.count_control,
            COUNT_ANOMALY_SAMPLE,
        )
        for value_control, text_reason in sorted(dict_control.items()):
            text_control = probe_format(value_control)
            if text_control in dict_role_of:
                continue
            dict_role_of[text_control] = f"control:{text_reason}"
            list_target.append(text_control)

    if options.count_limit is not None:
        list_target = list_target[: options.count_limit]

    print(f"characterize: anomaly={len(dict_anomaly)} target={len(list_target)}")
    moment_start = datetime.datetime.now(datetime.timezone.utc)
    list_observation: list[dict | None] = [None] * len(list_target)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=options.count_thread
    ) as executor_pool:
        dict_future = {
            executor_pool.submit(address_probe, text_address, options): index_target
            for index_target, text_address in enumerate(list_target)
        }
        count_done = 0
        for future_probe in concurrent.futures.as_completed(dict_future):
            index_target = dict_future[future_probe]
            document_result = future_probe.result()
            text_address = document_result["address"]
            document_block = dict_address_block.get(text_address) or block_find(
                list_block, probe_parse(text_address)
            )
            document_result["block_uuid"] = (
                document_block["block_uuid"] if document_block else None
            )
            document_result["phase3_outcome"] = (
                dict_anomaly.get(text_address, {}).get("outcome")
            )
            document_result["role"] = dict_role_of.get(text_address, "control")
            list_observation[index_target] = document_result
            count_done += 1
            if 0 == count_done % 20:
                print(f"characterize: probed {count_done}/{len(list_target)}")

    list_written = [item for item in list_observation if item is not None]
    list_block_document = []
    for text_uuid in dict_block_anomaly:
        document_block = dict_address_block[dict_block_anomaly[text_uuid][0]]
        document_rdap = document_block.get("rdap") or {}
        list_block_document.append(
            {
                "block_uuid": text_uuid,
                "registry": document_block["rir_record"]["registry"],
                "status": document_block["rir_record"]["status"],
                "start": document_block["rir_record"]["start"],
                "end": document_block["derived"]["address_end"],
                "size": document_block["rir_record"]["value"],
                "probe_count": document_block["probe_count"],
                "anomaly_count": len(dict_block_anomaly[text_uuid]),
                "rdap": {
                    "status": document_rdap.get("status"),
                    "handle": (document_rdap.get("summary") or {}).get("handle"),
                    "name": (document_rdap.get("summary") or {}).get("name"),
                    "organization": (document_rdap.get("summary") or {}).get("organization"),
                    "parent_handle": (document_rdap.get("summary") or {}).get("parent_handle"),
                },
            }
        )

    document_output = {
        "observed_at": moment_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parameters": {
            "http_port": options.http_port,
            "https_port": options.https_port,
            "control_count": options.count_control,
            "thread": options.count_thread,
            "timeout_seconds": options.seconds_timeout,
            "target_count": len(list_target),
            "limit": options.count_limit,
            "host_unrelated": TEXT_HOST_UNRELATED,
            "ms_floor_geosynchronous": round(
                2000.0 * KM_ALTITUDE_GEOSYNCHRONOUS / KM_PER_SECOND_LIGHT, 1
            ),
            "ms_floor_moon": round(
                2000.0 * KM_DISTANCE_MOON_MEAN / KM_PER_SECOND_LIGHT, 1
            ),
            "blind_spot_seconds": options.seconds_timeout,
        },
        "blocks": list_block_document,
        "observations": list_written,
    }
    with open(path_output, "w", encoding="utf-8") as file_output:
        json.dump(document_output, file_output, indent=4, ensure_ascii=True)
        file_output.write("\n")

    return {
        "anomaly": len(dict_anomaly),
        "target": len(list_target),
        "control": sum(
            1 for item in list_written if item["role"].startswith("control")
        ),
        "answered_http": sum(1 for item in list_written if item["signal"]["answers_http"]),
        "catch_all": sum(1 for item in list_written if item["signal"]["catch_all"]),
        "observed": len(list_written),
    }


class CharacterizeOptions:
    """Everything one characterization pass needs."""

    def __init__(
        self,
        path_data: pathlib.Path,
        count_control: int,
        count_thread: int,
        seconds_timeout: float,
        http_port: int,
        https_port: int,
        count_limit: int | None,
        flag_refresh: bool,
    ) -> None:
        self.path_data = path_data
        self.count_control = count_control
        self.count_thread = count_thread
        self.seconds_timeout = seconds_timeout
        self.http_port = http_port
        self.https_port = https_port
        self.count_limit = count_limit
        self.flag_refresh = flag_refresh


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Characterize the anomalous ip_probe addresses (phase 4)."
    )
    parser_arguments.add_argument(
        "--data-directory",
        type=pathlib.Path,
        default=PATH_DATA_DEFAULT,
        help="directory holding the phase 3 observations and receiving the characterization",
    )
    parser_arguments.add_argument(
        "--control-count",
        type=int,
        default=COUNT_CONTROL_DEFAULT,
        help="non-prime control addresses sampled from each block holding an anomaly",
    )
    parser_arguments.add_argument("--thread", type=int, default=COUNT_THREAD_DEFAULT)
    parser_arguments.add_argument(
        "--timeout", type=float, default=SECONDS_TIMEOUT_DEFAULT
    )
    parser_arguments.add_argument("--http-port", type=int, default=PORT_HTTP_DEFAULT)
    parser_arguments.add_argument("--https-port", type=int, default=PORT_HTTPS_DEFAULT)
    parser_arguments.add_argument("--limit", type=int, default=None)
    parser_arguments.add_argument(
        "--refresh",
        action="store_true",
        help="characterize again even when the result file already exists",
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    options = CharacterizeOptions(
        path_data=arguments_parsed.data_directory,
        count_control=arguments_parsed.control_count,
        count_thread=arguments_parsed.thread,
        seconds_timeout=arguments_parsed.timeout,
        http_port=arguments_parsed.http_port,
        https_port=arguments_parsed.https_port,
        count_limit=arguments_parsed.limit,
        flag_refresh=arguments_parsed.refresh,
    )

    try:
        dict_count = characterize(options)
    except (FileNotFoundError, ValueError) as error_characterize:
        print(f"characterize: FAIL: {error_characterize}", file=sys.stderr)
        return 1

    for text_key, value_count in dict_count.items():
        print(f"characterize: {text_key}={value_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
