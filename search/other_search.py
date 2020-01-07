from .base_search import Searcher, MAX_RESULTS
from .metadata_harvest import SemanticScholarScraper, PubMedScraper


class SemanticScholarSearcher(Searcher):
    def __init__(self, paperstore):
        super().__init__(paperstore)
        self.scraper = SemanticScholarScraper()

    def search(self, query, min_year=None, max_year=None, max_results=MAX_RESULTS):
        res = self.scraper.search(query, identity='', min_year=min_year, max_year=max_year)
        return res


class PubMedSearcher(Searcher):
    def __init__(self, paperstore):
        super().__init__(paperstore)
        self.scraper = PubMedScraper()

    def search(self, query, min_year=None, max_year=None, max_results=MAX_RESULTS):
        self.scraper.search(query, identity='')
