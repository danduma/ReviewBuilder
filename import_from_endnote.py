from argparse import ArgumentParser

from db.data import PaperStore, Paper
from db.endnote_html import loadRefsFromHTML
from search import getSearchResultsFromBib
from db.ref_utils import addUrlIfNewWithType


def main(conf):
    if conf.cache:
        paperstore = PaperStore()
    else:
        paperstore = None

    bib_entries = loadRefsFromHTML(conf.input)

    results = getSearchResultsFromBib(bib_entries)

    if paperstore:
        found, missing = paperstore.matchResultsWithPapers(results)
    else:
        found = []
        missing = results

    papers_to_add = [Paper(res.bib, res.extra_data) for res in missing]

    counter = 0

    for res in found:
        if res.bib.get('url'):
            if addUrlIfNewWithType(res.paper, res['url'], 'endnote'):
                counter += 1
        if res.bib.get('eprint'):
            if addUrlIfNewWithType(res.paper, res['eprint'], 'endnote'):
                counter += 1

    papers_existing = [res.paper for res in found]
    paperstore.updatePapers(papers_existing)

    print('Papers found', len(papers_existing))
    print('Papers not found', len(papers_to_add))
    print('Added', counter, 'urls')

if __name__ == '__main__':
    parser = ArgumentParser(
        description='Exports a bibliography to RIS (EndNote) for further gathering of PDFs')

    parser.add_argument('-i', '--input', type=str,
                        help='Input EndNote HTML file')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')

    conf = parser.parse_args()

    main(conf)
