# Feature: Probe Generation

## Purpose

The project observes IPv4 addresses that are unlikely to host an ordinary
service. The first step is a deterministic list of those addresses, so that
every later phase works from the same set.

The list is the `ip_probe` list: IPv4 addresses that are composed of four
prime octets and are valid for routing across the Internet.

## Requirements

* An `ip_probe` is an IPv4 address whose four octets are each a prime number.
* An `ip_probe` must be globally reachable unicast: it must not fall inside
  an IANA special-purpose block that is private, loopback, link-local,
  shared, documentation, benchmark, multicast, reserved, or broadcast.
* Only three excluded blocks intersect the four-prime-octet space:
  `127.0.0.0/8`, `224.0.0.0/4`, and `240.0.0.0/4`.
* The list must contain 7,400,808 addresses: 54 primes per octet, 54^4
  addresses, less 7 first-octet classes of 54^3 addresses each.
* The list must be written to `data/01_ip_probe.json` in ascending order.
* The list must be a JSON array of dotted-quad strings, one address per line.
* Generation must be deterministic: the same inputs produce the same file.
* Generation must not require network access.
* The feature must provide a count-only mode and a verification mode.
* Verification must reject an address that is not an `ip_probe` and an address
  list that is not strictly ascending.

## Behavior

* `python3 sources/ip_probe_generate.py --output data/01_ip_probe.json` writes
  the list and prints the number of addresses written.
* `python3 sources/ip_probe_generate.py --count-only` prints the number of
  addresses without writing a file.
* `python3 sources/ip_probe_generate.py --first N --output FILE` writes the
  first N addresses, which supports tests.
* `python3 sources/ip_probe_generate.py --verify FILE` validates a file,
  exits nonzero on a violation, and prints the count, the first address, and
  the last address.
* The first address of the list is `2.2.2.2`.
* The last address of the list is `223.251.251.251`.

## Dependencies

* None.
