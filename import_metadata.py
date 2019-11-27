from argparse import ArgumentParser
from base.general_utils import loadEntriesAndSetUp, writeOutputBib
import pandas as pd

def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, True)

    paperstore.addPapers(papers_to_add)
    if conf.force:
        paperstore.updatePapers(papers_existing)


if __name__ == '__main__':
    parser = ArgumentParser(description='Import metadata from bib file')
    parser.add_argument('-i', '--input', type=str,
                        help='Input bib file name')
    parser.add_argument('-f', '--force', type=bool, default=False,
                        help='Force updating of existing paper records')

    conf = parser.parse_args()

    main(conf)
