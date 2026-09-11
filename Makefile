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
#		         (phase 2 enrichment: add the RIR RDAP record to every
#		         collected block; answers are cached in dataflow.out/raw/)
#		observe: sh scripts/03-probe-observe.sh
#		         (phase 3: HTTP GET every probe that no operator holds,
#		         then write dataflow.out/05_ip_probe_http.json; pass --limit for a
#		         trial run)
#		build:  sh scripts/site-build.sh
#		site:   sh scripts/site-build.sh + sh scripts/site-condense.sh
#		        (the standard page set; see prompts/features/02-project-pages.md)
#		clean:  remove generated output (the RIR download cache in
#		        dataflow.out/raw/ is kept; use --refresh to fetch it again)
#		test:   npm test
#		deploy: RETIRED - all publishing to labs.bannister.us goes through
#		        the homelab project (homelab-publish; see the homelab's
#		        documents/09-project-pages-conventions.md). This target
#		        only reminds you of that; use the homelab's make deploy.
#		install: reserved; not yet defined.
#

# default target: build everything, including the site.
all: probes blocks enrich observe build site

FILE_01_PROBES=dataflow.out/01_ip_probe.json
FILE_02_BLOCKS=dataflow.out/02_ip_block.json
FILE_03_PROBES_HTTP=dataflow.out/05_ip_probe_http.json
FILE_04_BLOCKS_ENRICH=dataflow.out/04_ip_block_enrich.json
FILE_05_PROBES_HTTP=dataflow.out/05_ip_probe_http.json
FILE_06_BLOCKS_ENRICH=dataflow.out/06_ip_block_enrich.json
FILE_07_BLOCKS_ENRICH=dataflow.out/07_ip_block_enrich.json
FILE_08_BLOCKS_ENRICH=dataflow.out/08_ip_block_enrich.json

$(FILE_01_PROBES):
	sh scripts/01-probe-generate.sh

$(FILE_02_BLOCKS): $(FILE_01_PROBES)
	sh scripts/02-block-collect.sh

$(FILE_04_BLOCKS_ENRICH): $(FILE_02_BLOCKS)
	sh scripts/04-block-enrich.sh

$(FILE_05_PROBES_HTTP): $(FILE_04_BLOCKS_ENRICH)
	sh scripts/03-probe-observe.sh

probes: $(FILE_01_PROBES)
blocks: $(FILE_02_BLOCKS)
enrich: $(FILE_04_BLOCKS_ENRICH)
observe: $(FILE_05_PROBES_HTTP)

build:
	sh scripts/site-build.sh

site:
	sh scripts/site-build.sh
	sh scripts/site-condense.sh

clean:
	# rm -f dataflow.out/0*.json dataflow.out/* site.out/* logs/*
	# Want clean to be manual, not automated, as work products take a long time to generate and are not easily recoverable.

test:
	npm test

deploy:
	@echo '==== RETIRED: publishing goes through the homelab project (homelab-publish).'
	@echo '==== Build the pages here (make site), then run the homelab''s "make deploy"'
	@echo '==== to publish (see homelab documents/09-project-pages-conventions.md).'

install:
	@echo '==== No install yet defined'

.PHONY: all probes blocks enrich observe build site clean test deploy install
