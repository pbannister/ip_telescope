#!/bin/sh
#
# Phase 1 test: ip_probe generation (feature 03-probe-generation).
#
# Tier: portable for the count, sample, and cross-check assertions.
# The full-file check is tool-gated on dataflow.out/01_ip_probe.json existing; that
# file is generated and is not version-controlled.
#
set -eu

REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM_GENERATE="$REPOSITORY_ROOT/sources/ip_probe_generate.py"
FILE_PROBE="$REPOSITORY_ROOT/dataflow.out/01_ip_probe.json"

COUNT_PROBE_EXPECTED=7400808
COUNT_SAMPLE=108

fail() {
    echo "03-probe-generate: $1" >&2
    exit 1
}

count_probe=$(python3 "$PROGRAM_GENERATE" --count-only)
if [ "$COUNT_PROBE_EXPECTED" != "$count_probe" ]; then
    fail "count-only returned $count_probe, expected $COUNT_PROBE_EXPECTED"
fi

FILE_SAMPLE=$(mktemp)
trap 'rm -f "$FILE_SAMPLE"' EXIT

python3 "$PROGRAM_GENERATE" --first "$COUNT_SAMPLE" --output "$FILE_SAMPLE" > /dev/null
if ! output_verify=$(python3 "$PROGRAM_GENERATE" --verify "$FILE_SAMPLE" --first "$COUNT_SAMPLE"); then
    fail "generated sample failed verification: $output_verify"
fi

# Independent cross-check: enumerate 2.2.2.0-2.2.3.255 with trial division
# and require an exact match with the first 108 generated addresses. No
# excluded block covers that range, so the two lists must agree.
if ! python3 - "$FILE_SAMPLE" <<'PYTHON_CHECK'
import sys

path_sample = sys.argv[1]


def is_prime(value):
    if 2 > value:
        return False
    divisor = 2
    while divisor * divisor <= value:
        if 0 == value % divisor:
            return False
        divisor += 1
    return True


text_sample = []
for text_line in open(path_sample, encoding="ascii"):
    text_item = text_line.strip().rstrip(",").strip().strip('"')
    if text_item and text_item not in ("[", "]"):
        text_sample.append(text_item)

text_naive = []
for value_second in (2, 3):
    for value_fourth in range(256):
        if is_prime(value_fourth):
            text_naive.append(f"2.2.{value_second}.{value_fourth}")

if text_sample != text_naive:
    print(f"sample disagrees with naive enumeration: {text_sample[:4]} != {text_naive[:4]}")
    sys.exit(1)
PYTHON_CHECK
then
    fail "sample does not match the independent enumeration"
fi

if [ -f "$FILE_PROBE" ]; then
    if ! output_full=$(python3 "$PROGRAM_GENERATE" --verify "$FILE_PROBE"); then
        fail "full probe file failed verification: $output_full"
    fi
    echo "03-probe-generate: full file: $output_full"
else
    echo "03-probe-generate: WARN dataflow.out/01_ip_probe.json absent; run scripts/01-probe-generate.sh"
fi

echo '03-probe-generate: ok'
exit 0
