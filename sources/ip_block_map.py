#!/usr/bin/env python3
#
# ip_block_map.py - build the browsable map of the collected address blocks.
#
# Reads the work products and writes static HTML into the site output:
#
#   <site>/blocks.html               the index: totals, legend, the
#                                    irregularity classes with examples, and
#                                    one row per first octet
#   <site>/blocks/octet-<n>.html     the map itself: every block in one /8,
#                                    sorted by start address, with gap rows
#                                    where no delegation record covers the
#                                    space
#   <site>/blocks/<uuid>.html        one page per block, with its data
#
# The pages use the project template, so they carry the same navigation,
# footer, and homelab home-link marker as every other page.
#
# The registry's verbatim RDAP answer is deliberately not published: it
# carries registrant contact details (an email in 6,894 of the documents, a
# telephone number in 6,576). It stays in the local work product. The pages
# publish the summary and the derived facts.
#
# Usage:
#   python3 sources/ip_block_map.py
#   python3 sources/ip_block_map.py --no-probes
#
"""Build the browsable map of the address blocks (phase 2 data)."""

from __future__ import annotations

import argparse
import collections
import datetime
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from ip_block_collect import (  # noqa: E402
    block_address_end,
    block_prefix_text,
)
from ip_probe_generate import probe_format, probe_parse  # noqa: E402
from site_page import page_write, template_read  # noqa: E402

PATH_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH_DATA_DEFAULT = PATH_REPOSITORY_ROOT / "dataflow.out"
PATH_SITE_DEFAULT = PATH_REPOSITORY_ROOT / "site.out"
PATH_TEMPLATE_DEFAULT = PATH_REPOSITORY_ROOT / "site.in" / "template.html"

MARKER_CONTENT = "<!-- SITE-CONTENT -->"
COUNT_PROBE_LIMIT = 60
COUNT_EXAMPLE_LINK = 12

TEXT_SERVICE_OF_REGISTRY = {
    "afrinic": "rdap.afrinic.net",
    "apnic": "rdap.apnic.net",
    "arin": "rdap.arin.net",
    "lacnic": "rdap.lacnic.net",
    "ripencc": "rdap.db.ripe.net",
}

# One colour per RIR status, plus a colour per RDAP state. Colour is the only
# thing on the map that is not a fact, so the legend names every class.
TEXT_CLASS_STATUS = {
    "allocated": "st-allocated",
    "assigned": "st-assigned",
    "available": "st-available",
    "reserved": "st-reserved",
}
TEXT_CLASS_RDAP = {
    "own": "rd-own",
    "parent": "rd-parent",
    "404": "rd-404",
    "none": "rd-none",
}

STYLE_PAGE = """
    .map { font-size: 0.82rem; }
    .map table { width: 100%; }
    .map td, .map th { padding: 0.15em 0.4em; white-space: nowrap; }
    .map td.name, .map td.org { white-space: normal; }
    .map tr.gap td { background: #f0f0f0; color: #666; font-style: italic; }
    .map tr.octet th { background: #333; color: #fff; text-align: left; }
    .map tr:hover td { background: #eef6ff; }
    .st-allocated { background: #dbe9f7; }
    .st-assigned  { background: #dff0dc; }
    .st-available { background: #fdf3d0; }
    .st-reserved  { background: #f2dede; }
    .rd-parent { color: #a05000; }
    .rd-404 { color: #a00000; font-weight: 600; }
    .rd-none { color: #888; }
    .flag { font-weight: 600; }
    .legend span { display: inline-block; margin-right: 0.8em; padding: 0.1em 0.4em; }
    .count { text-align: right; }
    .probes { line-height: 1.9; }
    .probes code { margin-right: 0.4em; }
"""


def block_list_read(path_block: pathlib.Path) -> list[dict]:
    """Return the blocks, sorted by start address."""
    with open(path_block, "r", encoding="utf-8") as file_block:
        list_block = json.load(file_block)
    for document_block in list_block:
        document_block["_start"] = probe_parse(document_block["rir_record"]["start"])
        document_block["_end"] = block_address_end(
            document_block["_start"], document_block["rir_record"]["value"]
        )
        document_block["_octet"] = document_block["_start"] >> 24
    list_block.sort(key=lambda item: item["_start"])
    return list_block


