# Feature Index

- `01-site-build.md` — Site Build: generates `site.out/` from `site.in/`.
- `02-project-pages.md` — Project Pages: the standard published page set (status, dashboard, condensed todo/prompts/documents).
- `03-probe-generation.md` — Probe Generation: writes `dataflow.out/01_ip_probe.json`, the routable four-prime-octet address list.
- `04-block-collection.md` — Block Collection: places every probe in an RIR block, and separates the probes no operator holds.
- `05-probe-observation.md` — Probe Observation: asks each unheld probe one HTTP question and records the answer.
- `06-probe-characterization.md` — Probe Characterization: gathers the evidence that separates the four explanations for an anomalous probe, with control addresses in the same block.

- Features 01 and 02 are inherited from the project skeleton.
- Features numbered 03 and above are this project's own capability.
- Phase 1 implements feature 03, phase 2 implements feature 04, phase 3
  implements feature 05, and phase 4 implements feature 06.
