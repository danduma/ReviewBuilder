import bibtexparser
import re
import random


def fixBibData(bib, index):
    """
    Add mandatory missing fields to bibtex data

    :param bib:
    :param index:
    :return:
    """
    if "ENTRYTYPE" not in bib:
        bib["ENTRYTYPE"] = "ARTICLE"
    if "ID" not in bib or bib.get('year'):
        authors = parseBibAuthors(bib["author"])
        if not authors:
            bib['ID'] = 'id' + str(random.randint(1000, 9000))
        else:
            bib["ID"] = authors[0]["family"]

        bib['ID'] += bib.get("year", "YEAR") + bib["title"].split()[0].lower()

    return bib


def isPDFURL(url):
    return ('pdf' in url or 'openreview' in url)


def getDOIfromURL(url):
    if not url:
        return None

    match = re.search('(10\.\d+\/[a-zA-Z\.\d\-\_]+)\.pdf', url)
    if match:
        return match.group(1)

    match = re.search('(10\.\d+\/[a-zA-Z\.\d\-\_]+)/', url)
    if match:
        return match.group(1)

    match = re.search('(10\.\d+\/[a-zA-Z\.\d\-\_]+)\?', url)
    if match:
        return match.group(1)

    match = re.search('(10\.\d+\/[a-zA-Z\.\d\-\_]+)', url)
    if match:
        return match.group(1)

    return None


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
        authorstring = author.get('family', '')
        if author.get('middle', ''):
            authorstring += ' ' + author.get('middle')
        authorstring += ', ' + author.get('given', '')
        authorstrings.append(authorstring)

    authors_string = " and ".join(authorstrings)
    return authors_string


def normalizeURL(url: str):
    return url.replace('https:', 'http:')


def addUrlIfNew(paper, url: str, type: str, source: str):
    paper.extra_data['urls'] = paper.extra_data.get('urls', [])

    existing_urls = [normalizeURL(u['url']).lower() for u in paper.extra_data['urls']]

    if url.lower() not in existing_urls:
        paper.extra_data['urls'].append({'url': normalizeURL(url),
                                         'type': type,
                                         'source': source})


def readBibtexString(bibstr):
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
        db.entries.append(fixBibData(result.bib, index))

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