def probe_list_read(path_mapped: pathlib.Path, count_limit: int) -> dict[str, list[str]]:
    """Return up to count_limit probe addresses per block UUID."""
    dict_probe: dict[str, list[str]] = collections.defaultdict(list)
    with open(path_mapped, "r", encoding="ascii") as file_mapped:
        for text_line in file_mapped:
            text_item = text_line.strip().rstrip(",").strip()
            if not text_item or text_item in ("[", "]"):
                continue
            text_item = text_item.strip("[]")
            list_field = [
                text_field.strip().strip('"') for text_field in text_item.split(",")
            ]
            if 2 != len(list_field):
                continue
            text_address, text_uuid = list_field
            list_block_probe = dict_probe[text_uuid]
            if count_limit > len(list_block_probe):
                list_block_probe.append(text_address)
    return dict(dict_probe)


def outcome_map_read(path_observation: pathlib.Path) -> dict[str, dict]:
    """Return the phase 3 outcome per address, for the responses only."""
    if not path_observation.is_file():
        return {}
    with open(path_observation, "r", encoding="utf-8") as file_observation:
        document_observation = json.load(file_observation)
    return {
        item["address"]: item
        for item in document_observation.get("observations", [])
        if "timeout" != item.get("outcome")
    }


def characterization_map_read(path_characterize: pathlib.Path) -> dict[str, dict]:
    """Return the phase 4 signals per address."""
    if not path_characterize.is_file():
        return {}
    with open(path_characterize, "r", encoding="utf-8") as file_characterize:
        document_characterize = json.load(file_characterize)
    return {
        item["address"]: {
            "outcome": (item.get("http") or {}).get("outcome"),
            "isolated": (item.get("isolation") or {}).get("isolated"),
            "role": item.get("role"),
            "block_uuid": item.get("block_uuid"),
            "certificate": (item.get("https") or {}).get("certificate"),
        }
        for item in document_characterize.get("observations", [])
    }


def rdap_state_read(document_block: dict) -> tuple[str, str]:
    """Return the RDAP state and a short human note."""
    document_rdap = document_block.get("rdap") or {}
    text_status = document_rdap.get("status")
    dict_summary = document_rdap.get("summary") or {}
    if 200 == text_status:
        if dict_summary.get("start_address") == document_block["rir_record"]["start"]:
            return "own", "the registry object is this block"
        return (
            "parent",
            "the registry object is a parent: "
            f"{dict_summary.get('start_address')} - {dict_summary.get('end_address')}",
        )
    if 404 == text_status:
        return "404", "the registry holds no object for this address"
    if text_status is None:
        return "none", f"unanswered: {document_rdap.get('error') or 'not asked'}"
    return str(text_status), f"answered {text_status}"


def service_host_read(document_block: dict) -> str:
    """Return the RDAP service host that answered, if any."""
    text_service = (document_block.get("rdap") or {}).get("service") or ""
    if "//" in text_service:
        return text_service.split("/")[2]
    return text_service


def flag_read(document_block: dict, text_state: str) -> list[tuple[str, str]]:
    """Return the irregularity flags for a block, with their meanings."""
    list_flag = []
    if "parent" == text_state:
        list_flag.append(("P", "RDAP answered with a parent object, not this block"))
    if "404" == text_state:
        list_flag.append(("4", "the registry holds no object for this address"))
    if "none" == text_state:
        list_flag.append(("-", "RDAP was never answered"))
    document_rdap = document_block.get("rdap") or {}
    if 200 == document_rdap.get("status") and not (
        (document_rdap.get("summary") or {}).get("name")
    ):
        list_flag.append(("N", "the RDAP object has no name"))
    if service_host_read(document_block) and service_host_read(
        document_block
    ) != TEXT_SERVICE_OF_REGISTRY.get(document_block["rir_record"]["registry"]):
        list_flag.append(("S", "the RDAP service is not the delegation registry's"))
    document_summary = document_rdap.get("summary") or {}
    if (
        document_block["rir_record"]["country"]
        and document_summary.get("country")
        and document_block["rir_record"]["country"] != document_summary["country"]
    ):
        list_flag.append(("C", "the delegation country and the RDAP country differ"))
    return list_flag


