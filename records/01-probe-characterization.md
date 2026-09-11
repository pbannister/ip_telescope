# Record: probe characterization (phase 4)

## Outcome

Phase 4 characterized the anomalous `ip_probe` from the 2026-09-10 pass: the
addresses that answered, refused, or reset in space that no RIR operator
holds.

The pass probed 106 anomalies and 236 control addresses drawn from the same
four blocks — 342 targets — with the phase 4 battery: HTTP with the address
as `Host`, HTTP with an unrelated `Host` (the catch-all test), HTTPS with the
peer certificate, reverse DNS, and three TCP connect samples.

The expected characterization was written first
(`documents/07-characterization-theory.md`,
`prompts/features/06-probe-characterization.md`), so the evidence had
something to be compared against.

The result is recorded per site below, with the verdict, the confidence, and
the measurement that would overturn it.

## The Method Finding

**The four-prime pattern is not in the answers.** Every service answered its
non-prime neighbours as well, so the pattern was an artifact of where phase 3
looked, not a property of the services.

**Corrected 2026-09-11, by the owner.** The first wording here claimed that
prime-only answering "would have been the tell of another party running the
inverse exercise", so that its absence argued against group 1. The owner
disagrees, and is right: a party running the inverse exercise would most
likely be watching a *range*, not a pattern, and the probes would simply have
fallen inside a block they monitor. Answering the whole range is therefore
consistent with group 1 as well as with group 2, and this test separates
neither from the other.

What the control sample does establish is the extent of each live range, and
that the services do not exist because of the pattern. Separating a curious
party from an ordinary host needs the awareness test: a response that changes
because of our probing, a baseline from another vantage point, or content
that engages the pattern. None was observed, so group 1 stays open wherever
group 2 is asserted, and the verdicts below say so.

The sample also corrected the project's own sampling: it turned 99 answering
addresses into 237 in one block, so probing only four-prime addresses
undersamples a live range roughly four to one.

**The registry file is one witness, not the truth.** Adding the routing layer
— who actually announces the prefix — resolved three of the four sites
immediately. The delegation record, the RDAP object, the routing table, the
reverse DNS, and the certificate are separate testimonies that disagree more
often than the word "registry" suggests.

## Site A — 23.191.137.0–23.191.151.255 (ARIN, `reserved`)

**Evidence.**

- 237 of 245 probed targets answered, and all 237 gave the same answer: HTTP
  `301` to `https://<address>/`, `Server: nginx`, one body digest
  (`9e17cb15dd75…`).
- The catch-all test fired: an unrelated `Host` received the same answer.
- One certificate served the whole range: common name `ology.com`, subject
  alternative name `ology.com`, issuer Let's Encrypt R10, valid
  2025-03-02 to 2025-05-31 — **expired for over a year**.
- No reverse DNS on any address.
- The answering range is 23.191.144.127 to 23.191.151.251, which is exactly
  the eight `/24`s (`23.191.144.0/24` to `23.191.151.0/24`) announced by
  **AS400050**. The rest of the registry block, including `23.191.137.0/24`,
  is not announced and did not answer.
- `ology.com` resolves to `23.191.144.8` and `23.191.144.9`, inside that
  announced range.
- RDAP holds no object for the block, only its parent `23.0.0.0/8`, which
  ARIN holds itself.

**Verdict: incidental, with curious not excluded.** The anomaly is an artifact
of the delegation record. The space is announced, the domain's own DNS points
into it, and the certificate names the same domain: an ordinary web host whose
registry record is stale, and nothing about it is concealed.

Group 1 is *not* excluded, and the owner's correction of 2026-09-11 removed
the reason the first draft gave for excluding it: a curious party watching
`23.191.144.0/20` would answer exactly as this service does. What argues
against a watch post is the shape of the identity — a named commercial domain
with a certificate that expired in May 2025 reads as an abandoned ordinary
host rather than an active observer.

Confidence: **medium** for the verdict, **high** that this is not concealment.

