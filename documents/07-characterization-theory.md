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
This explanation is admissible, and it is the reason the project exists.

**Nothing is expected of it (owner, 2026-09-11).** The project keeps no list
of signatures to look for, because nobody knows what would be there to find;
holding a pattern in advance would be inventing the answer. An earlier draft
of this document did list four supposed signatures — light-speed latency, an
answer to a challenge generated after the run, content with no human
provenance, and identical behaviour across unrelated registries — and the
owner rejected that, correctly: they are guesses dressed as criteria, and
each one invites reading a coincidence as a conclusion.

What the project can do instead is **eliminate**. Every test that rules an
Earth-bound reading in or out narrows the space: distance by the light-speed
floor, identity by certificates and reverse DNS, origin by the routing layer,
custody by the registry. A case that survives all of them and still resists
explanation is recorded as **unexplained**, with the measurement that is
missing named. That is the honest end state, and it is where the fourth
explanation has to live until something arrives that fits nothing else.

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
| 1 Curious | To be found, or to watch who looks | A range that answers, not a pattern: the probes fell inside a block the other party already monitors. Deliberate, self-explanatory where they choose to speak, uniform across their range, stable between passes; a named certificate | Content that explains its own purpose or engages the pattern; identical answers from every address in the monitored range; evidence of awareness that the range is being probed | Expecting the exercise to show in the address pattern. A monitoring party answers its whole range, which looks exactly like an ordinary host |
| 2 Incidental | None | Default and catch-all artifacts; only part of the block answers; a boundary or an announcement explains it | Any `Host` header gets the same answer; a default-page fingerprint; a certificate naming an unrelated domain; reverse DNS pointing at a hosting provider; the live range matching an allocation boundary | A stale registry record looks exactly like an accident, and is a different story |
| 3 Nefarious | To hide | Mimicry of 1 or 2, with the layers disagreeing; behaviour that changes between passes | The application claims one identity while certificate, reverse DNS, or registry origin claim another; refusals and resets instead of answers; answering only under some probe patterns; hosting where no registry owner exists | Assuming concealment where a configuration accident would do; and assuming innocence because the page looks official |
| 4 Other | Unknown | **None.** No signature is expected and none is assumed; the category is what remains once the other three are ruled out | Nothing in the way of a pattern. What moves a case here is surviving every Earth-bound reading, with a measurement nobody can reproduce | Reading an unexplained feature as this explanation. Every hoax, and every measurement error, arrives here first |

## The Discriminating Tests

The tests are ordered by how much they discriminate per unit of effort.

- **The isolation test.** Probe the two addresses immediately beside every
  responder. An address that answers while both neighbours stay silent is
  being *addressed*; anything that covers a prefix is being *ranged*. This is
  the owner's strongest hint (2026-09-11), it costs two probes per responder,
  and it is the project's first filter. See the section above for the mundane
  readings it admits.
- **The control test.** Probe non-prime neighbours inside the same block. It
  answers two questions, and only two: how far the live range extends around
  an address that answers, and whether the service exists *because* of the
  four-prime pattern.
  It does **not** separate group 1 from group 2, and the owner corrected an
  earlier claim here that it did (2026-09-11). A curious party watching a
  range would answer every address in that range, exactly as an ordinary host
  would; the probes simply fell inside a block they monitor. Prime-only
  answering would be one particular style of deliberate placement, not the
  expected form of the exercise, so a negative result from this test says
  nothing against group 1.
  Separating group 1 from group 2 needs the awareness test below.
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
- **The awareness test.** This is what separates group 1 from group 2, and it
  is the hardest to run. A party watching a range knows it is being probed,
  and may show it: a response that changes after our probes, a service that
  answers on a schedule, a page that acknowledges the pattern, a reply to
  something only a prober would send. An ordinary host shows none of it. The
  test needs a baseline (the same probes from a second vantage point, or the
  same address probed by other parties) to tell "changed because of us" from
  "changed anyway".
- **The geography test.** Compare latency with the claimed location. A
  service claiming one continent while answering in three milliseconds is
  not where it says it is.
- **The light-speed test.** Compare the smallest round trip with the floor for
  each plausible distance, then repeat it from a second vantage point far
  away. That is a rule-out, not a detection: it can show that a responder is
  not at a distance, and it leaves the case unexplained rather than promoting
  it.
- **Elimination, not detection.** There is no test that detects the fourth
  explanation, because no signature for it is expected. The tests earn their
  place by removing Earth-bound readings one at a time; a case that survives
  them all is recorded as unexplained, with the missing measurement named.
  Anyone who writes a pattern list for the fourth explanation is guessing.

## Light-Speed Signatures

Distance is the cheapest hard fact the project has, because light takes time
and nothing beats it. The comparison below is a **falsifier**: it rules a
distance out, and it never announces what a case *is*. It is here because it
eliminates, not because a light-speed latency is expected of the fourth
explanation — nothing is expected of it (see above).

