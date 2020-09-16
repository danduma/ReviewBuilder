import os
import argparse
import pandas as pd

from itertools import chain
from collections import Counter

from db.data import PaperStore
from db.rayyan import loadRayyan, computeReviewerOverlap
from db.rayyan import selectPapersToReview


EXCLUSION_PRECEDENCE = [
        'foreign language',
        'is review',
        'uses images',
        'not radiology',
        'not nlp',
        'wrong publication type',
        'not peer reviewed',
        'cannot find fulltext',
        'conference',
        'too short'
        ]


def fix_reasons(r):
    if r == 'not radiology report':
        return 'not radiology'
    if r == 'not radiology reports':
        return 'not radiology'
    if r == 'review':
        return 'is review'
    if r == 'with_images':
        return 'uses images'
    if '_' in r:
        return r.replace('_', ' ')
    return r.strip()


def get_main_reason(reasons):
    reasons = set(map(fix_reasons, reasons))
    for r in EXCLUSION_PRECEDENCE:
        if r in reasons:
            return r
    print(reasons)
    return None


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Gather metadata such as'
                                     'reason for exclusion + bib information')

    args = parser.parse_args()

    paper_store = PaperStore()

    columns = ['title', 'abstract', 'authors', 'url']

    # 220 articles - original query
    querydf = loadRayyan(os.path.join('reasons_for_exclusion', 'rayyan-old-query.zip'))
    # Include all
    querydf = selectPapersToReview(querydf, 0)
    querydf['rayyan_source'] = 'old_query'

    # 397 articles, follow up snowballing and new query
    snowdf = loadRayyan(os.path.join('reasons_for_exclusion', 'rayyan-snowball.zip'))
    # Include all
    snowdf = selectPapersToReview(snowdf, 0)
    snowdf['rayyan_source'] = 'snowball'

    # sysreview articles
    sysreviewdf = pd.read_excel(os.path.join('reasons_for_exclusion', 'sysreview-15-09-2020.xlsx'))
    sysreviewdf['rayyan_source'] = 'combined'
    # Only keep columns we care about
    sysreviewdf = sysreviewdf[columns]
    # The last paper was added by Hang
    sysreviewdf = sysreviewdf.head(274)

    # Join on title - unsure if there is a better join to do

    joined = pd.concat([querydf, snowdf], ignore_index=True, sort=True)
    joined['lower_title'] = joined['title'].str.strip().str.lower()
    # Keep the snowballing entry if duplicate exists
    joined = joined.drop_duplicates(subset='lower_title', keep='last')

    joined = pd.concat([sysreviewdf, joined], ignore_index=True, sort=True)
    joined['lower_title'] = joined['title'].str.strip().str.lower()

    # Drop all duplicates (hence only keep entries that didn't make
    # it past Rayyan filtering)
    joined = joined.drop_duplicates(subset='lower_title', keep=False)

    joined = joined.reset_index(drop=True)
    del joined['lower_title']

    print(joined)

    possible_exclusion_reasons = set(map(fix_reasons, chain(*joined['exclusion_reasons'].tolist())))
    print('Possible exclusion reasons')
    print(possible_exclusion_reasons)

    exclusion_reasons = joined['exclusion_reasons']

    main_reasons = [get_main_reason(r) for r in exclusion_reasons]
    counts = Counter(main_reasons)
    print()
    for k, v in counts.most_common():
        print('%s: %d' % (k.ljust(25), v))
    print()
    print('Excluded %d articles' % sum(counts.values()))
