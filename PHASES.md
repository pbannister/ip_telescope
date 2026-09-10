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

Current: phase 3 — started

- Phase 1 — Probe generation: the deterministic `ip_probe` list, being every
  routable IPv4 address with four prime octets; written to
  `data/01_ip_probe.json` (7,400,808 addresses) — complete
- Phase 2 — Block collection: every RIR block that holds a probe, each with
  an assigned UUID, plus the probe-to-block mapping and the probes that no
  operator holds; written to `data/02_ip_block.json` (9,200 blocks),
  `data/03_ip_probe.json` (7,351,236 pairs), and `data/04_ip_probe.json`
  (49,572 addresses). Enriched with the RIR RDAP record for every block — complete
- Phase 3 — Probe observation: one HTTP `GET /` per probe that no operator
  holds, with the outcome class, status, headers, body digest, and timings;
  written to `data/05_ip_probe_http.json` — started
- Later phases — not yet defined; the criteria that make an address
  "curious" are revised as data arrives.

States: `not-started` | `started` | `complete`. Keep this file in sync
with the episodes that advance each phase and with `TODO.md`.
