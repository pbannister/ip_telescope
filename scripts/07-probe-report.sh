#!/bin/sh
#
# 07-probe-report.sh: show the work for every address phase 4 examined.
#
# Calls the report generator in sources/; performs no work of its own.
# Writes site.out/probes.html and site.out/probes/<address>.html.
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

DIRECTORY_DATA="$REPOSITORY_ROOT/dataflow.out"
DIRECTORY_SITE="$REPOSITORY_ROOT/site.out"

mkdir -p "$DIRECTORY_SITE"

python3 "$REPOSITORY_ROOT/sources/ip_probe_report.py" \
    --data-directory "$DIRECTORY_DATA" \
    --site-directory "$DIRECTORY_SITE" \
    "$@"
