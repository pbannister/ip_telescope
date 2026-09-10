#
#	Makefile for the ip_telescope project.
#
#	This Makefile is the human-facing driver.
#	Each rule calls the appropriate tool instead of reimplementing work:
#		probes:  sh scripts/01-probe-generate.sh
#		         (phase 1: write data/01_ip_probe.json)
#		blocks:  sh scripts/02-block-collect.sh
#		         (phase 2: fetch the RIR delegation files, then write
#		         data/02_ip_block.json, data/03_ip_probe.json, and
#		         data/04_ip_probe.json)
#		observe: sh scripts/03-probe-observe.sh
#		         (phase 3: HTTP GET every probe that no operator holds,
#		         then write data/05_ip_probe_http.json; pass --limit for a
#		         trial run)
#		build:  sh scripts/site-build.sh
#		site:   sh scripts/site-build.sh + sh scripts/site-condense.sh
#		        (the standard page set; see prompts/features/02-project-pages.md)
#		clean:  remove generated output (the RIR download cache in
#		        data/raw/ is kept; use --refresh to fetch it again)
#		test:   npm test
#		deploy: RETIRED - all publishing to labs.bannister.us goes through
#		        the homelab project (homelab-publish; see the homelab's
#		        documents/09-project-pages-conventions.md). This target
#		        only reminds you of that; use the homelab's make deploy.
#		install: reserved; not yet defined.
#

probes:
	sh scripts/01-probe-generate.sh

blocks:
	sh scripts/02-block-collect.sh

observe:
	sh scripts/03-probe-observe.sh

build:
	sh scripts/site-build.sh

site:
	sh scripts/site-build.sh
	sh scripts/site-condense.sh

clean:
	rm -f data/0*.json dataflow.out/* site.out/* logs/*

test:
	npm test

deploy:
	@echo '==== RETIRED: publishing goes through the homelab project (homelab-publish).'
	@echo '==== Build the pages here (make site), then run the homelab''s "make deploy"'
	@echo '==== to publish (see homelab documents/09-project-pages-conventions.md).'

install:
	@echo '==== No install yet defined'

.PHONY: probes blocks observe build site clean test deploy install
