#!/bin/sh
#
# 01-probe-generate.sh: phase 1 - write dataflow.out/01_ip_probe.json.
#
# Calls the generator in sources/; performs no work of its own.
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

FILE_PROBE="$REPOSITORY_ROOT/dataflow.out/01_ip_probe.json"

mkdir -p "$REPOSITORY_ROOT/dataflow.out"

python3 "$REPOSITORY_ROOT/sources/ip_probe_generate.py" --output "$FILE_PROBE" "$@"
