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
        df.insert(len(df.columns), reviewer_column_title, reviewer_column_data)

    df.insert(len(df.columns), 'exclusion_reasons', column_exclusion_reasons)
    df.insert(len(df.columns), 'labels', column_labels)

    for index, row in df.iterrows():
        match = re.search(r'PY - (\d+)\/+?', row['authors'])
        if match:
            df.at[index, 'year'] = match.group(1)
            df.at[index, 'authors'] = df.iloc[index]['authors'][:match.start()]

    included_counts = []
    excluded_counts = []
    maybe_counts = []

    for index, row in df.iterrows():
        included_count = 0
        excluded_count = 0
        maybe_count = 0
        for reviewer in reviewer_titles:
            if row.get(reviewer) == 'Included':
                included_count += 1
            elif row.get(reviewer) == 'Excluded':
                excluded_count += 1
            elif row.get(reviewer) == 'Maybe':
                maybe_count += 1
        included_counts.append(included_count)
        excluded_counts.append(excluded_count)
        maybe_counts.append(maybe_count)

    df.insert(len(df.columns), 'included_count', included_counts)
    df.insert(len(df.columns), 'excluded_count', excluded_counts)
    df.insert(len(df.columns), 'maybe_count', maybe_counts)

    return df


def computeOverlap(df):
    reviewer_columns = [c for c in df.columns if c.startswith('reviewer_')]
    df = df[reviewer_columns]

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

def filterDFForInclusion(df, screen='Included'):
    if screen == 'Included':
        return df[df['included_count'] > 0]
    elif screen == 'Excluded':
        return df[df['excluded_count'] > 0]
    elif screen == 'Maybe':
        return df[df['maybe_count'] > 0]


def computeReviewerOverlap(df):
    # df.at[df['reviewer_agrivas'] == 'Maybe', 'reviewer_agrivas'] = 'Included'
    # df.at[df['reviewer_Daniel'] == 'Maybe', 'reviewer_Daniel'] = 'Included'

    print('Total overlap')
    print(computeOverlap(df))

    print('\nIncluded overlap')
    print(computeOverlap(filterDFForInclusion(df, 'Included')))

    print('\nExcluded overlap')
    print(computeOverlap(filterDFForInclusion(df, 'Excluded')))


def selectPapersToReview(df, min_agreement=1):
    res = df[df['included_count'] >= min_agreement]
    res.drop(['key', 'issn', 'volume', 'pages', 'issue', 'language', 'location', 'notes'], axis=1, inplace=True)
    return res
