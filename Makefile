#
#	Makefile for the IP_telescope project.
#
#	This Makefile is the human-facing driver.
#	Each rule calls the appropriate tool instead of reimplementing work:
#		probes:  sh scripts/01-probe-generate.sh
#		         (phase 1: write dataflow.out/01_ip_probe.json)
#		blocks:  sh scripts/02-block-collect.sh
#		         (phase 2: fetch the RIR delegation files, then write
#		         dataflow.out/02_ip_block.json, dataflow.out/03_ip_probe.json, and
#		         dataflow.out/04_ip_probe.json)
#		enrich: sh scripts/04-block-enrich.sh
#		         (phase 2 enrichment: add the RIR RDAP record to the blocks;
#		         answers are cached in dataflow.out/raw/RDAP-CACHE.jsonl)
#		observe: sh scripts/03-probe-observe.sh
#		         (phase 3: HTTP GET every probe that no operator holds,
#		         then write dataflow.out/05_ip_probe_http.json; pass --limit for a
#		         trial run)
#		build:  sh scripts/site-build.sh
#		site:   sh scripts/site-build.sh + sh scripts/site-condense.sh
#		        (the standard page set; see prompts/features/02-project-pages.md)
#		clean:  manual by design; see the clean rule below.
#		test:   npm test
#		deploy: RETIRED - all publishing to labs.bannister.us goes through
#		        the homelab project (homelab-publish; see the homelab's
#		        documents/09-project-pages-conventions.md). This target
#		        only reminds you of that; use the homelab's make deploy.
#		install: reserved; not yet defined.
#
#	Work products are kept, never silently rebuilt. Two mechanisms enforce
#	that, and both must agree:
#
#	  * make: a rule names the file it produces, so a step whose file is
#	    already present does not run.
#	  * each program: a work product that exists is reused, and only
#	    --refresh writes it again.
#
#	The one exception is enrichment, which annotates 02_ip_block.json in
#	place rather than producing its own file; it is a phony target whose
#	program reuses the file whenever every block already carries its RDAP
#	record. Use --retry-failed to fill the blocks that were left unanswered.
#
#	Phase 4 and later add work products 06, 07, 08; they are not defined yet
#	(see TODO.md).
#

# default target: build everything, including the site.
all: probes blocks enrich observe build site

# Work products, in phase order.
FILE_01_PROBES=dataflow.out/01_ip_probe.json
FILE_02_BLOCKS=dataflow.out/02_ip_block.json
FILE_03_PROBES_MAPPED=dataflow.out/03_ip_probe.json
FILE_04_PROBES_OPEN=dataflow.out/04_ip_probe.json
FILE_05_PROBES_HTTP=dataflow.out/05_ip_probe_http.json

$(FILE_01_PROBES):
	sh scripts/01-probe-generate.sh

# One run writes all three phase 2 files; the program keeps them when all
# three are present.
$(FILE_02_BLOCKS) $(FILE_03_PROBES_MAPPED) $(FILE_04_PROBES_OPEN): $(FILE_01_PROBES)
	sh scripts/02-block-collect.sh

$(FILE_05_PROBES_HTTP): $(FILE_04_PROBES_OPEN)
	sh scripts/03-probe-observe.sh

probes: $(FILE_01_PROBES)
blocks: $(FILE_02_BLOCKS) $(FILE_03_PROBES_MAPPED) $(FILE_04_PROBES_OPEN)
enrich:
	sh scripts/04-block-enrich.sh
observe: $(FILE_05_PROBES_HTTP)

build:
	sh scripts/site-build.sh

site:
	sh scripts/site-build.sh
	sh scripts/site-condense.sh

clean:
	@echo '==== clean is manual: the work products take hours to generate'
	@echo '==== and the phase 3 pass can only be repeated against the live'
	@echo '==== Internet. To remove them deliberately:'
	@echo '====     rm -f dataflow.out/0*.json site.out/* logs/*'
	@echo '==== The RIR download cache in dataflow.out/raw/ is kept; refetch it'
	@echo '==== with: sh scripts/02-block-collect.sh --refresh'

test:
	npm test

deploy:
	@echo '==== RETIRED: publishing goes through the homelab project (homelab-publish).'
	@echo '==== Build the pages here (make site), then run the homelab''s "make deploy"'
	@echo '==== to publish (see homelab documents/09-project-pages-conventions.md).'

install:
	@echo '==== No install yet defined'

.PHONY: all probes blocks enrich observe build site clean test deploy install
