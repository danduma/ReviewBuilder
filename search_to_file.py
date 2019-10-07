from db.data import PaperStore, Paper

from search import GScholarSearcher, enrichMetadata
from argparse import ArgumentParser
from references import write_bibtex


def main(conf):
    if conf.cache:
        paperstore = PaperStore()
    else:
        paperstore = None

    if conf.engine == "scholar":
        searcher = GScholarSearcher(paperstore)
    # elif conf.engine == "pubmed":
    #     searcher = GScholarSearcher(paperstore)
    else:
        raise ValueError

    results = searcher.search(conf.query, min_year=conf.year_start, max_results=conf.max)
    found, missing = paperstore.matchResultsWithPapers(results)

    papers_to_add = [Paper(res.bib, res.extra_data) for res in missing]
    enrichMetadata(papers_to_add)

    paperstore.addPapers(papers_to_add)

    papers_existing = [Paper(res.bib, res.extra_data) for res in found]
    enrichMetadata(papers_existing)
    paperstore.updatePapers(papers_existing)

    all_papers = papers_to_add + papers_existing
    write_bibtex(all_papers, conf.file)


if __name__ == '__main__':
    parser = ArgumentParser(description='Saves article search results to a file')

    parser.add_argument('-q', '--query', type=str,
                        help='The query to use to retrieve the articles')
    parser.add_argument('-ys', '--year-start', type=int,
                        help='The minimum year for results')
    parser.add_argument('-ye', '--year-end', type=int,
                        help='The maximum year for results')
    parser.add_argument('-f', '--file', type=str,
                        help='Filename to dump the results to')
    parser.add_argument('-m', '--max', type=int, default=100,
                        help='Maximum number of results to retrieve')
    parser.add_argument('-e', '--engine', type=str, default="scholar",
                        help='Which search engine to use. Currently only "scholar" (Google Scholar) available ')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')

    conf = parser.parse_args()

    main(conf)