def row_build(
    document_block: dict,
    dict_probe: dict[str, list[str]],
    dict_outcome: dict[str, dict],
    dict_characterize: dict[str, dict],
) -> str:
    """Return the map row for one block."""
    document_rir = document_block["rir_record"]
    document_summary = (document_block.get("rdap") or {}).get("summary") or {}
    text_uuid = document_block["block_uuid"]
    text_state, text_state_note = rdap_state_read(document_block)
    list_probe = dict_probe.get(text_uuid, [])
    list_anomaly = [
        text_address for text_address in list_probe if text_address in dict_outcome
    ]
    list_isolated = [
        text_address
        for text_address in list_probe
        if (dict_characterize.get(text_address) or {}).get("isolated")
    ]
    text_flag = "".join(
        f"<span class='flag' title='{html.escape(text_meaning)}'>{text_code}</span>"
        for text_code, text_meaning in flag_read(document_block, text_state)
    )
    if list_anomaly:
        text_flag += f"<span class='flag' title='addresses that responded'>A</span>{len(list_anomaly)}"
    if list_isolated:
        text_flag += f"<span class='flag' title='responded alone'>I</span>{len(list_isolated)}"
    text_prefix = block_prefix_text(document_block["_start"], document_rir["value"])
    text_range = text_prefix or (
        f"{document_rir['start']} - {probe_format(document_block['_end'])}"
    )
    text_class = TEXT_CLASS_STATUS.get(document_rir["status"], "")
    return (
        f"<tr class='{text_class}'>"
        f"<td><a href='{text_uuid}.html'>{document_rir['start']}</a></td>"
        f"<td>{html.escape(str(text_range))}</td>"
        f"<td class='count'>{document_rir['value']:,}</td>"
        f"<td>{html.escape(document_rir['status'])}</td>"
        f"<td>{'yes' if document_block.get('assigned') else 'no'}</td>"
        f"<td>{html.escape(document_rir['country'] or '')}</td>"
        f"<td>{html.escape(document_rir['registry'])}</td>"
        f"<td class='{TEXT_CLASS_RDAP.get(text_state, '')}' title='{html.escape(text_state_note)}'>"
        f"{html.escape(text_state)}</td>"
        f"<td class='name'>{html.escape(str(document_summary.get('name') or ''))}</td>"
        f"<td>{html.escape(str(document_summary.get('type') or ''))}</td>"
        f"<td class='org'>{html.escape(str(document_summary.get('organization') or ''))}</td>"
        f"<td class='count'>{document_block['probe_count']:,}</td>"
        f"<td>{text_flag}</td></tr>"
    )


def table_head_build() -> str:
    """Return the map table header row."""
    return (
        "<tr><th>Start</th><th>Prefix or range</th><th class='count'>Size</th>"
        "<th>Status</th><th>Held</th><th>Country</th><th>Registry</th>"
        "<th>RDAP</th><th>Name</th><th>Type</th><th>Organization</th>"
        "<th class='count'>Probes</th><th>Flags</th></tr>"
    )


def legend_build(dict_count: collections.Counter) -> str:
    """Return the legend, with the counts for each class."""
    list_html = [
        "<p class='legend'>Status: "
        + " ".join(
            f"<span class='{TEXT_CLASS_STATUS[text_status]}'>{text_status} "
            f"{dict_count['status:' + text_status]:,}</span>"
            for text_status in ("allocated", "assigned", "available", "reserved")
            if dict_count["status:" + text_status]
        )
        + "</p>",
        "<p class='legend'>RDAP state: "
        + " ".join(
            f"<span class='{TEXT_CLASS_RDAP[text_key]}'>{text_label} "
            f"{dict_count['rdap:' + text_key]:,}</span>"
            for text_key, text_label in (
                ("own", "object for the block"),
                ("parent", "parent object"),
                ("404", "no object"),
                ("none", "unanswered"),
            )
            if dict_count["rdap:" + text_key]
        )
        + "</p>",
        "<p class='legend'>Flags: "
        "<span class='flag'>P</span> RDAP answered with a parent object · "
        "<span class='flag'>4</span> the registry holds no object · "
        "<span class='flag'>-</span> RDAP unanswered · "
        "<span class='flag'>N</span> no name in the RDAP object · "
        "<span class='flag'>A</span> an address in the block responded · "
        "<span class='flag'>I</span> an isolated responder · "
        f"<span class='flag'>S</span> the RDAP service is not the delegation "
        f"registry's ({dict_count['flag:S']:,} blocks) · "
        f"<span class='flag'>C</span> delegation country and RDAP country "
        f"differ ({dict_count['flag:C']:,} blocks)</p>",
    ]
    return "\n".join(list_html)


def count_build(
    list_block: list[dict],
    dict_probe: dict[str, list[str]],
    dict_outcome: dict[str, dict],
    dict_characterize: dict[str, dict],
) -> tuple[collections.Counter, list[dict]]:
    """Return the class counts and the gap list."""
    dict_count = collections.Counter()
    for document_block in list_block:
        text_uuid = document_block["block_uuid"]
        text_state, _ = rdap_state_read(document_block)
        dict_count[f"status:{document_block['rir_record']['status']}"] += 1
        dict_count[f"rdap:{text_state}"] += 1
        dict_count["held" if document_block.get("assigned") else "unheld"] += 1
        for text_code, _ in flag_read(document_block, text_state):
            dict_count[f"flag:{text_code}"] += 1
        list_probe = dict_probe.get(text_uuid, [])
        if any(text_address in dict_outcome for text_address in list_probe):
            dict_count["flag:A"] += 1
        if any(
            (dict_characterize.get(text_address) or {}).get("isolated")
            for text_address in list_probe
        ):
            dict_count["flag:I"] += 1
    list_gap = []
    value_end_previous = None
    for document_block in list_block:
        if value_end_previous is not None and document_block["_start"] > value_end_previous + 1:
            list_gap.append(
                {
                    "start": value_end_previous + 1,
                    "end": document_block["_start"] - 1,
                    "value": document_block["_start"] - value_end_previous - 1,
                    "octet": (value_end_previous + 1) >> 24,
                }
            )
        value_end_previous = document_block["_end"]
    return dict_count, list_gap


