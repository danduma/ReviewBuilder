from argparse import ArgumentParser
from db.rayyan import loadRayyan, computeReviewerOverlap, selectPapersToReview


def main(conf):
    df = loadRayyan(conf.input)
    computeReviewerOverlap(df)
    to_review = selectPapersToReview(df, conf.min_votes)
    print('\nTotal selected for review',len(to_review))
    to_review.to_csv(conf.output)


if __name__ == '__main__':
    parser = ArgumentParser(description='Filter results ')

    parser.add_argument('-i', '--input', type=str,
                        help='Input .zip file downloaded from Rayyan')
    parser.add_argument('-o', '--output', type=str,
                        help='Path to output report CSV')
    parser.add_argument('-v', '--min-votes', type=int, default=1,
                        help='Minimum votes for inclusion')

    conf = parser.parse_args()

    main(conf)
