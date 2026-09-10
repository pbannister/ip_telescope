# TODO

## Open Questions

* [ ] decide what makes an address "curious" (the project's real aim); the
      criteria will be revised as the phase 3 observations arrive.
* [ ] decide the phase 3 run parameters for the full 49,572-address pass
      (thread count and timeout), and whether the run is repeated on a
      schedule so that answers can be compared over time.
* [ ] confirm the phase 3 output name `data/05_ip_probe_http.json`.
* [ ] decide whether `data/02_ip_block.json` should be enriched with RDAP or
      whois object metadata (network handle, name, parent, organization,
      entities, events) for the 9,200 blocks, beyond the fields the RIR
      delegation files publish in bulk.
* [ ] decide whether phase 3 should also try HTTPS (`--port 443`) and
      whether a TLS handshake result belongs in the same observation.
* [ ] decide how to treat a `reserved` block that a transit network answers
      on behalf of: registry truth, or an answer worth chasing.
* [ ] define phase 4 and later: correlation of observations across blocks and
      registries, clustering of unusual answers, and re-observation over time.
* [ ] decide whether the 441 MB `data/03_ip_probe.json` earns its keep, or
      whether later phases should re-derive the mapping from `data/01` and
      `data/02`.

## Recently Completed

* [x] create the project from the skeleton (2026-09-10).
* [x] phase 1: probe generation, `sources/ip_probe_generate.py` and
      `scripts/01-probe-generate.sh`; `data/01_ip_probe.json` written with
      7,400,808 addresses and verified.
* [x] phase 2: block collection, `sources/ip_block_collect.py` and
      `scripts/02-block-collect.sh`; the five RIR delegation files fetched,
      and `data/02_ip_block.json`, `data/03_ip_probe.json`, and
      `data/04_ip_probe.json` written.
* [x] phase 3: observation tooling, `sources/ip_probe_observe.py` and
      `scripts/03-probe-observe.sh`, with a loopback test for the answered
      and refused paths.
