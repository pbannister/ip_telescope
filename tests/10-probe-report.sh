#!/bin/sh
#
# Probe report test (the per-probe reasoning pages).
#
# Tier: portable. Small fixtures stand in for the work products, so the test
# needs neither the real 770 MB of data nor a network.
#
# It checks that every anomaly gets a page, that the page carries the nine
# tests with their readings, that the site verdict is shown where the model
# has one, that an unmeasured test says so instead of implying a result, and
# that the stylesheet stays in the head.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_REPORT="$REPOSITORY_ROOT/sources/ip_probe_report.py"

DIRECTORY_TEST=$(mktemp -d)
trap 'rm -rf "$DIRECTORY_TEST"' EXIT

DIRECTORY_DATA="$DIRECTORY_TEST/dataflow.out"
DIRECTORY_SITE="$DIRECTORY_TEST/site.out"
mkdir -p "$DIRECTORY_DATA" "$DIRECTORY_SITE"

fail() {
    echo "10-probe-report: $1" >&2
    exit 1
}

cat > "$DIRECTORY_DATA/02_ip_block.json" <<'FIXTURE'
[
    {
        "block_uuid": "11111111-1111-5111-8111-111111111111",
        "probe_count": 54,
        "assigned": true,
        "rir_record": {
            "registry": "ripencc", "country": "SE", "type": "ipv4",
            "start": "2.2.0.0", "value": 65536, "date": "20100712",
            "status": "allocated", "extensions": ["opaque-1"]
        },
        "rdap": {
            "query": "2.2.0.0", "service": "https://rdap.db.ripe.net/", "status": 200,
            "fetched_at": "2026-09-10T16:39:00Z", "error": null,
            "summary": {
                "handle": "2.2.0.0 - 2.2.255.255", "name": "EXAMPLE-NET",
                "type": "ALLOCATED PA", "parent_handle": null,
                "start_address": "2.2.0.0", "end_address": "2.2.255.255",
                "country": "SE", "organization": "Example Operator AB", "event": {}
            },
            "document": {"entities": []}
        }
    },
    {
        "block_uuid": "22222222-2222-5222-8222-222222222222",
        "probe_count": 54,
        "assigned": false,
        "rir_record": {
            "registry": "arin", "country": "", "type": "ipv4",
            "start": "199.47.160.0", "value": 2048, "date": "",
            "status": "reserved", "extensions": [""]
        },
        "rdap": {
            "query": "199.47.160.0", "service": "https://rdap.arin.net/registry/",
            "status": 404, "fetched_at": "2026-09-10T16:39:01Z",
            "error": "HTTPError: 404", "summary": {}, "document": null
        }
    }
]
FIXTURE

cat > "$DIRECTORY_DATA/05_ip_probe_http.json" <<'FIXTURE'
{
    "observed_at": "2026-09-10T22:11:22Z",
    "parameters": {"port": 80},
    "counts": {},
    "observations": [
        {"address": "2.2.2.2", "outcome": "http_response", "http_status": 301, "elapsed_ms": 150},
        {"address": "199.47.167.2", "outcome": "connect_refused", "http_status": null, "elapsed_ms": 80}
    ]
}
FIXTURE

cat > "$DIRECTORY_DATA/06_ip_probe_characterize.json" <<'FIXTURE'
{
    "observed_at": "2026-09-11T10:06:00Z",
    "parameters": {
        "http_port": 80, "https_port": 443, "control_count": 12, "thread": 16,
        "timeout_seconds": 5.0, "target_count": 2, "limit": null,
        "host_unrelated": "ip-telescope-probe.invalid",
        "ms_floor_geosynchronous": 238.7, "ms_floor_moon": 2564.4,
        "blind_spot_seconds": 5.0, "wave_two_count": 4
    },
    "blocks": [],
    "isolation_summary": [],
    "observations": [
        {
            "address": "2.2.2.2", "is_probe": true, "octet": [2, 2, 2, 2],
            "http": {"host": "2.2.2.2", "scheme": "http", "outcome": "http_response",
                     "http_status": 301, "header": {"server": "nginx"}, "body_bytes": 162,
                     "body_sha256": "aaaa1111", "body_prefix": "<html>301</html>", "elapsed_ms": 150,
                     "error": null, "certificate": null},
            "http_host_other": {"host": "ip-telescope-probe.invalid", "scheme": "http",
                                "outcome": "http_response", "http_status": 301,
                                "header": {}, "body_bytes": 162, "body_sha256": "aaaa1111",
                                "body_prefix": "<html>301</html>", "elapsed_ms": 150,
                                "error": null, "certificate": null},
            "https": {"outcome": "certificate_unverified", "http_status": 200, "header": {},
                      "body_bytes": 0, "body_sha256": null, "body_prefix": null,
                      "elapsed_ms": 900, "error": "expired",
                      "certificate": {"verified": false, "subject": [{"name": "commonName", "value": "ology.com"}],
                                      "issuer": [{"name": "organizationName", "value": "Let's Encrypt"}],
                                      "not_before": "Mar  2 12:14:32 2025 GMT",
                                      "not_after": "May 31 12:14:31 2025 GMT",
                                      "subject_alt_name": [], "sha256": "cc", "self_signed": false,
                                      "covers_ip": null}},
            "ptr": {"name": null, "names": [], "error": null},
            "latency": {"sample_ms": [8, 9, 12], "ms_min": 8, "ms_median": 9, "ms_jitter": 4,
                        "connected": true, "quantum": "none",
                        "ms_floor_geosynchronous": 238.7, "ms_floor_moon": 2564.4},
            "signal": {}, "block_uuid": "11111111-1111-5111-8111-111111111111",
            "phase3_outcome": "http_response", "role": "anomaly",
            "isolation": {"responded": true, "isolated": false, "neighbour": [
                {"offset": -1, "address": "2.2.2.1", "measured": true, "outcome": "http_response", "responded": true},
                {"offset": 1, "address": "2.2.2.3", "measured": true, "outcome": "http_response", "responded": true}]}
        },
        {
            "address": "199.47.167.2", "is_probe": true, "octet": [199, 47, 167, 2],
            "http": {"host": "199.47.167.2", "scheme": "http", "outcome": "connect_refused",
                     "http_status": null, "header": {}, "body_bytes": 0, "body_sha256": null,
                     "body_prefix": null, "elapsed_ms": 80, "error": "connection refused",
                     "certificate": null},
            "http_host_other": {"host": "ip-telescope-probe.invalid", "scheme": "http",
                                "outcome": "connect_refused", "http_status": null, "header": {},
                                "body_bytes": 0, "body_sha256": null, "body_prefix": null,
                                "elapsed_ms": 80, "error": "connection refused", "certificate": null},
            "https": {"outcome": "timeout", "http_status": null, "header": {}, "body_bytes": 0,
                      "body_sha256": null, "body_prefix": null, "elapsed_ms": 5000,
                      "error": "timed out", "certificate": null},
            "ptr": {"name": null, "names": [], "error": null},
            "latency": {"sample_ms": [79, 80, 81], "ms_min": 79, "ms_median": 80, "ms_jitter": 2,
                        "connected": false, "quantum": "none",
                        "ms_floor_geosynchronous": 238.7, "ms_floor_moon": 2564.4},
            "signal": {}, "block_uuid": "22222222-2222-5222-8222-222222222222",
            "phase3_outcome": "connect_refused", "role": "anomaly",
            "isolation": {"responded": true, "isolated": true, "neighbour": [
                {"offset": -1, "address": "199.47.167.1", "measured": true, "outcome": "timeout", "responded": false},
                {"offset": 1, "address": "199.47.167.3", "measured": true, "outcome": "timeout", "responded": false}]}
        }
    ]
}
FIXTURE

