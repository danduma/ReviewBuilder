from search import GScholarSearcher
from argparse import ArgumentParser
from references import write_bibtex

def main(conf):
    if conf.engine =="scholar":
        searcher = GScholarSearcher()
    else:
        raise ValueError

    results = searcher.search(conf.query, 10)
    write_bibtex(results, conf.file)


if __name__ == '__main__':

    parser = ArgumentParser(description='Saves article search results to a file')

    parser.add_argument('-q', '--query', type=str,
                        help='The query to use to retrieve the articles')
    parser.add_argument('-f', '--file', type=str,
                        help='Filename to dump the results to')
    parser.add_argument('-m','--max', type=int, default=100,
                        help='Maximum number of results to retrieve')
    parser.add_argument('-e','--engine', type=str, default="scholar",
                        help='Which search engine to use. Currently only "scholar" (Google Scholar) available ')

    conf = parser.parse_args()

    main(conf)