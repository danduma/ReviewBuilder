import re

MAX_RESULTS = 100


class Searcher:
    def __init__(self, paperstore):
        self.paperstore = paperstore

    def search(self, query, min_year=None, max_year=None, max_results=MAX_RESULTS):
        pass


class SearchResult:
    def __init__(self, index, bib, source, extra_data):
        self.index = index
        self.bib = bib
        self.source = source
        self.extra_data = extra_data
        self.paper = None

    def __getitem__(self, item):
        return self.extra_data.get(item, self.bib.get(item))

    def __repr__(self):
        return f"<#%d: %s - %s - %s> \n %s" % (
            self.index, self.bib.get("title", ""),
            self.bib.get("author", ""),
            self.bib.get("year", ""), str(self.bib))


def getSearchResultsFromBib(bib_entries, max_results):
    results = []
    for index, bib in enumerate(bib_entries[:max_results]):
        res = SearchResult(index, bib, 'bibfile', {})
        if bib.get('note'):
            match = re.search('(\d+)\scites:\s.+?scholar\?cites\=(\d+)', bib['note'])
            if match:
                res.source = 'scholar'
                res.extra_data['scholarid'] = match.group(2)
                res.extra_data['citedby'] = match.group(1)
        results.append(res)

    return results