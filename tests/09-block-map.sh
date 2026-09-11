#!/bin/sh
#
# Block map test (the browsable map of the collected blocks).
#
# Tier: portable. Small fixtures stand in for the work products, so the test
# needs neither the real 770 MB of data nor a network.
#
# It checks the three things the map must do: lay the blocks out in address
# order with the gaps visible, give every block its own page with its data,
# and publish nothing that carries registrant contact details.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_MAP="$REPOSITORY_ROOT/sources/ip_block_map.py"

DIRECTORY_TEST=$(mktemp -d)
trap 'rm -rf "$DIRECTORY_TEST"' EXIT

DIRECTORY_DATA="$DIRECTORY_TEST/dataflow.out"
DIRECTORY_SITE="$DIRECTORY_TEST/site.out"
mkdir -p "$DIRECTORY_DATA" "$DIRECTORY_SITE"

fail() {
    echo "09-block-map: $1" >&2
    exit 1
}

# Two blocks in 2.0.0.0/8 with a gap between them: one operator-held, one not.
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
        "derived": {"address_end": "2.2.255.255", "prefix": "2.2.0.0/16", "opaque_id": "opaque-1"},
        "rdap": {
            "query": "2.2.0.0", "service": "https://rdap.db.ripe.net/", "status": 200,
            "fetched_at": "2026-09-10T16:39:00Z", "error": null,
            "summary": {
                "handle": "2.2.0.0 - 2.2.255.255", "name": "EXAMPLE-NET",
                "type": "ALLOCATED PA", "parent_handle": "2.0.0.0 - 2.255.255.255",
                "start_address": "2.2.0.0", "end_address": "2.2.255.255",
                "country": "SE", "organization": "Example Operator AB",
                "event": {"registration": "2010-07-12T00:00:00Z"}
            },
            "document": {
                "entities": [
                    {"roles": ["registrant"], "vcardArray": ["vcard", [["fn", {}, "text", "Example Operator AB"], ["email", {}, "text", "noc@example.invalid"]]]}
                ]
            }
        }
    },
    {
        "block_uuid": "22222222-2222-5222-8222-222222222222",
        "probe_count": 108,
        "assigned": false,
        "rir_record": {
            "registry": "arin", "country": "", "type": "ipv4",
            "start": "2.9.0.0", "value": 768, "date": "",
            "status": "reserved", "extensions": [""]
        },
        "derived": {"address_end": "2.9.2.255", "prefix": null, "opaque_id": ""},
        "rdap": {
            "query": "2.9.0.0", "service": "https://rdap.arin.net/registry/", "status": 404,
            "fetched_at": "2026-09-10T16:39:01Z", "error": "HTTPError: 404",
            "summary": {}, "document": null
        }
    }
]
FIXTURE

# One probe in the first block that answered, and its phase 4 isolation.
cat > "$DIRECTORY_DATA/03_ip_probe.json" <<'FIXTURE'
[
    ["2.2.2.2", "11111111-1111-5111-8111-111111111111"],
    ["2.2.2.3", "11111111-1111-5111-8111-111111111111"],
    ["2.9.2.2", "22222222-2222-5222-8222-222222222222"]
]
FIXTURE

cat > "$DIRECTORY_DATA/05_ip_probe_http.json" <<'FIXTURE'
{
    "observed_at": "2026-09-10T22:11:22Z",
    "parameters": {"port": 80},
    "counts": {"http_response": 1},
    "observations": [
        {"address": "2.2.2.2", "outcome": "http_response", "http_status": 200},
        {"address": "2.2.2.3", "outcome": "timeout"}
    ]
}
FIXTURE

cat > "$DIRECTORY_DATA/06_ip_probe_characterize.json" <<'FIXTURE'
{
    "observed_at": "2026-09-11T10:06:00Z",
    "parameters": {},
    "blocks": [],
    "isolation_summary": [],
    "observations": [
        {"address": "2.2.2.2", "role": "anomaly", "http": {"outcome": "http_response"},
         "isolation": {"responded": true, "isolated": true}}
    ]
}
FIXTURE

if ! output_map=$(python3 "$PROGRAM_MAP" \
    --data-directory "$DIRECTORY_DATA" \
    --site-directory "$DIRECTORY_SITE" \
    --template "$REPOSITORY_ROOT/site.in/template.html"); then
    fail "map generator failed: $output_map"
fi

[ -s "$DIRECTORY_SITE/blocks.html" ] || fail 'the map index was not written'
[ -s "$DIRECTORY_SITE/blocks/octet-002.html" ] || fail 'the octet page was not written'
[ -s "$DIRECTORY_SITE/blocks/11111111-1111-5111-8111-111111111111.html" ] \
    || fail 'the block page was not written'

python3 - "$DIRECTORY_SITE" <<'PYTHON_CHECK' || fail "the map content is wrong"
import pathlib
import sys

directory_site = pathlib.Path(sys.argv[1])
text_index = (directory_site / "blocks.html").read_text(encoding="utf-8")
text_octet = (directory_site / "blocks" / "octet-002.html").read_text(encoding="utf-8")
text_block = (
    directory_site / "blocks" / "11111111-1111-5111-8111-111111111111.html"
).read_text(encoding="utf-8")
text_reserved = (
    directory_site / "blocks" / "22222222-2222-5222-8222-222222222222.html"
).read_text(encoding="utf-8")

# The index lists the octet and the irregularity classes.
assert "2.0.0.0/8" in text_index, "the index does not list the octet"
assert "blocks/octet-002.html" in text_index, "the index does not link the octet page"
assert "no object" in text_index, "the index does not name the RDAP 404 class"

# The octet page is in address order, marks the status, and shows the gap.
assert text_octet.index("2.2.0.0") < text_octet.index("2.9.0.0"), "blocks are out of order"
assert "st-allocated" in text_octet, "the status colour is missing"
assert "st-reserved" in text_octet, "the reserved block is not marked"
assert "gap:" in text_octet, "the gap between the blocks is not shown"
assert "2.3.0.0" in text_octet, "the gap start is not described"
assert "2.8.255.255" in text_octet, "the gap end is not described"

# The block page carries the data and links back.
assert "Example Operator AB" in text_block, "the organization is missing"
assert "EXAMPLE-NET" in text_block, "the RDAP name is missing"
assert "2.2.2.2*" in text_block, "the responding probe is not marked"
assert "Isolated" in text_block, "the phase 4 result is missing"
assert "../blocks.html" in text_block, "the back link is missing"
assert "404" in text_reserved, "the 404 state is missing on the second block"
PYTHON_CHECK

# Publishing safety: no registrant contact details, and no leak-gate pattern.
if grep -rq 'noc@example.invalid' "$DIRECTORY_SITE"; then
    fail 'the map published a registrant contact address'
fi
PATTERNS='([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}|(^|[^0-9])(192\.168\.|10\.[0-9]{1,3}\.|172\.(1[6-9]|2[0-9]|3[01])\.)|preston|cainboy|/home/[a-zA-Z]|BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY'
if grep -rInE "$PATTERNS" "$DIRECTORY_SITE" > /dev/null; then
    fail 'the map output trips the leak gate'
fi

echo '09-block-map: ok'
exit 0
