from db.data import PaperStore, Paper

from argparse import ArgumentParser
from db.bibtex import read_bibtex_file, parseBibAuthors, write_bibtex
from search import getSearchResultsFromBib

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
    print('  is a review', len(df[df['exclude_reason'] == 'is_review']))
    print('  using images', len(df[df['exclude_reason'] == 'uses_images']))
    print('  not radiology', len(df[df['exclude_reason'] == 'not_radiology']))
    print('  not NLP', len(df[df['exclude_reason'] == 'not_nlp']))
    print('  is a patent', len(df[df['exclude_reason'] == 'is_patent']))


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
        url = paper.bib.get('url', paper.bib.get('eprint'))

        if not language:
            if len(text) < 62 or text.isupper():
                language = 'en'
            else:
                language = detect(text)

            if language != 'en':
                print(text)
                print("Lang:", language)
                print()

        language = language.lower()
        record['language'] = language

        lower_text = text.lower()

        if not language.startswith('en'):
            record['excluded'] = True
            record['exclude_reason'] = 'language'
            accept = False
        elif int(paper.bib.get('year', 0)) < 2015:
            record['excluded'] = True
            record['exclude_reason'] = 'year'
            accept = False
        elif 'review' in paper.title.lower():
            record['excluded'] = True
            record['exclude_reason'] = 'is_review'
            accept = False
        elif oneKeywordInText(['image', 'visual', 'chest x-ray'], lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'uses_images'
            accept = False
        elif oneKeywordNotInText(['radiolo'], lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'not_radiology'
            accept = False
        elif allKeywordsNotInText(
                ['text', 'langu', 'lingu', 'nlp', 'synta', 'embedding', 'information extraction', 'deep learning',
                 'deep neural', 'machine learning', 'artificial intelligence', 'document classification', 'supervised'],
                lower_text):
            record['excluded'] = True
            record['exclude_reason'] = 'not_nlp'
            accept = False
        elif url and 'patent' in url.lower():
            record['excluded'] = True
            record['exclude_reason'] = 'is_patent'
            accept = False

        if accept:
            included.append(paper)
        report.append(record)

    df = pd.DataFrame(report, columns=['id', 'year', 'title', 'excluded', 'exclude_reason', 'language', 'abstract'])
    return included, df


def main(conf):
    if conf.cache:
        paperstore = PaperStore()
    else:
        paperstore = None

    bib_entries = read_bibtex_file(conf.input)
    results = getSearchResultsFromBib(bib_entries)

    if paperstore:
        found, missing = paperstore.matchResultsWithPapers(results)
    else:
        found = []
        missing = results

    papers_missing = [Paper(res.bib, res.extra_data) for res in missing]
    papers_found = [res.paper for res in found]

    all_papers = papers_found + papers_missing

    included, df = filterPapers(all_papers)

    printReport(df)

    df.to_csv(conf.report_path)
    write_bibtex(included, conf.output)


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
