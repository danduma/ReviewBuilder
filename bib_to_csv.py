from argparse import ArgumentParser
from base.general_utils import loadEntriesAndSetUp

import pandas as pd

def dataframeFromPapers(papers):
    report = []

    for paper in papers:
        report.append(paper.asDict())

    df = pd.DataFrame(report, columns=['id', 'year', 'title', 'authors', 'venue', 'abstract', 'doi', 'pmid', ])
    return df


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache)


    df = dataframeFromPapers(all_papers)
    df.to_csv(conf.output)


if __name__ == '__main__':
    parser = ArgumentParser(description='Filter results ')

    parser.add_argument('-i', '--input', type=str,
                        help='Input bib file name')
    parser.add_argument('-o', '--output', type=str,
                        help='Output csv file name')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')

    conf = parser.parse_args()

    main(conf)
