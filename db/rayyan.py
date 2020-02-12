import pandas as pd
import re
from zipfile import ZipFile
from itertools import combinations
import numpy as np
from io import BytesIO


DROP_FIELDS = ['key',
               'issn',
               'volume',
               'pages',
               'issue',
               'language',
               'location',
               'notes',
               'journal',
               'day',
               'month',
               'maybe_count']


def parseInclusion(text):
    reviewers = {}
    exclusion_reasons = []
    labels = []

    for match in re.findall('\"([\w\s\.]+?)\"=>\"([\w\s]+?)\"', text):
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


# def compute_agreement(vals, vala, valb):
#     # Use to compute TP/TN/FP/FN
#     d = {(i, j): np.sum((vals[:, i] == vala) & (vals[:, j] == valb))
#          for i, j in combinations(range(vals.shape[1]), 2)}
#     df, c, vals = np.zeros((vals.shape[1], vals.shape[1])), \
#                       list(map(list, zip(*d.keys()))), list(d.values())
#     df[c[0], c[1]] = vals
#     return df


# def computeStats(df):
#     reviewer_columns = [c for c in df.columns if c.startswith('reviewer_')]
#     df = df[reviewer_columns]
#
#     a = df.values
#     TP = compute_agreement(a, 'Included', 'Included')
#     TN = compute_agreement(a, 'Excluded', 'Excluded')
#     FP = compute_agreement(a, 'Included', 'Excluded')
#     FN = compute_agreement(a, 'Excluded', 'Included')
#
#     print('TP', TP)
#     print('TN', TN)
#     print('FP', FP)
#     print('FN', FN)
#
#     print('Total', TP+TN+FP+FN)


def computeFleiss(df):
    reviewer_columns = [c for c in df.columns if c.startswith('reviewer_')]
    df = df[reviewer_columns]

    a = df.values
    classes = set(a.ravel())

    # rows are instances/examples
    # columns are classes
    # values are number of annotators assigned instance to class
    # so sum of each rows = num annotators
    P = np.hstack([np.sum(a == c, axis=1, keepdims=True)
                  for c in classes])
    # Below is wikipedia example - expected kappa: 0.210
    # P = np.array([[0, 0, 0, 0, 14],
    #               [0, 2, 6, 4, 2],
    #               [0, 0, 3, 5, 6],
    #               [0, 3, 9, 2, 0],
    #               [2, 2, 8, 1, 1],
    #               [7, 7, 0, 0, 0],
    #               [3, 2, 6, 3, 0],
    #               [2, 5, 3, 2, 2],
    #               [6, 5, 2, 1, 0],
    #               [0, 2, 2, 3, 7]])

    # N: number examples, k = number classes
    N, k = P.shape
    # n: number of annotators
    n = P.sum(axis=1)[0]
    assert(np.all(P.sum(axis=1) == n))
    # P_j..
    pee_jays = np.sum(P, axis=0) / (N * n)
    assert np.isclose(pee_jays.sum(), 1.), 'P_j calculation is wrong'

    # P_is
    pee_eye = np.sum(P * (P - 1), axis=1) / (n * (n - 1))

    pee_tilde = pee_eye.mean()
    pee_ee = np.sum(pee_jays ** 2)

    # Fleiss' kappa
    fleiss = (pee_tilde - pee_ee) / (1 - pee_ee)
    return fleiss


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
    print("Fleiss' kappa: %.2f" % computeFleiss(df))

    print('\nIncluded overlap')
    print(computeOverlap(filterDFForInclusion(df, 'Included')))

    print('\nExcluded overlap')
    print(computeOverlap(filterDFForInclusion(df, 'Excluded')))


def selectPapersToReview(df, min_agreement=1):
    res = df[df['included_count'] >= min_agreement]
    res.drop(DROP_FIELDS, axis=1, inplace=True)
    return res


def selectPapersToFilter(df, include_count, exclude_count):
    res = df[(df['included_count'] == include_count) & (df['excluded_count'] == exclude_count)]
    res.drop(DROP_FIELDS, axis=1, inplace=True)
    return res