def index_build(
    list_block: list[dict],
    dict_count: collections.Counter,
    list_gap: list[dict],
    dict_probe: dict[str, list[str]],
    dict_outcome: dict[str, dict],
) -> str:
    """Return the map index page content."""
    value_total = sum(document_block["rir_record"]["value"] for document_block in list_block)
    value_gap = sum(item["value"] for item in list_gap)
    dict_octet = collections.defaultdict(lambda: collections.Counter())
    for document_block in list_block:
        dict_octet[document_block["_octet"]]["block"] += 1
        dict_octet[document_block["_octet"]]["value"] += document_block["rir_record"]["value"]
        dict_octet[document_block["_octet"]][
            "held" if document_block.get("assigned") else "unheld"
        ] += 1
        text_state, _ = rdap_state_read(document_block)
        dict_octet[document_block["_octet"]][f"rdap:{text_state}"] += 1
        list_probe = dict_probe.get(document_block["block_uuid"], [])
        if any(text_address in dict_outcome for text_address in list_probe):
            dict_octet[document_block["_octet"]]["responded"] += 1
    for item_gap in list_gap:
        dict_octet[item_gap["octet"]]["gap"] += 1
        dict_octet[item_gap["octet"]]["gapvalue"] += item_gap["value"]

    list_html = [
        "<h1>Address block map</h1>",
        "<p>Every block the project collected from the five RIR delegation "
        "files, one page per first octet, each block sorted by start address "
        "with a link to all of its data. Grey rows inside a page are gaps: "
        "address space that no delegation record covers.</p>",
        "<p>"
        f"{len(list_block):,} blocks covering {value_total:,} addresses. "
        f"{len(list_gap):,} gaps covering {value_gap:,} addresses. "
        f"{dict_count['held']:,} blocks are operator-held and "
        f"{dict_count['unheld']:,} are not. "
        f"{dict_count['flag:A']:,} blocks hold at least one address that "
        f"responded, refused, or reset, and {dict_count['flag:I']:,} hold an "
        "isolated responder."
        "</p>",
        legend_build(dict_count),
        "<h2>Where to look</h2>",
        "<p>The irregularity classes, with a few examples each. Every block "
        "page carries the same flags.</p>",
        "<table><tr><th>Irregularity</th><th class='count'>Blocks</th>"
        "<th>Examples</th></tr>",
    ]
    for text_code, text_meaning, text_key in (
        ("P", "RDAP answered with a parent object, not the block", "rdap:parent"),
        ("4", "the registry holds no object for the address", "rdap:404"),
        ("-", "RDAP was never answered", "rdap:none"),
        ("N", "the RDAP object has no name", "flag:N"),
        ("S", "the RDAP service is not the delegation registry's", "flag:S"),
        ("C", "the delegation country and the RDAP country differ", "flag:C"),
    ):
        list_example = []
        for document_block in list_block:
            if len(list_example) >= COUNT_EXAMPLE_LINK:
                break
            if text_key.startswith("rdap:"):
                if rdap_state_read(document_block)[0] != text_key.split(":")[1]:
                    continue
            elif not any(
                text_flag == text_code for text_flag, _ in flag_read(document_block, "")
            ):
                continue
            text_uuid = document_block["block_uuid"]
            list_example.append(
                f"<a href='blocks/{text_uuid}.html'>{document_block['rir_record']['start']}</a>"
            )
        list_html.append(
            f"<tr><td><span class='flag'>{text_code}</span> {html.escape(text_meaning)}</td>"
            f"<td class='count'>{dict_count[text_key]:,}</td>"
            f"<td>{' · '.join(list_example) if list_example else '—'}</td></tr>"
        )
    list_html.append("</table>")

    list_html.append("<h2>By first octet</h2>")
    list_html.append("<table><tr><th>Network</th><th class='count'>Blocks</th>"
                     "<th class='count'>Addresses</th><th class='count'>Held</th>"
                     "<th class='count'>Not held</th><th class='count'>Gaps</th>"
                     "<th class='count'>Blocks with a response</th><th>RDAP states</th></tr>")
    for value_octet in sorted(dict_octet):
        dict_row = dict_octet[value_octet]
        list_state = " ".join(
            f"<span class='{TEXT_CLASS_RDAP[text_state]}'>{text_state} "
            f"{dict_row['rdap:' + text_state]}</span>"
            for text_state in ("own", "parent", "404", "none")
            if dict_row["rdap:" + text_state]
        )
        list_html.append(
            f"<tr><td><a href='blocks/octet-{value_octet:03d}.html'>"
            f"{value_octet}.0.0.0/8</a></td>"
            f"<td class='count'>{dict_row['block']:,}</td>"
            f"<td class='count'>{dict_row['value']:,}</td>"
            f"<td class='count'>{dict_row['held']:,}</td>"
            f"<td class='count'>{dict_row['unheld']:,}</td>"
            f"<td class='count'>{dict_row['gap']:,} ({dict_row['gapvalue']:,} addr)</td>"
            f"<td class='count'>{dict_row['responded']:,}</td>"
            f"<td>{list_state}</td></tr>"
        )
    list_html.append("</table>")
    list_html.append(
        "<p>This page is generated from <code>02_ip_block.json</code> by "
        "<code>sources/ip_block_map.py</code>. The registry's verbatim RDAP "
        "answer is not published: it carries registrant contact details, so it "
        "stays in the local work product.</p>"
    )
    return "\n".join(list_html)


