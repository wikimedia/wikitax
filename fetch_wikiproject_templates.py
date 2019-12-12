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

    return run(taxonomy, session, threads)


def run(taxonomy, session, threads):
    for wikiproject_name, templates in \
      fetch_wikiproject_templates(taxonomy, session, threads):
        if len(templates) > 0:
            print("{0}: {1}".format(wikiproject_name, json.dumps(templates)))


def fetch_wikiproject_templates(taxonomy, session, threads):
    def get_wikiproject_templates(wikiproject_name):
        logger.debug("Requesting redirects to Template:{0}"
                     .format(wikiproject_name))

        doc = session.get(
            formatversion=2,
            action='query',
            prop='linkshere',
            lhshow='redirect',
            lhnamespace=10,
            lhlimit=500,
            redirects='true',
            titles='Template:'+wikiproject_name
        )

        if 'query' in doc:
            if 'pages' in doc['query'] and len(doc['query']['pages']) > 0:
                if 'linkshere' in doc['query']['pages'][0] \
                  and len(doc['query']['pages'][0]['linkshere']) > 0:

                    template_redirect_links = \
                        doc['query']['pages'][0]['linkshere']

                    # list of template redirect titles
                    template_redirect_titles = \
                        [link['title'].replace('Template:', '')
                            for link in template_redirect_links]

                    # add canonical template title to
                    # list of template redirect titles
                    template_redirect_titles.append(
                        doc['query']['pages'][0]['title']
                        .replace('Template:', ''))

                    return template_redirect_titles

                else:
                    logger.error("Could not process {0}: {1}".format(
                        wikiproject_name, doc))
                    return {'error': doc}
            else:
                logger.error("Could not process {0}: {1}".format(
                    wikiproject_name, doc))
                return {'error': doc}
        else:
            logger.error("Could not process {0}: {1}".format(
                wikiproject_name, doc))
            return {'error': doc}

    with ThreadPoolExecutor(max_workers=threads) as executor:
        # Remove dupes
        all_wikiprojects = list(set(get_wikiprojects(taxonomy)))
        all_wikiproject_templates = executor.map(
            get_wikiproject_templates, all_wikiprojects)
        for wikiproject_name, templates in zip(
          all_wikiprojects, all_wikiproject_templates):
            yield wikiproject_name, list(templates)


def get_wikiprojects(taxonomy):
    for key, value in taxonomy.items():
        if isinstance(value, list):
            yield from iter(value)
        else:
            yield from get_wikiprojects(value)


if __name__ == "__main__":
    sys.exit(main())
