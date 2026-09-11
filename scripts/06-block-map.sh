#!/bin/sh
#
# 06-block-map.sh: build the browsable map of the collected address blocks.
#
# Calls the map generator in sources/; performs no work of its own.
# Writes site.out/blocks.html (the map) and site.out/blocks/<uuid>.html (one
# page per block) from the work products in dataflow.out/.
#
# Usage:
#   sh scripts/06-block-map.sh
#   sh scripts/06-block-map.sh --no-probes
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

DIRECTORY_DATA="$REPOSITORY_ROOT/dataflow.out"
DIRECTORY_SITE="$REPOSITORY_ROOT/site.out"

mkdir -p "$DIRECTORY_SITE"

python3 "$REPOSITORY_ROOT/sources/ip_block_map.py" \
    --data-directory "$DIRECTORY_DATA" \
    --site-directory "$DIRECTORY_SITE" \
    "$@"