def octet_page_build(
    value_octet: int,
    list_block: list[dict],
    list_gap: list[dict],
    dict_probe: dict[str, list[str]],
    dict_outcome: dict[str, dict],
    dict_characterize: dict[str, dict],
) -> str:
    """Return the map page content for one first octet."""
    value_total = sum(document_block["rir_record"]["value"] for document_block in list_block)
    value_gap = sum(item["value"] for item in list_gap)
    list_html = [
        f"<h1>{value_octet}.0.0.0/8</h1>",
        "<p><a href='../blocks.html'>← back to the map index</a></p>",
        "<p>"
        f"{len(list_block):,} blocks covering {value_total:,} addresses, "
        f"{len(list_gap):,} gaps covering {value_gap:,} addresses. "
        "Sorted by start address; grey rows are gaps.</p>",
        "<div class='map'><table>",
        table_head_build(),
    ]
    dict_gap_by_start = {item["start"]: item for item in list_gap}
    value_end_previous = None
    for document_block in list_block:
        item_gap = dict_gap_by_start.get(document_block["_start"] - 1) if False else None
        dict_gap_here = next(
            (
                item
                for item in list_gap
                if item["end"] == document_block["_start"] - 1
            ),
            None,
        )
        if dict_gap_here is not None:
            list_html.append(
                "<tr class='gap'><td colspan='13'>gap: "
                f"{probe_format(dict_gap_here['start'])} - "
                f"{probe_format(dict_gap_here['end'])} "
                f"({dict_gap_here['value']:,} addresses)</td></tr>"
            )
        list_html.append(
            row_build(document_block, dict_probe, dict_outcome, dict_characterize)
        )
        value_end_previous = document_block["_end"]
    dict_gap_last = next(
        (item for item in list_gap if item["end"] == value_end_previous - 1), None
    )
    if dict_gap_last is not None:
        list_html.append(
            "<tr class='gap'><td colspan='13'>gap to the end of the /8: "
            f"{probe_format(dict_gap_last['start'])} - "
            f"{probe_format(dict_gap_last['end'])} "
            f"({dict_gap_last['value']:,} addresses)</td></tr>"
        )
    list_html.append("</table></div>")
    return "\n".join(list_html)


