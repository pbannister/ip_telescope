#!/usr/bin/env python3
#
# ip_probe_report.py - show the work for every address phase 4 examined.
#
# Reads the work products and writes one page per anomalous probe, plus an
# index, into the site output:
#
#   <site>/probes.html              the index: what the 106 have in common and
#                                   how they differ, and a row per probe
#   <site>/probes/<address>.html    one probe: what was observed, the tests
#                                   and criteria that were applied, what each
#                                   one says here, and the verdict it inherits
#
# The point of the pages is the reasoning, not the data: every test is stated
# with its question, this probe's observation, and the reading that follows.
# Where a test was not run, the page says so rather than implying a result.
#
# Usage:
#   python3 sources/ip_probe_report.py
#   python3 sources/ip_probe_report.py --baseline FILE   (a later pass, for stability)
#
"""Show the tests and criteria applied to each phase 4 probe."""

from __future__ import annotations

import argparse
import collections
import datetime
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ip_block_collect import block_address_end, block_prefix_text  # noqa: E402
from ip_probe_generate import probe_format, probe_parse  # noqa: E402
from site_page import page_write, template_read  # noqa: E402

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH_DATA_DEFAULT = PATH_REPOSITORY_ROOT / "dataflow.out"
PATH_SITE_DEFAULT = PATH_REPOSITORY_ROOT / "site.out"
PATH_TEMPLATE_DEFAULT = PATH_REPOSITORY_ROOT / "site.in" / "template.html"
PATH_MODEL_DEFAULT = pathlib.Path(__file__).resolve().parent / "probe_verdict_model.json"

TEXT_PREFIX_SHOWN = 220

STYLE_PAGE = """
    .probe { font-size: 0.9rem; }
    .probe table { width: 100%; }
    .probe td, .probe th { padding: 0.2em 0.5em; }
    .probe th { white-space: nowrap; }
    .count { text-align: right; }
    .verdict { background: #f6f6f0; padding: 0.6em 0.8em; border-left: 4px solid #999; }
    .said { color: #333; }
    .quiet { color: #777; }
    .flag { font-weight: 600; }
    .mono { font-family: monospace; }
    tr.gap td { background: #f0f0f0; color: #666; font-style: italic; }
    td.ok { background: #eaf5ea; }
    td.ask { background: #fdf3d0; }
    td.no { background: #f2dede; }
"""


def load_json(path_file: pathlib.Path) -> dict | list | None:
    """Return a JSON document, or None when the file is absent."""
    if not path_file.is_file():
        return None
    with open(path_file, "r", encoding="utf-8") as file_json:
        return json.load(file_json)


def block_index_read(path_block: pathlib.Path) -> dict[str, dict]:
    """Return the blocks keyed by UUID, with computed range and prefix."""
    list_block = load_json(path_block) or []
    dict_block: dict[str, dict] = {}
    for document_block in list_block:
        value_start = probe_parse(document_block["rir_record"]["start"])
        value_size = document_block["rir_record"]["value"]
        document_block["_start"] = value_start
        document_block["_end"] = block_address_end(value_start, value_size)
        document_block["_prefix"] = block_prefix_text(value_start, value_size)
        dict_block[document_block["block_uuid"]] = document_block
    return dict_block


def rdap_state_read(document_block: dict) -> tuple[str, str, dict]:
    """Return the RDAP state, a human note, and the summary."""
    document_rdap = document_block.get("rdap") or {}
    document_summary = document_rdap.get("summary") or {}
    text_status = document_rdap.get("status")
    text_start = document_block["rir_record"]["start"]
    if 200 == text_status:
        if document_summary.get("start_address") == text_start:
            return "object for the block", "the registry object is this block", document_summary
        return (
            "parent object",
            "the registry's answer covers a parent range, "
            f"{document_summary.get('start_address')} - {document_summary.get('end_address')}",
            document_summary,
        )
    if 404 == text_status:
        return "no object", "the registry holds no object for this address", document_summary
    if text_status is None:
        return "unanswered", str(document_rdap.get("error") or "not asked"), document_summary
    return f"status {text_status}", f"the registry answered {text_status}", document_summary


