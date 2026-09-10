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
* Blocks must be written to `data/02_ip_block.json` in ascending order of
  start address.
* Probe-to-block pairs for operator-held blocks must be written to
  `data/03_ip_probe.json`.
* Probes that are not in an operator-held block must be written to
  `data/04_ip_probe.json` in ascending order.
* Collection must be reproducible: the same delegation files and the same
  probe list produce the same outputs.
* Collection must report the block and probe counts it wrote.

## Behavior

* `sh scripts/02-block-collect.sh` fetches the delegation files into
  `data/raw/` when absent, records their digests in
  `data/raw/SHA256SUMS` and the fetch time in `data/raw/FETCHED-AT.json`,
  then writes the three data files.
* `sh scripts/02-block-collect.sh --refresh` fetches the delegation files
  again before writing.
* `python3 sources/ip_block_collect.py --raw-directory DIR --data-directory DIR`
  performs the collection against any pair of directories.
* `data/02_ip_block.json` is an array of objects, one per block, with
  `block_uuid`, `probe_count`, `assigned`, the verbatim `rir_record`, and
  `derived` fields (`address_end`, `prefix`, `opaque_id`).
* `data/03_ip_probe.json` is an array of `[address, block_uuid]` pairs.
* `data/04_ip_probe.json` is an array of addresses.
* A block whose size is not a power of two has no `prefix` and is described
  by its start and end addresses.

## Dependencies

* `03-probe-generation.md` — supplies `data/01_ip_probe.json`.
