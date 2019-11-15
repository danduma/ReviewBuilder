import bibtexparser
import re
import random

import requests

from db.ref_utils import parseBibAuthors, normalizeTitle


def fixBibData(bib, index):
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
        if not authors:
            bib['ID'] = 'id' + str(random.randint(1000, 9000))
        else:
            bib["ID"] = authors[0]["family"]

        bib['ID'] += str(bib.get("year", "YEAR")) + bib["title"].split()[0].lower()

    return bib


def readBibtexString(bibstr):
    return bibtexparser.loads(bibstr).entries


def readBibtexFile(filename):
    return bibtexparser.load(open(filename, 'r')).entries


def writeBibtex(results: list, filename: str):
    """
    Exports the list of results to a BibTeX file.

    :param results: a list of either SearchResult or Paper objects, with a .bib dict property
    :param filename: file to export the bibtex to
    """
    db = bibtexparser.bibdatabase.BibDatabase()

    for index, result in enumerate(results):
        db.entries.append(fixBibData(result.bib, index))

    with open(filename, 'w') as bibtex_file:
        bibtexparser.dump(db, bibtex_file)


def getBibtextFromDOI(doi: str):
    assert doi
    headers = {'Accept': 'text/bibliography; style=bibtex'}
    url = 'http://doi.org/' + doi
    r = requests.get(url, headers=headers)
    text = r.content.decode('utf-8')
    bib = readBibtexString(text)
    return bib


def generateUniqueID(paper):
    """
    Returns a simple string id that is the mashup of the title and authors

    :param paper:
    :return:
    """
    author_bit = ''
    if paper.extra_data.get('xref_author'):
        authors = paper.extra_data['xref_author']
    else:
        try:
            authors = parseBibAuthors(paper.authors)
        except:
            print("Failed to parse authors string", paper.authors)
            authors = [{'given': '', 'family': ''}]

    for author in authors:
        if author.get('family'):
            author_bit += author.get('family', '_')[0] + author.get('given', '_')[0]

    title_bit = normalizeTitle(paper.title)
    title_bit = re.sub("\s+", "", title_bit)
    full_id = title_bit + "_" + author_bit
    full_id = full_id.lower()
    return full_id


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
