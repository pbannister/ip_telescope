#!/bin/sh
#
# Phase 2 test: RIR block collection (feature 04-block-collection).
#
# Tier: portable. The test builds a small delegation fixture in a temporary
# directory and checks the three phase 2 outputs, so it needs no network and
# no generated data.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_COLLECT="$REPOSITORY_ROOT/sources/ip_block_collect.py"

DIRECTORY_TEST=$(mktemp -d)
trap 'rm -rf "$DIRECTORY_TEST"' EXIT

DIRECTORY_RAW="$DIRECTORY_TEST/raw"
DIRECTORY_DATA="$DIRECTORY_TEST/data"
mkdir -p "$DIRECTORY_RAW" "$DIRECTORY_DATA"

fail() {
    echo "04-block-collect: $1" >&2
    exit 1
}

# Five delegation files are required; four only carry a header.
for text_registry in afrinic apnic arin lacnic ripencc; do
    echo "# delegation fixture: $text_registry" > "$DIRECTORY_RAW/delegated-$text_registry-extended-latest"
done

cat >> "$DIRECTORY_RAW/delegated-ripencc-extended-latest" <<'FIXTURE'
ripencc|SE|ipv4|2.2.0.0|65536|20100712|allocated|8845474d-f97a-46b9-8799-dfbd4416d57d
ripencc|SE|ipv4|3.3.3.0|768|20100712|assigned|
FIXTURE

cat >> "$DIRECTORY_RAW/delegated-apnic-extended-latest" <<'FIXTURE'
apnic|CN|ipv4|5.5.5.0|256|20100713|available|
FIXTURE

cat >> "$DIRECTORY_RAW/delegated-arin-extended-latest" <<'FIXTURE'
arin|US|ipv4|11.11.0.0|65536|20100713|reserved|
FIXTURE

cat > "$DIRECTORY_DATA/01_ip_probe.json" <<'FIXTURE'
[
    "2.2.2.2",
    "2.2.2.3",
    "3.3.3.3",
    "5.5.5.5",
    "7.7.7.7",
    "11.11.11.11"
]
FIXTURE

if ! output_collect=$(python3 "$PROGRAM_COLLECT" \
    --raw-directory "$DIRECTORY_RAW" \
    --data-directory "$DIRECTORY_DATA"); then
    fail "collector failed: $output_collect"
fi

python3 - "$DIRECTORY_DATA" <<'PYTHON_CHECK' || fail "phase 2 outputs are wrong"
import json
import sys

directory_data = sys.argv[1]


def load(name):
    with open(f"{directory_data}/{name}", encoding="ascii") as handle:
        return json.load(handle)


list_block = load("02_ip_block.json")
list_assigned = load("03_ip_probe.json")
list_open = load("04_ip_probe.json")

assert 4 == len(list_block), f"expected 4 blocks, got {len(list_block)}"

by_start = {block["rir_record"]["start"]: block for block in list_block}
assert {"2.2.0.0", "3.3.3.0", "5.5.5.0", "11.11.0.0"} == set(by_start), set(by_start)

block_assigned = by_start["2.2.0.0"]
assert "ripencc" == block_assigned["rir_record"]["registry"]
assert "allocated" == block_assigned["rir_record"]["status"]
assert True is block_assigned["assigned"]
assert 2 == block_assigned["probe_count"]
assert "2.2.0.0/16" == block_assigned["derived"]["prefix"]
assert "2.2.255.255" == block_assigned["derived"]["address_end"]
assert "8845474d-f97a-46b9-8799-dfbd4416d57d" == block_assigned["derived"]["opaque_id"]

# 3.3.3.0 with 768 addresses is not a power of two, so it has no prefix.
block_odd = by_start["3.3.3.0"]
assert 768 == block_odd["rir_record"]["value"]
assert None is block_odd["derived"]["prefix"]
assert "3.3.5.255" == block_odd["derived"]["address_end"]
assert 1 == block_odd["probe_count"]
assert True is block_odd["assigned"]

assert False is by_start["5.5.5.0"]["assigned"]
assert False is by_start["11.11.0.0"]["assigned"]
assert "reserved" == by_start["11.11.0.0"]["rir_record"]["status"]

assert [["2.2.2.2", block_assigned["block_uuid"]],
        ["2.2.2.3", block_assigned["block_uuid"]],
        ["3.3.3.3", block_odd["block_uuid"]]] == list_assigned, list_assigned

assert ["5.5.5.5", "7.7.7.7", "11.11.11.11"] == list_open, list_open

for block in list_block:
    assert 36 == len(block["block_uuid"]), block["block_uuid"]
PYTHON_CHECK

# The block UUIDs must be stable across runs.
DIGEST_FIRST=$(sha256sum "$DIRECTORY_DATA/02_ip_block.json" | cut -d' ' -f1)
python3 "$PROGRAM_COLLECT" --raw-directory "$DIRECTORY_RAW" --data-directory "$DIRECTORY_DATA" > /dev/null
DIGEST_SECOND=$(sha256sum "$DIRECTORY_DATA/02_ip_block.json" | cut -d' ' -f1)
if [ "$DIGEST_FIRST" != "$DIGEST_SECOND" ]; then
    fail "block file is not reproducible: $DIGEST_FIRST != $DIGEST_SECOND"
fi

echo '04-block-collect: ok'
exit 0