| Where the responder is | Distance | One round trip at the speed of light |
| --- | --- | --- |
| Low Earth orbit | 400–2,000 km | 3–13 ms |
| Geosynchronous orbit | 35,786 km | **239 ms** |
| The Moon | 384,400 km | **2,564 ms** |
| Sun–Earth L2 | 1.5 million km | 10.0 s |

**Scope (owner decision, 2026-09-11).** Distances much beyond L2 and the Moon
are out of scope: the project is not searching for latency that would imply
Mars or deeper space. L2 is the outer bound of interest.

**Measure one round trip, not one request.** A TCP connect completes in one
round trip; a full HTTP exchange costs two. A responder at lunar distance
would finish a connect in 2.6 seconds and a GET in 5.1 seconds, so a pass
that times whole requests with a three-second budget cannot see the Moon even
when it is talking to it. The connect measurement is the one that counts.

**Take the minimum of several samples.** Jitter only ever adds, so the
smallest of many round trips is the best available estimate of the
propagation floor. Three samples is a start; a candidate deserves more.

**A floor below the quantum rules the distance out.** This is the rigorous
half of the test, and it is free. If the best round trip to a responder is
80 ms, it is not on the Moon, and no amount of strangeness in the page
changes that.

**A floor on the quantum is a candidate, not a signature.** Ordinary
long-haul terrestrial paths sit in the geosynchronous band, so the band alone
decides nothing. Three further conditions must hold together:

- **A floor pinned to a quantum**, not merely inside a broad band, and
  consistent across passes.
- **Almost no jitter.** A vacuum path has no queueing on the space segment.
  A terrestrial long-haul path is never that steady.
- **Independence from the observer's position.** This is the decisive test.
  A terrestrial server answers a nearby observer faster than a distant one.
  A lunar responder does not care: moving an observer from beneath it to the
  far side of the Earth changes a lunar round trip by at most the Earth's
  radius each way, about 42 ms, or 1.6 percent of the quantum. Two widely
  separated vantage points seeing the same floor is the signature.
  The size of the vantage can be counted, which decides what a given second
  observer is worth. Two observers a thousand kilometres apart can differ by
  at most about 7 ms of lunar round trip, against tens of milliseconds over a
  terrestrial path: discriminating for the lunar floor. Two observers on the
  same coast differ by a few milliseconds either way, which is inside jitter
  and decides nothing in the geosynchronous band, where the quantum is only
  239 ms to begin with.

**A timeout is not evidence of absence.** Anything beyond the budget — L2 at
ten seconds, and anything slower — is recorded as a timeout, which is exactly
what a blackhole records. Every pass must state its budget so the blind spot
is visible. Since L2 is the outer bound of interest, a pass that wants to
cover it needs a wait of about eleven seconds.

**Choose the budget so the quantum of interest falls inside it.** The budget
decides which distances are testable rather than merely unobserved. A
five-second connect budget puts the lunar floor inside the window, so a
silent address is then evidence against the Moon, where a three-second budget
covering only whole requests would have left it ambiguous.

**The confounders.** Anycast and CDN place many servers that can look
location-independent; satellite internet puts ordinary users behind a
geosynchronous hop; and a long path through a congested transit network can
imitate both jitter and distance. Any of those is more likely than the fourth
explanation, and each is testable.

## The Isolation Test: The Strongest Hint

**Owner hypothesis, 2026-09-11.** The strongest hint of all is an `ip_probe`
that responds while the two addresses immediately beside it do not.

The reasoning is about *addressing* rather than *ranging*. A service that
covers a prefix lights its whole range: an operator's host, a stale registry
record, a monitoring party watching a block, all look the same from outside
because they all answer the neighbours. A single address lit between two dark
ones is different in kind: something was put on **that address**, on purpose,
and nothing was put on the addresses either side.

That is the shape a post office would have. It is also the shape of an
accident, so the mundane readings come first:

| Mundane reading | How to tell it apart |
| --- | --- |
| A single-address assignment (`/32`, or one address out of a larger block handed to a customer) | The registry object: RDAP may show a `/32` or a small assignment, and the block around it may be reserved or unassigned |
| A virtual address on a load balancer, NAT, or anycast | Ask twice: a VIP or anycast endpoint usually answers from more than one place, and a second vantage point sees a different floor |
| A host with a firewall rule that admits our probe and drops the rest | Change something small: a different port, a different `Host`, a different time. A rule written for one probe pattern keeps answering that pattern only |
| A neighbour that is dark *now* but answers later | Repeat the pass. Isolation that flickers is scheduling; isolation that persists is addressing |
| A probe artefact: the neighbour is routed differently, or it is in another operator's block | Look at the block boundary, and at who announces each of the three addresses |

