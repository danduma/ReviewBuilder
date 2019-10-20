from db.data import PaperStore, Paper

from search import GScholarSearcher, enrichAndUpdateMetadata
from argparse import ArgumentParser
from db.bibtex import writeBibtex


def main(conf):
    if conf.cache:
        paperstore = PaperStore()
    else:
        paperstore = None

    if conf.engine == "scholar":
        searcher = GScholarSearcher(paperstore)
    # elif conf.engine == "pubmed":
    #     searcher = PubMedSearcher(paperstore)
    else:
        raise ValueError

    if conf.query_file:
        with open(conf.query_file, 'r') as f:
            query = f.read()
    else:
        query = conf.query

    print("Query:", query)

    results = searcher.search(query, min_year=conf.year_start, max_results=conf.max)

    if conf.cache:
        found, missing = paperstore.matchResultsWithPapers(results)

        papers_to_add = [Paper(res.bib, res.extra_data) for res in missing]
        paperstore.updatePapers(papers_to_add)

    writeBibtex([Paper(res.bib, res.extra_data) for res in results], conf.file)


if __name__ == '__main__':
    parser = ArgumentParser(description='Searches an engine and saves results to a file')

    parser.add_argument('-q', '--query', type=str,
                        help='The query to use to retrieve the articles')
    parser.add_argument('-qf', '--query-file', type=str,
                        help='Text file containing the query to use to retrieve the articles')
    parser.add_argument('-h', '--headers-file', type=str,
                        help='YAML file containing the headers to use for requests, particularly to Google Scholar')
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
    parser.add_argument('-em', '--email', type=str,
                        help='Email to serve as identity to API endpoints')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')

    conf = parser.parse_args()

    main(conf)
