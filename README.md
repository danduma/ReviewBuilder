# ReviewBuilder
A collection of tools for automating parts of a Systematic Review of scientific literature.

Currently supports one use case: creating a bibtex file with the results of a Google Scholar search and augmenting the metadata for each result by retrieving its abstract and finding [Open Access](https://en.wikipedia.org/wiki/Open_access) versions of the paper on the web, including preprints. All results are cached locally in a SQLite database, aiming to make iterating over queries for obtaining papers for a review less painful.

- Implemented: Google Scholar, Crossref, Semantic Scholar (metadata), PubMed, arXiv, Unpaywall.
- Not yet implemented: Microsoft Academic, Semantic Scholar (search), Web of Science

## Installation

> pip install -r requirements.txt

## Example usage

> python search_to_file.py -q "OR \"natural language\" OR \"radiology reports\" OR lstm OR rnn OR bert OR elmo OR word2vec" -m 10 -f test.bib -ys 2015

This will send the supplied query to Google Scholar, and set the minimum year (--year-start) to 2015, retrieve a maximum of 10 results and save them in the file `test.bib`. 

Alternatively, we can save the query in a text file and pass that as a parameter:

> python search_to_file.py -qf query1.txt -m 10 -f test.bib -ys 2015

Bibtex does not store everything we are interested in, so by default, extra data from Scholar such as the link to the "related articles", number of citations and other tidbits will be directly saved to the local SQLite cache (see below).

Google Scholar offers perhaps the best coverage (recall) over all fields of science and does a great job at surfacing relevant articles. What it does not do, however, is make it easy to scrape, or connect these results to anything else useful. It does not provide any useful identifier for the results ([DOI](http://www.doi.org/), [PMID](https://www.ncbi.nlm.nih.gov/pmc/pmctopmid/), etc) or the abstract of the paper.  For this we need to use other services.

Once we have the list of results, we can collect extra data, such as the abstract of the paper and locations on the web where we may find it in open access, whether in HTML or PDF.

> python gather_metadata.py -i test.bib -o test_plus.bib --max 200

This will process a maximum of 200 entries from the `test.bib` file, and output an "enriched" version to `test_plus.bib`. For each entry it will try to:
1. match it with an entry in the local cache. If it can't be found go to step 2.
1. attempt to match the paper with its DOI via the [Crossref](http://www.crossref.org/) API.
1. once we have a DOI, check [SemanticScholar](http://www.semanticscholar.org/) for metadata and abstract for the paper
1. if we don't have a DOI or abstract, search [PubMed](http://www.ncbi.nlm.nih.gov/pubmed/) for its PubMed ID (PMID) and retrieve the abstract from there, if available
1. search [arXiv](http://arxiv.org) for a preprint of the paper
1. search [Unpawall](http://unpaywall.org) for available open access versions of the paper if we are missing a PDF link from the above

Many of these steps require approximate matching, both for the local cache and the results from the remote APIs. Often a preprint version of a paper will have a slightly different title or will be missing an author or two. This repo implements several heuristics for dealing with this.

A SQLite database cache is automatically created in `papers.sqlite` in the /db directory.


