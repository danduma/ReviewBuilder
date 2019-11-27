import pandas as pd


def readCSVFile(filename):
    df = pd.read_csv(filename)
    return df.to_dict(orient='records')
