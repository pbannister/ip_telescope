#!/bin/sh
#
# 02-block-collect.sh: phase 2 - RIR address blocks for the ip_probe list.
#
# Fetches the five RIR delegation files into data/raw/ (once; pass
# --refresh to fetch them again), records their digests and fetch time,
# then calls sources/ip_block_collect.py to write
# data/02_ip_block.json, data/03_ip_probe.json, and data/04_ip_probe.json.
#
# Usage:
#   sh scripts/02-block-collect.sh
#   sh scripts/02-block-collect.sh --refresh
#
set -eu

DIRECTORY_SCRIPT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$DIRECTORY_SCRIPT/.." && pwd)

DIRECTORY_RAW="$REPOSITORY_ROOT/data/raw"
DIRECTORY_DATA="$REPOSITORY_ROOT/data"
LIST_REGISTRY='afrinic apnic arin lacnic ripencc'

url_delegation_print() {
    case "$1" in
        afrinic) echo 'https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-extended-latest' ;;
        apnic)   echo 'https://ftp.apnic.net/stats/apnic/delegated-apnic-extended-latest' ;;
        arin)    echo 'https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest' ;;
        lacnic)  echo 'https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest' ;;
        ripencc) echo 'https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-extended-latest' ;;
        *)
            echo "url_delegation_print: unknown registry: $1" >&2
            exit 1
            ;;
    esac
}

FLAG_REFRESH=no
if [ '--refresh' = "${1:-}" ]; then
    FLAG_REFRESH=yes
    shift
fi

mkdir -p "$DIRECTORY_RAW"

for text_registry in $LIST_REGISTRY; do
    FILE_RAW="$DIRECTORY_RAW/delegated-$text_registry-extended-latest"
    if [ -s "$FILE_RAW" ] && [ "$FLAG_REFRESH" = no ]; then
        echo "cache: delegated-$text_registry-extended-latest"
        continue
    fi
    URL_DELEGATION=$(url_delegation_print "$text_registry")
    echo "fetch: $URL_DELEGATION"
    curl --silent --show-error --fail --location --retry 2 --max-time 600 \
        --output "$FILE_RAW" "$URL_DELEGATION"
done

if ! (cd "$DIRECTORY_RAW" && sha256sum delegated-*-extended-latest > SHA256SUMS); then
    echo '02-block-collect: cannot record delegation file digests' >&2
    exit 1
fi
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$DIRECTORY_RAW/FETCHED-AT.txt"

python3 "$REPOSITORY_ROOT/sources/ip_block_collect.py" \
    --raw-directory "$DIRECTORY_RAW" \
    --data-directory "$DIRECTORY_DATA" \
    "$@"
