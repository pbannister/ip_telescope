#!/bin/sh
#
# Phase 2 enrichment test: RDAP metadata for address blocks
# (feature 04-block-collection, RDAP enrichment requirements).
#
# Tier: portable. A local HTTP server plays the RDAP service, so the test
# needs no network and no registry access.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_ENRICH="$REPOSITORY_ROOT/sources/ip_block_enrich.py"

DIRECTORY_TEST=$(mktemp -d)
PID_SERVER=''

cleanup() {
    if [ -n "$PID_SERVER" ]; then
        kill "$PID_SERVER" 2>/dev/null || true
        wait "$PID_SERVER" 2>/dev/null || true
    fi
    rm -rf "$DIRECTORY_TEST"
}
trap cleanup EXIT

fail() {
    echo "06-block-enrich: $1" >&2
    exit 1
}

DIRECTORY_DATA="$DIRECTORY_TEST/data"
DIRECTORY_RAW="$DIRECTORY_TEST/raw"
DIRECTORY_WEB="$DIRECTORY_TEST/web"
mkdir -p "$DIRECTORY_DATA" "$DIRECTORY_RAW" "$DIRECTORY_WEB/ip"

# Two blocks: one the fake registry knows, one it does not.
cat > "$DIRECTORY_DATA/02_ip_block.json" <<'FIXTURE'
[
    {
        "block_uuid": "11111111-1111-5111-8111-111111111111",
        "probe_count": 2916,
        "assigned": true,
        "rir_record": {
            "registry": "ripencc",
            "country": "SE",
            "type": "ipv4",
            "start": "2.2.0.0",
            "value": 65536,
            "date": "20100712",
            "status": "allocated",
            "extensions": ["opaque-1"]
        }
    },
    {
        "block_uuid": "22222222-2222-5222-8222-222222222222",
        "probe_count": 108,
        "assigned": false,
        "rir_record": {
            "registry": "arin",
            "country": "",
            "type": "ipv4",
            "start": "23.131.1.0",
            "value": 768,
            "date": "",
            "status": "reserved",
            "extensions": [""]
        }
    }
]
FIXTURE

cat > "$DIRECTORY_WEB/ip/2.2.0.0" <<'FIXTURE'
{
    "objectClassName": "ip network",
    "handle": "2.2.0.0 - 2.2.255.255",
    "name": "SE-EXAMPLE-20100712",
    "type": "ALLOCATED PA",
    "country": "SE",
    "startAddress": "2.2.0.0",
    "endAddress": "2.2.255.255",
    "parentHandle": "0.0.0.0 - 255.255.255.255",
    "events": [
        {"eventAction": "registration", "eventDate": "2010-07-12T00:00:00Z"},
        {"eventAction": "last changed", "eventDate": "2016-04-20T10:11:12Z"}
    ],
    "entities": [
        {
            "roles": ["registrant"],
            "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "Example Operator AB"]]]
        }
    ]
}
FIXTURE

PORT_SERVER=$(python3 -c '
import socket
socket_probe = socket.socket()
socket_probe.bind(("127.0.0.1", 0))
print(socket_probe.getsockname()[1])
socket_probe.close()
')

python3 -m http.server "$PORT_SERVER" --bind 127.0.0.1 --directory "$DIRECTORY_WEB" \
    > /dev/null 2>&1 &
PID_SERVER=$!

count_try=0
while [ "$count_try" -lt 50 ]; do
    if python3 -c "
import socket, sys
socket_probe = socket.socket()
socket_probe.settimeout(0.5)
sys.exit(0 if 0 == socket_probe.connect_ex(('127.0.0.1', $PORT_SERVER)) else 1)
"; then
        break
    fi
    count_try=$((count_try + 1))
    sleep 0.1
done
if [ "$count_try" -ge 50 ]; then
    fail 'local RDAP test server did not start'
fi

if ! output_enrich=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DATA" \
    --raw-directory "$DIRECTORY_RAW" \
    --service "http://127.0.0.1:$PORT_SERVER" \
    --rate 0 \
    --timeout 5); then
    fail "enricher failed: $output_enrich"
fi

python3 - "$DIRECTORY_DATA/02_ip_block.json" "$DIRECTORY_RAW/RDAP-CACHE.jsonl" \
    <<'PYTHON_CHECK' || fail "enrichment output is wrong"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    list_block = json.load(handle)

block_known, block_missing = list_block
assert 200 == block_known["rdap"]["status"], block_known["rdap"]["status"]
assert "SE-EXAMPLE-20100712" == block_known["rdap"]["summary"]["name"]
assert "Example Operator AB" == block_known["rdap"]["summary"]["organization"]
assert "2010-07-12T00:00:00Z" == block_known["rdap"]["summary"]["event"]["registration"]
assert "ip network" == block_known["rdap"]["document"]["objectClassName"]
assert "2.2.0.0" == block_known["rdap"]["query"]

