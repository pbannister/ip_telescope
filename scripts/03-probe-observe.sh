#!/bin/sh
#
# 03-probe-observe.sh: phase 3 - HTTP GET every ip_probe that no operator holds.
#
# Calls the observer in sources/; performs no work of its own.
# Every option of the observer is accepted and passed through, for example:
#   sh scripts/03-probe-observe.sh --limit 100
#   sh scripts/03-probe-observe.sh --thread 128 --timeout 3
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

DIRECTORY_DATA="$REPOSITORY_ROOT/dataflow.out"

python3 "$REPOSITORY_ROOT/sources/ip_probe_observe.py" --data-directory "$DIRECTORY_DATA" "$@"
