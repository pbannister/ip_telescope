# Feature: Block Collection

## Purpose

A probe address on its own says little. Phase 2 places every `ip_probe`
address inside the registry block that a Regional Internet Registry (RIR)
publishes for it, so that later phases can separate two very different
populations:

* addresses an operator holds, where an ordinary service may live, and
* addresses no operator holds, where any answer at all is an anomaly.

## Requirements

* The input must be the five RIR delegation files in extended record format:
  ARIN, RIPE NCC, APNIC, LACNIC, and AFRINIC.
* A delegation record is `registry|country|type|start|value|date|status|extension...`.
* Only `ipv4` records may be used.
* An address block is an operator-held block when its status is `allocated`
  or `assigned`.
* An address block is not operator-held when its status is any other value,
  such as `available` or `reserved`.
* An address that lies in no delegation record is not operator-held.
* Every block that contains at least one `ip_probe` must be recorded once.
* Every block must carry a UUID.
* The block UUID must be derived from the registry, the start address, and
  the size, so that the same block keeps the same UUID across runs.
* The RIR record must be preserved verbatim alongside the derived range.
* Blocks must be written to `dataflow.out/02_ip_block.json` in ascending order of
  start address.
* Probe-to-block pairs for operator-held blocks must be written to
  `dataflow.out/03_ip_probe.json`.
* Probes that are not in an operator-held block must be written to
  `dataflow.out/04_ip_probe.json` in ascending order.
* Collection must be reproducible: the same delegation files and the same
  probe list produce the same outputs.
* Collection must report the block and probe counts it wrote.
* The three phase 2 files must be kept when all three already exist: a run
  that finds them must report the reuse and write nothing.
* They must be written again only when the caller asks for it with
  `--refresh`.

## Requirements (RDAP enrichment)

* Every collected block must be enrichable with the RIR object behind it, taken from RDAP.
* The RDAP service for a block must come from the IANA RDAP bootstrap for IPv4, unless a service is named explicitly.
* Every RDAP answer must be stored verbatim under an `rdap` key of the block, next to a summary of handle, name, type, parent handle, start and end address, country, organization, and events.
* Every answer must be cached in `dataflow.out/raw/RDAP-CACHE.jsonl`, so a repeated run does not ask a registry twice.
* An answer of `404` must be recorded as an answer, not treated as a failure: it states that the registry holds no object for that address.
* A transport failure must not be recorded as an answer: the address must be asked again by a later run.
* A registry service that fails a configured number of times in a row must be closed for the rest of the run, so that one unreachable endpoint cannot stall the whole collection; its blocks are recorded as unanswered and are asked again later.
* Requests must be rate limited across threads, and a rate limit or transport failure must be retried a bounded number of times.
* Enrichment must be idempotent: running it twice must leave the block file unchanged.
* A default enrichment run must reuse the block file when every block already carries its RDAP record, and must write nothing.
* Asking again for the blocks left unanswered must be explicit, through `--retry-failed`.
* The block file must be written only when the run has something to add: a new answer, or a cached answer not yet applied.

## Behavior

* `sh scripts/02-block-collect.sh` fetches the delegation files into
  `dataflow.out/raw/` when absent, records their digests in
  `dataflow.out/raw/SHA256SUMS` and the fetch time in `dataflow.out/raw/FETCHED-AT.json`,
  then writes the three data files.
* `sh scripts/02-block-collect.sh --refresh` fetches the delegation files
  again before writing.
* `python3 sources/ip_block_collect.py --raw-directory DIR --data-directory DIR`
  performs the collection against any pair of directories.
* `sh scripts/04-block-enrich.sh` adds RDAP metadata to every collected
  block; `--limit N` enriches only the first N uncached blocks, and
  `--refresh` ignores the cache.
* A run that finds the three phase 2 files reports
  `collect: reuse=yes` with their sizes, and writes nothing.
* `sh scripts/02-block-collect.sh --refresh` and
  `python3 sources/ip_block_collect.py ... --refresh` write the three files
  again.
* A default enrichment run reports `enrich: reuse=yes` when every block
  already carries its RDAP record. `--retry-failed` asks again only for the
  blocks whose last answer was a failure or a rate limit.
* `--rate` sets the requests per second across all threads, and `--thread`
  sets the number of concurrent requests.
* `--retry` and `--retry-wait` bound the retries of a rate limit or a
  transport failure.
* A closed service is reported as `service_closed` in the run summary, and
  its blocks carry the error `service closed: too many consecutive failures`.
* Progress is reported every 500 answered blocks.
* `dataflow.out/raw/RDAP-CACHE.jsonl` holds one JSON record per answered address and
  is the record of what each registry was asked.
* `dataflow.out/02_ip_block.json` is an array of objects, one per block, with
  `block_uuid`, `probe_count`, `assigned`, the verbatim `rir_record`, and
  `derived` fields (`address_end`, `prefix`, `opaque_id`).
* `dataflow.out/03_ip_probe.json` is an array of `[address, block_uuid]` pairs.
* `dataflow.out/04_ip_probe.json` is an array of addresses.
* A block whose size is not a power of two has no `prefix` and is described
  by its start and end addresses.

## Dependencies

* `03-probe-generation.md` — supplies `dataflow.out/01_ip_probe.json`.
