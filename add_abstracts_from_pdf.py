import os
from base.general_utils import loadEntriesAndSetUp
from base.file_download import bulkDownload
from base.pdf_extract import getAbstractFromPDF
from argparse import ArgumentParser
from db.bibtex import writeBibtex


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache, conf.max)

    no_abstract_but_pdf = [p for p in all_papers if not p.has_abstract and p.has_pdf]
    bulkDownload(no_abstract_but_pdf, conf.dir, 'results_report.csv', do_not_download_just_list=True)

    successful = []
    for paper in no_abstract_but_pdf:
        if not os.path.exists(paper.pdf_filename):
            continue

        abstract = getAbstractFromPDF(paper.pdf_filename)

        if abstract:
            print(abstract)
            paper.bib['abstract'] = abstract
            paperstore.updatePapers([paper])
            successful.append(paper)

    print('Generated',len(successful), 'new abstracts')
    writeBibtex(successful, conf.output)


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Tries to download the PDF for each file and extract the abstract from it')

    parser.add_argument('-i', '--input', type=str,
                        help='Input Bibtex file with the previously cached search results')
    parser.add_argument('-o', '--output', type=str,
                        help='Output Bbibex file into which to update the new, augmented results')
    parser.add_argument('-d', '--dir', type=str,
                        help='Directory where to store the downloaded PDFs')
    parser.add_argument('-m', '--max', type=int, default=100,
                        help='Maximum number of results to process')
    parser.add_argument('-em', '--email', type=str,
                        help='Email to serve as identity to API endpoints')
    parser.add_argument('-c', '--cache', type=bool, default=True,
                        help='Use local cache for results')

    conf = parser.parse_args()

    main(conf)
