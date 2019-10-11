import requests
import scholarly
from time import sleep
from .base_search import Searcher, MAX_RESULTS, SearchResult
import bibtexparser
from tqdm import tqdm
from random import random
from db.bibtex import fixBibData, getDOIfromURL


class GScholarSearcher(Searcher):
    """
    Retrieves results and bibtex data from Google Scholar
    """

    def __init__(self, paperstore):
        super().__init__(paperstore)
        self.min_delay_between_requests = 0.1

    def randomSleep(self):
        sleep(self.min_delay_between_requests + random() / 10)  # random sleep so we don't get blocked

    def search(self, query, min_year=None, max_year=None, max_results=MAX_RESULTS):
        # TODO implement max year
        if min_year:
            scholarly.scholarly._PUBSEARCH = '/scholar?as_ylo=' + str(min_year) + '&q={0}'

        query = scholarly.search_pubs_query(query)
        results = []
        index = 0
        for result in tqdm(query, desc="Getting results", total=max_results):
            bib = fixBibData(result.bib, index)

            extra_data = {}

            for field in ['citedby', 'id_scholarcitedby', 'url_scholarbib', 'url']:
                if hasattr(result, field):
                    extra_data[field] = getattr(result, field)

            doi = getDOIfromURL(bib.get('url'))
            if not doi:
                doi = getDOIfromURL(bib.get('eprint'))

            if doi:
                bib['doi'] = doi

            result = SearchResult(index, bib, result.source, extra_data)
            results.append(result)
            index += 1

            if len(results) == max_results:
                break

            if len(results) % 10 == 0:
                self.randomSleep()
        return results

    def getScholarBibForResults(self, results):
        res = []
        for result in tqdm(results, desc="Getting Scholar bib data"):
            if result.get("url_scholarbib"):
                bib = result["bib"]
                try:
                    r = requests.get(result["url_scholarbib"])
                    # print(r)
                    db = bibtexparser.loads(r.text)
                    bib = db.entries[0]

                except Exception as e:
                    print(e)

                bib['abstract'] = result["bib"]['abstract']
                for key in ['abstract', 'eprint', 'url']:
                    if key in result["bib"]:
                        bib[key] = result["bib"][key]
                result["bib"] = bib

                self.randomSleep()
