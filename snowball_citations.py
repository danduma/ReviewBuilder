from base.general_utils import loadEntriesAndSetUp, writeOutputBib
from argparse import ArgumentParser
from filter_results import filterPapers, printReport, filterOnePaper
from search.metadata_harvest import semanticscholarmetadata, enrichAndUpdateMetadata
import pandas as pd


def getCitingPapers(paper):
    try:
        paper, citing_papers = semanticscholarmetadata.getMetadata(paper, get_citing_papers=True)
    except Exception as e:
        print(e.__class__.__name__, e)
        return []

    return citing_papers


def deDupePaperList():
    pass


def snowballCitations(paperstore, all_papers):
    newfound_paper_list = []
    report = []

    all_titles_ever_seen = {}
    search_nodes = all_papers

    while len(search_nodes) > 0:
        paper = search_nodes.pop(0)
        new_papers = getCitingPapers(paper)
        for new_paper in new_papers:
            if new_paper.title in all_titles_ever_seen:
                print('[Skipping] already seen paper', new_paper.title)
                all_titles_ever_seen[new_paper.title] += 1
                continue

            semanticscholarmetadata.getMetadata(new_paper)
            new_paper.extra_data['done_semanticscholar'] = True
            paperstore.updatePapers([new_paper])

            all_titles_ever_seen[new_paper.title] = 1
            # year = new_paper.bib.get('year', 0)
            # if year and int(year) >= 2015:
            #     newfound_paper_list.append(Paper(paper.bib, paper.extra_data))
            # else:
            #     print(new_paper)
            paper, record = filterOnePaper(new_paper, exclude_rules={'no_pdf': False,
                                                                     'year': False,
                                                                     'is_review':False})
            report.append(record)

            if paper:
                newfound_paper_list.append(paper)
                print('Adding new seed paper', new_paper.bib['title'])
                search_nodes.append(new_paper)
            else:
                print('[Excluded]:', record['exclude_reason'], new_paper.bib['title'])

    df = pd.DataFrame(report, columns=['id', 'year', 'title', 'excluded', 'exclude_reason', 'language', 'abstract'])

    return newfound_paper_list, df


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache)

    # successful, unsuccessful = enrichAndUpdateMetadata(papers_to_add, paperstore, conf.email)

    snowballed_papers = snowballCitations(paperstore, all_papers)
    print('Number of snowballed papers:', len(snowballed_papers))

    successful, unsuccessful = enrichAndUpdateMetadata(snowballed_papers, paperstore, conf.email)

    included, df = filterPapers(snowballed_papers)
    printReport(df)

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
