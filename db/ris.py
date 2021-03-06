from db.bibtex import fixBibData
from db.ref_utils import parseBibAuthors, authorListFromListOfAuthors
from RISparser import readris

mapping = [
    ('address', 'AD'),
    ('abstract', 'AB'),
    ('doi', 'DO'),
    ('eprint', 'LK'),
    ('editor', 'ED'),
    ('issue', 'IS'),
    ('journal', 'JF'),
    ('publisher', 'PB'),
    ('title', 'TI'),
    ('url', 'UR'),
    ('volume', 'VL'),
]

type_mapping = {
    'inproceedings': 'CONF',
    'article': 'JOUR',
    'thesis': 'THES',
    'book': 'BOOK',
}

reverse_type_mapping = {b: a for a, b in type_mapping.items()}


def exportBibToRIS(entries):
    lines = []
    for entry in entries:
        authors = parseBibAuthors(entry['author'])

        if entry['ENTRYTYPE'].lower() in type_mapping:
            ris_type = type_mapping[entry['ENTRYTYPE'].lower()]
        else:
            ris_type = 'JOUR'

        lines.append('TY  - ' + ris_type)

        for author in authors:
            au_line = 'AU  - %s, %s' % (author['family'], author['given'])
            if author.get('middle'):
                au_line += ' ' + author['middle']
            lines.append(au_line)

        # lines.append('PY  - %s/%s/%s/' % (entry['year'], entry['month'], entry['day']))
        lines.append('PY  - %s' % (entry.get('year', ''),))

        pages = entry.get('pages')
        if pages:
            bits = pages.split('-')

            lines.append('SP  - ' + bits[0])
            lines.append('EP  - ' + bits[-1])

        for eq in mapping:
            if entry.get(eq[0]):
                lines.append(str(eq[1]) + '  - ' + str(entry[eq[0]]))

        lines.append('ER  - ')

    return '\n'.join(lines)


def writeBibToRISFile(entries, filename):
    with open(filename, 'w') as f:
        text = exportBibToRIS(entries)
        f.write(text)


def writeRIS(papers, filename):
    bibs = [paper.bib for paper in papers]
    writeBibToRISFile(bibs, filename)


def readRIS(filename):
    with open(filename, 'r') as f:
        entries = readris(f)

    res = []

    for entry in entries:
        entry['author'] = authorListFromListOfAuthors(entry.get('authors', []))
        if 'authors' in entry:
            del entry['authors']

        new_type = 'article'
        if entry.get('type_of_reference'):
            if entry['type_of_reference'] in reverse_type_mapping:
                new_type = reverse_type_mapping[entry['type_of_reference']]

        entry['ENTRYTYPE'] = new_type
        entry = fixBibData(entry, 0)
        res.append(entry)

    return res
