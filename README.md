# ReviewBuilder
A bunch of tools for automating parts of a Systematic Review of scientific literature.

Currently supports one use case: creating a bibtex file with the results of a Google Scholar search. 

New: added metadata search on Crossref and SemanticScholar to retrieve abstracts. Results are cached locally in a SQLite database.

## Installation

> pip install -r requirements.txt

## Example usage

> python search_to_file.py -q "lstm OR rnn OR bert OR elmo OR word2vec OR \"natural language\" \"radiology reports\" " -m 10 -f test.bib

This will send the query to Google Scholar, collect metadata from Crossref and SemanticScholar and save the first 10 results in BibTeX format in the file `test.bib`