def block_page_build(
    document_block: dict,
    list_probe: list[str],
    dict_outcome: dict[str, dict],
    dict_characterize: dict[str, dict],
    dict_verdict: dict | None = None,
) -> str:
    """Return the per-block page content."""
    document_rir = document_block["rir_record"]
    document_rdap = document_block.get("rdap") or {}
    document_summary = document_rdap.get("summary") or {}
    document_document = document_rdap.get("document") or {}
    text_state, text_state_note = rdap_state_read(document_block)
    list_flag = flag_read(document_block, text_state)
    text_prefix = block_prefix_text(document_block["_start"], document_rir["value"])
    text_extension = ", ".join(
        text_item for text_item in (document_rir.get("extensions") or []) if text_item
    )
    list_html = [
        f"<h1>Block {html.escape(document_rir['start'])}</h1>",
        "<p><a href='../blocks.html'>← back to the map index</a> · "
        f"<a href='octet-{document_block['_octet']:03d}.html'>"
        f"{document_block['_octet']}.0.0.0/8</a></p>",
        "<table>",
        f"<tr><th>Range</th><td>{html.escape(document_rir['start'])} - "
        f"{html.escape(probe_format(document_block['_end']))}</td></tr>",
        f"<tr><th>Prefix</th><td>"
        f"{html.escape(str(text_prefix or 'not a CIDR block'))}</td></tr>",
        f"<tr><th>Size</th><td>{document_rir['value']:,} addresses</td></tr>",
        f"<tr><th>Status</th><td>{html.escape(document_rir['status'])} — "
        f"{'operator-held' if document_block.get('assigned') else 'not operator-held'}</td></tr>",
        f"<tr><th>Registry</th><td>{html.escape(document_rir['registry'])}</td></tr>",
        f"<tr><th>Country (delegation)</th><td>{html.escape(document_rir['country'] or '—')}</td></tr>",
        f"<tr><th>Date</th><td>{html.escape(document_rir['date'] or '—')}</td></tr>",
        f"<tr><th>Opaque id</th><td>{html.escape(text_extension or '—')}</td></tr>",
        f"<tr><th>Block UUID</th><td><code>{html.escape(document_block['block_uuid'])}</code></td></tr>",
        f"<tr><th>Probes</th><td>{document_block['probe_count']:,}</td></tr>",
        f"<tr><th>RDAP state</th><td>{html.escape(text_state)} — "
        f"{html.escape(text_state_note)}</td></tr>",
        f"<tr><th>RDAP service</th><td>{html.escape(service_host_read(document_block) or '—')}</td></tr>",
        f"<tr><th>RDAP fetched</th><td>{html.escape(str(document_rdap.get('fetched_at') or '—'))}</td></tr>",
        f"<tr><th>Flags</th><td>"
        + (
            " · ".join(
                f"<span class='flag'>{text_code}</span> {html.escape(text_meaning)}"
                for text_code, text_meaning in list_flag
            )
            or "none"
        )
        + "</td></tr>",
        "</table>",
        "<h2>RIR delegation record</h2>",
        "<table>",
        f"<tr><th>registry</th><td>{html.escape(document_rir['registry'])}</td></tr>",
        f"<tr><th>country</th><td>{html.escape(document_rir['country'])}</td></tr>",
        f"<tr><th>type</th><td>{html.escape(document_rir['type'])}</td></tr>",
        f"<tr><th>start</th><td>{html.escape(document_rir['start'])}</td></tr>",
        f"<tr><th>value</th><td>{document_rir['value']:,}</td></tr>",
        f"<tr><th>date</th><td>{html.escape(document_rir['date'])}</td></tr>",
        f"<tr><th>status</th><td>{html.escape(document_rir['status'])}</td></tr>",
        f"<tr><th>extensions</th><td>{html.escape(repr(document_rir['extensions']))}</td></tr>",
        "</table>",
        "<h2>RDAP summary</h2>",
        "<table>",
    ]
    for text_key, text_label in (
        ("handle", "handle"),
        ("name", "name"),
        ("type", "type"),
        ("parent_handle", "parent handle"),
        ("start_address", "start address"),
        ("end_address", "end address"),
        ("country", "country"),
        ("organization", "organization"),
    ):
        list_html.append(
            f"<tr><th>{text_label}</th><td>"
            f"{html.escape(str(document_summary.get(text_key) or '—'))}</td></tr>"
        )
    list_html.append(
        f"<tr><th>events</th><td>"
        f"{html.escape(json.dumps(document_summary.get('event') or {}))}</td></tr>"
    )
    list_entity = document_document.get("entities") if isinstance(document_document, dict) else None
    if list_entity:
        list_role = collections.Counter()
        for dict_entity in list_entity:
            if isinstance(dict_entity, dict):
                for text_role in dict_entity.get("roles", []):
                    list_role[text_role] += 1
        list_html.append(
            f"<tr><th>entities</th><td>{len(list_entity)}: "
            f"{html.escape(', '.join(f'{k} × {v}' for k, v in sorted(list_role.items())))}"
            " (contact details are not published)</td></tr>"
        )
    list_html.append("</table>")

    list_anomaly = [
        text_address for text_address in list_probe if text_address in dict_outcome
    ]
    if list_anomaly:
        list_html.append("<h2>Addresses in this block that responded</h2><table>")
        list_html.append(
            "<tr><th>Address</th><th>Phase 3</th><th>Phase 4</th><th>Isolated</th></tr>"
        )
        for text_address in list_anomaly:
            dict_characterized = dict_characterize.get(text_address) or {}
            list_html.append(
                f"<tr><td><a href='../probes/{text_address}.html'>{html.escape(text_address)}</a></td>"
                f"<td>{html.escape(str(dict_outcome[text_address]['outcome']))}</td>"
                f"<td>{html.escape(str(dict_characterized.get('outcome') or '—'))}</td>"
                f"<td>{'yes' if dict_characterized.get('isolated') else '—'}</td></tr>"
            )
        list_html.append("</table>")

    if list_probe:
        list_html.append(
            f"<h2>Probes in this block</h2><p>{document_block['probe_count']:,} probes; "
            f"the first {len(list_probe):,} are listed. An asterisk means phase 3 "
            "heard something back.</p>"
        )
        list_html.append(
            "<p class='probes'><code>"
            + html.escape(
                " ".join(
                    text_address + ("*" if text_address in dict_outcome else "")
                    for text_address in list_probe
                )
            )
            + "</code></p>"
        )

    list_html.append(layers_build(document_block, dict_characterize, dict_verdict))
    list_html.append(
        "<p>The registry's verbatim RDAP answer is kept in the local work "
        "product <code>dataflow.out/02_ip_block.json</code> and is not "
        "published, because it carries registrant contact details.</p>"
    )
    return "\n".join(list_html)


