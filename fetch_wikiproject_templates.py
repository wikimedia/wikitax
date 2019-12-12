"""
Generate a mapping between WikiProjects and their templates using English
Wikipedia's API.

Usage:
    fetch_wikiproject_templates (-h | help)
    fetch_wikiproject_templates <taxon>...
                                [--ua-email=<address>] [--threads=<num>]
                                [--debug]

Options:
    -h --help     Prints this documentation
    <taxon>       A yaml file containing partial or whole taxonomy.  Multiple
                  files will be merged.
    --ua-email=<address>  An email address to be included as a user-agent
                          header for requests to the MediaWiki API.
    --threads=<num>  How many threads to run in parallel [default: 4]
    -d --debug  Print log information while running
"""
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

import docopt
import mwapi
import yamlconf

ENWIKI_HOST = 'https://en.wikipedia.org'
logger = logging.getLogger(__name__)


def main():
    args = docopt.docopt(__doc__)
    logging.basicConfig(
        level=logging.INFO if not args['--debug'] else logging.DEBUG,
        format='%(asctime)s %(levelname)s:%(name)s -- %(message)s'
    )
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

    taxon_paths = args['<taxon>']
    logger.info("Loading taxon from {0}".format(taxon_paths))
    taxonomy = yamlconf.load(*(open(p) for p in taxon_paths))

    session = mwapi.Session(ENWIKI_HOST, user_agent=args['--ua-email'])
    threads = int(args['--threads'])

    run(taxonomy, session, threads)


def run(taxonomy, session, threads):
    for wp_name, templates in fetch_wp_templates(taxonomy, session, threads):
        if len(templates) > 0:
            print("{0}: {1}".format(wp_name, json.dumps(templates)))


def fetch_wp_templates(taxonomy, session, threads):
    def get_wikiproject_templates(wikiproject_name):
        logger.debug("Requesting redirects to Template:{0}"
                     .format(wikiproject_name))
        doc = session.get(formatversion=2, action='query', prop='linkshere',
                          lhshow='redirect', lhnamespace=10, lhlimit=500,
                          redirects=True,
                          titles="Template:" + wikiproject_name)
        if 'error' in doc:
            logging.error("Could not process {0}: {1}"
                          .format(wikiproject_name, doc['error']))
            return []
        else:
            if 'missing' in doc['query']['pages'][0]:
                logging.warning(
                    "Could not process {0}: could not find main template"
                    .format(wikiproject_name))
            else:
                templates.add(doc['query']['pages'][0]['title'])

            for linkshere in doc['query']['pages'][0].get('linkshere', []):
                templates.add(linkshere['title'][9:])

            return templates

    with ThreadPoolExecutor(max_workers=threads) as executor:
        # Remove dupes
        all_wikiprojects = list(set(get_wikiprojects(taxonomy)))
        all_wp_templates = executor.map(
            get_wikiproject_templates, all_wikiprojects)
        for wp_name, templates in zip(all_wikiprojects, all_wp_templates):
            yield wp_name, list(templates)


def get_wikiprojects(taxonomy):
    for key, value in taxonomy.items():
        if isinstance(value, list):
            yield from iter(value)
        else:
            yield from get_wikiprojects(value)


if __name__ == "__main__":
    sys.exit(main())