**Falsifier.** If AS400050 withdrew its announcement and the answers
persisted, or if the certificate and DNS were unrelated to the announced
range, this reading would fail. It would move to group 1 if an awareness test
showed the service reacting to our probes; it would move to an ordinary live
service if the certificate were renewed and the site came back to life.

## Site B — 103.241.72.0/22 (APNIC, `reserved`)

**Evidence.**

- Four targets answered: `103.241.73.190`, `.191`, `.192` with an nginx `200`
  serving a Chinese redirect page ("正在跳转") that loads `car.js`, and
  `103.241.74.84` serving an unconfigured `Apache/2.4.29 (Ubuntu)` default
  page with no TLS.
- The catch-all test fired on the nginx host.
- Certificate: common name `baidu.sina.2022.5508085.com`, alternative names
  `2022.mid.jx.500.5508085.com`, `baidu.sina.2022.5508085.com`, and
  `motogp.2022.rossi.5508085.com`; issuer Let's Encrypt YR1; valid
  2026-07-31 to 2026-10-29, current.
- `baidu.sina.2022.5508085.com` resolves to `103.241.73.190`, inside the
  block.
- `103.241.73.0/24` is announced by **AS152194 (CTG Server Limited)**, a
  hosting provider, although the delegation file calls the whole `/22`
  `reserved`.
- No reverse DNS.

**Verdict: two separate claims, and they are both true.**

- **Incidental**, for the anomaly: the prefix is announced while the registry
  record says `reserved`, so the anomaly is a records artifact.
- **Nefarious**, for the activity: an automatic redirect page, a throwaway
  domain farm in the certificate, an unrelated host on the same `/24`, no
  reverse DNS, and hosting in space with no recorded owner. Nobody needs that
  combination to be found.

Confidence: **medium**. Abuse of a reseller's host cannot be separated from a
deliberate operator without the provider's own records.

**Falsifier.** A hosting-abuse report, the provider's allocation record, or
the content disappearing after a takedown would move the second claim.

## Site C — 103.149.23.0/24 (APNIC, `reserved`)

**Evidence.**

- No address answered HTTP.
- Six addresses refused the connection (`103.149.23.11`, `.13`, `.14`, `.67`,
  `.70`, `.71`); the rest timed out.
- Round-trip time 170–181 ms, stable across samples.
- The `/24` is announced by **AS4657 (StarHub Ltd, Singapore)**.
- `103.149.23.0/24` is listed as `reserved` by APNIC.

**Verdict: incidental.** A stale registry record plus ordinary filtering on an
announced range where no service runs. The refusals are a live network saying
"nothing here", not a concealed service. The geography test passes: the
latency is consistent with the announced operator's location. Confidence:
**high**.

## Site D — 199.47.160.0/21 (ARIN, `reserved`, no RDAP object)

**Evidence.**

- No address answered HTTP.
- Two refusals (`199.47.167.2`, `.103`) and four resets (`.167.19`, `.20`,
  `.22`, `.100`); the rest timed out.
- Round-trip time 80–81 ms, stable.
- `199.47.167.0/24` is announced by **AS14902**, although the containing `/21`
  is not announced.
- RDAP holds no object for the block at all.

**Verdict: unexplained, narrowing to incidental.** The refusals come from an
announced `/24` inside a block with no registry object. Ordinary filtering is
the most likely reading, and the evidence does not identify the device or its
purpose. Recording this as unexplained rather than guessing is the point of
the confidence column.

**Falsifier, and the next measurement.** A traceroute, or the same probe from
an independent vantage point such as a RIPE Atlas measurement, would place
the reset source. A repeat pass would show whether the reset set moves.

## Decisions

- The four-prime pattern is not evidence of another party's interest; the
  control sample is the cheapest way to test it, and it comes first.
- A characterization states one claim per layer. Site B carries two claims
  because the registry artifact and the hosted activity are different
  questions with different evidence.
- The routing layer is part of the battery from now on. It resolved three of
  four sites for the cost of an API call.
