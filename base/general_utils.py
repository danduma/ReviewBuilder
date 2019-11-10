from db.bibtex import readBibtexFile
from db.data import PaperStore, Paper
from search import getSearchResultsFromBib
from db.ref_utils import simpleResultDeDupe
from db.bibtex import writeBibtex
from db.ris import writeRIS
from db.csv import readCSVFile

def loadEntriesAndSetUp(input, use_cache=True, max_results=10000000):
    if use_cache:
        paperstore = PaperStore()
    else:
        paperstore = None

    bib_entries = readInputBib(input)
    results = getSearchResultsFromBib(bib_entries, max_results)

    results = simpleResultDeDupe(results)

    if paperstore:
        found, missing = paperstore.matchResultsWithPapers(results)
    else:
        found = []
        missing = results

    papers_to_add = [Paper(res.bib, res.extra_data) for res in missing]
    papers_existing = [res.paper for res in found]

    all_papers = papers_to_add + papers_existing

    # FIXME: a second dedupe is needed because it seems I'm matching the wrong paper
    # a total of 5 records suffer from this so it's no big deal
    all_papers = simpleResultDeDupe(all_papers)

    return paperstore, papers_to_add, papers_existing, all_papers

def readInputBib(filename):
    if filename.endswith('.bib'):
        return readBibtexFile(filename)
    elif filename.endswith('.csv'):
        return readCSVFile(filename)
    elif filename.endswith('.ris'):
        raise NotImplementedError

def writeOutputBib(bib, filename):
    if filename.endswith('.ris'):
        writeRIS(bib, filename)
    else:
        writeBibtex(bib, filename)