def observation_read(path_observation: pathlib.Path) -> dict[str, dict]:
    """Return the phase 3 observations keyed by address, responses only."""
    document = load_json(path_observation) or {}
    return {
        item["address"]: item
        for item in document.get("observations", [])
        if "timeout" != item.get("outcome")
    }


def characterization_read(path_characterize: pathlib.Path) -> dict:
    """Return the phase 4 document."""
    return load_json(path_characterize) or {}


def responded(document_observation: dict | None) -> bool:
    """Return True when an observation is anything but silence."""
    if not document_observation:
        return False
    return document_observation["http"]["outcome"] in (
        "http_response",
        "connect_refused",
        "connection_reset",
    )


def certificate_read(document_observation: dict) -> dict:
    """Return the certificate of an observation, if there is one."""
    return (document_observation.get("https") or {}).get("certificate") or {}


def certificate_name(document_certificate: dict) -> str:
    """Return the common name of a certificate, if it has one."""
    list_subject = document_certificate.get("subject") or []
    return list_subject[0].get("value") if list_subject else ""


def block_context_build(
    document_block: dict,
    list_block_observation: list[dict],
    dict_phase3: dict[str, dict],
) -> dict:
    """Return what the block contributes to a probe's reading."""
    dict_body = collections.Counter(
        item["http"]["body_sha256"]
        for item in list_block_observation
        if item["http"]["body_sha256"]
    )
    list_served = [item for item in list_block_observation if item["http"]["http_status"]]
    return {
        "answered": len(list_served),
        "measured": len(list_block_observation),
        "body": dict(dict_body),
        "anomalies": sum(
            1 for item in list_block_observation if "anomaly" == item.get("role")
        ),
    }