- An anomaly with no HTTP content can still be characterized, but only as far
  as the routing layer allows.
- "Unexplained" is recorded as a result, with the measurement that is missing.

## Verification

- `tests/08-probe-characterize.sh` — portable, passes: the answer, the
  catch-all signal, the control refusal, the self-signed certificate capture,
  and the reuse rule.
- The full suite passes, `make test`, 2026-09-11.
- The pass itself: 342 targets in 3m22s, 2026-09-11, verified against the
  live Internet.

## Follow-Ups

- Repeat the pass later to test stability, which is one of the discriminators
  the criteria rely on.
- Place the reset source at Site D with a traceroute and an outside vantage
  point.
- Map the live ranges exactly, rather than by sample, for Sites A and B.
- Decide whether reviewing the routing layer belongs in phase 4 or becomes a
  separate collection step.
- **Second vantage point (deferred; owner note, 2026-09-11).** The owner's
  webhost has servers in Oregon and is reachable over SSH. It is not to be
  used, and it is the wrong end of the test for the geosynchronous band,
  because it shares the project host's coast — the project host reports
  `America/Los_Angeles`, and two observers on one coast differ by a few
  milliseconds either way, which is inside jitter. It may still be usable for
  the lunar floor: two observers a thousand kilometres apart can differ by at
  most about 7 ms of lunar round trip, against tens of milliseconds over a
  terrestrial path, and the quantum is 2,564 ms. The strong version of the
  test still wants an observer on another continent.

## Addendum: the light-speed test, and a second pass — 2026-09-11

### The correction the light-speed test forced

Phase 3 timed whole HTTP requests, and a request costs two round trips. A
responder at lunar distance would need about 5.1 seconds to answer a `GET` —
outside the 3-second phase 3 budget, and therefore recorded as a timeout,
which is exactly what a blackhole records. The same responder would complete
a TCP connect, one round trip, in 2.6 seconds.

Phase 4 measures connects, and its 5-second budget puts the lunar floor
inside the window. Anything past that budget — Sun–Earth L2 at 10 seconds,
which is the outer bound the project means to look at — stays invisible, and
the result file now states that budget next to the two floors, so the blind
spot is visible rather than implied.

### Result

Pass 2 ran 2026-09-11T09:04:39Z and recorded the bands. Of 342 targets, 245
connected and 89 were clipped at the budget. **No address had a floor on
either quantum**: every one classified as `none`.

| Site | Smallest connect | Median |
| --- | --- | --- |
| `23.191.137.0` (ARIN) | 8 ms | 65 ms |
| `103.241.72.0` (APNIC) | 170 ms | 171 ms |

Jitter ran from 1 ms to 1004 ms, median 10 ms, and no address was jitter-free.

The exclusion half of the test is what bites here. A floor of 8 ms rules out
geosynchronous orbit by a factor of thirty and the Moon by a factor of three
hundred. The refusals at 170–181 ms in `103.149.23.0/24` rule that site out of
geosynchronous orbit too, which agrees with the announcement: StarHub,
Singapore, on the ground.

So the fourth explanation has no evidence behind it: for every address that
answered, the measurement rules it out, and for the addresses that stayed
silent, the budget already covered the Moon.

**Corrected 2026-09-11, same pass.** The first wording here said the pass
"said nothing at all" about the 89 targets clipped at the budget. That is
wrong, and the arithmetic says why: the lunar round trip is 2,564 ms and the
budget is 5,000 ms, so a responder at lunar distance *would have answered in
time*. The 89 targets did not, which excludes the Moon for them as well as
for the addresses that answered. What stays outside the window is Sun–Earth
L2 at 10 seconds and anything slower. The owner scoped the search to L2 and
nearer on 2026-09-11, so the remaining blind spot is the outer edge of the
range of interest rather than the whole far field.

One trap worth recording. Thirty-one of the 99 phase 3 answers fell within a
quarter of the geosynchronous quantum, and every one of them was an ordinary
long-haul path. Two things were wrong with that reading: the band is a filter
rather than a finding, and it was applied there to two-round-trip times,
which inflates a floor by roughly half.

