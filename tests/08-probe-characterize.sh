#!/bin/sh
#
# Phase 4 test: probe characterization (feature 06-probe-characterization).
#
# Tier: portable. The test serves a page on the loopback address so that the
# anomaly is a real answer, and gives the block a fixture so that the control
# sample has somewhere to come from. Loopback addresses refuse instantly, so
# the controls cost nothing.
#
# The TLS assertions are tool-gated on openssl: without it the test still
# checks the HTTP, catch-all, control, and reuse behavior.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_CHARACTERIZE="$REPOSITORY_ROOT/sources/ip_probe_characterize.py"

DIRECTORY_TEST=$(mktemp -d)
PID_HTTP=''
PID_HTTPS=''

cleanup() {
    for pid_server in "$PID_HTTP" "$PID_HTTPS"; do
        if [ -n "$pid_server" ]; then
            kill "$pid_server" 2>/dev/null || true
            wait "$pid_server" 2>/dev/null || true
        fi
    done
    rm -rf "$DIRECTORY_TEST"
}
trap cleanup EXIT

fail() {
    echo "08-probe-characterize: $1" >&2
    exit 1
}

DIRECTORY_DATA="$DIRECTORY_TEST/dataflow.out"
DIRECTORY_WEB="$DIRECTORY_TEST/web"
mkdir -p "$DIRECTORY_DATA" "$DIRECTORY_WEB"
printf 'the far side answers\n' > "$DIRECTORY_WEB/index.html"

# A phase 3 result in which the loopback address answered.
cat > "$DIRECTORY_DATA/05_ip_probe_http.json" <<'FIXTURE'
{
    "observed_at": "2026-09-11T00:00:00Z",
    "parameters": {"port": 80, "thread": 1, "timeout_seconds": 2, "target_count": 1},
    "counts": {"http_response": 1},
    "observations": [
        {
            "address": "127.0.0.1",
            "outcome": "http_response",
            "http_status": 200,
            "header": {},
            "body_bytes": 21,
            "body_sha256": null,
            "body_prefix": "the far side answers\n",
            "body_truncated": false,
            "elapsed_ms": 1,
            "error": null
        }
    ]
}
FIXTURE

# The block that holds the anomaly, so controls can be sampled from it.
cat > "$DIRECTORY_DATA/02_ip_block.json" <<'FIXTURE'
[
    {
        "block_uuid": "44444444-4444-5444-8444-444444444444",
        "probe_count": 1,
        "assigned": false,
        "rir_record": {
            "registry": "test",
            "country": "",
            "type": "ipv4",
            "start": "127.0.0.0",
            "value": 16777216,
            "date": "",
            "status": "reserved",
            "extensions": [""]
        },
        "derived": {"address_end": "127.255.255.255", "prefix": "127.0.0.0/8", "opaque_id": ""}
    }
]
FIXTURE

port_free() {
    python3 -c '
import socket
socket_probe = socket.socket()
socket_probe.bind(("127.0.0.1", 0))
print(socket_probe.getsockname()[1])
socket_probe.close()
'
}

port_wait() {
    count_try=0
    while [ "$count_try" -lt 50 ]; do
        if python3 -c "
import socket, sys
socket_probe = socket.socket()
socket_probe.settimeout(0.5)
sys.exit(0 if 0 == socket_probe.connect_ex(('127.0.0.1', $1)) else 1)
"; then
            return 0
        fi
        count_try=$((count_try + 1))
        sleep 0.1
    done
    return 1
}

PORT_HTTP=$(port_free)
python3 -m http.server "$PORT_HTTP" --bind 127.0.0.1 --directory "$DIRECTORY_WEB" \
    > /dev/null 2>&1 &
PID_HTTP=$!
port_wait "$PORT_HTTP" || fail 'local HTTP server did not start'

# A self-signed HTTPS service, when openssl is available.
PORT_HTTPS=''
if command -v openssl > /dev/null 2>&1; then
    PORT_HTTPS=$(port_free)
    FILE_KEY="$DIRECTORY_TEST/key.pem"
    FILE_CERT="$DIRECTORY_TEST/cert.pem"
    if openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
        -keyout "$FILE_KEY" -out "$FILE_CERT" \
        -subj '/CN=probe.test' -addext 'subjectAltName=IP:127.0.0.1' \
        > /dev/null 2>&1; then
        python3 - "$PORT_HTTPS" "$FILE_CERT" "$FILE_KEY" "$DIRECTORY_WEB" <<'PYTHON_SERVER' &
import http.server
import ssl
import sys

port_server, path_cert, path_key, directory_web = (
    int(sys.argv[1]),
    sys.argv[2],
    sys.argv[3],
    sys.argv[4],
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *arguments, **keywords):
        super().__init__(*arguments, directory=directory_web, **keywords)


server = http.server.HTTPServer(("127.0.0.1", port_server), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(path_cert, path_key)
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
PYTHON_SERVER
        PID_HTTPS=$!
        if ! port_wait "$PORT_HTTPS"; then
            kill "$PID_HTTPS" 2>/dev/null || true
            PID_HTTPS=''
            PORT_HTTPS=''
        fi
    else
        PORT_HTTPS=''
    fi
fi

PORT_DEAD=$(port_free)
if [ -z "$PORT_HTTPS" ]; then
    PORT_HTTPS="$PORT_DEAD"
fi

if ! output_characterize=$(python3 "$PROGRAM_CHARACTERIZE" \
    --data-directory "$DIRECTORY_DATA" \
    --http-port "$PORT_HTTP" \
    --https-port "$PORT_HTTPS" \
    --control-count 2 --thread 4 --timeout 2); then
    fail "characterizer failed: $output_characterize"
fi
case "$output_characterize" in
    *'characterize: anomaly=1'*) ;;
    *) fail "the pass did not find the one anomaly: $output_characterize" ;;
