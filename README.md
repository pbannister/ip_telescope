# IP_telescope: pointed at the quiet web

## Preamble

How would you uncover an alien postoffice?

There is a premise in science fiction that an alien race might gate first contact behind a proof of intelligence or capability. 
Arthur C. Clarke wrote stories where humans uncovered a probe buried on the Moon. 
Discovery of the probe meant humans had advanced enough to leave the Earth, and detect a buried probe on the Moon.

A more humorous story noted that (at the time) postal mail was faster across the country than local delivery. 
The character in the story addressed a letter to another star, which vanished instantly - and became the starting point for first contact.

In present, we might imagine an alien presence on the web, waiting to be discovered. 
What sort of clue or anomalous behavior might be a similar proof of intelligence?

We might be looking for hidden-in-plain sight proof of other folk, not us.
A smart alien probe might connect to the web, and wait to be found.
That presence might be very ... alien.

Let us compound the speculation.
What if the speculation of old Greek philosophers were true?
What if reality was more than what we can sense?
What if Quantum Mechanics is a hint not an answer?
What if reality is a fractal web, not a continuous line?

If reality is fractal, then perhaps there are intra-space routers on the internet.
Those routers (and the addresses behind) would be less alien, just unexpected.

(To be clear, I do not *believe* in any of this. But will look, to be sure.)

## Start

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

- Phase 1 — probe generation: `dataflow.out/01_ip_probe.json`.
- Phase 2 — block collection: `dataflow.out/02_ip_block.json`, `dataflow.out/03_ip_probe.json`, `dataflow.out/04_ip_probe.json`.
- Phase 3 — probe observation: `dataflow.out/05_ip_probe_http.json`.
- Later phases are not yet defined; the criteria for "curious" will be revised as data arrives.

## The Data Files

| File | Contents | Count | Size |
| --- | --- | --- | --- |
| `dataflow.out/01_ip_probe.json` | every routable four-prime-octet address | 7,400,808 | 147 MB |
| `dataflow.out/02_ip_block.json` | RIR blocks holding at least one probe, each with a UUID and its RDAP record | 9,200 | 163 MB |
| `dataflow.out/03_ip_probe.json` | `[address, block_uuid]` for probes inside operator-held blocks | 7,351,236 | 441 MB |
| `dataflow.out/04_ip_probe.json` | probes in blocks no operator holds: the phase 3 targets | 49,572 | 1.0 MB |
| `dataflow.out/05_ip_probe_http.json` | one HTTP observation per phase 3 target | 49,572 | 18 MB |
| `dataflow.out/06_ip_probe_characterize.json` | phase 4 evidence: anomalies, controls, neighbours | 598 | 3.5 MB |

- Counts verified 2026-09-10 against the RIR delegation files fetched that day.
- Of the 9,200 probe-bearing blocks, 8,616 are operator-held (`allocated` or `assigned`) and 584 are not (`available` or `reserved`).
- Every probe falls inside some RIR record; no probe is entirely absent from the registry files.
- `dataflow.out/03_ip_probe.json` is large because it repeats the mapping that `dataflow.out/01` plus `dataflow.out/02` already imply; it exists so that later phases can stream one file.
- `dataflow.out/02_ip_block.json` is large because each block carries its RDAP document verbatim, as the RIR returned it; the delegation fields alone occupy about 6 MB.
- The 2026-09-10 phase 3 pass over the 49,572 unheld probes answered 99 times, refused 6 times, reset once, and timed out 49,466 times. Every answer sat in a block the registry calls `reserved`; 582 of the 584 unheld blocks were silent.
- The 2026-09-10 RDAP enrichment answered for 8,556 of the 9,200 blocks and returned `404` (no object) for 27. It left 617 unanswered: `rdap.afrinic.net` was unreachable from the owning host, and the other registries answered `429` once the run pressed them. An unanswered address is not treated as answered, so a later run asks again.
- The loudest answer, `23.191.149.0/24`, sits inside ARIN's own reserved space: RDAP records no operator for the block, only its parent `23.0.0.0/8`, which ARIN holds itself, yet 98 probes there answered with an nginx `301`. The refusing addresses in `199.47.160.0/21` sit in a block ARIN has no RDAP object for at all.

## Running the Project

- `make probes` writes `dataflow.out/01_ip_probe.json`.
- `make blocks` fetches the RIR delegation files into `dataflow.out/raw/` and writes the phase 2 files. Add `--refresh` to fetch again: `sh scripts/02-block-collect.sh --refresh`.
- `make enrich` adds the RIR RDAP record to every collected block, caching each answer in `dataflow.out/raw/RDAP-CACHE.jsonl`. Use `--limit N` for a trial; the lookup is rate limited by `--rate` requests per second.
- `make observe` runs phase 3 over `dataflow.out/04_ip_probe.json`. Use `--limit` for a trial run.
- `make characterize` runs phase 4 over the phase 3 anomalies: the probe battery, plus non-prime control addresses sampled from the same blocks. `--control-count N` sets the sample size, and `--limit N` bounds a trial.
- `make map` builds the browsable block map into `site.out/`.
- `make probe-report` builds the per-probe reasoning pages into `site.out/`.
- `python3 sources/ip_block_audit.py` checks every block for fields that
  contradict the fields they came from; `--repair` rewrites the ones with a
  single correct value.
- `make test` runs every test; the phase tests are portable and need no network.
- `make site` builds the project pages, including the map.

## Characterizing an Anomaly

An answer from space no operator holds has four admitted explanations:
**curious** (other folk running the inverse exercise), **incidental** (an
accident of configuration), **nefarious** (local folk who need to hide), and
**other** (not local folk).