### Stability

Pass 2 ran 21 minutes after pass 1. All 241 answers, all 241 body digests, and
every control outcome were identical; not one address changed state.

Stability is one of the discriminators, and these sites are stable, which is
what the verdicts predict for ordinary services and evidence against a moving
operation. A 21-minute window is a first data point, not a proof.

## Addendum: the isolation test — 2026-09-11

Owner hypothesis: the strongest hint is an `ip_probe` that responds while the
two addresses immediately beside it do not. A service that covers a prefix
lights its whole range; one lit address between two dark ones was *placed*
there.

The pass now runs a second wave over the immediate neighbours of every
responder. Pass 3 (2026-09-11T10:06Z) measured 598 targets — 106 anomalies,
236 controls, and 256 neighbours — in 4m10s. Of those, 499 responded and
**6 responded alone**.

| Address | Answer | Floor | Block | Neighbours ±1 |
| --- | --- | --- | --- | --- |
| `103.149.23.11` | refused | 178 ms | APNIC `reserved`, announced by StarHub | both silent |
| `103.149.23.67` | refused | 183 ms | APNIC `reserved`, announced by StarHub | both silent |
| `199.47.167.2` | refused | 79 ms | ARIN `reserved`, no RDAP object | both silent |
| `199.47.167.22` | reset | 80 ms | ARIN `reserved`, no RDAP object | both silent |
| `199.47.167.100` | reset | 79 ms | ARIN `reserved`, no RDAP object | both silent |
| `199.47.167.103` | refused | 80 ms | ARIN `reserved`, no RDAP object | both silent |

Two of the six were addresses phase 3 never probed: phase 4 found them as
controls. That is the filter doing its job — it is not limited to the
addresses the prime pattern pointed at.

**None of the six serves a page.** Every one refuses or resets, with no
certificate, no reverse DNS, and a floor consistent with the operator's
location (StarHub, Singapore; and the AS14902 prefix on the ground).

**The wider neighbourhood, measured, changes the reading.** Four of the six
have a small responding cluster two to four addresses away: `103.149.23.13`
and `.14` sit beside `.11`; `103.149.23.70` and `.71` beside `.67`;
`199.47.167.19` and `.20` beside `.22`; `199.47.167.100` beside `.103`.
Scattered singles and small adjacent pairs inside an announced prefix are what
individually used addresses look like — hosts that exist and reject port 80 —
rather than a service covering a range.

**Verdicts, updated.** Site C (`103.149.23.0/24`) stays **incidental**, now
more precisely: six single addresses in use within an announced StarHub
prefix, not a service. Site D (`199.47.160.0/21`) stays **unexplained,
narrowing to incidental**: the responses come from individually used
addresses inside `199.47.167.0/24`, which is announced although the
containing `/21` has neither an announcement nor an RDAP object. No group 1
candidate emerged; what emerged is a short list worth the next measurement.

**What the filter bought.** All 499 responders reduce to six candidates, in
two blocks, with named next steps: probe more ports on those six (a host
usually exposes or refuses others; a deliberate single-address service chose
port 80), place the reset source with a traceroute, sweep the two `/24`s to
the address so the isolation is exact rather than sampled, and repeat to see
whether the six persist.

**The inverse filter, noticed while checking the ranges.** Inside the live
ARIN range — `/24`s 144 to 151, which match AS400050's eight announced `/24`s
exactly — six measured addresses stayed silent while everything around them
answered: `23.191.149.7`, `.149.20`, `.149.255`, `.150.3`, `.151.20`,
`.151.25`. A dark address inside a lit range is the mirror of the isolation
test and may be a filter rather than an absence. It is recorded here as an
observation, not a finding.

## Commits

- `4ae326b` feat: characterize the phase 3 anomalies with control probes
- `fac9fe6` feat: measure light-speed bands and repeat the phase 4 pass
