# TODO

## Open Questions

* [ ] decide what makes an address "curious" (the project's real aim); the
      phase 3 pass of 2026-09-10 offers candidates: an answer where the
      registry says `reserved`, a refused connection where no host exists,
      and an answer that arrives faster than a distant server could give it.
* [ ] phase 4 (done 2026-09-11, see `records/01-probe-characterization.md`)
      left these follow-ups:
    * [ ] place the reset source at Site D (`199.47.167.0/24`): a traceroute,
          or the same probe from an outside vantage point such as a RIPE
          Atlas measurement.
    * [ ] repeat the phase 4 pass later: stability is one of the
          discriminators, and a single pass cannot test it.
    * [ ] map the live ranges of Sites A and B exactly, rather than by
          sample, so the answering boundary is known to the address.
    * [ ] decide whether a routing-layer lookup (who announces the prefix)
          belongs in the phase 4 battery or becomes its own collection step.
    * [ ] decide whether Site B warrants a hosting-abuse report to the
          announcing operator, and whether the project does that at all.
    * [ ] second vantage point (**deferred; do not use it yet**). Owner note,
          2026-09-11: the webhost has servers in Oregon and can be reached
          over SSH. It sits on the same coast as the project host, which
          reports `America/Los_Angeles`, and that is the wrong end of the
          test: for a geosynchronous-band candidate two observers on one
          coast differ by a few milliseconds, inside jitter, while observers
          on different continents differ by tens of milliseconds. It may
          still be usable for the lunar floor, where the whole Earth spans at
          most 42 ms of round trip — and two observers a thousand kilometres
          apart about 7 ms — against a 2,564 ms quantum. Do not probe from it,
          and do not treat it as the decisive second observer.
    * [ ] **deferred; do not attempt** — a cloud virtual machine in a distant
          region (Amazon, Google, or the like), recorded by the owner on
          2026-09-11. This is the strongest of the deferred options: the
          region is a known place, so the separation is known and can be
          chosen to suit the band being tested, which the Oregon host cannot
          do. Costs a few cents an hour; the provider's egress may not reach
          dark space, though every address worth testing answered, so it is
          routed; and a provider may read address probing as scanning, so it
          must stay a handful of documented connects.
    * [ ] the strong version of that test still needs an observer on another
          continent: Europe or Asia, at a known distance.
    * [ ] run the far-field test deliberately: one pass with a long wait —
          ten seconds reaches Sun–Earth L2 — on a sample of addresses, since
          the ordinary budget records everything past it as a timeout.
    * [ ] take more than three latency samples for any address whose floor
          lands in a light-speed band, so the jitter criterion has something
          to measure.
* [ ] work the isolation list (owner hypothesis, 2026-09-11: the strongest
      hint is a responder whose two immediate neighbours stay silent). For
      every isolated responder, rule out the mundane readings one at a time —
      a single-address assignment, a virtual address on a load balancer or
      anycast, a firewall rule written for one probe pattern, a neighbour
      that is dark now and answers later, and a block boundary that routes
      the three addresses differently. See the isolation table in
      `documents/07-characterization-theory.md`.
* [ ] decide whether the isolation filter should also drive phase 5: inside
      operator-held blocks, `ip_probe` that answer alone are the rogue-host
      signature, but finding them needs a sampling strategy, since phase 3
      never probed held space.
* [ ] revise the characterization criteria as the phase 4 evidence arrives:
      what counts as self-explanation, whether a verdict needs a second
      observation, how to read a service that answers on only some of the
      four-prime addresses, and what confidence scale to use.
* [ ] phase 5 (deferred) — hunt rogue `ip_probe` inside operator-held blocks:
      an address that answers although the registry's own object does not
      cover it, most likely hidden in a large block. Rank candidates by block
      size and by the gap between the registry object and the answers.
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

* [x] decide how to treat the block UUID drift (done 2026-09-11 on the
      owner's instruction: the phase 2 files were regenerated, so the UUIDs
      match the rule, and the characterization was remapped). Original note:
      the namespace string changed
      from `ip_telescope` to `IP_telescope` after the phase 2 files were
      written, so all 9,200 UUIDs no longer match today's derivation rule
      even though the data is internally consistent. Either regenerate the
      phase 2 files (cheap: the RDAP cache refills without network, and the
      characterization would need a repeat pass) or freeze the old namespace
      string. See `records/02-block-audit-and-map.md`.
* [x] drop the redundant fields (done 2026-09-11): `derived.address_end`,
      `derived.prefix`, `derived.opaque_id`, and `rdap.query` are gone.
* [ ] decide whether to move the verbatim RDAP documents to a sidecar file:
      they are 159 MB of the 163 MB block file, and the summary is what
      readers use.
* [ ] decide whether the block map should be published in full (9,247 pages,
      about 48 MB, re-uploaded on every homelab deploy because each fetched
      page is stamped) or trimmed to the index and the 47 octet pages.

## Recently Completed

* [x] show the work per probe (2026-09-11): `sources/ip_probe_report.py` and
      `scripts/07-probe-report.sh` write `site.out/probes.html` and one page
      per phase 4 anomaly, each stating the nine tests, what each test saw
      there, the reading, and the inherited site verdict. The verdicts come
      from `sources/probe_verdict_model.json`, the machine-readable copy of
      the record's conclusions.

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
* [x] add the isolation test (owner hypothesis, 2026-09-11): the pass now
      probes the two immediate neighbours of every responder in a second
      wave, records `isolation.responded`, `isolation.neighbour`, and
      `isolation.isolated`, and lists every isolated responder in an
      `isolation_summary` in the result file.
* [x] audit the block fields and build the browsable map (2026-09-11):
      `sources/ip_block_audit.py` found 21 blocks claiming a CIDR they were
      not (repaired) and the UUID namespace drift, and now reports zero
      internal contradictions; `sources/ip_block_map.py` writes the map —
      index, 47 per-octet pages with gap rows, and 9,200 per-block pages.
      See `records/02-block-audit-and-map.md`.