cat > "$DIRECTORY_TEST/model.json" <<'FIXTURE'
{
    "note": "fixture",
    "site": [
        {
            "block_start": "2.2.0.0",
            "name": "Site X",
            "verdict": "Incidental",
            "confidence": "High",
            "evidence": ["The range answers as one, which is configuration."],
            "falsifier": "A second vantage point disagreeing would change it.",
            "record": "../records-01-probe-characterization.html"
        }
    ]
}
FIXTURE

if ! output_report=$(python3 "$PROGRAM_REPORT" \
    --data-directory "$DIRECTORY_DATA" \
    --site-directory "$DIRECTORY_SITE" \
    --template "$REPOSITORY_ROOT/site.in/template.html" \
    --model "$DIRECTORY_TEST/model.json"); then
    fail "probe report failed: $output_report"
fi
case "$output_report" in
    *'106 probe page'*) fail "the report counted the wrong number of probes" ;;
    *'2 probe page'*) ;;
    *) fail "unexpected report line: $output_report" ;;
esac

[ -s "$DIRECTORY_SITE/probes.html" ] || fail 'the probe index was not written'
[ -s "$DIRECTORY_SITE/probes/2.2.2.2.html" ] || fail 'the first probe page was not written'
[ -s "$DIRECTORY_SITE/probes/199.47.167.2.html" ] || fail 'the second probe page was not written'

python3 - "$DIRECTORY_SITE" <<'PYTHON_CHECK' || fail "the probe pages are wrong"
import pathlib
import sys

directory_site = pathlib.Path(sys.argv[1])
text_index = (directory_site / "probes.html").read_text(encoding="utf-8")
text_page = (directory_site / "probes" / "2.2.2.2.html").read_text(encoding="utf-8")
text_isolated = (directory_site / "probes" / "199.47.167.2.html").read_text(encoding="utf-8")

# the index lists each probe and counts what they have in common
assert "probes/2.2.2.2.html" in text_index, "the index does not link the first probe"
assert "probes/199.47.167.2.html" in text_index, "the index does not link the second probe"
assert "have in common" in text_index, "the index does not summarise the set"
assert "Not one was host-aware" in text_index or "host-aware" in text_index, \
    "the index does not report the catch-all finding"

# the page carries the nine tests, with a reading for each
for text_test in ("1. Registry custody", "2. Ranging (isolation)", "3. Catch-all",
                  "4. Uniformity", "5. Identity", "6. Stability", "7. Distance",
                  "8. Self-explanation", "9. Concealment"):
    assert text_test in text_page, f"missing test on the page: {text_test}"

# the tests that were run say what they saw
assert "ology.com" in text_page, "the certificate is not reported"
assert "floor 8 ms" in text_page, "the light-speed floor is not reported"
assert "One page repeated across many addresses" in text_page, "the uniformity reading is missing"
assert "is addressed to this address" in text_isolated, "the isolation reading is missing"
assert "Not measured for this address" in text_page, "an unrun test must say so"

# the verdict the probe inherits, and the honest note that it is block-scale
assert "Site X: Incidental" in text_page, "the site verdict is missing"
assert "What would change it" in text_page, "the falsifier is missing"
assert "unclassified" in text_isolated or "No site verdict covers this block" in text_isolated, \
    "a block with no verdict must say so"

# the stylesheet stays out of the body
text_head = text_page[: text_page.index("</head>")]
text_body = text_page[text_page.index("</head>") :]
assert ".probe {" in text_head, "the stylesheet is not in the head"
assert ".probe {" not in text_body, "stylesheet text is leaking into the page body"
PYTHON_CHECK

echo '10-probe-report: ok'
exit 0
