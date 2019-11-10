import pandas as pd
import re
from zipfile import ZipFile
from itertools import combinations
import numpy as np
from io import BytesIO


def parseInclusion(text):
    reviewers = {}
    exclusion_reasons = []
    labels = []

    for match in re.findall('\"([\w\s]+?)\"=>\"([\w\s]+?)\"', text):
        reviewers[match[0]] = match[1]

        if match[1].lower() == 'excluded':
            exclusion_reasons = []
            match = re.search('RAYYAN-EXCLUSION-REASONS: ([\w\s,]+)', text)
            if match:
                exclusion_reasons.extend(match.group(1).split(','))

        match = re.search('RAYYAN-LABELS: ([\w\s,]+)', text)
        if match:
            labels.extend(match.group(1).split(','))

    return reviewers, exclusion_reasons, labels


def loadRayyan(filename):
    with ZipFile(filename, 'r') as zip:
        data = zip.read('articles.csv')
        data = BytesIO(data)
        df = pd.read_csv(data)

    column_labels = []
    column_exclusion_reasons = []
    column_reviewers = []
    all_unique_reviewers = set()

    for index, row in df.iterrows():
        reviewers, exclusion_reasons, labels = parseInclusion(row['notes'])
        column_labels.append(labels)
        column_exclusion_reasons.append(exclusion_reasons)
        column_reviewers.append(reviewers)

        all_unique_reviewers = all_unique_reviewers | set(reviewers.keys())

    reviewer_titles = []

    for reviewer in all_unique_reviewers:
        reviewer_column_title = 'reviewer_' + reviewer
        reviewer_titles.append('reviewer_' + reviewer)
        reviewer_column_data = [r.get(reviewer) for r in column_reviewers]
        df.insert(10, reviewer_column_title, reviewer_column_data)

    df.insert(11, 'exclusion_reasons', column_exclusion_reasons)
    df.insert(12, 'labels', column_labels)

    included_counts = []

    for index, row in df.iterrows():
        included_count = 0
        for reviewer in reviewer_titles:
            if row.get(reviewer) == 'Included':
                included_count += 1
        included_counts.append(included_count)

    df.insert(13, 'included_count', included_counts)

    return df


def computeOverlap(df):
    a = df.values
    d = {(i, j): np.mean(a[:, i] == a[:, j]) for i, j in combinations(range(a.shape[1]), 2)}

    res, c, vals = np.zeros((a.shape[1], a.shape[1])), \
                   list(map(list, zip(*d.keys()))), list(d.values())

    res[c[0], c[1]] = vals

    return pd.DataFrame(res, columns=df.columns, index=df.columns)


def computeOverlap3(df):
    Yourdf = pd.DataFrame(columns=df.columns, index=df.columns)
    Yourdf = Yourdf.stack(dropna=False).to_frame().apply(lambda x: (df[x.name[0]] == df[x.name[1]]).mean(),
                                                         axis=1).unstack()
    Yourdf = Yourdf.where(np.triu(np.ones(Yourdf.shape), 1).astype(np.bool))
    return Yourdf


# def computeOverlap(df):
#     pd.crosstab(df.columns, df.columns, )

def filterDFForInclusion(df, reviewer_columns, screen='Included'):
    df2 = df.copy()

    rows_to_include = []

    for index, row in df2.iterrows():
        for reviewer in reviewer_columns:
            if row.get(reviewer) == screen:
                rows_to_include.append(index)
                break
    return df2.iloc[rows_to_include]


def computeReviewerOverlap(df):
    reviewer_columns = [c for c in df.columns if c.startswith('reviewer_')]
    df = df[reviewer_columns]

    df['reviewer_agrivas'][df['reviewer_agrivas'] == 'Maybe'] = 'Included'
    df['reviewer_Daniel'][df['reviewer_Daniel'] == 'Maybe'] = 'Included'

    res_df = computeOverlap(df)
    print('Total overlap')
    print(res_df)

    print('\nIncluded overlap')
    print(computeOverlap(filterDFForInclusion(df, reviewer_columns, 'Included')))

    print('\nExcluded overlap')
    print(computeOverlap(filterDFForInclusion(df, reviewer_columns, 'Excluded')))


def selectPapersToReview(df, min_agreement=1):
    return df[df['included_count'] >= min_agreement]


def test():
    df = loadRayyan('/Users/masterman/Downloads/b1c75bc72aef9d8e_45981_89617_2019-11-10_20-08-12.zip')
    computeReviewerOverlap(df)
    print(len(selectPapersToReview(df, 1)))


if __name__ == '__main__':
    test()
