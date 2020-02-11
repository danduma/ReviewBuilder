from argparse import ArgumentParser
from db.rayyan import loadRayyan, computeReviewerOverlap
from db.rayyan import selectPapersToReview, selectPapersToFilter


def main(conf):
    df = loadRayyan(conf.input)
    computeReviewerOverlap(df)
    # If we want exact include/exclude - call filter
    if (conf.num_included, conf.num_excluded) != (None, None):
        to_filter = selectPapersToFilter(df,
                                         include_count=conf.num_included,
                                         exclude_count=conf.num_excluded)
        print('\nTotal selected for filtering', len(to_filter))
        to_filter.to_csv(conf.output)
    else:
        to_review = selectPapersToReview(df, conf.min_votes)
        print('\nTotal selected for review', len(to_review))
        to_review.to_csv(conf.output)


if __name__ == '__main__':
    parser = ArgumentParser(description='Filter results ')

    parser.add_argument('-i', '--input', type=str,
                        help='Input .zip file downloaded from Rayyan')
    parser.add_argument('-o', '--output', type=str,
                        help='Path to output report CSV')
    parser.add_argument('-v', '--min-votes', type=int, default=1,
                        help='Minimum votes for inclusion')
    parser.add_argument('--num_included', type=int,
                        help='Exact number of inclusion votes')
    parser.add_argument('--num_excluded', type=int,
                        help='Exact number of exclusion votes')

    conf = parser.parse_args()

    main(conf)
