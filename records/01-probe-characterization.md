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

**The four-prime pattern did not survive.** Every service answered its
non-prime neighbours as well. Prime-only answering would have been the tell
of another party running the inverse exercise; it is not there. The pattern
was an artifact of where phase 3 looked, not a property of the services.

The control sample turned 99 answering addresses into 237 in one block, so
probing only four-prime addresses undersamples a live range roughly four to
one.

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

**Verdict: incidental.** The anomaly is an artifact of the delegation record.
The space is announced, the domain's own DNS points into it, and the
certificate names the same domain: an ordinary web host whose registry record
is stale, not a hidden operation. Confidence: **high**.

**Falsifier.** If AS400050 withdrew its announcement and the answers
persisted, or if the certificate and DNS were unrelated to the announced
range, this reading would fail.

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

## Commits

- `4ae326b` feat: characterize the phase 3 anomalies with control probes