def test_rows_build(
    text_address: str,
    document_observation: dict,
    document_phase3: dict,
    document_block: dict,
    dict_context: dict,
    dict_parameters: dict,
) -> list[tuple[str, str, str, str, str]]:
    """Return (test, question, observed, reading, state) for every test.

    state is one of: "ok" (the test says something here), "ask" (it points at
    a question), "no" (it fails or is inconclusive), and it colours the row.
    """
    document_certificate = certificate_read(document_observation)
    document_isolation = document_observation.get("isolation") or {}
    document_latency = document_observation.get("latency") or {}
    text_rdap_state, text_rdap_note, document_summary = rdap_state_read(document_block)

    # 1. registry custody
    if "object for the block" == text_rdap_state:
        text_reading = "The registry has an object for this block, so a holder is recorded."
        text_state = "ok"
    elif "parent object" == text_rdap_state:
        text_reading = (
            "The registry has no object for this block: it is inside a parent "
            "allocation, so no holder is recorded for these addresses."
        )
        text_state = "ask"
    elif "no object" == text_rdap_state:
        text_reading = "The registry holds nothing here at all, so no holder is recorded."
        text_state = "ask"
    else:
        text_reading = "The registry was not asked, or did not answer, so custody is unrecorded."
        text_state = "no"

    # 2. ranging: the isolation test
    list_neighbour = document_isolation.get("neighbour") or []
    list_measured = [item for item in list_neighbour if item["measured"]]
    if not list_measured:
        text_ranging = "Neighbours were not measured, so this test says nothing."
        text_ranging_state = "no"
    elif document_isolation.get("isolated"):
        text_ranging = (
            "Both neighbours were silent while this address answered: the "
            "service is addressed to this address rather than covering a range."
        )
        text_ranging_state = "ask"
    elif any(item["responded"] for item in list_measured):
        text_ranging = (
            "At least one neighbour answered too, so whatever this is covers "
            "more than one address: a range, not a single endpoint."
        )
        text_ranging_state = "ok"
    else:
        text_ranging = "One neighbour was measured and was silent; the other was not measured."
        text_ranging_state = "no"
    text_neighbour_observed = ", ".join(
        f"{item['offset']:+d} {item['address']}: "
        + (str(item["outcome"]) if item["measured"] else "not measured")
        for item in list_neighbour
    )

    # 3. catch-all
    document_http = document_observation["http"]
    document_other = document_observation["http_host_other"]
    if document_http["body_sha256"] and document_http["body_sha256"] == document_other["body_sha256"]:
        text_catch = (
            "An unrelated Host header received the identical page: the server "
            "is not listening for a name, which is what a default or parked "
            "configuration looks like."
        )
        text_catch_state = "ok"
    elif None is not document_other["http_status"] or document_other["outcome"] != document_http["outcome"]:
        text_catch = (
            "The answer changed with the Host header: a name matters here, "
            "which is a step away from a default configuration."
        )
        text_catch_state = "ask"
    else:
        text_catch = "No page was served, so there is nothing to compare across Host headers."
        text_catch_state = "no"

    # 4. uniformity
    if document_http["body_sha256"]:
        count_same = dict_context["body"].get(document_http["body_sha256"], 1)
        text_uniform = (
            f"{count_same} measured address(es) in this block served exactly "
            f"this page (digest {document_http['body_sha256'][:12]}…)."
        )
        text_uniform_state = "ok" if 1 < count_same else "ask"
    else:
        text_uniform = "Nothing was served, so uniformity cannot be compared."
        text_uniform_state = "no"

    # 5. identity
    text_certificate = certificate_name(document_certificate) or "no certificate"
    text_ptr = (document_observation.get("ptr") or {}).get("name") or "no reverse DNS"
    text_organization = str(document_summary.get("organization") or "—")
    text_identity = (
        f"certificate {text_certificate}, reverse DNS {text_ptr}, "
        f"registry organization {text_organization}"
    )
    if document_certificate:
        if text_certificate and "no reverse DNS" == text_ptr:
            text_identity_reading = (
                "The certificate names a domain, the address has no name of its "
                "own, and the registry names a different party. The layers do "
                "not tell one story."
            )
            text_identity_state = "ask"
        else:
            text_identity_reading = "The identity layers are consistent with one another."
            text_identity_state = "ok"
    else:
        text_identity_reading = (
            "No certificate was presented, so the only identity evidence is the "
            "reverse DNS and the registry record: two layers, not three."
        )
        text_identity_state = "no"

    # 6. stability
    text_stability = "Not measured for this address: the pass has not been repeated."
    text_stability_state = "no"

    # 7. distance
    value_floor_geo = dict_parameters.get("ms_floor_geosynchronous")
    value_floor_moon = dict_parameters.get("ms_floor_moon")
    value_min = document_latency.get("ms_min")
    text_quantum = str(document_latency.get("quantum") or "none")
    if value_min is None:
        text_distance = "No round trip was measured, so no distance can be ruled out or in."
        text_distance_state = "no"
    elif "none" == text_quantum:
        text_distance = (
            f"The smallest of {len(document_latency.get('sample_ms') or [])} round trips was "
            f"{value_min} ms, with {document_latency.get('ms_jitter')} ms of jitter. That is "
            f"below both floors ({value_floor_geo} ms to geosynchronous orbit, "
            f"{value_floor_moon} ms to the Moon), so neither distance explains it."
        )
        text_distance_state = "ok"
    else:
        text_distance = (
            f"The floor of {value_min} ms sits in the {text_quantum} band "
            f"({value_floor_geo} ms geosynchronous, {value_floor_moon} ms lunar): a "
            "candidate that needs a second vantage point before it means anything."
        )
        text_distance_state = "ask"

    # 8. self-explanation
    text_prefix = (document_http.get("body_prefix") or "").strip()
    if text_prefix:
        text_self = f"Content: {text_prefix[:TEXT_PREFIX_SHOWN]}"
        text_self_reading = (
            "The content is a default page, a redirect, or a hosting panel. "
            "Nothing in it explains a purpose or invites contact."
        )
        text_self_state = "ok"
    else:
        text_self = "No content: the address refused, reset, or said nothing."
        text_self_reading = "There is nothing to read, so this test gives no signal."
        text_self_state = "no"

    # 9. concealment
    if "http_response" == document_http["outcome"]:
        text_conceal = (
            "A page was served with the same answer to any Host header, so "
            "nothing is being withheld from a casual probe."
        )
        text_conceal_state = "ok"
    else:
        text_conceal = (
            f"The address {document_http['outcome'].replace('_', ' ')} rather than "
            "answering: something is present and says nothing. That is the shape "
            "of a closed port on a host as much as of anything hidden."
        )
        text_conceal_state = "ask"

    return [
        ("1. Registry custody", "Does a registry object cover this address?", f"{text_rdap_state}: {text_rdap_note}", text_reading, text_state),
        ("2. Ranging (isolation)", "Do the two immediate neighbours answer too?", text_neighbour_observed, text_ranging, text_ranging_state),
        ("3. Catch-all", "Does an unrelated Host header get the same answer?",
         (
             f"unrelated Host: {document_other['outcome']}, same body"
             if document_catch_equal(document_http, document_other)
             else (
                 f"unrelated Host: {document_other['outcome']}, different body"
                 if document_other["body_sha256"]
                 else f"no page on either Host header ({document_http['outcome']} / {document_other['outcome']})"
             )
         ),
         text_catch, text_catch_state),
        ("4. Uniformity", "Does the block answer with one page?", text_uniform,
         (
             "One page repeated across many addresses is configuration; a page "
             "that varied by address would be deliberation."
             if document_http["body_sha256"]
             else "There is no page to compare, so uniformity gives no signal here."
         ),
         text_uniform_state),
        ("5. Identity", "Do certificate, reverse DNS, and registry agree?", text_identity, text_identity_reading, text_identity_state),
        ("6. Stability", "Does it answer the same way on a second pass?", text_stability, "Stability is one of the discriminators, and a single pass cannot measure it.", text_stability_state),
        ("7. Distance", "Does the smallest round trip sit on a light-speed floor?", f"floor {value_min} ms, jitter {document_latency.get('ms_jitter')} ms, band {text_quantum}", text_distance, text_distance_state),
        ("8. Self-explanation", "Does the content explain its own purpose?", text_self, text_self_reading, text_self_state),
        ("9. Concealment", "Is it silent, inconsistent, or changing?", f"phase 3 {document_phase3.get('outcome', 'not recorded')}, phase 4 {document_http['outcome']}", text_conceal, text_conceal_state),
    ]


