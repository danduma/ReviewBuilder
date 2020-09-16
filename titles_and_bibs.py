import os
import argparse
import pandas as pd

from db.data import PaperStore
from db.rayyan import loadRayyan, computeReviewerOverlap
from db.rayyan import selectPapersToReview


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Gather metadata such as'
                                     'reason for exclusion + bib information')
    parser.add_argument('-o', '--outfile', type=str,
                        help='Output pandas csv filename')

    args = parser.parse_args()

    paper_store = PaperStore()

    # sysreview articles
    sysreviewdf = pd.read_excel(os.path.join('reasons_for_exclusion', 'sysreview-15-09-2020.xlsx'))

    bibs = []

    # Add bib files to the dataframe for those that have a bib entry
    for title in sysreviewdf.title:
        paper = paper_store.findPapersByTitle(title)
        if paper:
            bibs.append(paper[0].bib)
        else:
            bibs.append(None)

    sysreviewdf['bib'] = bibs

    # Only keep titles and bibs
    sysreviewdf = sysreviewdf[['title', 'bib']]

    print(sysreviewdf)
    print('Writing results to %s' % args.outfile)
    sysreviewdf.to_csv(args.outfile, index=False)

    # notes = joined.notes.str.split('|').str[1]
    # notes = notes.str.split(':').str[-1]
    # notes = notes.str.split(',')
    # print(notes.isna().sum())
    #
    # # Extract reasons from the notes section
    # pass