assert 404 == block_missing["rdap"]["status"], block_missing["rdap"]
assert None is block_missing["rdap"]["document"]
assert {} == block_missing["rdap"]["summary"]
assert "11111111-1111-5111-8111-111111111111" == block_known["block_uuid"]
assert 2916 == block_known["probe_count"]

with open(sys.argv[2], encoding="utf-8") as handle:
    list_cache = [json.loads(line) for line in handle if line.strip()]
assert 2 == len(list_cache), len(list_cache)
PYTHON_CHECK

# A second run must reuse the cache and change nothing.
DIGEST_FIRST=$(sha256sum "$DIRECTORY_DATA/02_ip_block.json" | cut -d' ' -f1)
if ! output_enrich=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DATA" \
    --raw-directory "$DIRECTORY_RAW" \
    --service "http://127.0.0.1:$PORT_SERVER" \
    --rate 0); then
    fail "second enricher run failed: $output_enrich"
fi
DIGEST_SECOND=$(sha256sum "$DIRECTORY_DATA/02_ip_block.json" | cut -d' ' -f1)
if [ "$DIGEST_FIRST" != "$DIGEST_SECOND" ]; then
    fail "cached run changed the block file"
fi
case "$output_enrich" in
    *'enrich: queried=0'*) ;;
    *) fail "cached run still queried the service: $output_enrich" ;;
esac

# A service that never answers must not stall the run, and its failures must
# not be cached as if they were answers.
DIRECTORY_DEAD="$DIRECTORY_TEST/dead"
mkdir -p "$DIRECTORY_DEAD/dataflow.out" "$DIRECTORY_DEAD/raw"

python3 - "$DIRECTORY_DEAD/dataflow.out/02_ip_block.json" <<'PYTHON_FIXTURE'
import json
import sys

list_block = []
for index_block in range(5):
    list_block.append(
        {
            "block_uuid": f"33333333-3333-5333-8333-33333333333{index_block}",
            "probe_count": 1,
            "assigned": True,
            "rir_record": {
                "registry": "arin",
                "country": "US",
                "type": "ipv4",
                "start": f"23.191.15{index_block}.0",
                "value": 256,
                "date": "20100101",
                "status": "allocated",
                "extensions": [""],
            },
        }
    )
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(list_block, handle, indent=4)
PYTHON_FIXTURE

PORT_DEAD=$(python3 -c '
import socket
socket_probe = socket.socket()
socket_probe.bind(("127.0.0.1", 0))
print(socket_probe.getsockname()[1])
socket_probe.close()
')

if ! output_dead=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DEAD/dataflow.out" \
    --raw-directory "$DIRECTORY_DEAD/raw" \
    --service "http://127.0.0.1:$PORT_DEAD" \
    --rate 0 --thread 4 --retry 1 --retry-wait 0 --timeout 2); then
    fail "enricher failed against a dead service: $output_dead"
fi
case "$output_dead" in
    *service_closed=*) ;;
    *) fail "dead service was not closed: $output_dead" ;;
esac

python3 - "$DIRECTORY_DEAD/dataflow.out/02_ip_block.json" <<'PYTHON_CHECK' || fail "dead-service run is wrong"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    list_block = json.load(handle)
assert 5 == len(list_block)
for document_block in list_block:
    assert None is document_block["rdap"]["status"], document_block["rdap"]
    assert {} == document_block["rdap"]["summary"]
PYTHON_CHECK

# A default run leaves the failed blocks as they stand: a work product is
# not rewritten behind the owner's back.
if ! output_keep=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DEAD/dataflow.out" \
    --raw-directory "$DIRECTORY_DEAD/raw" \
    --service "http://127.0.0.1:$PORT_DEAD" \
    --rate 0 --thread 4 --retry 1 --retry-wait 0 --timeout 2); then
    fail "enricher failed on the keep run: $output_keep"
fi
case "$output_keep" in
    *'enrich: reuse=yes'*) ;;
    *) fail "a default run rewrote the block file: $output_keep" ;;
esac

# Asking again is deliberate, and only --retry-failed does it.
if ! output_retry=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DEAD/dataflow.out" \
    --raw-directory "$DIRECTORY_DEAD/raw" \
    --service "http://127.0.0.1:$PORT_DEAD" \
    --rate 0 --thread 4 --retry 1 --retry-wait 0 --timeout 2 --retry-failed); then
    fail "enricher failed on the retry run: $output_retry"
fi
case "$output_retry" in
    *'query=5'*) ;;
    *) fail "--retry-failed did not ask the failed blocks again: $output_retry" ;;
esac

echo '06-block-enrich: ok'
exit 0
