# Characterizing an Anomalous ip_probe

This document records what the project *expects* to see, before it looks.

The observed characterization lives in the records, one per site, dated, with
the evidence that produced the verdict.

## The Problem

Phase 3 asked 49,572 addresses that no operator holds one HTTP question.
Ninety-nine of them answered.

An answer is not an explanation.
An address in space that no registry hands to anyone may answer for four
quite different reasons, and the difference matters more than the answer.

The project admits four explanations.

## The Four Explanations

**1. Curious.** Other folk running the inverse exercise: looking for
connections with no obvious purpose, in the same spirit as this project.
They want to be found, or at least they do not mind.
Their work is deliberate, self-explanatory, and stable.

**2. Incidental.** The address responds through an accident of
configuration: a default virtual host, a hosting panel's parked page, a
router answering on a range nobody meant to route, a registry record that
went stale while the range was quietly transferred, or a mis-announcement.
Nobody chose this address. Nothing is being said.

**3. Nefarious.** Local folk who need to hide: command-and-control
infrastructure, spam or proxy endpoints, a range used without permission
because attribution is hard there.
They will imitate group 1 or group 2 when noticed, which is why a
convincing default page is not evidence of innocence.

**4. Other.** Not local folk.
This explanation is admissible, it is the reason the project exists, and it
is the one most likely to be reached by wishful thinking rather than
evidence.

## Where To Look

Two theories place the search, and they are not equally cheap.

**Theory one: unexpected response in unallocated space.** The addresses no
operator holds, where nothing is supposed to answer at all. This is the
phase 3 result already in hand: 99 answers, 6 refusals, 1 reset, and 582 of
584 blocks silent. It is the obvious place, and it is small enough to
characterize properly. This is **phase 4**.

**Theory two: rogue `ip_probe` inside operator-held blocks.** An address
inside a block that some operator holds normally answers because a normal
service lives there. The interesting case is narrower: an address that
answers while its surroundings say it should not, or that the registry's own
object does not cover.
A rogue host hides best in a large block, where the owner cannot know every
address.
This theory is a test rather than a survey, and it is **deferred to phase 5**
until the characterization criteria are trusted.

## Expected Characterization

| | Motive | Expected signature | What would confirm it | The trap |
| --- | --- | --- | --- | --- |
| 1 Curious | To be found, or to watch who looks | Deliberate, self-explanatory, uniform across the range, stable between passes; answers only on the four-prime addresses; a named certificate | Content that explains its own purpose; identical answers from every deliberate address and nothing from the neighbours | Content may be absent by design; silence from the neighbours may be a filter rather than a choice |
| 2 Incidental | None | Default and catch-all artifacts; only part of the block answers; a boundary or an announcement explains it | Any `Host` header gets the same answer; a default-page fingerprint; a certificate naming an unrelated domain; reverse DNS pointing at a hosting provider; the live range matching an allocation boundary | A stale registry record looks exactly like an accident, and is a different story |
| 3 Nefarious | To hide | Mimicry of 1 or 2, with the layers disagreeing; behaviour that changes between passes | The application claims one identity while certificate, reverse DNS, or registry origin claim another; refusals and resets instead of answers; answering only under some probe patterns; hosting where no registry owner exists | Assuming concealment where a configuration accident would do; and assuming innocence because the page looks official |
| 4 Other | Unknown | A capability we cannot reproduce | Latency below the light-speed bound for the claimed distance; an answer to a challenge generated after the run; content with no human provenance; the same behaviour in unrelated registries at the same moment | Every hoax, and every measurement error, lands here first |

## The Discriminating Tests

The tests are ordered by how much they discriminate per unit of effort.

- **The control test.** Probe non-prime neighbours inside the same block. An
  incumbent service answers everywhere; a deliberate exercise answers only on
  the four-prime addresses. This single comparison separates group 1 from
  group 2 more sharply than any amount of reading the page.
- **The catch-all test.** Ask for the same page with an unrelated `Host`
  header. An identical answer means the server is not listening for a name,
  which is the signature of a default or parked configuration.
- **The layer-disagreement test.** Compare the certificate subject, the
  reverse DNS name, the RDAP organization, and the application's own claim.
  Agreement everywhere suggests an ordinary operator; disagreement is the
  signature of group 3.
- **The uniformity test.** Compare answers across addresses in one block. One
  page repeated everywhere is a configuration; a page that varies by address
  is deliberate.
- **The stability test.** Repeat the pass later. Deliberate services persist;
  hidden ones move.
- **The self-explanation test.** Look for content that explains its own
  purpose: a banner, an invitation, a puzzle, a robots.txt with a purpose.
- **The geography test.** Compare latency with the claimed location. A
  service claiming one continent while answering in three milliseconds is
  not where it says it is.
- **The impossibility test.** Reserved for group 4, and the only test that
  can support it: a measurement no Earth-bound explanation reproduces.

## The Traps

- **Mimicry.** Group 3 imitates groups 1 and 2, so a tidy default page is not
  evidence of an accident.
- **The mirror.** This project's own probes look like the thing it hunts. The
  prime-octet pattern is the tell, in both directions.
- **Hoax bias.** A human hoax is far more likely than the fourth explanation,
  and the project's own owner is a candidate author.
- **Absence of evidence.** An unexplained answer is not evidence for group 4.
  It is an unexplained answer.
- **Registry lag.** `reserved` in a delegation file is a claim with a date,
  not a fact. RDAP and the routing table are separate testimonies, and they
  disagree more often than the word "registry" suggests.
- **Anycast and CDN.** One service answering from many places explains
  uniformity without any deliberation at all.

## The Decision Procedure

1. Gather the evidence: the probe battery, in one pass, with controls.
2. Rule out the incumbent: does a non-prime neighbour answer too? If so, the
   explanation is incidental or ordinary, and the work stops there.
3. Test deliberation: answers only on four-prime addresses, or content that
   explains itself. That points to group 1.
4. Test concealment: do the layers disagree, does the behaviour change between
   passes, is the answer a refusal rather than a page? That points to group 3.
5. Test impossibility, and only then: is there a measurement that no
   Earth-bound explanation reproduces? That points to group 4.
6. Otherwise record **unexplained**, and name the measurement that is missing.

## How It Is Recorded

- The expected characterization is this document and
  `prompts/features/06-probe-characterization.md`.
- The observed evidence is `dataflow.out/06_ip_probe_characterize.json`, one
  record per probed address, controls included.
- The observed characterization is a record in `records/`, one per site,
  dated, with the evidence, the verdict, the confidence, and the falsifier.
- The criteria are expected to change as data arrives. Each revision is dated
  here rather than silently replacing the old text.

## Open Questions

- What counts as self-explanation? A page, a banner, a challenge, a
  `robots.txt`, or a name that mentions the pattern.
- Should every anomalous address be probed on more than one occasion before a
  verdict, given that stability is one of the discriminators?
- How should a service that answers on *some* four-prime addresses be read?
  Partial answers suggest filtering, which is itself a signal.
- What confidence scale? Proposal: high, medium, low, and
  single-observation, which is where every first pass starts.
- Should the deferred phase 5 rank candidates by block size, by the gap
  between the registry object and the answers, or by both.
