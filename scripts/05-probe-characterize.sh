#!/bin/sh
#
# 05-probe-characterize.sh: phase 4 - characterize the anomalous ip_probe.
#
# Calls the characterizer in sources/; performs no work of its own.
# Every option of the characterizer is accepted and passed through, for example:
#   sh scripts/05-probe-characterize.sh --limit 6
#   sh scripts/05-probe-characterize.sh --control-count 4 --refresh
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

DIRECTORY_DATA="$REPOSITORY_ROOT/dataflow.out"

python3 "$REPOSITORY_ROOT/sources/ip_probe_characterize.py" \
    --data-directory "$DIRECTORY_DATA" \
    "$@"
