# ip_telescope: a telescope pointed at the quiet addresses

> Mail addressed to another star leaves the post office faster than mail
> addressed across town. What if the reply is already waiting, addressed to
> an address that should not exist?

This project collects information about IPv4 addresses that are *curious*:
addresses whose answers, or whose silence, do not match what the registry
says should be there.

The first curiosity is a number trick. An `ip_probe` is an IPv4 address
whose four octets are each prime, and which is valid for routing across the
Internet, for example `2.2.2.2` or `223.251.251.251`. There are exactly
7,400,808 of them. A service that answers only on such addresses is not
something an ordinary operator would build by accident.

The second curiosity is the quiet space. Most of those addresses sit inside
blocks a Regional Internet Registry (RIR) has handed to an operator, where a
boring service is expected. The rest — 49,572 addresses — sit in space that
no operator holds, where `available` or `reserved` is the official answer and
*nothing* is supposed to reply at all. Every answer from that space is worth
a look.

- This repository is structured for collaborative development with a Large Language Model (LLM).
- This file `README.md` is located at the root of the project structure.

The LLM should begin by reading these files in this order (the numeric prefix marks the load order):

1. `prompts/01-contract.md`
2. `prompts/02-workflow.md`
3. `prompts/03-conventions.md`

- These define the interaction rules, workflow, and formatting conventions.
- The LLM must follow the workflow defined in `prompts/02-workflow.md` for every task.

Human contributors should begin by reading:

- `prompts/README.md`
- `documents/README.md`

Note there are rules meant only to constrain Aider behavior:

- `tools/aider-rules.md` (Aider users only)

All project features are defined in `prompts/features/` and implemented in `sources/`.

## Phases

The work proceeds in phases; see `PHASES.md` for the current state.

- Phase 1 — probe generation: `data/01_ip_probe.json`.
- Phase 2 — block collection: `data/02_ip_block.json`, `data/03_ip_probe.json`, `data/04_ip_probe.json`.
- Phase 3 — probe observation: `data/05_ip_probe_http.json`.
- Later phases are not yet defined; the criteria for "curious" will be revised as data arrives.

## The Data Files

| File | Contents | Count | Size |
| --- | --- | --- | --- |
| `data/01_ip_probe.json` | every routable four-prime-octet address | 7,400,808 | 147 MB |
| `data/02_ip_block.json` | RIR blocks holding at least one probe, each with a UUID and its RDAP record | 9,200 | 5.6 MB + RDAP |
| `data/03_ip_probe.json` | `[address, block_uuid]` for probes inside operator-held blocks | 7,351,236 | 441 MB |
| `data/04_ip_probe.json` | probes in blocks no operator holds: the phase 3 targets | 49,572 | 1.0 MB |
| `data/05_ip_probe_http.json` | one HTTP observation per phase 3 target | 49,572 | 18 MB |

- Counts verified 2026-09-10 against the RIR delegation files fetched that day.
- Of the 9,200 probe-bearing blocks, 8,616 are operator-held (`allocated` or `assigned`) and 584 are not (`available` or `reserved`).
- Every probe falls inside some RIR record; no probe is entirely absent from the registry files.
- `data/03_ip_probe.json` is large because it repeats the mapping that `data/01` plus `data/02` already imply; it exists so that later phases can stream one file.
- The 2026-09-10 phase 3 pass over the 49,572 unheld probes answered 99 times, refused 6 times, reset once, and timed out 49,466 times. Every answer sat in a block the registry calls `reserved`; 582 of the 584 unheld blocks were silent.

## Running the Project

- `make probes` writes `data/01_ip_probe.json`.
- `make blocks` fetches the RIR delegation files into `data/raw/` and writes the phase 2 files. Add `--refresh` to fetch again: `sh scripts/02-block-collect.sh --refresh`.
- `make enrich` adds the RIR RDAP record to every collected block, caching each answer in `data/raw/RDAP-CACHE.jsonl`. Use `--limit N` for a trial; the lookup is rate limited by `--rate` requests per second.
- `make observe` runs phase 3 over `data/04_ip_probe.json`. Use `--limit` for a trial run.
- `make test` runs every test; the phase tests are portable and need no network.
- `make site` builds the project pages.

## Data Directory (owner override)

The skeleton writes generated data to `dataflow.out/`.
This project keeps its generated data in `data/` instead, as the owner
specified, and ignores it in git:

- `data/0*.json` are generated outputs.
- `data/raw/` is the RIR download cache, with `SHA256SUMS` and `FETCHED-AT.txt` recording what was fetched.
- Both are reproducible from `sources/` and the RIR sources; the versions that matter are pinned in the outcome records.

## Conduct

- Phase 3 asks one `GET /` of each target and stops there.
- The targets are addresses that no operator holds, so no service is being disturbed.
- A run states its parameters (port, thread count, timeout) in its own output file.
- Response bodies are never stored beyond a 256-character prefix; only length and digest are kept.

## Top-Level Map

- `README.md` is the project overview.
- `TODO.md` tracks pending and completed project tasks.
- `PHASES.md` tracks the phase state.
- `prompts/` contains LLM interaction rules, common requirements, feature requirements, task definitions, and episode work orders.
- `documents/` contains human-consumption documents: the interaction pattern, worked examples, and tool notes.
- `records/` contains version-controlled outcome, incident, and handoff records.
- `sources/` contains implementations: one program per phase.
- `scripts/` contains project scripts, one per phase, numbered in phase order.
- `tests/` contains tests and validation code.
- `data/` contains the probe list, the collected blocks, and the observations (not version-controlled).
- `data/raw/` contains the fetched RIR delegation files (not version-controlled).
- `logs/` contains generated logs (not version-controlled).
- `site.in/` contains static-site input.
- `site.out/` contains generated static-site output (not version-controlled).
- `Makefile` drives generation (`make probes`, `make blocks`, `make observe`), the tests (`make test`), and cleanup (`make clean`).

## Canonical Files

The following filenames are canonical and must not be renamed or duplicated without an explicit task:

- `README.md`
- `TODO.md`
- `Makefile`
