from base.general_utils import loadEntriesAndSetUp, writeOutputBib
from argparse import ArgumentParser
from filter_results import filterPapers
from search.metadata_harvest import semanticscholarmetadata, enrichAndUpdateMetadata


def getCitingPapers(paper):

    # res = semanticscholarmetadata.search(paper.title, '', get_citing_papers=True)
    try:
        meta = semanticscholarmetadata.getMetadata(paper)
    except:
        return []

    print(meta)

def deDupePaperList():
    pass


def snowballCitations(paperstore, all_papers):
    paper_list = []

    for paper in all_papers:
        getCitingPapers(paper)


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache)

    successful, unsuccessful = enrichAndUpdateMetadata(papers_to_add, paperstore, conf.email)

    snowballCitations(paperstore, all_papers)

    included, df = filterPapers(all_papers)

    writeOutputBib(included, conf.output)


if __name__ == '__main__':
    parser = ArgumentParser(description='Filter results ')

    parser.add_argument('-i', '--input', type=str,
                        help='Input bib file name with seed papers')
    parser.add_argument('-o', '--output', type=str,
                        help='Output bib file name with snowballed')
    parser.add_argument('-r', '--report-path', type=str, default='filter_report.csv',
                        help='Path to output report CSV')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')
    parser.add_argument('-em', '--email', type=str,
                        help='Email to serve as identity to API endpoints')

    conf = parser.parse_args()

    main(conf)
