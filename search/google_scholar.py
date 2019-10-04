import requests
import scholarly
from time import sleep
from .base_search import Searcher, MAX_RESULTS
import bibtexparser
from tqdm import tqdm
from random import random


class GScholarSearcher(Searcher):
    """
    Retrieves results and bibtex data from Google Scholar
    """
    def randomSleep(self):
        sleep(0.1 + random() / 10)  # random sleep so we don't get blocked

    def search(self, query, max_results=MAX_RESULTS):
        query = scholarly.search_pubs_query(query)
        results = []
        for result in tqdm(query, desc="Getting results", total=max_results):
            bib = result.bib

            result_dict = {"bib": bib,
                           "citedby": result.citedby,
                           "url": result.url_scholarbib,
                           "id_scholarcitedby": result.id_scholarcitedby,
                           "source": result.source,
                           "url_scholarbib": result.url_scholarbib
                           }

            results.append(result_dict)
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