def layers_build(
    document_block: dict,
    dict_characterize: dict[str, dict],
    dict_verdict: dict | None,
) -> str:
    """Return the testimonies about this block, side by side.

    The delegation file, the registry object, the routing table, the RPKI
    state, the DNS, and the certificate are separate witnesses. Where they
    disagree, the disagreement is the finding.
    """
    text_state, text_state_note = rdap_state_read(document_block)
    dict_routing = (dict_verdict or {}).get("routing") or {}
    dict_certificate: dict[str, dict] = {}
    for dict_item in dict_characterize.values():
        if dict_item.get("block_uuid") != document_block["block_uuid"]:
            continue
        dict_cert = dict_item.get("certificate") or {}
        if dict_cert.get("sha256") and dict_cert["sha256"] not in dict_certificate:
            dict_certificate[dict_cert["sha256"]] = dict_cert
    list_certificate = []
    for dict_cert in dict_certificate.values():
        list_subject = dict_cert.get("subject") or [{}]
        list_alt = dict_cert.get("subject_alt_name") or []
        list_certificate.append(
            f"<b>{html.escape(str(list_subject[0].get('value') or '—'))}</b>: "
            + html.escape(
                ", ".join(f"{item.get('type')}:{item.get('value')}" for item in list_alt)
                or "no subject alternative names"
            )
            + f"; valid {html.escape(str(dict_cert.get('not_before') or '—'))} to "
            f"{html.escape(str(dict_cert.get('not_after') or '—'))}, "
            f"verified {dict_cert.get('verified')}, SHA-256 "
            f"{html.escape(str((dict_cert.get('sha256') or '')[:24]))}…"
        )
    document_rir = document_block["rir_record"]
    return (
        "<h2>Who operates this: the layers, side by side</h2><table>"
        f"<tr><th>Delegation file</th><td>{html.escape(document_rir['status'])}"
        f"{', ' + html.escape(document_rir['country']) if document_rir['country'] else ''}"
        f"{', ' + html.escape(document_rir['date']) if document_rir['date'] else ''}</td></tr>"
        f"<tr><th>Registry object</th><td>{html.escape(text_state)} — {html.escape(text_state_note)}</td></tr>"
        f"<tr><th>Routing</th><td>{html.escape(str(dict_routing.get('origin_asn') or 'not recorded'))} "
        f"{html.escape(str(dict_routing.get('origin_name') or ''))}"
        f"{', announcing ' + html.escape(str(dict_routing.get('announced'))) if dict_routing.get('announced') else ''}"
        f"{', first seen ' + html.escape(str(dict_routing.get('first_seen'))) if dict_routing.get('first_seen') else ''}"
        f"{', visibility ' + html.escape(str(dict_routing.get('visibility'))) if dict_routing.get('visibility') else ''}</td></tr>"
        f"<tr><th>Authorization</th><td>{html.escape(str(dict_routing.get('authorization') or 'not recorded'))}</td></tr>"
        f"<tr><th>DNS pointing here</th><td>{html.escape(str(dict_routing.get('dns') or 'not recorded'))}</td></tr>"
        + (
            f"<tr><th>Registrant</th><td>{html.escape(str(dict_routing.get('registrant')))}</td></tr>"
            if dict_routing.get("registrant")
            else ""
        )
        + (
            f"<tr><th>Operators named</th><td>{html.escape(str(dict_routing.get('operators_named')))}</td></tr>"
            if dict_routing.get("operators_named")
            else ""
        )
        + (
            f"<tr><th>Application</th><td>{html.escape(str(dict_routing.get('application')))}</td></tr>"
            if dict_routing.get("application")
            else ""
        )
        + (
            f"<tr><th>Publication</th><td>{html.escape(str(dict_routing.get('publication')))}</td></tr>"
            if dict_routing.get("publication")
            else ""
        )
        + f"<tr><th>Certificate</th><td>{'<br>'.join(list_certificate) if list_certificate else 'none presented'}</td></tr>"
        "</table>"
    )


