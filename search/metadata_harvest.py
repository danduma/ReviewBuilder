import warnings

warnings.filterwarnings("ignore")

import requests
import re, json
import urllib.parse
from db.bibtex import readBibtexString, authorListFromDict, fixBibData, getDOIfromURL, addUrlIfNew, \
    isPDFURL, getBibtextFromDOI
from db.data import Paper, computeAuthorDistance, rerankByTitleSimilarity, basicTitleCleaning, dist, removeListWrapper
from .base_search import SearchResult
from tqdm import tqdm
import datetime
from time import sleep
from datetime import timedelta
from io import StringIO, BytesIO
from lxml import etree

BIB_FIELDS_TRANSFER = ['abstract', 'address', 'annote', 'author', 'booktitle', 'chapter',
                       'crossref', 'doi', 'edition', 'editor',
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


def refreshDOIfromURLs(paper):
    """
    If paper has no DOI, it tries to find one in any URLs stored in the bib or extra_data dicts

    :param paper: Paper or SearchResult
    """
    if paper.doi:
        return

    doi = getDOIfromURL(paper.bib.get('url', ''))
    if doi:
        paper.bib['doi'] = doi
    else:
        for url_dict in paper.extra_data.get('urls', []):
            doi = getDOIfromURL(url_dict['url'])
            if doi:
                paper.bib['doi'] = doi
                break


def mergeResultData(result1, result2):
    """
    Merges bibtex and extra_data dictionaries for a SearchResult and or a Paper

    :param result1:
    :param result2:
    :return:
    """
    # if there's no year we should update the ID after getting the year
    to_update_id = not result1.bib.get('year') or not 'ID' in result1.bib

    for field in BIB_FIELDS_TRANSFER:
        if len(str(result2.bib.get(field, ''))) > len(str(result1.bib.get(field, ''))):
            result1.bib[field] = str(result2.bib[field])

    for field in ['ID', 'ENTRYTYPE']:
        if field in result2.bib:
            result1.bib[field] = str(result2.bib[field])

    if 'ID' not in result2.bib and to_update_id:
        if 'ID' in result1.bib:
            del result1.bib['ID']
        fixBibData(result1.bib, 1)

    for field in result2.extra_data:
        if field not in result1.extra_data:
            result1.extra_data[field] = result2.extra_data[field]

    if 'urls' in result2.extra_data:
        for url in result2.extra_data['urls']:
            addUrlIfNew(result1, url['url'], url['type'], url['source'])

    refreshDOIfromURLs(result1)
    return result1


class NiceScraper:
    def __init__(self, basic_delay=0., rate_limit=None, rate_interval=None):
        self.response_times = []
        self.request_times = []
        self.avg_response_time = 0
        self.basic_delay = basic_delay
        self.delay = 0.0
        self.rate_limit = rate_limit
        if isinstance(rate_interval, str):
            self.rate_interval = parse_time(rate_interval)
        else:
            self.rate_interval = rate_interval

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

    def request(self, url, headers=None):
        """
        Makes a nice request, enforcing rate limits and adjusting the wait time
        between requests based on latency

        :param url: url to fetch
        :param headers: headers to pass
        :return: request object
        """
        self.playNice()

        self.request_times.append(datetime.datetime.now())
        before = datetime.datetime.now()

        r = requests.get(url, headers=headers)

        duration = datetime.datetime.now() - before

        self.setRateLimitsFromHeaders(r)

        self.response_times.append(duration.total_seconds())
        print(self.__class__.__name__.split('.')[-1], "request took", self.response_times[-1])

        return r

    def setRateLimitsFromHeaders(self, request):
        if request.headers.get('X-Rate-Limit-Limit'):
            self.rate_limit = int(request.headers.get('X-Rate-Limit-Limit'))
        if 'X-Rate-Limit-Interval' in request.headers:
            try:
                self.rate_interval = parse_time(request.headers['X-Rate-Limit-Interval'])
            except:
                print("Failed to parse X-Rate-Limit-Interval string",
                      request.headers['X-Rate-Limit-Interval'])
                self.rate_interval = None

    def search(self, title, identity, max_results=5):
        raise NotImplementedError

    def matchPaperFromResults(self, paper, identity, ok_title_distance=0.1, ok_author_distance=0.1):
        """
        Tries to match a paper with a DOI and retrieves its metadata if successful

        :param paper:
        :param identity:
        :return:
        """
        class_name = self.__class__.__name__.split('.')[-1]

        try:
            results = self.search(paper.title, identity, max_results=5)
        except Exception as e:
            print('Error during %s.search()' % class_name, e)
            results = None

        if not results:
            return False

        sorted_results = rerankByTitleSimilarity(results, paper.title)

        top_res = sorted_results[0][1]

        title_distance = dist.distance(top_res['title'].lower(), paper.title.lower())
        author_distance = computeAuthorDistance(paper, top_res)

        if title_distance > 0.1:
            if title_distance <= ok_title_distance and author_distance <= ok_author_distance:
                print('\n[matched] Title distance is above 0.1, but within settings')
                print('Title:', paper.title)
                print('Best match:', top_res['title'])
                print('title distance:', title_distance, 'author distance:', author_distance)
            else:
                print('\n[skipped] Distance is too great \n')
                print('Title:', paper.title)
                print('title distance:', title_distance, 'author distance:', author_distance)
                print('Options:\n' + '\n'.join([r[1]['title'] for r in sorted_results]), '\n')
                return False

        try:
            mergeResultData(paper, top_res)
            return True
        except Exception as e:
            print('Error during %s.matchPaperFromResults() mergeResultData()' % class_name, e)
            return False


class CrossrefSearch(NiceScraper):

    def bulkSearchCrossref(self, papers):
        pass
        # r = requests.get("https://doi.crossref.org/simpleTextQuery")

    def search(self, title, identity, year=None, max_results=1):
        """
        Searchs and returns a number of results from Crossref

        :param title: article title
        :param identity: email address to provide to Crossref
        :param year: publication year
        :param max_results:
        :return: list of Crossref JSON data results
        """
        urllib.parse.quote(title, safe='')
        headers = {'User-Agent': 'ReviewBuilder(mailto:%s)' % identity}
        url = 'https://api.crossref.org/works?rows={}&query.title={}'.format(max_results, title)
        if year:
            url += '&query.published=' + str(year)

        r = self.request(url, headers)

        d = r.json()
        if d['status'] != 'ok':
            raise ValueError('Error in request:' + d['status'] + str(d['message']))

        results = []
        for index, item in enumerate(d['message']['items']):
            # print(item.get('type'))
            new_bib = {'doi': item['DOI'],
                       'title': basicTitleCleaning(removeListWrapper(item['title']))}

            if 'container-title' in item:
                # reference-entry, book

                if item.get('type') in ['journal-article', 'reference-entry']:
                    new_bib['journal'] = removeListWrapper(item['container-title'])
                    new_bib['ENTRYTYPE'] = 'article'
                elif item.get('type') in ['book-chapter']:
                    new_bib['ENTRYTYPE'] = 'inbook'
                    new_bib['booktitle'] = removeListWrapper(item['container-title'])
                elif item.get('type') in ['proceedings-article']:
                    new_bib['ENTRYTYPE'] = 'inproceedings'
                    new_bib['booktitle'] = removeListWrapper(item['container-title'])

            if item.get('type') in ['book']:
                new_bib['ENTRYTYPE'] = 'book'

            if item.get('type') not in ['journal-article', 'reference-entry', 'book', 'book-chapter',
                                        'proceedings-article']:
                print(json.dumps(item, indent=3))

            for field in [('publisher-location', 'address'),
                          ('publisher', 'publisher'),
                          ('issue', 'issue'),
                          ('volume', 'volume'),
                          ('page', 'pages'),
                          ]:
                if field[0] in item:
                    new_bib[field[1]] = str(item[field[0]])

            if 'URL' in item:
                new_bib['url'] = item['URL']

            if "issued" in item:
                date_parts = item['issued']['date-parts'][0]
                new_bib['year'] = str(date_parts[0])
                if len(date_parts) > 1:
                    new_bib['month'] = str(date_parts[1])
                if len(date_parts) > 2:
                    new_bib['day'] = str(date_parts[2])

            authors = []
            for author in item.get('author', []):
                authors.append({'given': author.get('given', ''), 'family': author.get('family', '')})

            if item.get('author'):
                new_bib['author'] = authorListFromDict(authors)

            new_extra = {'x_authors': authors,
                         'language': item.get('language')
                         }

            new_res = SearchResult(index, new_bib, 'crossref', new_extra)

            addUrlIfNew(new_res, item['URL'], 'main', 'crossref')

            if 'link' in item:
                for link in item['link']:
                    if isPDFURL(link['URL']):
                        addUrlIfNew(new_res, link['URL'], 'pdf', 'crossref')

            results.append(new_res)

        return results


class UnpaywallMetadata(NiceScraper):

    def getMetadata(self, paper, identity):
        if not paper.doi:
            raise ValueError("Paper has no DOI")

        url = 'https://api.unpaywall.org/v2/%s?email=%s' % (paper.doi, identity)

        r = self.request(url)

        data = r.json()
        if data.get('error') == 'true':
            return

        top_url = data.get('best_oa_location')
        if not top_url:
            return

        if top_url.get('url_for_pdf') in top_url:
            addUrlIfNew(paper, top_url['url_for_pdf'], 'pdf', 'unpaywall')
        if top_url.get('url_for_landing_page'):
            addUrlIfNew(paper, top_url['url_for_landing_page'], 'main', 'unpaywall')
        if top_url.get('url'):
            url = top_url['url']
            if isPDFURL(url):
                type = 'pdf'
            else:
                type = 'main'

            addUrlIfNew(paper, url, type, 'unpaywall')

        paper.extra_data['done_unpaywall'] = True


class PubMedSearch(NiceScraper):
    def search(self, title, identity, max_results=5):
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax={max_results}&sort=relevance&term='
        url += urllib.parse.quote(title)

        r = self.request(url)
        d = r.json()
        id_list = d['esearchresult']['idlist']

        try:
            result = self.getMetadata(id_list)
        except Exception as e:
            print('Error during %s.getMetadata()' % self.__class__.__name__.split('.')[-1], e)
            result = None

        return result

    def getMetadata(self, pmids: list):
        """
        Returns a dict with metadata extracted from PubMed from a PMID

        rettype = {NULL = xml, abstract, medline, uilist, docsum}
        retmode = {xml, text}

        :param pmids: list of PMID to get
        :return: dict with metadata from XML returned
        """
        assert isinstance(pmids, list)

        if not pmids:
            return []

        if len(pmids) > 1:
            pmids = ','.join(pmids)
        else:
            pmids = pmids[0]

        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=' + pmids
        r = self.request(url)

        text = StringIO(r.content.decode('utf-8'))
        tree = etree.parse(text)

        results = []

        for index, article_node in enumerate(tree.xpath('/PubmedArticleSet/PubmedArticle')):
            new_bib = {}

            article = article_node.xpath('MedlineCitation/Article')[0]

            doi = article.xpath('ELocationID[@EIdType="doi"]')
            if doi:
                new_bib['doi'] = doi[0].text

            new_bib['title'] = article.xpath('ArticleTitle')[0].text

            abstract = ""
            for abs_piece in article.xpath('Abstract/AbstractText'):
                if 'Label' in abs_piece.keys():
                    abstract += abs_piece.get('Label') + "\n"

                abstract += abs_piece.text + '\n'
            new_bib['abstract'] = abstract

            authors = []
            for author in article.xpath('AuthorList/Author'):
                new_author = {'given': author.xpath('ForeName')[0].text,
                              'family': author.xpath('LastName')[0].text, }
                authors.append(new_author)

            new_bib['author'] = authorListFromDict(authors)
            if article.xpath('ArticleDate'):
                date_node = article.xpath('ArticleDate')[0]
            elif article_node.xpath('PubmedData/History/PubMedPubDate[@PubStatus="pubmed"]'):
                date_node = article_node.xpath('PubmedData/History/PubMedPubDate[@PubStatus="pubmed"]')[0]

            new_bib['year'] = date_node.xpath('Year')[0].text
            new_bib['month'] = date_node.xpath('Month')[0].text
            new_bib['day'] = date_node.xpath('Day')[0].text

            new_extra = {'pmid': article_node.xpath('MedlineCitation/PMID')[0].text,
                         'x_authors': authors,
                         'language': article.xpath('Language')[0].text}

            new_res = SearchResult(index, new_bib, 'pubmed', new_extra)
            results.append(new_res)

        return results

    def getAlternateIDs(self, pmids: list):
        """
        Gets DOI and PMCID for a list of PMIDs

        :param pmids: list of PMID to resolve
        :return:
        """
        if isinstance(pmids, list):
            if len(pmids) > 1:
                pmids = ','.join([str(p) for p in pmids])
            else:
                pmids = pmids[0]

        res = {}

        r = requests.get(
            'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=my_tool&email=my_email@example.com&ids=' + str(
                pmids))

        text = StringIO(r.content.decode('utf-8'))
        tree = etree.parse(text)
        for record in tree.xpath('/pmcids/record'):
            new_res = {}
            if 'pmcid' in record.keys():
                new_res['pmcid'] = record.get('pmcid')
            if 'doi' in record.keys():
                new_res['doi'] = record.get('doi')
            res[record.get('pmid')] = new_res
        return res

    def enrichWithMetadata(self, paper):
        if not paper.pmid:
            return

        if not paper.doi:
            ids = self.getAlternateIDs(paper.pmid)
            if 'doi' in ids[paper.pmid]:
                paper.doi = ids[paper.pmid]['doi']
            if 'pmcid' in ids[paper.pmid]:
                paper.pmcid = ids[paper.pmid]['pmcid']

        res = self.getMetadata([paper.pmid])[0]

        mergeResultData(paper, res)

        paper.extra_data['done_pubmed'] = True


class arXivSearcher(NiceScraper):
    def search(self, title, identity, max_results=5):
        url = 'http://export.arxiv.org/api/query?search_query=title:{}&start=0&max_results={}'.format(
            urllib.parse.quote(title), max_results)
        r = self.request(url)

        text = BytesIO(r.content)
        tree = etree.parse(text)

        ns_map = {'ns': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}

        results = []
        for index, entry in enumerate(tree.xpath('/ns:feed/ns:entry', namespaces=ns_map)):
            new_bib = {'arxivid': entry.xpath('ns:id', namespaces=ns_map)[0].text.split('/')[-1],
                       'title': entry.xpath('ns:title', namespaces=ns_map)[0].text,
                       'abstract': entry.xpath('ns:summary', namespaces=ns_map)[0].text,
                       }

            published = entry.xpath('ns:published', namespaces=ns_map)[0].text
            match = re.search(r"(\d{4})-(\d{2})-(\d{2})", published)

            new_bib['year'] = match.group(1)
            new_bib['month'] = str(int(match.group(2)))
            new_bib['date'] = str(int(match.group(3)))

            authors = []
            for author in entry.xpath('ns:author', namespaces=ns_map):
                bits = author.xpath('ns:name', namespaces=ns_map)[0].text.split()
                authors.append({'given': bits[0], 'family': bits[-1]})

            new_bib['author'] = authorListFromDict(authors)
            new_extra = {
                'x_authors': authors,
                'ax_main_category': entry.xpath('arxiv:primary_category', namespaces=ns_map)[0].get('term'),

            }

            categories = []
            for cat in entry.xpath('ns:category', namespaces=ns_map):
                categories.append(cat.get('term'))

            new_extra['ax_categories'] = categories

            new_res = SearchResult(index, new_bib, 'arxiv', new_extra)

            for link in entry.xpath('ns:link', namespaces=ns_map):
                if link.get('title') == 'pdf':
                    addUrlIfNew(new_res, link.get('href'), 'pdf', 'arxiv')
                elif 'arxiv.org/abs/' in link.get('href'):
                    addUrlIfNew(new_res, link.get('href'), 'main', 'arxiv')

            results.append(new_res)

        return results


class GScholarMetadata(NiceScraper):
    def getBibtex(self, paper):
        if paper.extra_data.get("url_scholarbib"):
            bib = paper.bib
            url = paper.extra_data.get("url_scholarbib")
            try:
                r = self.request(url)

                # print(r)
                text = r.content.decode('utf-8')
                bib = readBibtexString(text)[0]

            except Exception as e:
                print(e)

            bib['abstract'] = paper.abstract
            for key in ['abstract', 'eprint', 'url']:
                if key in paper.bib:
                    bib[key] = paper.bib[key]
            paper.bib = bib


class SemanticScholarMetadata(NiceScraper):
    def getMetadata(self, paper):
        if not paper.doi:
            raise ValueError('paper has no DOI')

        url = 'https://api.semanticscholar.org/v1/paper/' + paper.doi

        r = self.request(url)
        d = r.json()

        if 'error' in d:
            print("SemanticScholar error:", d['error'])
            return

        for field in ['abstract', 'year', 'venue']:
            if d.get(field):
                paper.bib[field] = str(d[field])

        if d.get('arxivId'):
            paper.arxivid = d['arxivId']

        for topic in d['topics']:
            # we really don't need to store the url, it's just
            # https://www.semanticscholar.org/topic/{topicId}
            del topic['url']

        authors = []
        for author in d['authors']:
            bits = author['name'].split()
            new_author = {'given': bits[0], 'family': bits[-1]}
            if len(bits) > 2:
                new_author['middle'] = " ".join(bits[1:len(bits) - 1])
            authors.append(new_author)

        paper.bib['author'] = authorListFromDict(authors)

        paper.extra_data['ss_topics'] = d['topics']
        paper.extra_data['ss_authors'] = d['authors']
        paper.extra_data['ss_id'] = d['paperId']


crossrefsearcher = CrossrefSearch()
scholarmetadata = GScholarMetadata(basic_delay=0.1)
unpaywallmetadata = UnpaywallMetadata(rate_limit=100000, rate_interval='24h')
pubmedsearcher = PubMedSearch()
arxivsearcher = arXivSearcher()
semanticscholarmetadata = SemanticScholarMetadata()


def enrichAndUpdateMetadata(papers, paperstore, identity):
    successful = []
    unsuccessful = []

    for paper in tqdm(papers, desc='Enriching metadata'):
        try:
            enrichMetadata(paper, identity)
            successful.append(paper)
        except Exception as e:
            print(e)
            unsuccessful.append(paper)

        paperstore.updatePapers([paper])

    return successful, unsuccessful


def enrichMetadata(paper: Paper, identity):
    """
    Tries to retrieve metadata from Crossref and abstract from SemanticScholar for a given paper,
    Google Scholar bib if all else fails

    :param paper: Paper instance
    """
    paper.title = basicTitleCleaning(paper.title)
    original_title = paper.title

    if paper.pmid and not paper.extra_data.get("done_pubmed"):
        pubmedsearcher.enrichWithMetadata(paper)
        paper.extra_data['done_pubmed'] = True

    # if we don't have a DOI, we need to find it on Crossref
    if not paper.doi and not paper.extra_data.get('done_crossref', False):
        crossrefsearcher.matchPaperFromResults(paper, identity)

        if paper.doi:
            new_bib = getBibtextFromDOI(paper.doi)
            paper = mergeResultData(paper,
                                    SearchResult(1, new_bib[0], 'crossref', paper.extra_data))
            paper.extra_data['done_crossref'] = True

    # if we have a DOI and we haven't got the abstract yet
    if paper.doi and not paper.extra_data.get('done_semanticscholar'):
        semanticscholarmetadata.getMetadata(paper)
        paper.extra_data['done_semanticscholar'] = True

    # try PubMed if we still don't have a DOI or PMID
    if not paper.pmid and not paper.extra_data.get('done_pubmed'):
        # if (not paper.doi or not paper.has_full_abstract) and not paper.pmid and not paper.extra_data.get('done_pubmed'):
        if pubmedsearcher.matchPaperFromResults(paper, identity, ok_title_distance=0.4):
            pubmedsearcher.enrichWithMetadata(paper)
            paper.extra_data['done_pubmed'] = True

    # if we don't have an abstract maybe it's on arXiv
    if not paper.has_full_abstract and not paper.extra_data.get('done_arxiv'):
    # if not paper.extra_data.get('done_arxiv'):
        if arxivsearcher.matchPaperFromResults(paper, identity, ok_title_distance=0.35):
            paper.extra_data['done_arxiv'] = True

    # try to get open access links if DOI present and missing PDF link
    if not paper.has_pdf_link and paper.doi and not paper.extra_data.get('done_unpaywall'):
        unpaywallmetadata.getMetadata(paper, identity)
        paper.extra_data['done_unpaywall'] = True

    # if all else has failed but we have a link to Google Scholar bib data, get that
    if not paper.year and paper.extra_data.get('url_scholarbib'):
        scholarmetadata.getBibtex(paper)

    if paper.title != original_title:
        print('Original: %s\nNew: %s' % (original_title, paper.title))
    paper.bib = fixBibData(paper.bib, 1)


def test():
    title = 'NegBio: a high-performance tool for negation and uncertainty detection in radiology reports'

    # res = searchSemanticScholar(title)

    # res = searchCrossref(title)
    # for r in res:
    #     print(json.dumps(r, indent=3))
    pubmedsearcher.search(title, 'dduma@ed.ac.uk')


if __name__ == '__main__':
    test()
