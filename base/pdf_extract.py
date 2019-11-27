import os
import tika
import enchant

d1 = enchant.Dict("en_US")
d2 = enchant.Dict("en_UK")

import re

if not os.environ.get('TIKA_PATH'):
    os.environ['TIKA_PATH'] = '~/'

tika.initVM()
from tika import parser


def dehyphenate(text):
    """
    Removes hyphens from text intelligently, checking plausible spelling

    :param text: hyphenated text
    :return: text: de-hyphenated text
    """

    def rep_func(match):
        full_word = match.group(1) + match.group(2)
        if d1.check(full_word) or d2.check(full_word):
            return full_word
        else:
            return match.group(1) + '-' + match.group(2)

    text = re.sub('(\w+)-\n(\w+)', rep_func, text)
    return text


def cleanUpTikaText(text):
    text = re.sub('\n+', '\n', text)
    return text


def findHeaders(strings, text, default):
    str_start = -1

    for str_string in strings:
        str_start = text.find(str_string)
        if str_start != -1:
            break

    if str_start == -1:
        str_start = default

    return str_start


# def getAbstract(text):
#     abs_start = findHeaders(['Abstract', 'ABSTRACT'], text, 0)
#     abs_end = findHeaders(["Keywords:", "Keywords :", "KEYWORDS:", 'Related Work', 'Previous Work'], text[abs_start:],
#                           len(text))
#
#     abstract = text[abs_start:abs_end]
#     return abstract

regex_abstract = re.compile('(^Abstract[\:\—\-\s\n]*.+?)^(\d*\.?\s*Introduction|Keywords\s*\:?|Previous work)',
                            re.MULTILINE | re.IGNORECASE | re.DOTALL)

regex_summary = re.compile(
    '(^(Abstract|Summary)\s*\:?\n.+?)^(\d*\.?\s*Introduction|Keywords\s*\:?|Previous work|Table of contents)',
    re.MULTILINE | re.IGNORECASE | re.DOTALL)

regex_thesis = re.compile('I.+?declare that.+?(dissertation|thesis)', re.MULTILINE | re.DOTALL)


def getAbstractFromPDF(filename):
    parsed = readPDF(filename)

    if parsed.get('error'):
        print(parsed['error'])
        return None

    if parsed.get('status', 200) == 422:
        print('Tika:: Unprocessable entity', filename)
        return None

    text = parsed['content']
    if not text:
        print('Tika:: No text in file', filename)
        return None

    text = cleanUpTikaText(text)

    if regex_thesis.search(text):
        match = regex_summary.search(text)
    else:
        match = regex_abstract.search(text)

    if match:
        abstract = match.group(1)
    else:
        print('[[[[[[Could not find the abstract]]]]]]')
        print(text[:1000])
        print('\n\n')
        return None

    abstract = dehyphenate(abstract)
    abstract = cleanUpTikaText(abstract)

    return abstract


def readPDF(filename, to_xml=False):
    try:
        parsed = parser.from_file(filename, xmlContent=to_xml)
    except UnicodeEncodeError as e:
        print(e.__class__.__name__, e)
        return {'error': e.__class__.__name__ + ': ' + e.__str__()}
    return parsed


def getStructuredArticle(xml):
    pass


def test():
    parsed = readPDF(
        '/Users/masterman/Downloads/Towards dataset creation and establishing baselines for sentence-level neural clinical paraphrase generation and simplification.pdf',
        to_xml=True)
    print(parsed['content'])


def test2():
    parsed = readPDF(
        '/Users/masterman/Downloads/Towards dataset creation and establishing baselines for sentence-level neural clinical paraphrase generation and simplification.pdf',
        to_xml=False)
    full_text = cleanUpTikaText(parsed['content'])
    abstract = getAbstractFromPDF(full_text)
    clean_abstract = dehyphenate(abstract)
    print(clean_abstract)
    print()


if __name__ == '__main__':
    test()
