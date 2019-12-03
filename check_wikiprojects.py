"""
Check the WikiProjects in a taxonomy to make sure that they exist.

Usage:
    check_wikiprojects (-h | help)
    check_wikiprojects <taxon>...
                       [--ua-email=<address>] [--threads=<num>]
                       [--verbose] [--debug]

Options:
    -h --help     Prints this documentation
    <taxon>       A yaml file containing partial or whole taxonomy.  Multiple
                  files will be merged.
    --ua-email=<address>  An email address to be included as a user-agent
                          header for requests to the MediaWiki API.
    --threads=<num>  How many threads to run in parallel [default: 4]
    -d --debug  Print log information while running
    -v --verbose  Print log information while running
"""
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

    return check_wikiprojects(taxonomy, session, threads)


def check_wikiprojects(taxonomy, session, threads):
    def get_page_info(title):
        doc = session.get(
            action='query', prop='info', titles='Wikipedia:' + title,
            redirects=True, formatversion=2)

        page_info = {}
        if 'query' in doc:
            if 'redirects' in doc['query']:
                page_info['redirect_to'] = doc['query']['redirects'][0]['to']
            if 'pages' in doc['query'] and len(doc['query']['pages']) > 0:
                page_info.update(doc['query']['pages'][0])
                return page_info
            else:
                return {'error': doc}
        else:
            return {'error': doc}

    issues = 0
    with ThreadPoolExecutor(max_workers=threads) as executor:
        branches_titles = list(enumerate_titles(taxonomy))
        page_infos = executor.map(
            get_page_info, (bt[1] for bt in branches_titles))

        for (branches, title), page_info in zip(branches_titles, page_infos):
            path = ".".join(branches) + "." + title
            logging.debug("Processing {0}".format(path))
            if 'error' in page_info:
                logging.error("Could not process {0}: {1}"
                              .format(path, page_info['error']))
                issues += 1
            elif page_info.get('missing', False):
                logging.warning("{0} doesn't exist!".format(path))
                issues += 1
            elif 'redirect_to' in page_info:
                logging.warning("{0} is a redirect to {1}!"
                                .format(path, page_info['redirect_to']))
                issues += 1
            elif page_info['length'] < 150:
                logging.warning("{0} is a very short page ({1} chars)"
                                .format(path, page_info['length']))
                issues += 1

    if issues > 0:
        return 1
    else:
        return 0


def enumerate_titles(taxon):
    for key, value in taxon.items():
        if isinstance(value, list):
            for title in value:
                yield [key], title
        else:
            for branches, title in enumerate_titles(taxon[key]):
                yield [key] + branches, title


if __name__ == "__main__":
    sys.exit(main())