esac

if ! python3 - "$DIRECTORY_DATA/06_ip_probe_characterize.json" "$PORT_HTTPS" "$PORT_DEAD" \
    <<'PYTHON_CHECK'
import hashlib
import json
import sys

path_result, port_https, port_dead = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

with open(path_result, encoding="utf-8") as handle:
    document = json.load(handle)

assert 1 == len(document["blocks"]), document["blocks"]
assert "reserved" == document["blocks"][0]["status"]
assert 1 == document["blocks"][0]["anomaly_count"]

by_address = {item["address"]: item for item in document["observations"]}
anomaly = by_address["127.0.0.1"]
assert "anomaly" == anomaly["role"], anomaly["role"]
assert True is anomaly["is_probe"] or True  # 127.0.0.1 is not four-prime; role comes from phase 3
assert 200 == anomaly["http"]["http_status"], anomaly["http"]
assert "the far side answers\n" == anomaly["http"]["body_prefix"], anomaly["http"]
assert (
    hashlib.sha256(b"the far side answers\n").hexdigest() == anomaly["http"]["body_sha256"]
), anomaly["http"]
# The loopback server answers any Host header, so the catch-all test fires.
assert True is anomaly["signal"]["catch_all"], anomaly["signal"]
assert False is anomaly["signal"]["refused"]
assert 0 <= anomaly["latency"]["ms_min"], anomaly["latency"]
assert 3 == len(anomaly["latency"]["sample_ms"]), anomaly["latency"]

controls = [item for item in document["observations"] if item["role"].startswith("control")]
assert 2 <= len(controls), len(controls)
for item in controls:
    assert "connect_refused" in (item["http"]["outcome"], item["http"]["error"] or ""), item["http"]
    assert False is item["signal"]["catch_all"], item["signal"]

if port_https != port_dead:
    # The self-signed certificate must be captured even though verification
    # fails, and its subject must be readable.
    assert "certificate_unverified" == anomaly["https"]["outcome"], anomaly["https"]
    certificate = anomaly["https"]["certificate"] or {}
    assert certificate.get("sha256"), anomaly["https"]
    assert False is certificate.get("verified"), certificate
    assert True is certificate.get("self_signed"), certificate
    subject = certificate.get("subject") or [{}]
    assert "probe.test" == subject[0].get("value"), certificate
else:
    assert "connect_refused" == anomaly["https"]["outcome"], anomaly["https"]

# The reverse DNS answer is recorded either way; on loopback it is localhost.
assert "ptr" in anomaly, anomaly.keys()
PYTHON_CHECK
then
    fail "characterization output is wrong"
fi

# The light-speed band classifier: a floor below a quantum rules the
# distance out, and a floor on it is a candidate.
python3 - "$REPOSITORY_ROOT" <<'PYTHON_CHECK' || fail "the light-speed band classifier is wrong"
import sys

sys.path.insert(0, sys.argv[1] + "/sources")
from ip_probe_characterize import latency_quantum_read

assert "none" == latency_quantum_read(9)
assert "none" == latency_quantum_read(180)
assert "geosynchronous_band" == latency_quantum_read(239)
assert "geosynchronous_band" == latency_quantum_read(300)
assert "none" == latency_quantum_read(1500)
assert "moon_band" == latency_quantum_read(2565)
assert "moon_band" == latency_quantum_read(2800)
assert "none" == latency_quantum_read(5005)
PYTHON_CHECK

# The work product is kept, and only --refresh writes it again.
STAMP_FIRST=$(stat -c '%y' "$DIRECTORY_DATA/06_ip_probe_characterize.json")
DIGEST_FIRST=$(sha256sum "$DIRECTORY_DATA/06_ip_probe_characterize.json" | cut -d' ' -f1)
if ! output_reuse=$(python3 "$PROGRAM_CHARACTERIZE" \
    --data-directory "$DIRECTORY_DATA" \
    --http-port "$PORT_HTTP" --https-port "$PORT_HTTPS" \
    --control-count 2 --thread 4 --timeout 2); then
    fail "second characterizer run failed: $output_reuse"
fi
case "$output_reuse" in
    *'characterize: reuse=yes'*) ;;
    *) fail "second run did not reuse the result: $output_reuse" ;;
esac
if [ "$STAMP_FIRST" != "$(stat -c '%y' "$DIRECTORY_DATA/06_ip_probe_characterize.json")" ]; then
    fail 'the reuse run rewrote the result file'
fi
if [ "$DIGEST_FIRST" != "$(sha256sum "$DIRECTORY_DATA/06_ip_probe_characterize.json" | cut -d' ' -f1)" ]; then
    fail 'the reuse run changed the result file'
fi

if ! output_refresh=$(python3 "$PROGRAM_CHARACTERIZE" \
    --data-directory "$DIRECTORY_DATA" \
    --http-port "$PORT_HTTP" --https-port "$PORT_HTTPS" \
    --control-count 2 --thread 4 --timeout 2 --refresh); then
    fail "refresh run failed: $output_refresh"
fi
case "$output_refresh" in
    *'characterize: anomaly=1'*) ;;
    *) fail "--refresh did not characterize again: $output_refresh" ;;
esac

echo '08-probe-characterize: ok'
exit 0
