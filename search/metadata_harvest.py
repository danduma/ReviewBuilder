import requests
import json, re
import urllib.parse
from strsimpy.normalized_levenshtein import NormalizedLevenshtein
from references.bibtex import dict_from_string
from tqdm import tqdm
from bs4 import BeautifulSoup

dist = NormalizedLevenshtein()

BIB_FIELDS = ['address', 'annote', 'author', 'booktitle', 'chapter', 'crossref', 'edition', 'editor',
              'howpublished', 'institution', 'issue', 'journal', 'key',
              'month', 'note', 'number', 'organization',
              'pages', 'publisher', 'school', 'series', 'title', 'type', 'volume', 'year']


def searchCrossref(title, year=None, max_results=1):
    urllib.parse.quote(title, safe='')
    url = 'https://api.crossref.org/works?rows={}&query.title={}'.format(max_results, title)
    if year:
        url += '&query.published=' + str(year)

    r = requests.get(url)
    # print(r.text)
    d = r.json()
    if d['status'] != 'ok':
        raise ValueError('Error in request:' + d['status'] + str(d['message']))

    return d['message']['items']


def getBibtextFromDOI(doi):
    headers = {'Accept': 'text/bibliography; style=bibtex'}
    url = 'http://doi.org/' + doi
    r = requests.get(url, headers=headers)
    bib = dict_from_string(r.text)
    return bib


def mergeBibs(bib, new_bib):
    for field in BIB_FIELDS:
        if not bib.get(field) and new_bib.get(field):
            bib[field] = new_bib[field]
    return bib


def basicTitleCleaning(title):
    return re.sub(r'\s+', ' ', title, flags=re.MULTILINE)


def rerankBySimilarity(results, paper):
    scores = []
    for res in results:
        res['title'] = [basicTitleCleaning(res['title'][0])]
        scores.append((dist.distance(res['title'][0].lower(), paper.title.lower()), res))

    return sorted(scores, key=lambda x: x[0], reverse=False)


def searchSemanticScholar(title):
    '''
    FIXME: may require JS to run, and so Selenium

    :param title:
    :return:
    '''
    r = requests.get('https://www.semanticscholar.org/search?q=' + urllib.parse.quote(title))
    soup = BeautifulSoup(r.text, features='lxml')
    res = []
    for result in soup.find_all('div', {'class': 'search-result-title'}):
        print(result)

    return res


def getDataFromSemanticScholar(paper):
    if not paper.doi:
        raise ValueError('paper has no DOI')

    url = 'https://api.semanticscholar.org/v1/paper/' + paper.doi
    r = requests.get(url)
    d = r.json()

    if 'error' in d:
        print("SemanticScholar error:", d['error'])
        return

    if 'abstract' in d:
        paper.bib['abstract'] = d['abstract']

    if d.get('arxivId'):
        paper.arxivid = d['arxivId']

    paper.extra_data['ss_topics'] = d['topics']
    paper.extra_data['ss_authors'] = d['authors']
    paper.extra_data['ss_id'] = d['paperId']


def enrichMetadata(papers: list):
    for paper in tqdm(papers, desc='Enriching metadata'):
        if not paper.doi:
            paper.title = basicTitleCleaning(paper.title)

            if not paper.extra_data.get('done_crossref', False):
                results = searchCrossref(paper.title, max_results=5)
                sorted_results = rerankBySimilarity(results, paper)

                top_res = sorted_results[0][1]

                print('Query title:', paper.title)
                print('Best match:', top_res['title'][0])
                print('distance:', dist.distance(top_res['title'][0].lower(), paper.title.lower()))

                if dist.distance(top_res['title'][0].lower(), paper.title.lower()) > 0.1:
                    print('Best matching title does not match:' + top_res['title'][0] + ',\n' + paper.title)
                    continue

                paper.doi = top_res['DOI']
                new_bib = getBibtextFromDOI(top_res['DOI'])
                paper.bib = mergeBibs(paper.bib, new_bib[0])
                paper.extra_data['done_crossref'] = True
                paper.extra_data['xref_author'] = top_res['author']
                paper.extra_data['language'] = top_res.get('language')
                paper.extra_data['urls'] = paper.extra_data.get('urls', [])
                paper.extra_data['urls'].append({'url': top_res['URL'], 'type': 'main', 'source': 'crossref'})

                if 'link' in top_res:
                    for link in top_res['link']:
                        new_link = {'url': link['URL']}
                        if 'pdf' in link['URL']:
                            new_link['type'] = 'pdf'
                            new_link['source'] = 'crossref'

        if not paper.extra_data.get('done_semanticscholar'):
            getDataFromSemanticScholar(paper)
            paper.extra_data['done_semanticscholar'] = True


def test():
    title = 'Natural language processing technologies in radiology research and clinical applications'

    # res = searchSemanticScholar(title)

    # res = searchCrossref(title)
    # for r in res:
    #     print(json.dumps(r, indent=3))


if __name__ == '__main__':
    test()