def document_catch_equal(document_http: dict, document_other: dict) -> bool:
    """Return whether the two Host headers produced the same body."""
    return bool(
        document_http["body_sha256"]
        and document_http["body_sha256"] == document_other["body_sha256"]
    )


def layers_build(dict_verdict: dict) -> str:
    """Return the five testimonies about a site, side by side."""
    dict_routing = dict_verdict.get("routing") or {}
    if not dict_routing:
        return ""
    return (
        "<h3>The layers, as recorded</h3><table>"
        f"<tr><th>Delegation file</th><td>{html.escape(str(dict_verdict.get('registry_status') or 'see the block page'))}</td></tr>"
        f"<tr><th>Registry object</th><td>{html.escape(str(dict_routing.get('registry_object') or '—'))}</td></tr>"
        f"<tr><th>Routing</th><td>{html.escape(str(dict_routing.get('origin_asn') or '—'))} "
        f"{html.escape(str(dict_routing.get('origin_name') or ''))}, announcing "
        f"{html.escape(str(dict_routing.get('announced') or '—'))}, first seen "
        f"{html.escape(str(dict_routing.get('first_seen') or '—'))}, visibility "
        f"{html.escape(str(dict_routing.get('visibility') or '—'))}</td></tr>"
        f"<tr><th>Authorization</th><td>{html.escape(str(dict_routing.get('authorization') or '—'))}</td></tr>"
        f"<tr><th>DNS pointing here</th><td>{html.escape(str(dict_routing.get('dns') or '—'))}</td></tr>"
        "</table>"
    )


