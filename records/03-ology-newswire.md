# Record: ology.com and 23.191.137.0 — 2026-09-11

## What was asked

The owner read the site served from Site A and found its story "aspirational
but unfulfilled", and asked four things: what is known about `ology.com` and
the block; whether the history of domain ownership can be reconstructed;
whether the certificate names any IP addresses, and whether that data is on a
page; whether the sampled addresses come from one physical host; and why the
block reads as unused.

Everything below was gathered on 2026-09-11, from the project's own work
products plus public registries, RPKI, BGP data, certificate transparency,
the Internet Archive, and a few traceroutes.

## The block, layer by layer

| Layer | What it says |
| --- | --- |
| Registry delegation (ARIN's file) | `23.191.137.0 - 23.191.151.255`, status `reserved`, no country, no date. Fifteen `/24`s; nothing delegated to anyone |
| RDAP custody | An address inside the answering range returns **404: "The ip you are seeking as '23.191.144.9/32' is/are not here."** ARIN holds no object for it, not even a parent for that address |
| Routing | Announced since **2021-10-21** by origin **AS400050**, continuously to today, seen by 322–324 of 324 RIS peers. The announced set is exactly `/24`s 144 to 151 — eight of the fifteen |
| ASN record | **None.** ARIN whois has no entry (control tests resolve AS15169, AS16509, AS399261, AS400000, AS400100 and AS400284 in the same lookup, so the tool works). PeeringDB: "Entity not found". RADB: no object. CAIDA AS Rank knows the ASN (rank 27942) but holds no name for it. Only bgp.he.net names it: **"Ology Newswire, Inc."** |
| RPKI | A validation of `23.191.144.0/24` for origin 400050 returns **status unknown, no validating ROAs**: nobody holds an RPKI certificate for the space |
| Certificate | One certificate served as the default: CN `ology.com`, SAN `DNS:ology.com` only, Let's Encrypt R10, valid 2025-03-02 to **2025-05-31, expired**, not self-signed, no IP address in it |
| DNS | `ology.com` and six subdomains resolve into the block: `feed`, `list`, `beacon`, `link`, `api`, `archive` → `23.191.144.8/.9`; `ns1.ology.com` → `23.191.145.2`, so the company runs its own authoritative nameserver inside the block |

## The domain

- **Registered 2002-05-02**, registrar GoDaddy, four client-hold statuses,
  **registry expiry 2029-03-07**: the registration is paid years ahead.
- Name servers are **AWS Route 53** (`awsdns-*`), mail is **Amazon SES**
  (`inbound-smtp.us-east-1.amazonaws.com`), and a
  `google-site-verification` record is present: the domain is administered on
  AWS, by someone who is still paying attention to it.
- Certificate transparency (certspotter; crt.sh was returning 502) shows
  16 issuances in 2026 for `ology.com` and the subdomains above, so renewal
  automation is live — but the hosts in this block still serve the March 2025
  certificates, expired since early June 2025.

**The history, from the Internet Archive** (captures every year since 1998):

| Year | What the site was |
| --- | --- |
| 2002 | "OLOGY — SPOTLIGHT ON ... Solutions Company Partners News Contact": a corporate site |
| 2012 | "Ology is all about passion": a topic-and-celebrity social site (Home, Join, FAQ, News, Login, Celebs, Fashion, Film, Geek, Humor, Music, Politics, Sport) |
| 2018 | "Home \| ology" with About, Privacy, Terms, DMCA and advertising scaffolding |
| 2021–2026 | "Ology Newswire": a JavaScript application, unchanged across all three years |

So the ownership history is *partly* reconstructible. The registry redacts the
registrant, and no free source reconstructs the holder list; what can be
recovered is the property's behaviour over time — a corporate site, then a
social network, then an ad-supported content site, then a dormant
application — plus the current administration on AWS. That answers "who and
why" only in outline: the domain has been commercially motivated since 2002,
and the current holder maintains it without publishing who they are.

## Why it reads as unused

Because the project's map is built from the **delegation files**, which record
what registries delegate, and this space has never been delegated. It is
ARIN's own `/8` (`NET23`), and ARIN marks this sub-block reserved and holds no
RDAP object for the addresses. There is no RPKI ROA either, so the space is
announced and used with no registry record and no cryptographic claim at all.
The registry answer is not wrong: nothing here has been *assigned*. It is
simply not the whole story — a company has been operating 2,048 of those
addresses since October 2021.

## One physical host? No

Two independent measurements say the block is served by several hosts in
several places, behind one configuration:

- **Round-trip floors differ by a factor of ten between `/24`s**: 7 ms
  (`23.191.148.0/24`), 9 ms (`.144`), 34 ms (`.150`), 53 ms (`.145`), 58 ms
  (`.151`), 71 ms (`.147`, `.149`). One host cannot be 7 ms and 71 ms away
  from the same observer at the same time.
- **The visible last hops differ**: traces toward `.150` and `.151` end in
  Vultr's network (netname `CONSTANT`), while `.149` is reached over Arelion
  transit. Filtered hops leave `.144`, `.145` and `.148` unresolved, which is
  itself a difference in filtering behaviour.
- Yet the **content is identical everywhere**: 482 measured addresses, one
  body digest, one certificate, one catch-all `301` to HTTPS. One
  configuration, many hosts — a fleet, or a set of sites sharing a template,
  not a single server with a sloppy DNS entry.

Per-vhost certificates confirm the configuration is name-based: asking for
`feed.ology.com` or `beacon.ology.com` returns that name's own (also expired)
certificate, while `api.ology.com` falls back to the default. By bare IP the
server answers `400` over HTTPS, which is what a name-based vhost does when
it does not recognise the name it was addressed by.

## Answers, in one line each

- **The certificate names no IP address**: SAN is `DNS:ology.com` only, and
  the certificate data now appears on each probe page and each block page.
- **Not one host**: floors spread 7–71 ms across `/24`s, and the paths end in
  different provider networks.
- **The host organization is the domain's own company**: AS400050, "Ology
  Newswire, Inc." per bgp.he.net, announcing since 2021-10-21, with its own
  nameserver in the block — and with no record in ARIN, PeeringDB, RADB, or
  RPKI.
- **The block reads as unused because it was never delegated**; the annotation
  comes from the delegation file, and the routing, DNS, and content all tell a
  different story.
- **"Aspirational but unfulfilled" is measurable**: every name in the block
  fails TLS with an expired certificate (since June 2025) while certificate
  renewals for those same names continue in 2026 elsewhere.

## What is still unknown, and the next measurements

- Who the registrant is. A paid privacy-free registry lookup, or the
  registrar's records, would be needed; the project will not buy them.
- Why ARIN has no ASN record while the ASN has been announced for five years,
  and whether the announcement is authorised. ARIN's own inbox is the
  authority; the project does not write to it.
- Whether the newer certificates are deployed on hosts elsewhere: a TLS
  handshake against each name from a second vantage point would show it.
- What the application does. It needs JavaScript; the project reads headers
  and certificates, not scripts.

## Addendum: the follow-up investigation — 2026-09-11

### The registrant, and what each route costs

The public record stops at a privacy service: the registrar's own whois shows
**Registrant Organization: Domains By Proxy, LLC**, Registrant Name
"Registration Private", 100 S. Mill Ave, Suite 1600 — GoDaddy's proxy. The
registration is locked, prepaid to 2029-03-07, and the registrant is not
published.

| Route | Cost | What it yields |
| --- | --- | --- |
| Registrar whois / RDAP | free | Registrar, dates, statuses, and the proxy — everything the record shows today |
| The site's own archived legal pages | free | **The operators, named in their own documents** (see below). This worked |
| ICANN Registration Data Request Service (RDRS) | free | A request to GoDaddy for the non-public registrant data; the requester must attest to a legitimate purpose (intellectual property, fraud, security). Curiosity about an anomalous address is not one |
| Paid historical whois (DomainTools, WhoisXMLAPI, SecurityTrails, Whoisology and similar) | roughly ten to a few tens of dollars for a report; subscription tiers run toward a hundred dollars a month | Registrant records from before the privacy era, if the domain was not private then. The pre-2018 record is exactly where a name would sit |
| State corporate registry (Secretary of State) | free to a few dollars per search | Officers and registered agents of the LLC or corporation, if the entity is registered in that state |
| Subpoena or UDRP | hundreds to thousands | The registrar's records, under legal process |

Prices move; they should be checked before spending anything. The free route
was the productive one.

### The operators, named by their own documents

| When | Who | Where it says so |
| --- | --- | --- |
| 2012 | **Ology Media, Inc.** | The archived terms page: "DMCA Complaints Ology Media, Inc." |
| 2012-2018 | **NewPress, LLC** | The archived privacy, terms, and DMCA pages: "the policies and procedures of NewPress, LLC", "Infringement for Company at NewPress, LLC" |
| 2021-2026 | **Ology Newswire, Inc.** | The ASN name, the application title, and the Substack |

Three named operators behind one domain across twenty-four years. The
registrant of record today is still hidden, but the *operators* are public
because they published their own legal notices.

### What the application is, and why it looks dead

- The site is a **Vue single-page application** (`chunk-vendors`, `app.js`,
  Bootstrap and core-js inside). Its only data sources are three feed URLs,
  `https://feed.ology.com/feed/<topic>/latest.jsonl` for politics feeds, and a
  link to `ology.substack.com`. **No websockets, no analytics identifiers, no
  other endpoints: nothing is hidden in the client.**
- **The feed times out.** A request to `feed.ology.com/feed/politics-mainstream/latest.jsonl`
  returns nothing after 35 seconds, so the application waits for data that
  never arrives. That is the whole of "the site does not work".
- The named services are configured and unhappy: `feed`, `list`, `link`, and
  `api` answer `400` at the root, `beacon` answers `403`, `archive` answers
  `500`. Names of that shape — feed, list, beacon, link — are a publishing
  stack: content feeds, a mailing list, open tracking, and click tracking.
- The publication moved to Substack: **Public Square Networks, by Ology
  Newswire**, launched five years ago, with **two posts, June and July 2021,
  and nothing since**.

### The timeline the evidence supports

**2021**: the venture starts — Substack posts in June and July, the ASN's
first announcement in October. **2021-2025**: the stack runs, on rented hosts
in more than one place, with per-name certificates. **May-June 2025**: those
certificates lapse and are not replaced on these hosts. **2026**: still
reachable, still paid for (the registration runs to 2029), still broken.

### The port-knock hypothesis, tested as far as it can be

The idea: meaningful behaviour might require hitting several addresses in a
particular order with particular keys. What the evidence says:

- **The key in this stack is the name, not a sequence.** Addressed by IP, every
  address gives the same `301` and the same expired certificate; addressed by
  name, the services answer differently (`400`, `403`, `500`) and present their
  own certificates. Whatever is selective here is selected by `Host`/SNI.
- **No state changed under our probing.** Three passes over the same addresses
  (two 21 minutes apart, one later) gave byte-identical answers; nothing
  changed after other addresses had been touched. A knock sequence that latches
  a door would have to be a sequence we did not guess — but it would also have
  to leave no trace in any of those passes.
- **What could still be tested**: ordered probes with distinctive markers,
  comparing a given address's answer before and after a chosen sequence;
  longer observation over days, to catch a schedule; endpoint enumeration on
  the named services (public paths only). What cannot be tested is the space of
  sequences and keys, which is unbounded — so a negative result would be weak
  evidence and a positive one would be accidental.

**Assessment**: nothing in the client, the services, or the certificates is
shaped like a covert channel, and the mundane reading now has a name, a
timeline, and a business. The genuinely unexplained part has narrowed to
paperwork: an ASN and a block of address space in daily use since 2021 that no
registry admits to knowing about.

## Commits

- `pending` docs: follow the registrant and the application

## Commits

- `4fe3070` docs: investigate ology.com and the block that serves it
