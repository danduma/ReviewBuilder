# ReviewBuilder
A bunch of tools for automating parts of a Systematic Review of scientific literature.

Example usage:

> search_to_file -q "lstm OR rnn OR bert OR elmo OR word2vec OR \"natural language\" \"radiology reports\" " -m 10 -f test.bib

This will send the query to Google Scholar and save the first 10 results in BibTeX format in the file `test.bib`