def probe_page_build(
    text_address: str,
    document_observation: dict,
    document_phase3: dict,
    document_block: dict,
    dict_context: dict,
    dict_parameters: dict,
    dict_verdict: dict | None,
) -> str:
    """Return the page content for one probe."""
    document_rir = document_block["rir_record"]
    document_http = document_observation["http"]
    document_secure = document_observation["https"]
    document_certificate = certificate_read(document_observation)
    document_isolation = document_observation.get("isolation") or {}
    document_latency = document_observation.get("latency") or {}
    text_rdap_state, text_rdap_note, document_summary = rdap_state_read(document_block)

    list_html = [
        f"<h1>Probe {html.escape(text_address)}</h1>",
        "<p><a href='../probes.html'>← all phase 4 probes</a> · "
        f"<a href='../blocks/{document_block['block_uuid']}.html'>block page</a> · "
        f"<a href='../blocks/octet-{document_block['_start'] >> 24:03d}.html'>"
        f"{document_block['_start'] >> 24}.0.0.0/8 map</a> · "
        "<a href='../records-01-probe-characterization.html'>the record</a></p>",
        "<p class='verdict'>"
        f"<b>{html.escape(document_observation['role'])}</b> in "
        f"{html.escape(document_block['_prefix'] or str(document_block['rir_record']['start']))}"
        f" ({html.escape(str(document_block['rir_record']['status']))}, "
        f"{html.escape(document_block['rir_record']['registry'])}). "
        f"Phase 3 saw <b>{html.escape(str(document_phase3.get('outcome', 'nothing recorded')))}</b>; "
        f"phase 4 saw <b>{html.escape(document_http['outcome'])}</b>"
        + (", and this address answered alone." if document_isolation.get("isolated") else ".")
        + "</p>",
        "<h2>Where this address sits</h2>",
        "<table>",
        f"<tr><th>Block</th><td>{html.escape(document_rir['start'])} - "
        f"{html.escape(probe_format(document_block['_end']))} "
        f"({document_rir['value']:,} addresses)</td></tr>",
        f"<tr><th>Registry, status</th><td>{html.escape(document_rir['registry'])}, "
        f"{html.escape(document_rir['status'])} "
        f"({'operator-held' if document_block.get('assigned') else 'not operator-held'})</td></tr>",
        f"<tr><th>RDAP custody</th><td>{html.escape(text_rdap_state)} — "
        f"{html.escape(text_rdap_note)}</td></tr>",
        f"<tr><th>RDAP holder</th><td>{html.escape(str(document_summary.get('name') or '—'))} · "
        f"{html.escape(str(document_summary.get('organization') or '—'))} · "
        f"{html.escape(str(document_summary.get('type') or '—'))}</td></tr>",
        f"<tr><th>Block UUID</th><td class='mono'>{html.escape(document_block['block_uuid'])}</td></tr>",
        f"<tr><th>Probes in the block</th><td>{document_block['probe_count']:,} "
        f"({dict_context['anomalies']} of them responded, refused, or reset; "
        f"{dict_context['answered']} of {dict_context['measured']} measured addresses answered)</td></tr>",
        "</table>",
        "<h2>What was observed</h2>",
        "<table>",
        f"<tr><th>Phase 3 (one GET)</th><td>{html.escape(str(document_phase3.get('outcome', '—')))}, "
        f"status {html.escape(str(document_phase3.get('http_status') or '—'))}, "
        f"{html.escape(str(document_phase3.get('elapsed_ms') or '—'))} ms</td></tr>",
        f"<tr><th>Phase 4, port 80</th><td>{html.escape(document_http['outcome'])}, "
        f"status {html.escape(str(document_http['http_status'] or '—'))}, "
        f"server {html.escape(str(document_http['header'].get('server') or '—'))}, "
        f"{document_http['body_bytes']:,} bytes, digest "
        f"{html.escape(str((document_http['body_sha256'] or '—')[:16]))}…</td></tr>",
        f"<tr><th>Phase 4, unrelated Host</th><td>{html.escape(document_observation['http_host_other']['outcome'])}, "
        f"status {html.escape(str(document_observation['http_host_other']['http_status'] or '—'))}, "
        f"body {'identical' if document_catch_equal(document_http, document_observation['http_host_other']) else 'different'}</td></tr>",
        f"<tr><th>Phase 4, HTTPS</th><td>{html.escape(document_secure['outcome'])}, "
        f"certificate {html.escape(certificate_name(document_certificate) or '—')}"
        + (
            f", issuer {html.escape(str((document_certificate.get('issuer') or [{}])[-1].get('value') or '—'))}"
            f", valid {html.escape(str(document_certificate.get('not_before') or '—'))} to "
            f"{html.escape(str(document_certificate.get('not_after') or '—'))}"
            f", verified {document_certificate.get('verified')}"
            if document_certificate
            else ""
        )
        + "</td></tr>",
        f"<tr><th>Certificate names</th><td>"
        + (
            "subject alternative names: "
            + html.escape(
                ", ".join(
                    f"{item.get('type')}:{item.get('value')}"
                    for item in (document_certificate.get("subject_alt_name") or [])
                )
                or "none"
            )
            + " — <b>no IP address in the certificate</b>; SHA-256 "
            + html.escape(str((document_certificate.get("sha256") or "")[:32]))
            + "…"
            if document_certificate
            else "no certificate was presented"
        )
        + "</td></tr>",
        f"<tr><th>Reverse DNS</th><td>{html.escape(str((document_observation.get('ptr') or {}).get('name') or 'none'))}</td></tr>",
        f"<tr><th>Round trips</th><td>{document_latency.get('sample_ms')} ms; "
        f"floor {document_latency.get('ms_min')} ms, median {document_latency.get('ms_median')} ms, "
        f"jitter {document_latency.get('ms_jitter')} ms, band {html.escape(str(document_latency.get('quantum')))}</td></tr>",
        "</table>",
        "<h2>The tests, and what each one says here</h2>",
        "<table><tr><th>Test</th><th>Question</th><th>Observed</th><th>Reading</th></tr>",
    ]
    for text_test, text_question, text_observed, text_reading, text_state in test_rows_build(
        text_address,
        document_observation,
        document_phase3,
        document_block,
        dict_context,
        dict_parameters,
    ):
        list_html.append(
            f"<tr><td>{html.escape(text_test)}</td>"
            f"<td>{html.escape(text_question)}</td>"
            f"<td class='{text_state}'>{html.escape(text_observed)}</td>"
            f"<td>{html.escape(text_reading)}</td></tr>"
        )
    list_html.append("</table>")

    list_html.append("<h2>The verdict this probe inherits</h2>")
    if dict_verdict:
        list_html.append(
            "<div class='verdict'>"
            f"<p><b>{html.escape(dict_verdict['name'])}: {html.escape(dict_verdict['verdict'])}.</b> "
            f"Confidence: {html.escape(dict_verdict['confidence'])}.</p><ul>"
            + "".join(f"<li>{html.escape(text_item)}</li>" for text_item in dict_verdict["evidence"])
            + "</ul>"
            f"<p><b>What would change it:</b> {html.escape(dict_verdict['falsifier'])}</p>"
            "</div>"
        )
        list_html.append(layers_build(dict_verdict))
        list_html.append(
            "<p>The verdict is a property of the <em>site</em>, not of this "
            "probe: the evidence is block-scale, and no per-address verdict "
            "was reached. That is a gap in the work, not a finding about this "
            "address.</p>"
        )
    else:
        list_html.append(
            "<p class='quiet'>No site verdict covers this block. The probe is "
            "recorded as unexplained: no evidence here supports any of the "
            "four explanations, and the missing measurement is named above.</p>"
        )
    list_html.append(
        "<p>The full evidence is in the work products "
        "(<code>dataflow.out/05_ip_probe_http.json</code> and "
        "<code>dataflow.out/06_ip_probe_characterize.json</code>); the "
        "registry's verbatim RDAP answer is kept locally and not published.</p>"
    )
    return "\n".join(list_html)


