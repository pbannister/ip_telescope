#!/bin/sh
#
# Phase 3 test: HTTP observation of unassigned probes
# (feature 05-probe-observation).
#
# Tier: portable. The test runs a local HTTP server on the loopback address,
# so it proves both the answered path and the refused path without touching
# any address outside the host.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_OBSERVE="$REPOSITORY_ROOT/sources/ip_probe_observe.py"

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
    echo "05-probe-observe: $1" >&2
    exit 1
}

DIRECTORY_DATA="$DIRECTORY_TEST/data"
DIRECTORY_WEB="$DIRECTORY_TEST/web"
mkdir -p "$DIRECTORY_DATA" "$DIRECTORY_WEB"
printf 'the far side answers\n' > "$DIRECTORY_WEB/index.html"
printf '[\n    "127.0.0.1"\n]\n' > "$DIRECTORY_DATA/04_ip_probe.json"

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
    fail 'local test server did not start'
fi

# The answered path.
if ! output_observe=$(python3 "$PROGRAM_OBSERVE" \
    --data-directory "$DIRECTORY_DATA" \
    --port "$PORT_SERVER" \
    --timeout 2); then
    fail "observer failed: $output_observe"
fi

python3 - "$DIRECTORY_DATA/05_ip_probe_http.json" <<'PYTHON_CHECK' || fail "answered path is wrong"
import hashlib
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    document = json.load(handle)

assert 1 == document["parameters"]["target_count"], document["parameters"]
assert False is document["parameters"]["interrupted"]
assert {"http_response": 1} == document["counts"], document["counts"]

observation = document["observations"][0]
assert "127.0.0.1" == observation["address"]
assert "http_response" == observation["outcome"], observation
assert 200 == observation["http_status"], observation
assert "the far side answers\n" == observation["body_prefix"], observation
assert 21 == observation["body_bytes"], observation["body_bytes"]
assert hashlib.sha256(b"the far side answers\n").hexdigest() == observation["body_sha256"]
assert False is observation["body_truncated"]
assert 0 <= observation["elapsed_ms"]
PYTHON_CHECK

# The refused path: the same port with the server gone.
kill "$PID_SERVER" 2>/dev/null || true
wait "$PID_SERVER" 2>/dev/null || true
PID_SERVER=''

if ! output_observe=$(python3 "$PROGRAM_OBSERVE" \
    --data-directory "$DIRECTORY_DATA" \
    --port "$PORT_SERVER" \
    --timeout 2); then
    fail "observer failed on the refused path: $output_observe"
fi

python3 - "$DIRECTORY_DATA/05_ip_probe_http.json" <<'PYTHON_CHECK' || fail "refused path is wrong"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    document = json.load(handle)

observation = document["observations"][0]
assert "connect_refused" == observation["outcome"], observation
assert None is observation["http_status"], observation
PYTHON_CHECK

echo '05-probe-observe: ok'
exit 0
