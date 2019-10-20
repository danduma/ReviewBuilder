from argparse import ArgumentParser
from db.ref_utils import isPDFURL, parseBibAuthors
from base.general_utils import loadEntriesAndSetUp

from multiprocessing.pool import ThreadPool
import os
import requests
import pandas as pd


def fetch_url(entry):
    result = {'id': entry['id'],
              'file_exists': False,
              'return_code': None}

    if not os.path.exists(entry['filename']):
        print("Get %s - %s" % (entry['id'][:30], entry['url']))
        r = requests.get(entry['url'], stream=True)
        if r.status_code == 200:
            with open(entry['filename'], 'wb') as f:
                for chunk in r:
                    f.write(chunk)

        result['return_code'] = r.status_code
    else:
        result['file_exists'] = True

    return result


def generateFilename(paper):
    res = ''
    authors = parseBibAuthors(paper.authors)
    if not authors:
        print(paper.authors)
        print()

    if authors and authors[0].get('family'):
        res += authors[0]['family'] + ' '
    if paper.year:
        res += '(%s)' % paper.year

    if len(res) > 0:
        res += ' - '
    res += paper.norm_title.title()
    return res


def bulkDownload(papers, root_dir, report_path):
    root_dir = os.path.abspath(root_dir)

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    download_tasks = []

    for paper in papers:
        if not paper.year:
            print("missing year", paper)
        task_record = {'id': paper.id,
                       'doi': paper.doi,
                       'filename': os.path.join(root_dir, generateFilename(paper)) + '.pdf',
                       'abstract': paper.abstract
                       }
        url = None
        url_source = None

        for url_rec in paper.extra_data.get('urls', []):
            if url_rec['type'] == 'pdf':
                url = url_rec['url']
                url_source = url_rec['source']
                break

        if not url:
            if paper.bib.get('eprint'):
                url = paper.bib['eprint']
                url_source = 'search'
            elif paper.bib.get('url') and isPDFURL(paper.bib['url']):
                url = paper.bib['url']
                url_source = 'search'

        if url:
            task_record['url'] = url
            task_record['url_source'] = url_source
            download_tasks.append(task_record)
        else:
            print(paper.extra_data)
            print(paper.bib)
            print()


    df = pd.DataFrame(download_tasks)
    df.to_csv('download_tasks.csv')

    return

    results = ThreadPool(8).imap_unordered(fetch_url, download_tasks)

    df = pd.DataFrame(results)
    df.to_csv(report_path)


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache, conf.max)

    bulkDownload(all_papers, conf.dir, conf.report_path)


if __name__ == '__main__':
    parser = ArgumentParser(description='Filter results ')

    parser.add_argument('-i', '--input', type=str,
                        help='Input bib file name')
    parser.add_argument('-d', '--dir', type=str,
                        help='Directory where to store the output')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')
    parser.add_argument('-m', '--max', type=int, default=100,
                        help='Maximum number of results to process')
    parser.add_argument('-r', '--report-path', type=str, default='results_report.csv',
                        help='Path to CSV file with a download report')

    conf = parser.parse_args()

    main(conf)
