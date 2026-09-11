# Feature: Probe Characterization

## Purpose

Phase 3 finds addresses that answer where no operator holds them. An answer
is not an explanation.

An anomalous `ip_probe` has four admitted explanations:

* **Curious** — other folk running the inverse exercise, looking for
  connections with no obvious purpose.
* **Incidental** — an address that responds through an accident of
  configuration.
* **Nefarious** — local folk who need to hide, and who may imitate the first
  two.
* **Other** — not local folk, and nothing is expected of it: the project keeps
  no signature list for this explanation, because nobody knows what would be
  there to find (owner, 2026-09-11).

This feature gathers the evidence that separates those explanations, records
the evidence that would overturn its own conclusion, and keeps the reasoning
where a later pass can check it.

## Requirements

* Every anomalous address must be characterized against all four
  explanations, not assigned to the first plausible one.
* The evidence must come from the address itself: an explanation that rests
  only on expectation is not a characterization.
* An address that no evidence explains must be recorded as **unexplained**.
  Unexplained is a result, not a failure.
* Each characterization must state the evidence, the verdict, a confidence,
  and what evidence would overturn it.
* Each anomalous address must be probed together with **control addresses**
  in the same block.
* The two addresses immediately beside every responder must be probed, in a
  second wave after the first, so that the isolation test has both sides
  measured for every responder, including responders the pass found itself.
* Each observation must record whether the address responded, the outcome of
  each immediate neighbour, and whether the address responded alone:
  `isolation.responded`, `isolation.neighbour`, and `isolation.isolated`.
* An address is isolated only when it responded and *both* neighbours were
  measured and neither answered. An unmeasured neighbour leaves the question
  open rather than answering it.
* The result file must carry an `isolation_summary` listing every isolated
  responder, so the sharpest filter in the project is visible without
  post-processing.
* A control address must be one whose octets are not all prime, because an
  incumbent service answers on every address in its range, while a
  deliberate exercise answers only on the four-prime addresses.
* The probes for every address must record:
    * the HTTP root on the configured HTTP port, with the address as `Host`;
    * the HTTP root with an unrelated `Host`, which detects a catch-all
      virtual host;
    * the HTTPS root on the configured HTTPS port, with the peer certificate:
      subject, issuer, subject alternative names, validity, fingerprint, and
      whether verification succeeded;
    * the reverse DNS name, or its absence;
    * several TCP connect latency samples, taken as single round trips;
    * the block context: registry, status, size, and the RDAP handle, name,
      and organization.
* The latency samples must measure one round trip, not a whole request: a
  full HTTP exchange costs two round trips, and a responder at lunar distance
  would need about 5.1 seconds for a request against 2.6 seconds for a
  connect.
* The pass must record the light-speed floor for geosynchronous orbit and for
  the Moon, and name the band a measured floor falls in, if any.
* The pass must record its timeout budget as a blind spot: an address that
  does not answer within the budget is recorded as a timeout, which cannot be
  distinguished from a responder beyond that distance.
* The jitter of the latency samples must be recorded, because a floor pinned
  to a quantum is only a candidate until the jitter is small and a second
  vantage point sees the same floor.
* Headers, certificate fields, and the response body digest and prefix must
  be recorded verbatim, so that a later pass can compare without repeating
  the work.
* A service that answers on four-prime addresses and not on their neighbours
  must be recorded as deliberate; a service that answers on both must not.
* A verdict of **other** requires evidence that no Earth-bound explanation
  reproduces, and must name the measurement that would confirm it. A verdict
  of **other** must never rest on a pattern: no signature is expected of that
  explanation, so a pattern found in the data is a coincidence until it is a
  measurement.
* A verdict of **nefarious** requires a disagreement between layers: the
  application says one thing while the certificate, the reverse DNS, or the
  registry says another.
* The pass must record its parameters and its observation time.
* The pass must reuse an existing result file unless the caller asks for
  `--refresh`.
* Hunting rogue probes inside operator-held blocks is a later phase and is
  not part of this feature.

## Behavior

* `sh scripts/05-probe-characterize.sh` reads the phase 3 observations from
  `dataflow.out/05_ip_probe_http.json` and the blocks from
  `dataflow.out/02_ip_block.json`, then writes
  `dataflow.out/06_ip_probe_characterize.json`.
* An address is anomalous when phase 3 recorded `http_response`,
  `connect_refused`, or `connection_reset` for it.
* `--control-count N` sets how many non-prime control addresses are sampled
  from each block that holds an anomaly; the default is 12.
* `--thread`, `--timeout`, `--http-port`, and `--https-port` set the probe
  behavior; `--limit N` bounds a trial run.
* The result file is an object with `observed_at`, `parameters`, `blocks`,
  and `observations`.
* Each observation records the address, whether it is an `ip_probe`, the
  block it sits in, the phase 3 outcome, the probe results, and the derived
  signals (`catch_all`, `certificate_self_signed`, `certificate_covers_ip`,
  `ptr_present`, `latency_quantum`, and the latency samples).
* `parameters` carries `ms_floor_geosynchronous`, `ms_floor_moon`, and
  `blind_spot_seconds`, so the result states the distances it could and could
  not see.
* Each observation's `latency` records `sample_ms`, `ms_min`, `ms_median`,
  `ms_jitter`, and `quantum`, where `quantum` is `none`,
  `geosynchronous_band`, or `moon_band`.
* A run that finds an existing result file reports the reuse and probes
  nothing; `--refresh` probes again.

## Dependencies

* `03-probe-generation.md` — supplies the probe list.
* `04-block-collection.md` — supplies the blocks, including the blocks no
  operator holds.
* `05-probe-observation.md` — supplies the phase 3 observations that select
  the anomalies.
