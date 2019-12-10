"""
Print out the nodes of a taxonomy

Usage:
    print_nodes (-h | help)
    print_nodes <taxon>... [--debug]

Options:
    -h --help     Prints this documentation
    <taxon>       A yaml file containing partial or whole taxonomy.  Multiple
                  files will be merged.
    -d --debug  Print log information while running
"""
import logging
import sys

import docopt
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

    return print_nodes(taxonomy)


def print_nodes(taxonomy):
    for line in format_node_lines(taxonomy):
        print(line)


def format_node_lines(taxonomy, depth=0):
    for key in sorted(taxonomy.keys()):
        value = taxonomy[key]
        yield ("  " * depth) + " - " + str(key)
        if isinstance(value, list):
            pass
        else:
            yield from format_node_lines(value, depth+1)


if __name__ == "__main__":
    sys.exit(main())