def main(arguments: list[str]) -> int:
    """Run the command line."""
    parser_arguments = argparse.ArgumentParser(
        description="Build the browsable map of the collected address blocks."
    )
    parser_arguments.add_argument(
        "--data-directory", type=pathlib.Path, default=PATH_DATA_DEFAULT
    )
    parser_arguments.add_argument(
        "--site-directory", type=pathlib.Path, default=PATH_SITE_DEFAULT
    )
    parser_arguments.add_argument(
        "--template", type=pathlib.Path, default=PATH_TEMPLATE_DEFAULT
    )
    parser_arguments.add_argument("--limit-probe", type=int, default=COUNT_PROBE_LIMIT)
    parser_arguments.add_argument(
        "--no-probes", action="store_true", help="skip the probe-to-block file"
    )
    arguments_parsed = parser_arguments.parse_args(arguments)

    path_block = arguments_parsed.data_directory / "02_ip_block.json"
    if not path_block.is_file():
        print(f"map: FAIL: missing block file: {path_block}", file=sys.stderr)
        return 1

    moment_start = datetime.datetime.now(datetime.timezone.utc)
    text_template = template_read(arguments_parsed.template)
    list_block = block_list_read(path_block)
    dict_probe: dict[str, list[str]] = {}
    if not arguments_parsed.no_probes:
        path_mapped = arguments_parsed.data_directory / "03_ip_probe.json"
        if path_mapped.is_file():
            dict_probe = probe_list_read(path_mapped, arguments_parsed.limit_probe)
    dict_outcome = outcome_map_read(
        arguments_parsed.data_directory / "05_ip_probe_http.json"
    )
    dict_characterize = characterization_map_read(
        arguments_parsed.data_directory / "06_ip_probe_characterize.json"
    )

    document_model = {}
    path_model = pathlib.Path(__file__).resolve().parent / "probe_verdict_model.json"
    if path_model.is_file():
        with open(path_model, "r", encoding="utf-8") as file_model:
            document_model = json.load(file_model)
    dict_verdict_of = {}
    for dict_verdict in document_model.get("site", []):
        for document_block in list_block:
            if document_block["rir_record"]["start"] == dict_verdict["block_start"]:
                dict_verdict_of[document_block["block_uuid"]] = dict_verdict

    dict_count, list_gap = count_build(list_block, dict_probe, dict_outcome, dict_characterize)
    page_write(
        arguments_parsed.site_directory / "blocks.html",
        text_template,
        "Address block map",
        index_build(list_block, dict_count, list_gap, dict_probe, dict_outcome),
        STYLE_PAGE,
    )

    dict_block_octet = collections.defaultdict(list)
    dict_gap_octet = collections.defaultdict(list)
    for document_block in list_block:
        dict_block_octet[document_block["_octet"]].append(document_block)
    for item_gap in list_gap:
        dict_gap_octet[item_gap["octet"]].append(item_gap)
    for value_octet, list_octet_block in dict_block_octet.items():
        page_write(
            arguments_parsed.site_directory / "blocks" / f"octet-{value_octet:03d}.html",
            text_template,
            f"{value_octet}.0.0.0/8 block map",
            octet_page_build(
                value_octet,
                list_octet_block,
                dict_gap_octet.get(value_octet, []),
                dict_probe,
                dict_outcome,
                dict_characterize,
            ),
            STYLE_PAGE,
        )
    for document_block in list_block:
        page_write(
            arguments_parsed.site_directory
            / "blocks"
            / f"{document_block['block_uuid']}.html",
            text_template,
            f"Block {document_block['rir_record']['start']}",
            block_page_build(
                document_block,
                dict_probe.get(document_block["block_uuid"], []),
                dict_outcome,
                dict_characterize,
                dict_verdict_of.get(document_block["block_uuid"]),
            ),
            STYLE_PAGE,
        )
    print(
        f"map: wrote the index, {len(dict_block_octet):,} octet page(s), and "
        f"{len(list_block):,} block page(s) into {arguments_parsed.site_directory} "
        f"at {moment_start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
