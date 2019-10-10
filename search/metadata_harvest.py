import requests
import re
import urllib.parse
from strsimpy.normalized_levenshtein import NormalizedLevenshtein
from db.bibtex import read_bibtex_string
from tqdm import tqdm
from bs4 import BeautifulSoup
import datetime
from time import sleep
from datetime import timedelta

dist = NormalizedLevenshtein()

BIB_FIELDS = ['address', 'annote', 'author', 'booktitle', 'chapter', 'crossref', 'edition', 'editor',
              'howpublished', 'institution', 'issue', 'journal', 'key',
              'month', 'note', 'number', 'organization',
              'pages', 'publisher', 'school', 'series', 'title', 'type', 'volume', 'year']

TRUSTED_BIB_FIELDS = ['address', 'annote', 'author', 'booktitle', 'chapter', 'crossref',
                      'edition', 'editor',
                      'howpublished', 'institution', 'issue', 'journal', 'key',
                      'month', 'note', 'number', 'organization',
                      'pages', 'publisher', 'school', 'series', 'type', 'volume', 'year']

interval_regex = re.compile(r'((?P<hours>\d+?)hr)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')


def parse_time(time_str):
    parts = interval_regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


class NiceScraper:
    def __init__(self, basic_delay=0., rate_limit=None, rate_interval=None):
        self.response_times = []
        self.request_times = []
        self.avg_response_time = 0
        self.basic_delay = basic_delay
        self.delay = 0.0
        self.rate_limit = None
        self.rate_interval = None

    def playNice(self):

        if self.rate_limit and len(self.request_times) >= self.rate_limit:
            now = datetime.datetime.now()

            diff = now - self.request_times[-self.rate_limit]
            if diff < self.rate_interval:
                print('Waiting for the rate limit')
                sleep(self.rate_interval - diff.total_seconds())

        if len(self.response_times) > 0:
            self.avg_response_time = sum(self.response_times[-10:]) / len(self.response_times[-10:])
            if self.response_times[-1] > self.avg_response_time:
                self.delay += 0.1
            else:
                self.delay -= 0.1
                self.delay = max(self.delay, 0)
        else:
            self.avg_response_time = 0

        if self.delay:
            sleep(self.delay)

    def setRateLimitsFromHeaders(self, request):
        self.rate_limit = int(request.headers.get('X-Rate-Limit-Limit'))
        if 'X-Rate-Limit-Interval' in request.headers:
            try:
                self.rate_interval = parse_time(request.headers['X-Rate-Limit-Interval'])
            except:
                print("Failed to parse X-Rate-Limit-Interval string",
                      request.headers['X-Rate-Limit-Interval'])
                self.rate_interval = None


class CrossrefSearch(NiceScraper):

    def bulkSearchCrossref(self, papers):
        r = requests.get("https://doi.crossref.org/simpleTextQuery")

    def search(self, title, year=None, max_results=1):
        """
        Searchs and returns a number of results from Crossref

        :param title: article title
        :param year: publication year
        :param max_results:
        :return: list of Crossref JSON data rsults
        """
        urllib.parse.quote(title, safe='')
        headers = {'User-Agent': 'ReviewBuilder(mailto:dduma@sms.ed.ac.uk)'}
        url = 'https://api.crossref.org/works?rows={}&query.title={}'.format(max_results, title)
        if year:
            url += '&query.published=' + str(year)

        self.playNice()

        self.request_times.append(datetime.datetime.now())
        before = datetime.datetime.now()
        r = requests.get(url, headers=headers)
        duration = datetime.datetime.now() - before

        self.setRateLimitsFromHeaders(r)

        self.response_times.append(duration.total_seconds())
        print("Duration", self.response_times[-1])

        d = r.json()
        if d['status'] != 'ok':
            raise ValueError('Error in request:' + d['status'] + str(d['message']))

        return d['message']['items']


class GScholarMetadata(NiceScraper):
    def getScholarBib(self, paper):
        if paper.extra_data.get("url_scholarbib"):
            bib = paper.bib
            url = paper.extra_data.get("url_scholarbib")
            try:
                self.playNice()

                before = datetime.datetime.now()
                r = requests.get(url)
                duration = datetime.datetime.now() - before

                self.response_times.append(duration.total_seconds())

                # print(r)
                text = r.content.decode('utf-8')
                bib = read_bibtex_string(text)[0]

            except Exception as e:
                print(e)

            bib['abstract'] = paper.abstract
            for key in ['abstract', 'eprint', 'url']:
                if key in paper.bib:
                    bib[key] = paper.bib[key]
            paper.bib = bib


crossrefsearcher = CrossrefSearch()
scholarmetadata = GScholarMetadata(basic_delay=0.1)


def getBibtextFromDOI(doi):
    headers = {'Accept': 'text/bibliography; style=bibtex'}
    url = 'http://doi.org/' + doi
    r = requests.get(url, headers=headers)
    text = r.content.decode('utf-8')
    bib = read_bibtex_string(text)
    return bib


def mergeBibs(bib, new_bib):
    for field in TRUSTED_BIB_FIELDS:
        if len(new_bib.get(field, '')) > len(bib.get(field, '')):
            bib[field] = new_bib[field]

    for field in ['ID', 'ENTRYTYPE']:
        if field in new_bib:
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


def enrichAndUpdateMetadata(papers, paperstore):
    successful = []
    unsuccessful = []

    for paper in tqdm(papers, desc='Enriching metadata'):
        try:
            enrichMetadata(paper)
            successful.append(paper)
        except Exception as e:
            print(e)
            unsuccessful.append(paper)

        paperstore.updatePapers([paper])


def enrichMetadata(paper):
    """
    Tries to retrieve metadata from Crossref and abstract from SemanticScholar for a given paper,
    Google Scholar bib if all else fails

    :param paper: Paper instance
    """
    # if we don't have a DOI, we need to find it
    if not paper.doi:
        paper.title = basicTitleCleaning(paper.title)

        if not paper.extra_data.get('done_crossref', False):
            results = crossrefsearcher.search(paper.title, max_results=5)
            sorted_results = rerankBySimilarity(results, paper)

            top_res = sorted_results[0][1]

            print('Query title:', paper.title)
            print('Best match:', top_res['title'][0])
            print('distance:', dist.distance(top_res['title'][0].lower(), paper.title.lower()))

            if dist.distance(top_res['title'][0].lower(), paper.title.lower()) > 0.1:
                print('[Best matching title does not match!]\n')
                print('Options:' + '\n'.join([r[1]['title'][0] for r in sorted_results]))
            else:
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

    # if we have a DOI and we haven't got the abstract yet
    if paper.doi and not paper.extra_data.get('done_semanticscholar'):
        getDataFromSemanticScholar(paper)
        paper.extra_data['done_semanticscholar'] = True

    # if all else has failed but we have a link to Google Scholar bib data, get that
    if not paper.year and paper.extra_data.get('url_scholarbib'):
        scholarmetadata.getScholarBib(paper)


def test():
    title = 'Natural language processing technologies in radiology research and clinical applications'

    # res = searchSemanticScholar(title)

    # res = searchCrossref(title)
    # for r in res:
    #     print(json.dumps(r, indent=3))


if __name__ == '__main__':
    test()
