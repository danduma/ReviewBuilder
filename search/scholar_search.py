import requests
import scholarly
from time import sleep
from .search import Searcher, MAX_RESULTS
import bibtexparser
from tqdm import tqdm
from random import random


class GScholarSearcher(Searcher):
    def search(self, query, max_results=MAX_RESULTS):
        query = scholarly.search_pubs_query(query)
        results = []
        for result in tqdm(query, desc="Getting results", total=max_results):
            bib = result.bib

            if result.url_scholarbib:
                try:
                    r = requests.get(result.url_scholarbib)
                    # print(r)
                    db = bibtexparser.loads(r.text)
                    bib = db.entries[0]
                    sleep(0.2 + random())  # random sleep so we don't get blocked
                except Exception as e:
                    print(e)

                bib['abstract'] = result.bib['abstract']
                for key in ['abstract', 'eprint', 'url']:
                    if key in result.bib:
                        bib[key] = result.bib[key]

            result_dict = {"bib": bib,
                           "citedby": result.citedby,
                           "url": result.url_scholarbib,
                           "id_scholarcitedby": result.id_scholarcitedby,
                           "source": result.source}

            results.append(result_dict)
            if len(results) == max_results:
                break

            if len(results) % 10 == 0:
                sleep(0.8 + random())
        return results