The expected characterization is written down before the evidence is read:

- `documents/07-characterization-theory.md` — the four explanations, the
  discriminating tests, and the traps.
- `prompts/features/06-probe-characterization.md` — the capability and its
  requirements.

The observed characterization is a dated record per site, with the evidence,
the verdict, the confidence, and the measurement that would overturn it.
An address that no evidence explains is recorded as **unexplained**, which is
a result and not a failure.

The first filter is the **isolation test**. A service that covers a prefix
lights its whole range, so an address that answers while the two addresses
immediately beside it stay silent is being *addressed*, not *ranged* —
something was put on that one address on purpose. It costs two extra probes
per responder, and it reduces a long list of "something answered" to the
short list of "something was placed here" (owner hypothesis, 2026-09-11).

The control sample is the next test, and it answers two questions: how far
the live range extends around an address that answers, and whether the
service exists *because* of the four-prime pattern. It does not separate a
curious party from an ordinary one: a party watching a range would answer
every address in it, exactly as an ordinary host would, because the probes
simply fell inside a block they monitor (owner correction, 2026-09-11). What
would separate them is the awareness test — a response that changes because
of our probing, or content that engages the pattern.

## Work Products Are Kept

Each phase produces a numbered work product in `dataflow.out/`, and each one
costs real time to build. Nothing is rebuilt silently:

| Work product | Cost to build from scratch |
| --- | --- |
| `01_ip_probe.json` | 8 seconds of CPU |
| `02_ip_block.json`, `03_ip_probe.json`, `04_ip_probe.json` | 16 seconds, plus the RIR downloads |
| the RDAP records inside `02_ip_block.json` | about 40 minutes of registry queries |
| `05_ip_probe_http.json` | 19 minutes of live Internet probing, not repeatable on demand |
| `06_ip_probe_characterize.json` | a few minutes of live probing per pass, and the sites may change between passes |

Two mechanisms enforce the rule, and both must agree:

- **make** names the file each step produces, so a step whose file is present does not run. `make all` with everything present takes about five seconds and touches no network.
- **each program** keeps a work product that already exists. It reports `reuse:` and exits without writing. `--refresh` is the only way to write it again, and it is deliberate.

The raw inputs are cached separately, and are separate from the work products:

- `dataflow.out/raw/delegated-*-extended-latest` — the five RIR delegation files, fetched once. `--refresh` on the block script fetches them again.
- `dataflow.out/raw/RDAP-BOOTSTRAP-IPV4.json` — the IANA RDAP bootstrap.
- `dataflow.out/raw/RDAP-CACHE.jsonl` — one record per answered address, so a repeated enrichment asks the registries nothing it already knows.

One exception, because enrichment annotates a file rather than producing one:

- A default `make enrich` reuses `02_ip_block.json` whenever every block already carries its RDAP record. It asks nothing.
- `sh scripts/04-block-enrich.sh --retry-failed` is the deliberate gap-filler: it asks again for the blocks whose last answer was a failure or a rate limit (617 of 9,200 on 2026-09-10), then writes the file.
- `--refresh` ignores the cache and asks the registries for every block again.

`make clean` is manual by design; it explains what to remove rather than
removing it. The RIR download cache in `dataflow.out/raw/` is never touched
by it.

## Data Directory

This project keeps generated data in `dataflow.out/`, and ignores it in git:

- `dataflow.out/0*.json` are generated outputs.
- `dataflow.out/raw/` is the RIR download cache, with `SHA256SUMS` and `FETCHED-AT.txt` recording what was fetched.
- Both are reproducible from `sources/` and the RIR sources; the versions that matter are pinned in the outcome records.

## Conduct

- Phase 3 asks one `GET /` of each target and stops there.
- The targets are addresses that no operator holds, so no service is being disturbed.
- A run states its parameters (port, thread count, timeout) in its own output file.
- Response bodies are never stored beyond a 256-character prefix; only length and digest are kept.

## Published Pages

The project publishes a page set through the homelab, which fetches this
repository's generated `site.out/` tree and deploys it:

- `index.html` — the project status.
- `dashboard.html` — the work-product counts.
- `findings.html` — **the observed `ip_probe` results**, with the evidence and
  the verdicts for each site that answered.
- `probes.html` — **every phase 4 probe, with the reasoning**: the index counts
  what the set has in common, and each of the 106 addresses has its own page
  with the nine tests applied, what each test saw there, the reading that
  follows, and the site verdict it inherits. Built by `make probe-report`.
- `blocks.html` — **the browsable map of the collected blocks**: an index with
  the irregularity classes, then one page per first octet listing every block
  in address order with its status, RDAP state, name, type, organization, and
  the gaps where no delegation record covers the space, and one page per block
  with all of its data. Built by `make map`.
- `todo.html`, `prompts.html`, `documents.html`, `records.html` — the
  condensed work plan, rules, knowledge, and records, each with the full text
  of every file behind it.

`make site` builds them. Registration lives in the homelab's
`sources/projects.yaml`; this project never pushes to the web server itself.

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
- `dataflow.out/` contains the probe list, the collected blocks, and the observations (not version-controlled).
- `dataflow.out/raw/` contains the fetched RIR delegation files (not version-controlled).
- `logs/` contains generated logs (not version-controlled).
- `site.in/` contains static-site input.
- `site.out/` contains generated static-site output (not version-controlled).
- `Makefile` drives generation (`make probes`, `make blocks`, `make observe`), the tests (`make test`), and cleanup (`make clean`).

## Canonical Files

The following filenames are canonical and must not be renamed or duplicated without an explicit task:

- `README.md`
- `TODO.md`
- `Makefile`
