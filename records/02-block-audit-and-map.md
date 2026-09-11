# Record: block audit and browsable map — 2026-09-11

## Outcome

Two things were asked for: a report on inconsistency between the redundant
and derived fields of `02_ip_block.json`, and browsable maps of what the
project has gathered.

Both exist now.

- `sources/ip_block_audit.py` checks every block against the fields its
  derived fields came from, and can repair the ones with a single correct
  value (`--repair`).
- `sources/ip_block_map.py` writes the browsable map into `site.out/`:
  an index, one page per first octet, and one page per block.

## The audit

Every derived field is checked against its source: the end address against
start plus size, the prefix against start and size, the UUID against
registry+start+size, the assigned flag against the status, the opaque id
against the extensions, and each RDAP summary field against the document it
was drawn from.

**Two defects, both fixed or recorded.**

1. **21 blocks claimed a CIDR they were not.** A power-of-two size is not
   enough; the start address must also be aligned. `13.168.0.0` with
   1,048,576 addresses was stored as `13.168.0.0/12`, which names
   `13.160.0.0-13.175.255.255` — a different range. Twenty-one such blocks
   were repaired to "not a CIDR block", and the generator now checks
   alignment.

2. **All 9,200 block UUIDs no longer matched their derivation rule.** The
   namespace string was changed from `ip_telescope` to `IP_telescope` on
   2026-09-11, after the blocks were written. The data was internally
   consistent — the probe-to-block file and the characterization referred to
   the same UUIDs — but re-deriving from today's code produced a different
   set, so any join rebuilt today would silently miss.

   **Resolved the same day, by the owner's instruction**: the phase 2 files
   were regenerated, so the UUIDs now match the rule. The regeneration ran in
   17 seconds, the RDAP annotations were reapplied from the cache in 4 seconds
   without asking a registry anything, and the characterization's block
   references were remapped (4 block entries, 598 observations, 6 isolation
   entries; zero stale references). The audit's namespace note is gone.

After the repair and the regeneration: **zero internal contradictions** across
9,200 blocks.

## The irregularities the audit found (all cross-source, none defects)

| Class | Blocks | What it is |
| --- | --- | --- |
| RDAP answered with a parent object | 870 | The block has no registry object of its own; the answer covers its parent, so the block is inside an allocation rather than being one |
| The RDAP service is not the delegation registry's | 544 | The record is held by one registry while the address space belongs to another: legacy registrations, the classic case being RIPE records for space inside ARIN's `/8`s |
| Delegation country and RDAP country differ | 534 | The transfer or reassignment the registry has not caught up with |
| RDAP holds no object at all | 27 | The registry has nothing for the address |
| RDAP unanswered | 609 | AFRINIC was unreachable; the others rate limited the pass |
| The RDAP object has no name | 20 | Usually AFRINIC objects, which often carry only a handle |

These are the project's subject matter rather than faults, and the map now
shows them per block.

## The map

- `site.out/blocks.html` — the index: totals, the legend, and the
  irregularity classes with example links.
- `site.out/blocks/octet-<n>.html` — 47 pages, one per populated first
  octet, blocks sorted by start address, with a grey row wherever no
  delegation record covers the space. Status is colour-coded; RDAP state is
  colour-coded; per-block flags are letters (P parent, 4 no object, - never
  answered, N no name, S service mismatch, C country mismatch, A responded,
  I isolated).
- `site.out/blocks/<uuid>.html` — one page per block: the delegation record,
  the derived fields, the RDAP summary and events, the flags with their
  meanings, the addresses that responded with their phase 3 and phase 4
  outcomes, and the block's probes (first 60, a mark on the ones that
  answered).
- Built by `make map`, and by `make site` before the page set is condensed.

**Decision: the registry's verbatim RDAP answer is not published.** It
carries registrant contact details — an email address in 6,894 of the
documents and a telephone number in 6,576 — so the published pages carry the
summary instead, and the verbatim documents stay in the local work product.
The map test enforces this, and runs the homelab's leak-gate pattern over
the generated output.

## Fields dropped

The owner instructed on 2026-09-11 that the fields below be dropped, and they
are gone from the regenerated file: `derived.address_end`, `derived.prefix`,
`derived.opaque_id` (the whole `derived` object), and `rdap.query`. Readers
compute the range and the prefix from the record with the helpers
`block_address_end` and `block_prefix_text` in `ip_block_collect.py`.

The reasoning behind each, kept for the record:

- **Dropped.** `derived.address_end` (start + value − 1), `derived.prefix`
  (start and value, and it was wrong for 21 blocks until repaired),
  `derived.opaque_id` (a copy of `rir_record.extensions[0]`), and `rdap.query`
  (always `rir_record.start`). The audit no longer checks them because there
  is nothing left to contradict, and the `--repair` mode was removed with
  them.
- **Keep, though derived.** `block_uuid`: it is the join key for
  `03_ip_probe.json` and the characterization, and the namespace drift shows
  what happens when a derivation rule moves under a stored value.
  `probe_count`: derivable from `03_ip_probe.json`, but only by scanning
  441 MB. `assigned`: a projection of the status, but it encodes the
  project's *policy* about which statuses count as held, which is expected
  to change.
- **Keep the summary, and the document, but consider splitting them.**
  `rdap.summary` is a projection of `rdap.document`; the summary is 6 MB of
  the file and the documents are the other 159 MB. If the verbatim documents
  move to a sidecar file, `02_ip_block.json` drops to about 6 MB and the map
  and the audit still work.

## Verification

- `python3 sources/ip_block_audit.py` — 0 internal contradictions, 9,200
  blocks, 2026-09-11.
- `make test` — all nine tests pass, including `tests/09-block-map.sh`, which
  builds the map from fixtures and checks the order, the gap rows, the
  per-block page, and that no registrant contact detail is published.
- `make site` — index, 47 octet pages, 9,200 block pages, in 8 seconds.

## Also in this pass

- **The map's stylesheet moved into the head.** It was being written into the
  page body, so a block of CSS rendered as visible text at the top of every
  map page. `tests/09-block-map.sh` now asserts that the stylesheet is in the
  head and not in the body.
- **The fourth explanation lost its pattern list** (owner, 2026-09-11). The
  theory document had listed four supposed signatures for "other" — a
  light-speed latency, an answer to a challenge generated after the run,
  content with no human provenance, and identical behaviour across unrelated
  registries. The owner rejected the list, and rightly: they were guesses
  dressed as criteria. Nothing is expected of that explanation now; the tests
  earn their place by eliminating Earth-bound readings, and a case that
  survives them is recorded as unexplained. Nothing in the computed result
  changed: the light-speed pass found no candidate before and finds none now.
- **Two new enricher modes**: `--cache-only` reapplies the cached RDAP
  answers and asks the registries nothing, which is what makes a regeneration
  cheap; and the keep-the-file rule now compares the stored annotation with
  the cached one, so a rebuild that changes content is no longer mistaken for
  a no-op.

## Commits

- `0d2942e` feat: audit the block fields and build the browsable map
- the leak-gate boundary fix in the homelab: `cd97427` fix: do not read a
  public address as a private one in the leak gate
- the regeneration, the field drops, the stylesheet fix, and the fourth
  explanation's reframing: `pending`
