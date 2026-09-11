#!/bin/sh
#
# Work-product reuse test (features 03, 04, and 05).
#
# Tier: portable. Proves that each program keeps a work product that already
# exists, and writes it again only when --refresh is given. The work products
# cost seconds to hours to build - the phase 3 pass costs half an hour of
# live Internet probing - so a silent rebuild is a real loss.
#
# No network is used: the only endpoints are a closed loopback port, so the
# RDAP and HTTP probes fail in the fast, refused way.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_GENERATE="$REPOSITORY_ROOT/sources/ip_probe_generate.py"
PROGRAM_COLLECT="$REPOSITORY_ROOT/sources/ip_block_collect.py"
PROGRAM_ENRICH="$REPOSITORY_ROOT/sources/ip_block_enrich.py"
PROGRAM_OBSERVE="$REPOSITORY_ROOT/sources/ip_probe_observe.py"

DIRECTORY_TEST=$(mktemp -d)
trap 'rm -rf "$DIRECTORY_TEST"' EXIT

DIRECTORY_DATA="$DIRECTORY_TEST/dataflow.out"
DIRECTORY_RAW="$DIRECTORY_DATA/raw"
mkdir -p "$DIRECTORY_RAW"

fail() {
    echo "07-work-product-reuse: $1" >&2
    exit 1
}

stamp_get() {
    stat -c '%y' "$1"
}

digest_get() {
    sha256sum "$1" | cut -d' ' -f1
}

assert_kept() {
    FILE_CHECK=$1
    STAMP_BEFORE=$2
    DIGEST_BEFORE=$3
    TEXT_LABEL=$4
    if [ "$STAMP_BEFORE" != "$(stamp_get "$FILE_CHECK")" ]; then
        fail "$TEXT_LABEL: the file was rewritten"
    fi
    if [ "$DIGEST_BEFORE" != "$(digest_get "$FILE_CHECK")" ]; then
        fail "$TEXT_LABEL: the file content changed"
    fi
}

expect_prefix() {
    TEXT_OUTPUT=$1
    TEXT_PREFIX=$2
    TEXT_LABEL=$3
    case "$TEXT_OUTPUT" in
        "$TEXT_PREFIX"*) ;;
        *) fail "$TEXT_LABEL: expected '$TEXT_PREFIX...', got: $TEXT_OUTPUT" ;;
    esac
}

expect_contains() {
    TEXT_OUTPUT=$1
    TEXT_NEEDLE=$2
    TEXT_LABEL=$3
    case "$TEXT_OUTPUT" in
        *"$TEXT_NEEDLE"*) ;;
        *) fail "$TEXT_LABEL: expected '$TEXT_NEEDLE', got: $TEXT_OUTPUT" ;;
    esac
}

