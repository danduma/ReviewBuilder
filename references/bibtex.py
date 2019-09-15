import bibtexparser
import re


def convert_result(result, index):
    bib = result["bib"]
    if "ENTRYTYPE" not in bib:
        bib["ENTRYTYPE"] = "ARTICLE"
    if "ID" not in bib:
        # if 'author' in bib:
        bib["ID"] = "id" + str(index)

    return result["bib"]


def write_bibtex(results, filename):
    db = bibtexparser.bibdatabase.BibDatabase()
    for index, result in enumerate(results):
        db.entries.append(convert_result(result, index))

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
