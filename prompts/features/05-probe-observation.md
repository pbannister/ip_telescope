# Feature: Probe Observation

## Purpose

The addresses that no RIR operator holds are the quiet part of the Internet:
no service is supposed to answer there. Phase 3 asks each of those addresses
one plain question over HTTP and records the answer, so that later phases can
compare answers against expectations.

An answer from unheld space is not automatically meaningful — a transit
network may answer on behalf of a block, and a middlebox may reply for
anything. The feature therefore records enough detail to tell those cases
apart later: the outcome class, the HTTP status, the response headers, a
digest of the body, and how long the exchange took.

## Requirements

* The input must be `dataflow.out/04_ip_probe.json`, the probes that are not inside
  an operator-held block.
* Each target must receive one `GET /` request over TCP to the configured
  port, default 80.
* The request must identify the project in its `User-Agent` header.
* A target must not receive more than one request per run.
* The observation must record, per target: the address, the outcome class,
  the HTTP status, response headers of interest, body length, body SHA-256,
  a short body prefix, whether the body was truncated, the elapsed
  milliseconds, and the error text when the exchange failed.
* The outcome class must distinguish an HTTP response, a refused connection,
  a timeout, an unreachable network, an unreachable host, a reset
  connection, a protocol error, and any other error.
* The response body must not be stored beyond a fixed prefix, so a run
  cannot become a payload collection.
* The observation file must record the run parameters, the outcome counts,
  and the observation time, so a result can be reproduced and compared.
* Observations must keep the ascending address order of the input.
* A run must write whatever it has when it is interrupted.
* The feature must support a target limit, a thread count, and a timeout.
* An observation file that already exists must be kept: a run that finds one
  must report the reuse and probe nothing.
* The pass must be repeated only when the caller asks for it with
  `--refresh`, because a repeat is live Internet traffic that cannot be
  recreated from anything on disk.

## Behavior

* `sh scripts/03-probe-observe.sh` observes every target in
  `dataflow.out/04_ip_probe.json` and writes `dataflow.out/05_ip_probe_http.json`.
* `sh scripts/03-probe-observe.sh --limit 100` observes the first 100
  targets, which supports a trial run.
* `--thread` sets the number of concurrent requests; `--timeout` sets the
  seconds allowed per request.
* When `dataflow.out/05_ip_probe_http.json` already exists, the program prints
  `reuse: <file> observed_at=<time> target=N observed=M` and probes nothing.
* `--refresh` observes again and writes the file.
* An unreadable observation file is reported and then observed again.
* `dataflow.out/05_ip_probe_http.json` is an object with `observed_at`,
  `parameters`, `counts`, and `observations`.
* Each entry of `observations` is one target; `counts` maps outcome class to
  the number of targets with that class.
* An interrupted run sets `parameters.interrupted` to true and still writes
  the observations completed so far.

## Dependencies

* `03-probe-generation.md` — supplies the probe list.
* `04-block-collection.md` — supplies `dataflow.out/04_ip_probe.json`.