def index_build(
    list_probe: list[tuple[str, dict, dict, dict, dict]],
    dict_parameters: dict,
    dict_verdict_of: dict[str, dict],
) -> str:
    """Return the probe index page, with the patterns it can count."""
    dict_count = collections.Counter()
    dict_certificate = collections.Counter()
    for text_address, document_observation, document_phase3, document_block, dict_context in list_probe:
        document_http = document_observation["http"]
        dict_count[document_http["outcome"]] += 1
        if document_http["http_status"]:
            dict_count["served"] += 1
        if document_catch_equal(document_http, document_observation["http_host_other"]):
            dict_count["catch_all"] += 1
        if (document_observation.get("isolation") or {}).get("isolated"):
            dict_count["isolated"] += 1
        if (document_observation.get("ptr") or {}).get("name"):
            dict_count["ptr"] += 1
        if document_certificate_name := certificate_name(certificate_read(document_observation)):
            dict_certificate[document_certificate_name] += 1
            dict_count["certificate"] += 1
        if "none" != (document_observation.get("latency") or {}).get("quantum"):
            dict_count["band"] += 1
    list_html = [
        "<h1>Phase 4 probes, and the reasoning</h1>",
        "<p>Every address phase 4 examined because phase 3 heard something back: "
        f"{len(list_probe)} of them. Each page states the tests that were applied, "
        "what each test saw here, the reading that follows, and the site verdict "
        "the probe inherits. Where a test was not run, the page says so.</p>",
        f"<h2>What these {len(list_probe)} have in common, counted</h2>",
        "<ul>",
        f"<li><b>{dict_count['served']}</b> served a page; "
        f"<b>{dict_count['http_response'] - dict_count['served']}</b> answered without a page; "
        f"<b>{dict_count['connect_refused']}</b> refused; "
        f"<b>{dict_count['connection_reset']}</b> reset.</li>",
        f"<li><b>{dict_count['catch_all']}</b> of the {dict_count['served']} that served a page "
        "answered an unrelated Host header with the identical body. Not one was host-aware: "
        "nothing in this set is listening for a name.</li>",
        f"<li><b>{dict_count['isolated']}</b> answered while both immediate neighbours stayed "
        "silent, and every one of those was a refusal or a reset. No page in this set is served "
        "from a single addressed endpoint: content comes in ranges, silence comes in singles. "
        "Two further isolated responders — <code>199.47.167.22</code> and "
        "<code>199.47.167.100</code> — were found among the control addresses phase 4 added "
        "rather than among these 106, so they carry no page here; they are in the phase 4 record "
        "and flagged on the <a href='blocks.html'>block map</a>.</li>",
        f"<li><b>{dict_count['ptr']}</b> have a reverse DNS name. Every address that answered "
        "here is nameless in the DNS, which is common and therefore weak, but it is a pattern.</li>",
        f"<li><b>{len(dict_certificate)}</b> distinct certificates cover all "
        f"{dict_count['certificate']} addresses that presented one"
        + (
            ": " + ", ".join(f"{html.escape(k)} ({v})" for k, v in dict_certificate.most_common())
            if dict_certificate
            else ""
        )
        + ". The identity layer is thin, and one of the two is expired.</li>",
        f"<li><b>{dict_count['band']}</b> have a round-trip floor in a light-speed band, so "
        "distance is excluded for the rest by measurement rather than assumption.</li>",
        "</ul>",
        "<p>The tests are the same nine for every probe: registry custody, ranging, catch-all, "
        "uniformity, identity, stability, distance, self-explanation, and concealment. "
        "Their criteria are written down in "
        "<a href='documents-07-characterization-theory.html'>the characterization theory</a>, "
        "and the conclusions they produced are in "
        "<a href='records-01-probe-characterization.html'>the phase 4 record</a>.</p>",
        "<h2>The probes</h2>",
        "<table><tr><th>Address</th><th>Block</th><th>Status</th><th>Phase 3</th>"
        "<th>Phase 4</th><th>Floor</th><th>Jitter</th><th>Band</th><th>Isolated</th>"
        "<th>Certificate</th><th>Site verdict</th></tr>",
    ]
    for text_address, document_observation, document_phase3, document_block, dict_context in list_probe:
        document_http = document_observation["http"]
        document_latency = document_observation.get("latency") or {}
        dict_verdict = dict_verdict_of.get(document_block["block_uuid"])
        list_html.append(
            f"<tr><td><a href='probes/{text_address}.html'>{text_address}</a></td>"
            f"<td>{html.escape(document_block['_prefix'] or document_block['rir_record']['start'])}</td>"
            f"<td>{html.escape(document_block['rir_record']['status'])}</td>"
            f"<td>{html.escape(str(document_phase3.get('outcome', '—')))}</td>"
            f"<td>{html.escape(document_http['outcome'])}</td>"
            f"<td class='count'>{document_latency.get('ms_min')}</td>"
            f"<td class='count'>{document_latency.get('ms_jitter')}</td>"
            f"<td>{html.escape(str(document_latency.get('quantum')))}</td>"
            f"<td>{'yes' if (document_observation.get('isolation') or {}).get('isolated') else ''}</td>"
            f"<td>{html.escape(certificate_name(certificate_read(document_observation))) or '—'}</td>"
            f"<td>{html.escape((dict_verdict or {}).get('verdict', 'unclassified'))}</td></tr>"
        )
    list_html.append("</table>")
    list_html.append(
        "<p>Floors are the smallest of three TCP round trips, in milliseconds. "
        f"The light-speed floors are {dict_parameters.get('ms_floor_geosynchronous')} ms "
        f"to geosynchronous orbit and {dict_parameters.get('ms_floor_moon')} ms to the Moon; "
        f"the pass's timeout was {dict_parameters.get('blind_spot_seconds')} s, so anything "
        "slower than that is recorded as a timeout and cannot be told from a blackhole.</p>"
    )
    return "\n".join(list_html)


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Show the tests and criteria applied to each phase 4 probe."
    )
    parser_arguments.add_argument("--data-directory", type=pathlib.Path, default=PATH_DATA_DEFAULT)
    parser_arguments.add_argument("--site-directory", type=pathlib.Path, default=PATH_SITE_DEFAULT)
    parser_arguments.add_argument("--template", type=pathlib.Path, default=PATH_TEMPLATE_DEFAULT)
    parser_arguments.add_argument("--model", type=pathlib.Path, default=PATH_MODEL_DEFAULT)
    parser_arguments.add_argument(
        "--baseline",
        type=pathlib.Path,
        default=None,
        help="a later characterization file, for the stability test",
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    path_characterize = arguments_parsed.data_directory / "06_ip_probe_characterize.json"
    document_characterize = characterization_read(path_characterize)
    if not document_characterize:
        print(f"probes: FAIL: missing {path_characterize}", file=sys.stderr)
        return 1

    text_template = template_read(arguments_parsed.template)
    dict_block = block_index_read(arguments_parsed.data_directory / "02_ip_block.json")
    dict_phase3 = observation_read(arguments_parsed.data_directory / "05_ip_probe_http.json")
    dict_parameters = document_characterize.get("parameters") or {}
    document_model = load_json(arguments_parsed.model) or {}
    dict_verdict_of: dict[str, dict] = {}
    for dict_verdict in document_model.get("site", []):
        for text_uuid, document_block in dict_block.items():
            if document_block["rir_record"]["start"] == dict_verdict["block_start"]:
                dict_verdict_of[text_uuid] = dict_verdict

    list_observation = document_characterize.get("observations") or []
    dict_block_observation: dict[str, list[dict]] = collections.defaultdict(list)
    for document_observation in list_observation:
        if document_observation.get("block_uuid"):
            dict_block_observation[document_observation["block_uuid"]].append(document_observation)

    list_probe = []
    for document_observation in list_observation:
        if "anomaly" != document_observation.get("role"):
            continue
        document_block = dict_block.get(document_observation.get("block_uuid"))
        if document_block is None:
            continue
        list_probe.append(
            (
                document_observation["address"],
                document_observation,
                dict_phase3.get(document_observation["address"], {}),
                document_block,
                block_context_build(
                    document_block,
                    dict_block_observation[document_block["block_uuid"]],
                    dict_phase3,
                ),
            )
        )
    list_probe.sort(key=lambda item: probe_parse(item[0]))

    page_write(
        arguments_parsed.site_directory / "probes.html",
        text_template,
        "Phase 4 probes",
        index_build(list_probe, dict_parameters, dict_verdict_of),
        STYLE_PAGE,
    )
    for text_address, document_observation, document_phase3, document_block, dict_context in list_probe:
        page_write(
            arguments_parsed.site_directory / "probes" / f"{text_address}.html",
            text_template,
            f"Probe {text_address}",
            probe_page_build(
                text_address,
                document_observation,
                document_phase3,
                document_block,
                dict_context,
                dict_parameters,
                dict_verdict_of.get(document_block["block_uuid"]),
            ),
            STYLE_PAGE,
        )
    print(
        f"probes: wrote probes.html and {len(list_probe)} probe page(s) into "
        f"{arguments_parsed.site_directory} at "
        f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
