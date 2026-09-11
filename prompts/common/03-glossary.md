# Glossary

## Semantic-sort naming

- The complete semantic-sort naming rules are defined in `prompts/flavors/01-semantic-sort-naming.md`.

## DELTA protocol

- DELTA applies minimal corrections.
- A DELTA applies to the immediately preceding assistant output unless another artifact is identified.
- A DELTA changes only the named portions.
- A DELTA does not regenerate full output unless explicitly requested.
- If a DELTA cannot be applied without changing additional portions, clarification is required.

## Universal failure-prevention rules

- Universal failure-prevention rules apply across supported languages, tools, and file formats.
- These rules define scope, clarification, anti-hallucination, safety, privacy-boundary, risky-operations, and output behavior.

## One-sentence-per-line

- Each prose sentence occupies one line when the applicable document convention requires it.
- This rule does not apply to code blocks.

## One-statement-per-line

- Independent statements must not be combined on one physical line when the target language supports separating them.
- The target language formatter and syntax rules take precedence.

## Feature file

- A file in `prompts/features/`.
- A feature file defines a project capability.
- A feature file describes requirements and behavior.
- A feature file applies only when referenced by the task or a directly referenced feature dependency.

## Plan block

- A block listing ordered steps.

## Output block

- A block containing final output.
- An output block follows the exact requested format.
- An output block contains no unrequested commentary.

## Context block

- A block providing additional information.
- A context block contains file contents, requirements, notes, samples, or constraints.
- A context block does not add instructions unless explicitly labeled as a constraint.

## Scope-based identifier length

- The amount of identifier detail appropriate to the identifier's scope.

## Ordered transformation pipeline

- A sequence of transformations applied in a defined order.

## Generated file

- A generated file is produced by a script, build tool, generator, or other automated process.
- Generated files must be identified as generated.
- Generated files must not be edited manually unless explicitly requested.
- Generated output must be written only to the designated output directory.

## Incident record

- A record of an incident: what happened, root cause, fix, lessons, and safeguards for a retry.
- An incident record is written after the incident settles and before new work starts.

## Handoff record

- A record written at a session boundary so a fresh session resumes without the prior conversation's memory.
- A handoff record lists the verified current state and the next tasks in order.

## Live-state test

- A test that verifies a documented model against live reality.
- A live-state test requires declared access and reports PASS/WARN/FAIL.
- Live-state tests form one tier of the test policy in `prompts/02-workflow.md`.

## Privacy boundary

- Owner-declared content that is off-limits to the LLM.
- Privacy boundaries are authoritative scope exclusions.

## Stability rules

- Stability rules define project behavior that should not change without explicit instruction.

## ip_probe

- An `ip_probe` is an IPv4 address whose four octets are each prime and which is valid for routing across the Internet.
- "Valid for routing" means globally reachable unicast: not inside an IANA special-purpose block that is private, loopback, link-local, shared, documentation, benchmark, multicast, reserved, or broadcast.
- The project holds 7,400,808 of them.

## Address block

- An address block is an IPv4 range as a Regional Internet Registry publishes it in its delegation file.
- A block is described by its registry, country, start address, size, date, status, and extensions.
- Every block the project keeps carries a UUID derived from the registry, the start address, and the size.

## Operator-held block

- An operator-held block is an address block whose RIR status is `allocated` or `assigned`.
- Any other status, such as `available` or `reserved`, is not operator-held.
- An address inside no delegation record is not operator-held.

## Probe observation

- A probe observation is one HTTP `GET /` to one probe address, with its outcome class, status, headers, body digest, and elapsed time.
- The project observes only probes that are not in an operator-held block.

## Outcome class

- An outcome class names how an observation ended: `http_response`, `connect_refused`, `timeout`, `network_unreachable`, `host_unreachable`, `connection_reset`, `protocol_error`, or `error`.

## RDAP

- RDAP (Registration Data Access Protocol) is the registry query protocol that returns the object behind an address block: handle, name, type, parent handle, addresses, country, organization, events, and remarks.
- The authoritative RDAP service for an address is chosen from the IANA RDAP bootstrap for IPv4.
- The project stores each RDAP answer verbatim in `dataflow.out/02_ip_block.json` under the block's `rdap` key, and caches it in `dataflow.out/raw/RDAP-CACHE.jsonl`.

## Phase

- A phase is a numbered milestone of the project; see `PHASES.md`.
- Phase 1 generates the probe list, phase 2 collects the blocks, and phase 3 observes the probes that no operator holds.
