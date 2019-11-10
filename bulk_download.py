from argparse import ArgumentParser

from base.file_download import bulkDownload
from base.general_utils import loadEntriesAndSetUp


def main(conf):
    paperstore, papers_to_add, papers_existing, all_papers = loadEntriesAndSetUp(conf.input, conf.cache, conf.max)

    bulkDownload(all_papers, conf.dir, conf.report_path, do_not_download_just_list=False)


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
