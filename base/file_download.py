import os
from multiprocessing.pool import ThreadPool

import pandas as pd
import requests

from db.ref_utils import parseBibAuthors, isPDFURL


def fetch_url(entry):
    result = {'id': entry['id'],
              'file_exists': False,
              'return_code': None}

    if not os.path.exists(entry['filename']):
        print("Get %s - %s" % (entry['id'][:30], entry['url']))
        try:
            r = requests.get(entry['url'], stream=True)
            result['return_code'] = r.status_code
            if r.status_code == 200:
                with open(entry['filename'], 'wb') as f:
                    for chunk in r:
                        f.write(chunk)
        except Exception as e:
            print(e.__class__.__name__, e)
            result['return_code'] = 'TooManyRedirects'

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


def bulkDownload(papers, root_dir, report_path, do_not_download_just_list=False):
    root_dir = os.path.abspath(root_dir)

    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    download_tasks = []

    for paper in papers:
        # if not paper.year:
        #     print("missing year", paper)

        filename = os.path.join(root_dir, generateFilename(paper)) + '.pdf'
        paper.pdf_filename = filename

        task_record = {'id': paper.id,
                       'doi': paper.doi,
                       'filename': filename,
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

    if do_not_download_just_list:
        return

    results = ThreadPool(8).imap_unordered(fetch_url, download_tasks)

    df = pd.DataFrame(results)
    df.to_csv(report_path)
