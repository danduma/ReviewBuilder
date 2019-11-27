from argparse import ArgumentParser

from db.data import Paper
from db.ref_utils import normalizeTitle
from base.general_utils import readInputBib, writeOutputBib


def merge_two_dicts(x, y):
    z = x.copy()  # start with x's keys and values
    z.update(y)  # modifies z with y's keys and values & returns None
    return z


def buildHashTable(bib):
    res = {}
    for entry in bib:
        norm_title = normalizeTitle(entry['title'])
        res[norm_title] = entry
    return res


def set_sub(a, b):
    res = set(a.keys()) - set(b.keys())
    res_list = [value for key, value in a.items() if key in res]
    return [Paper(x, {}) for x in res_list]


def set_intersect(a, b):
    res = set(a.keys()) & set(b.keys())
    res_list = [value for key, value in a.items() if key in res]
    return [Paper(x, {}) for x in res_list]


def set_union(a, b):
    res = set(a.keys()) | set(b.keys())
    full_dict = merge_two_dicts(a, b)
    res_list = [value for key, value in full_dict.items() if key in res]
    return [Paper(x, {}) for x in res_list]


def main(conf):
    bib1 = readInputBib(conf.input1)
    bib2 = readInputBib(conf.input2)

    s1 = buildHashTable(bib1)
    s2 = buildHashTable(bib2)

    list_sub1 = set_sub(s1, s2)
    list_sub2 = set_sub(s2, s1)
    list_and = set_intersect(s1, s2)
    list_or = set_union(s1, s2)

    writeOutputBib(list_sub1, conf.output + '_a-b.bib')
    writeOutputBib(list_sub2, conf.output + '_b-a.bib')
    writeOutputBib(list_and, conf.output + '_a_and_b.bib')
    writeOutputBib(list_or, conf.output + '_a_or_b.bib')

    print('A - B:', len(list_sub1))
    print('B - A:', len(list_sub2))
    print('B & A:', len(list_and))
    print('B | A:', len(list_or))


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Compute diff between bib lists. Takes 2 lists of bib entries, an "old" and a "new" one. It outputs 3 lists: 1. papers only found in input1 2. papers only in input 2 3. papers in both')

    parser.add_argument('-i1', '--input1', type=str,
                        help='Input bib/RIS/CSV file name (older)')
    parser.add_argument('-i2', '--input2', type=str,
                        help='Input bib/RIS/CSV file name (newer)')
    parser.add_argument('-o', '--output', type=str,
                        help='Beginning of output filename')

    conf = parser.parse_args()

    main(conf)
