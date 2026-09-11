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

2. **All 9,200 block UUIDs no longer match their derivation rule.** The
   namespace string was changed from `ip_telescope` to `IP_telescope` on
   2026-09-11, after the blocks were written. The data is internally
   consistent — the probe-to-block file and the characterization refer to
   the same UUIDs — but re-deriving from today's code would produce a
   different set, so any join rebuilt today would silently miss. The audit
   accepts the historical namespace and reports it as a note rather than an
   error. **A decision is needed**: regenerate the phase 2 files (cheap: the
   RDAP cache refills without network), or freeze the old namespace.

After the repair: **zero internal contradictions** across 9,200 blocks.

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

## Fields that can be dropped

The audit answers the question of which redundancy earns its keep.

- **Droppable outright.** `derived.address_end` (start + value − 1),
  `derived.prefix` (start and value, and it was wrong for 21 blocks until
  repaired), `derived.opaque_id` (a copy of `rir_record.extensions[0]`), and
  `rdap.query` (always `rir_record.start`).
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

## Commits

- `pending` feat: audit the block fields and build the browsable map
