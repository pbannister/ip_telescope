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
* [ ] confirm the phase 3 output name `dataflow.out/05_ip_probe_http.json`.
* [ ] decide whether phase 3 should also try HTTPS (`--port 443`) and
      whether a TLS handshake result belongs in the same observation.
* [ ] decide how to treat a `reserved` block that a transit network answers
      on behalf of: registry truth, or an answer worth chasing.
* [ ] define phase 4 and later: correlation of observations across blocks and
      registries, clustering of unusual answers, and re-observation over time.
* [ ] decide whether the 441 MB `dataflow.out/03_ip_probe.json` earns its keep, or
      whether later phases should re-derive the mapping from `dataflow.out/01` and
      `dataflow.out/02`.
* [ ] decide whether the project pages should generate the dashboard from
      `dataflow.out/` instead of the hand-written snapshot.
* [ ] re-ask the blocks left without an RDAP record on 2026-09-10, 617 of
      9,200: `rdap.afrinic.net` was unreachable from the owning host (196
      blocks), and LACNIC, ARIN, RIPE NCC, and APNIC answered `429` under
      sustained load (421 blocks). Retry later at a slower rate with
      `sh scripts/04-block-enrich.sh --retry-failed`, or fall back to
      `whois` on port 43 for AFRINIC. A default enrichment run keeps the
      block file as it stands and does not retry them.
* [ ] decide whether enrichment should write its own numbered work product
      (for example `06_ip_block_enrich.json`) instead of annotating
      `02_ip_block.json` in place. The placeholder variables for files 04,
      06, 07, and 08 that once sat in the Makefile were removed because no
      program produced them, which made `make enrich` re-run on every
      invocation; the in-place annotation is what the programs do today.

## Recently Completed

* [x] create the project from the skeleton (2026-09-10).
* [x] phase 1: probe generation, `sources/ip_probe_generate.py` and
      `scripts/01-probe-generate.sh`; `dataflow.out/01_ip_probe.json` written with
      7,400,808 addresses and verified.
* [x] phase 2: block collection, `sources/ip_block_collect.py` and
      `scripts/02-block-collect.sh`; the five RIR delegation files fetched,
      and `dataflow.out/02_ip_block.json`, `dataflow.out/03_ip_probe.json`, and
      `dataflow.out/04_ip_probe.json` written.
* [x] phase 3: observation tooling, `sources/ip_probe_observe.py` and
      `scripts/03-probe-observe.sh`, with a loopback test for the answered
      and refused paths.
* [x] phase 3: the full pass over all 49,572 unheld probes, 2026-09-10,
      thread 128, timeout 3 — 99 answers, 6 refusals, 1 reset, 49,466
      timeouts in 19m23s; `dataflow.out/05_ip_probe_http.json` written.
* [x] phase 2 enrichment: `sources/ip_block_enrich.py` and
      `scripts/04-block-enrich.sh`, adding the RIR RDAP record to every
      collected block, with answers cached in `dataflow.out/raw/RDAP-CACHE.jsonl`.
      — **Decided 2026-09-10 by the owner**: enrich all 9,200 probe-bearing
      blocks, not only the blocks no operator holds.
* [x] keep every work product instead of rebuilding it (2026-09-11): each
      program now reuses a file that already exists and reports `reuse:`,
      `--refresh` is the only way to write one again, and `tests/07-work-product-reuse.sh`
      proves it for all four stages. Verified against the real 770 MB of work
      products: running every phase script left all five files byte-for-byte
      and timestamp-for-timestamp unchanged, and `make all` fell from about
      50 minutes of network work to 5 seconds.
* [x] fix the half-finished move to `dataflow.out/` (2026-09-11): the
      collect, enrich, and observe scripts still passed `--data-directory
      data/`, a directory that no longer existed, and the program defaults
      pointed there too.
