from argparse import ArgumentParser
from base.general_utils import loadEntriesAndSetUp, writeOutputBib
import pandas as pd
from langdetect import detect
from langdetect import DetectorFactory

DetectorFactory.seed = 0
import re


def getPaperText(paper):
    res = paper.title
    abs = paper.bib.get('abstract')
    if abs:
        abstract = paper.bib.get('abstract', '')
        abstract = re.sub(r'[\n\s]+', ' ', abstract)
        abstract = re.sub(r'\s+', ' ', abstract)

        res += " " + abstract
    return res


def isPatent(paper):
    url = paper.bib.get('url', paper.bib.get('eprint'))
    return 'patent' in paper.bib.get('journal', '') or (url and 'patent' in url.lower())


def oneKeywordInText(keywords, text):
    text_lower = text.lower()
    for kw in keywords:
        kw = kw.lower()
        if kw in text_lower:
            return True

    return False


def allKeywordsInText(keywords, text):
    text_lower = text.lower()

    in_text = 0

    for kw in keywords:
        kw = kw.lower()
        if kw in text_lower:
            in_text += 1

    return in_text == len(keywords)


def oneKeywordNotInText(keywords, text):
    text_lower = text.lower()
    for kw in keywords:
        kw = kw.lower()
        if kw not in text_lower:
            return True

    return False


def allKeywordsNotInText(keywords, text):
    text_lower = text.lower()
    not_in_text = 0

    for kw in keywords:
        kw = kw.lower()
        if kw not in text_lower:
            not_in_text += 1

    return not_in_text == len(keywords)


def printReport(df):
    print('Included papers', len(df[df['excluded'] == False]))
    print('Excluded papers', len(df[df['excluded'] == True]))
    print('Excluded because of')
    print('  language', len(df[df['exclude_reason'] == 'language']))
    print('  is a patent', len(df[df['exclude_reason'] == 'is_patent']))
    print('  year out of range', len(df[df['exclude_reason'] == 'year']))
    print('  is a review', len(df[df['exclude_reason'] == 'is_review']))
    print('  using images', len(df[df['exclude_reason'] == 'uses_images']))
    print('  full text not available', len(df[df['exclude_reason'] == 'no_pdf']))
    print('  not radiology', len(df[df['exclude_reason'] == 'not_radiology']))
    print('  not NLP', len(df[df['exclude_reason'] == 'not_nlp']))


def collectStats(papers):
    results = []
    for paper in papers:
        res = {
            # 'id': paper.id,
            'has_year': bool(paper.year),
            'has_title': bool(paper.title),
            # 'authors': paper.authors,
            'has_doi': bool(paper.doi),
            'has_arxivid': bool(paper.arxivid),
            'has_pmid': bool(paper.pmid),
            'has_ssid': bool(paper.extra_data.get('ss_id')),
            'has_valid_id': paper.has_valid_id,
            'has_abstract': paper.has_abstract,
            'has_full_abstract': paper.has_full_abstract,
            'has_pdf': paper.has_pdf_link,
            'not_abstract_but_pdf': not paper.has_abstract and paper.has_pdf
        }
        results.append(res)

    df = pd.DataFrame(results)
    for field in df.columns:
        print(field, len(df[df[field] == True]))
    print()


def filterPapers(papers):
    included = []
    report = []

    for paper in papers:
        record = {
            'title': paper.title,
            # 'year': int(paper.year) if paper.year else None,
            'year': paper.year,
            'authors': paper.authors,
            'venue': paper.venue,
            'abstract': paper.abstract,
            'excluded': False,
            'exclude_reason': None
        }
        accept = True

        text = getPaperText(paper)
        language = paper.extra_data.get('language')

        if not language:
            if len(text) < 62 or text.isupper():
                language = 'en'
            else:
                language = detect(text)

            # if language != 'en':
            #     print(text)
            #     print("Lang:", language)
            #     print()

        language = language.lower()
        record['language'] = language

        lower_text = text.lower()

        if paper.title == "Identifying peripheral arterial disease cases using natural language processing of clinical notes":
            print()

        if not language.startswith('en'):
            record['excluded'] = True
            record['exclude_reason'] = 'language'
            accept = False
        elif isPatent(paper):
            record['excluded'] = True
            record['exclude_reason'] = 'is_patent'
            accept = False
        elif int(paper.bib.get('year', 0)) < 2015:
            record['excluded'] = True
            record['exclude_reason'] = 'year'
            accept = False
        elif oneKeywordInText(['review', 'overview'], paper.title.lower()) or oneKeywordInText(['this review', 'this chapter'], lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'is_review'
            accept = False
        elif oneKeywordInText(['images', 'visual', 'chest x-ray', 'segmentation'], lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'uses_images'
            accept = False
        elif not paper.has_pdf:
            record['excluded'] = True
            record['exclude_reason'] = 'no_pdf'
            accept = False
        elif allKeywordsNotInText(['radiolo', 'imaging report', ' CT', ',CT', ':CT', 'MRI'], lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'not_radiology'
            accept = False
        elif allKeywordsNotInText(
                ['text', 'langu', 'lingu', 'nlp', 'synta', 'embedding', 'information extraction',
                 'text mining', 'words',
                 'deep learning', 'deep neural',
                 'machine learning', 'artificial intelligence', 'document classification', ],
                lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'not_nlp'
            accept = False

        if accept:
            included.append(paper)
        report.append(record)

    df = pd.DataFrame(report, columns=['id', 'year', 'title', 'excluded', 'exclude_reason', 'language', 'abstract'])
    return included, df


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache)

    collectStats(all_papers)
    included, df = filterPapers(all_papers)

    printReport(df)

    df.to_csv(conf.report_path)

    writeOutputBib(included, conf.output)

if __name__ == '__main__':
    parser = ArgumentParser(description='Filter results ')

    parser.add_argument('-i', '--input', type=str,
                        help='Input bib file name')
    parser.add_argument('-o', '--output', type=str,
                        help='Output bib file name')
    parser.add_argument('-r', '--report-path', type=str, default='filter_report.csv',
                        help='Path to output report CSV')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')

    conf = parser.parse_args()

    main(conf)
