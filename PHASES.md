# Phases

Project work proceeds in numbered phases. A phase is a milestone that
groups one or more episodes (the reviewable work units; see
`prompts/how-to-write-episodes.md` §9 and the homelab project-pages
conventions `documents/09-project-pages-conventions.md` §6).

**Change the current phase only when committing the project** (owner rule
2026-08-26): the phase belongs to this project, not to the homelab
registry. The homelab reads it from the generated `site.out/phase.txt`
(emitted by `scripts/site-condense.sh` from the `Current:` line below) and
shows it next to the activity status (active/planned/deferred/complete),
which the human declares in the homelab registry.

Current: phase 4 — complete

- Phase 1 — Probe generation: the deterministic `ip_probe` list, being every
  routable IPv4 address with four prime octets; written to
  `dataflow.out/01_ip_probe.json` (7,400,808 addresses) — complete
- Phase 2 — Block collection: every RIR block that holds a probe, each with
  an assigned UUID, plus the probe-to-block mapping and the probes that no
  operator holds; written to `dataflow.out/02_ip_block.json` (9,200 blocks),
  `dataflow.out/03_ip_probe.json` (7,351,236 pairs), and
  `dataflow.out/04_ip_probe.json` (49,572 addresses). Enriched with the RIR
  RDAP record for every block: 8,556 answered, 27 answered `404`, 617 left
  unanswered when AFRINIC was unreachable and the other registries rate
  limited the run — complete
- Phase 3 — Probe observation: one HTTP `GET /` per probe that no operator
  holds, with the outcome class, status, headers, body digest, and timings;
  written to `dataflow.out/05_ip_probe_http.json`. The 2026-09-10 pass ran
  49,572 targets in 19 minutes: 99 answers, 6 refusals, 1 reset, 49,466
  timeouts — complete
- Phase 4 — Probe characterization: gather the evidence that separates the
  four explanations for an anomalous probe (curious, incidental, nefarious,
  other), including non-prime control addresses in the same blocks; the
  expected characterization is `documents/07-characterization-theory.md` and
  the observed one is `records/01-probe-characterization.md`; written to
  `dataflow.out/06_ip_probe_characterize.json` (342 targets: 106 anomalies
  and 236 controls). The four-prime pattern did not survive the controls, and
  the routing layer resolved three of the four sites — complete
- Phase 5 — Rogue probes inside operator-held blocks: an address that answers
  where the registry's own object does not cover it, most likely hidden in a
  large block; deferred until the phase 4 criteria are trusted — not-started

States: `not-started` | `started` | `complete`. Keep this file in sync
with the episodes that advance each phase and with `TODO.md`.
