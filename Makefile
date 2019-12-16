# Remove target files after command failure.
.DELETE_ON_ERROR:

datasets/wikiproject_taxonomy.halfak_20191202.yaml:
	cat taxonomies/wikiproject/halfak_20191202/taxons/*.yaml > $@

datasets/wikiproject_to_template.halfak_20191202.yaml: \
		datasets/wikiproject_taxonomy.halfak_20191202.yaml
	python fetch_wikiproject_templates.py $^ > $@
