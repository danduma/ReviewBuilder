import bibtexparser
import re


def fix_bib_data(bib, index):
    """
    Add mandatory missing fields to bibtex data

    :param bib:
    :param index:
    :return:
    """
    if "ENTRYTYPE" not in bib:
        bib["ENTRYTYPE"] = "ARTICLE"
    if "ID" not in bib:
        authors = parseBibAuthors(bib["author"])
        # bib["ID"] = 'id' + str(index)
        bib["ID"] = authors[0]["family"] + bib.get("year", "____") + bib["title"].split()[0].lower()
    return bib


def parseBibAuthors(authors):
    bits = authors.split('and')
    authors = []
    for bit in bits:
        match = re.search(r"([A-Z]+)\s+(\w+)", bit)
        if match:
            author = {"given": match.group(1), "family": match.group(2)}
            authors.append(author)
        else:
            match = re.search(r"([A-Z]\w+)\s*,\s*([A-Z]\w*)", bit)
            if match:
                author = {"given": match.group(2), "family": match.group(1)}
                authors.append(author)
            else:
                author = {"given": '', "family": bit}
                # raise ValueError("Couldn't find names")
    return authors


def authorListFromDict(authors):
    authorstrings = []
    for author in authors:
        authorstrings.append(author.get('given', '') + author.get('middle', '') + " " + author.get('family', ''))

    authors_string = " and ".join(authorstrings)
    return authors_string


def read_bibtex_string(bibstr):
    return bibtexparser.loads(bibstr).entries


def read_bibtex_file(filename):
    return bibtexparser.load(open(filename, 'r')).entries


def write_bibtex(results: list, filename: str):
    """
    Exports the list of results to a BibTeX file.

    :param results: a list of either SearchResult or Paper objects, with a .bib dict property
    :param filename: file to export the bibtex to
    """
    db = bibtexparser.bibdatabase.BibDatabase()

    for index, result in enumerate(results):
        db.entries.append(fix_bib_data(result.bib, index))

    with open(filename, 'w') as bibtex_file:
        bibtexparser.dump(db, bibtex_file)


def test():
    bibtex = """@ARTICLE{Cesar2013,
      author = {Jean César},
      title = {An amazing title},
      year = {2013},
      volume = {12},
      pages = {12--23},
      journal = {Nice Journal},
      abstract = {This is an abstract. This line should be long enough to test
         multilines...},
      comments = {A comment},
      keywords = {keyword1, keyword2}
    }
    """

    with open('bibtex.bib', 'w') as bibfile:
        bibfile.write(bibtex)

    with open("bibtex.bib") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    print(bib_database.entries)


if __name__ == '__main__':
    test()
