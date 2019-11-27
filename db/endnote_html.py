import re
from db.ref_utils import isPDFURL

mapping = [
    # ('Reference Type: ', 'ENTRYTYPE'),
    ('Title', 'title'),
    ('Journal', 'journal'),
    ('DOI', 'doi'),
    ('Author Address', 'address'),
    ('Author', 'author'),
    ('volume', 'VL'),
]

type_mapping = {
    'Journal Article': 'article',
    'Thesis': 'thesis',
    'Book': 'book',
}


def loadRefsFromHTML(filename):
    with open(filename) as f:
        html = f.read()

    html = html[html.find('<body>') + 6:]
    # html = re.sub('.+<body>', '', html, flags=re.DOTALL)
    entries = re.split('(<p>\n<p>\n<p>)', html)
    res = []

    for entry in entries:
        lines = entry.split('\n')
        new_bib = {}

        for line in lines:
            match = re.search('<b>Reference Type: <\/b> (.+?)<p>', line)
            if match:
                if match.group(1) in type_mapping:
                    new_bib['ENTRYTYPE'] = type_mapping[match.group(1)]
                else:
                    new_bib['ENTRYTYPE'] = 'article'

            for bib_map in mapping:
                match = re.search('<b>' + bib_map[0] + ':<\/b> (.+?)<p>', line)
                if match:
                    new_bib[bib_map[1]] = match.group(1)

        for match in re.finditer('<A HREF="(.+?)">', entry):
            if isPDFURL(match.group(1)):
                new_bib['eprint'] = match.group(1)
            else:
                new_bib['url'] = match.group(1)

        res.append(new_bib)

    return res