**The test is cheap and sharp, and it is now the project's first filter.** It
costs two extra probes per responder, and it divides a long list of "something
answered" into the small set of "something was placed here", which is the set
worth an awareness test.

Note what it does *not* do: it does not separate the four explanations by
itself. An isolated responder may still be an ordinary single-address
service, and it may be a curious party's post. It says where to look, not
what is there.

## The Traps

- **Mimicry.** Group 3 imitates groups 1 and 2, so a tidy default page is not
  evidence of an accident.
- **The mirror.** This project's own probes look like the thing it hunts. The
  prime-octet pattern is the tell, in both directions — and the owner's
  correction (2026-09-11) is that the tell is in *our* pattern, not in
  theirs. Expecting the other party to answer only on four-prime addresses
  assumes they organised their infrastructure around a pattern they may not
  even know exists.
- **Hoax bias.** A human hoax is far more likely than the fourth explanation,
  and the project's own owner is a candidate author.
- **Absence of evidence.** An unexplained answer is not evidence for group 4.
  It is an unexplained answer.
- **A latency band is not a signature.** Thirty-one of the phase 3 answers
  sat within a quarter of the geosynchronous quantum, and every one of them
  was ordinary long-haul terrestrial routing. The band is a filter for
  candidates, not a finding.
- **Registry lag.** `reserved` in a delegation file is a claim with a date,
  not a fact. RDAP and the routing table are separate testimonies, and they
  disagree more often than the word "registry" suggests.
- **Anycast and CDN.** One service answering from many places explains
  uniformity without any deliberation at all.

## The Decision Procedure

1. Gather the evidence: the probe battery, in one pass, with controls and with
   the two immediate neighbours of every responder.
2. Filter for addressing: does the responder answer alone, with both immediate
   neighbours silent? Those are the candidates worth the rest of this
   procedure. Everything that answers its neighbours is a range, and a range
   is an operator, a stale record, or a watching party — three readings the
   remaining tests cannot separate.
3. Rule out the incumbent shape: a range that answers is ordinary; a single
   lit address needs the mundane readings from the isolation table ruled out
   one by one.
4. Test deliberation: content that explains itself, answers that vary by
   address rather than repeating one page, or any sign of awareness of the
   probing. That points to group 1.
5. Test concealment: do the layers disagree, does the behaviour change between
   passes, is the answer a refusal rather than a page? That points to group 3.
6. Eliminate what can be eliminated: distance with the light-speed floor,
   identity with certificates and reverse DNS, origin with the routing layer,
   custody with the registry. Do not hunt for a pattern; there is none to
   expect for the fourth explanation, and a pattern found in the data is a
   coincidence until it is a measurement.
7. Otherwise record **unexplained**, and name the measurement that is missing.

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
- What tolerance counts as a floor "pinned" to a quantum? The battery
  currently bands a floor from 0.95 to 1.30 times the quantum, which is wide
  enough to catch ordinary long-haul paths, so the band is a filter and the
  jitter and vantage tests do the deciding.
- Where does the second vantage point come from? The project has one host
  today, on the US west coast, and the decisive test needs an observer far
  from it. Three candidates, all recorded as **deferred options that are not
  to be used yet** (owner notes, 2026-09-11):

  | Option | Worth | Catch |
  | --- | --- | --- |
  | A cloud virtual machine in a distant region (Amazon, Google, or the like) | **The strongest of the three.** The region is a known place, so the distance is known rather than guessed, and the observer can be put wherever the arithmetic asks: an intercontinental separation is what the geosynchronous band needs | Costs a few cents an hour; the provider's egress may not reach dark address space at all, though every address worth testing here answered, so it is routed by definition; a provider may treat address probing as scanning, so keep it to a handful of connects to named addresses, documented |
  | The owner's webhost in Oregon | Free, reachable over SSH, and weak: it shares the project host's coast | Same-coast observers differ by a few milliseconds either way, which decides nothing in the geosynchronous band; it could still speak to the lunar floor |
  | A RIPE Atlas measurement | Many vantage points, someone else's hardware, no account of one's own to run | Needs an account and credits, and the anchors' locations are the operator's, not chosen for this question |

  **What the deferred test would do**, so that it is ready to run rather than
  an idea: from the second vantage, measure one round trip to the same
  addresses — the six isolated responders, a representative address of each
  answering site, and any address whose floor lands in a band — as the
  smallest of at least thirty connects, and record the vantage's region and
  evidence for it. Then compare floors. The same floor from both places, with
  no jitter, is the signature that no terrestrial path produces; a floor that
  shifts with the observer, by about the difference in path length, is a
  terrestrial answer and closes the question.
- Should the far field get its own pass with a deliberately long wait — ten
  seconds would reach L2 — on a sample of addresses, given that the ordinary
  budget cannot see past it?
- Should the deferred phase 5 rank candidates by block size, by the gap
  between the registry object and the answers, or by both.