PORT_DEAD=$(python3 -c '
import socket
socket_probe = socket.socket()
socket_probe.bind(("127.0.0.1", 0))
print(socket_probe.getsockname()[1])
socket_probe.close()
')

# --- phase 1: the probe list ------------------------------------------------
FILE_PROBE="$DIRECTORY_DATA/01_ip_probe.json"

output=$(python3 "$PROGRAM_GENERATE" --first 162 --output "$FILE_PROBE")
expect_prefix "$output" 'write:' "probe first run"
STAMP_PROBE=$(stamp_get "$FILE_PROBE")
DIGEST_PROBE=$(digest_get "$FILE_PROBE")

output=$(python3 "$PROGRAM_GENERATE" --first 162 --output "$FILE_PROBE")
expect_prefix "$output" 'reuse:' "probe second run"
assert_kept "$FILE_PROBE" "$STAMP_PROBE" "$DIGEST_PROBE" "probe list"

output=$(python3 "$PROGRAM_GENERATE" --first 162 --output "$FILE_PROBE" --refresh)
expect_prefix "$output" 'write:' "probe --refresh run"

# --- phase 2: the blocks ----------------------------------------------------
cat > "$FILE_PROBE" <<'FIXTURE'
[
    "2.2.2.2",
    "2.2.2.3",
    "5.5.5.5",
    "7.7.7.7"
]
FIXTURE

for text_registry in afrinic apnic arin lacnic ripencc; do
    echo "# delegation fixture: $text_registry" \
        > "$DIRECTORY_RAW/delegated-$text_registry-extended-latest"
done
cat >> "$DIRECTORY_RAW/delegated-ripencc-extended-latest" <<'FIXTURE'
ripencc|SE|ipv4|2.2.0.0|65536|20100712|allocated|opaque-1
FIXTURE
cat >> "$DIRECTORY_RAW/delegated-apnic-extended-latest" <<'FIXTURE'
apnic|CN|ipv4|5.5.5.0|256|20100713|reserved|
FIXTURE

FILE_BLOCK="$DIRECTORY_DATA/02_ip_block.json"
FILE_MAPPED="$DIRECTORY_DATA/03_ip_probe.json"
FILE_OPEN="$DIRECTORY_DATA/04_ip_probe.json"

output=$(python3 "$PROGRAM_COLLECT" \
    --raw-directory "$DIRECTORY_RAW" --data-directory "$DIRECTORY_DATA")
expect_prefix "$output" 'collect: block=' "block first run"
STAMP_BLOCK=$(stamp_get "$FILE_BLOCK")
DIGEST_BLOCK=$(digest_get "$FILE_BLOCK")
STAMP_MAPPED=$(stamp_get "$FILE_MAPPED")
DIGEST_MAPPED=$(digest_get "$FILE_MAPPED")
STAMP_OPEN=$(stamp_get "$FILE_OPEN")
DIGEST_OPEN=$(digest_get "$FILE_OPEN")

output=$(python3 "$PROGRAM_COLLECT" \
    --raw-directory "$DIRECTORY_RAW" --data-directory "$DIRECTORY_DATA")
expect_prefix "$output" 'collect: reuse=yes' "block second run"
assert_kept "$FILE_BLOCK" "$STAMP_BLOCK" "$DIGEST_BLOCK" "block file"
assert_kept "$FILE_MAPPED" "$STAMP_MAPPED" "$DIGEST_MAPPED" "probe-to-block file"
assert_kept "$FILE_OPEN" "$STAMP_OPEN" "$DIGEST_OPEN" "unheld probe file"

output=$(python3 "$PROGRAM_COLLECT" \
    --raw-directory "$DIRECTORY_RAW" --data-directory "$DIRECTORY_DATA" --refresh)
expect_prefix "$output" 'collect: block=' "block --refresh run"

# --- phase 2 enrichment: the RDAP record ------------------------------------
output=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DATA" \
    --raw-directory "$DIRECTORY_RAW" \
    --service "http://127.0.0.1:$PORT_DEAD" \
    --rate 0 --thread 2 --retry 1 --retry-wait 0 --timeout 2)
expect_contains "$output" 'enrich: block=' "enrich first run"
STAMP_ENRICH=$(stamp_get "$FILE_BLOCK")
DIGEST_ENRICH=$(digest_get "$FILE_BLOCK")

output=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DATA" \
    --raw-directory "$DIRECTORY_RAW" \
    --service "http://127.0.0.1:$PORT_DEAD" \
    --rate 0 --thread 2 --retry 1 --retry-wait 0 --timeout 2)
expect_contains "$output" 'enrich: reuse=yes' "enrich second run"
assert_kept "$FILE_BLOCK" "$STAMP_ENRICH" "$DIGEST_ENRICH" "enriched block file"

# A retry of the failed blocks is deliberate, and must ask again.
output=$(python3 "$PROGRAM_ENRICH" \
    --data-directory "$DIRECTORY_DATA" \
    --raw-directory "$DIRECTORY_RAW" \
    --service "http://127.0.0.1:$PORT_DEAD" \
    --rate 0 --thread 2 --retry 1 --retry-wait 0 --timeout 2 --retry-failed)
case "$output" in
    *'query=2'*) ;;
    *) fail "--retry-failed did not ask for the failed blocks: $output" ;;
esac

# --- phase 3: the HTTP observations -----------------------------------------
printf '[\n    "127.0.0.1"\n]\n' > "$FILE_OPEN"

FILE_HTTP="$DIRECTORY_DATA/05_ip_probe_http.json"

output=$(python3 "$PROGRAM_OBSERVE" \
    --data-directory "$DIRECTORY_DATA" \
    --port "$PORT_DEAD" --timeout 2)
expect_prefix "$output" 'observe: target=1' "observe first run"
STAMP_HTTP=$(stamp_get "$FILE_HTTP")
DIGEST_HTTP=$(digest_get "$FILE_HTTP")

output=$(python3 "$PROGRAM_OBSERVE" \
    --data-directory "$DIRECTORY_DATA" \
    --port "$PORT_DEAD" --timeout 2)
expect_prefix "$output" 'reuse:' "observe second run"
assert_kept "$FILE_HTTP" "$STAMP_HTTP" "$DIGEST_HTTP" "observation file"

output=$(python3 "$PROGRAM_OBSERVE" \
    --data-directory "$DIRECTORY_DATA" \
    --port "$PORT_DEAD" --timeout 2 --refresh)
expect_prefix "$output" 'observe: target=1' "observe --refresh run"

echo '07-work-product-reuse: ok'
exit 0
