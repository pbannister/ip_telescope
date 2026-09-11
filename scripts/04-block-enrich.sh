#!/bin/sh
#
# 04-block-enrich.sh: phase 2 enrichment - add RIR RDAP metadata to blocks.
#
# Calls the enricher in sources/; performs no work of its own.
# Every option of the enricher is accepted and passed through, for example:
#   sh scripts/04-block-enrich.sh --limit 20
#   sh scripts/04-block-enrich.sh --refresh --rate 3
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

DIRECTORY_DATA="$REPOSITORY_ROOT/dataflow.out"
DIRECTORY_RAW="$REPOSITORY_ROOT/dataflow.out/raw"

python3 "$REPOSITORY_ROOT/sources/ip_block_enrich.py" \
    --data-directory "$DIRECTORY_DATA" \
    --raw-directory "$DIRECTORY_RAW" \
    "$@"
