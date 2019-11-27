from base.general_utils import loadEntriesAndSetUp, writeOutputBib

from search import enrichAndUpdateMetadata
from argparse import ArgumentParser
from db.bibtex import writeBibtex


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache, conf.max)

    if conf.cache:
        successful, unsuccessful = enrichAndUpdateMetadata(papers_to_add, paperstore, conf.email)

    if conf.force and conf.cache:
        enrichAndUpdateMetadata(papers_existing, paperstore, conf.email)

    all_papers = papers_to_add + papers_existing
    writeOutputBib(all_papers, conf.output)


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Gathers metadata, including the abstract, on a list of search results by searching on Crossref, PubMed, arXiv, Semantic Scholar and Unpaywall')

    parser.add_argument('-i', '--input', type=str,
                        help='Input BIB/RIS file with the previously cached search results')
    parser.add_argument('-o', '--output', type=str,
                        help='Output BIB/RIS file into which to update the new, augmented results')
    parser.add_argument('-m', '--max', type=int, default=100,
                        help='Maximum number of results to process')
    parser.add_argument('-em', '--email', type=str,
                        help='Email to serve as identity to API endpoints')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')
    parser.add_argument('-f', '--force', type=bool, default=False,
                        help='Force updating metadata for cached results')

    conf = parser.parse_args()

    main(conf)
