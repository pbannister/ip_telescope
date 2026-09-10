# TODO

## Open Questions

* [ ] decide what makes an address "curious" (the project's real aim); the
      phase 3 pass of 2026-09-10 offers candidates: an answer where the
      registry says `reserved`, a refused connection where no host exists,
      and an answer that arrives faster than a distant server could give it.
* [ ] investigate the 2026-09-10 answers, in order:
    * [ ] `23.191.149.0/24`: 98 of the 216 probes in ARIN block
          `23.191.137.0-23.191.151.255` (`reserved`) answered with an nginx
          `301` to HTTPS; the rest of the block stayed silent.
    * [ ] `103.241.73.191`: an nginx `200` serving a Chinese hosting-panel
          page from APNIC block `103.241.72.0/22` (`reserved`).
    * [ ] `103.149.23.0/24` and `199.47.160.0/21` (`reserved`, APNIC and
          ARIN): six addresses refused the connection and one reset it,
          which means something is listening or filtering there.
* [ ] decide whether phase 3 should be repeated on a schedule so that
      answers can be compared over time, and whether a repeat uses the same
      parameters (port 80, thread 128, timeout 3).
* [ ] confirm the phase 3 output name `data/05_ip_probe_http.json`.
* [ ] decide whether phase 3 should also try HTTPS (`--port 443`) and
      whether a TLS handshake result belongs in the same observation.
* [ ] decide how to treat a `reserved` block that a transit network answers
      on behalf of: registry truth, or an answer worth chasing.
* [ ] define phase 4 and later: correlation of observations across blocks and
      registries, clustering of unusual answers, and re-observation over time.
* [ ] decide whether the 441 MB `data/03_ip_probe.json` earns its keep, or
      whether later phases should re-derive the mapping from `data/01` and
      `data/02`.
* [ ] decide whether the project pages should generate the dashboard from
      `data/` instead of the hand-written snapshot.

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
* [x] phase 3: the full pass over all 49,572 unheld probes, 2026-09-10,
      thread 128, timeout 3 — 99 answers, 6 refusals, 1 reset, 49,466
      timeouts in 19m23s; `data/05_ip_probe_http.json` written.
* [x] phase 2 enrichment: `sources/ip_block_enrich.py` and
      `scripts/04-block-enrich.sh`, adding the RIR RDAP record to every
      collected block, with answers cached in `data/raw/RDAP-CACHE.jsonl`.
      — **Decided 2026-09-10 by the owner**: enrich all 9,200 probe-bearing
      blocks, not only the blocks no operator holds.
