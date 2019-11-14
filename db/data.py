import sqlite3
import os, re, json
import pandas as pd
import bibtexparser

from strsimpy import NormalizedLevenshtein

stopwords = set(["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself",
                 "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its",
                 "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this",
                 "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has",
                 "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or",
                 "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between",
                 "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down",
                 "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there",
                 "when", "where", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"])

from db.bibtex import generateUniqueID
from db.ref_utils import parseBibAuthors, normalizeTitle

current_dir = os.path.dirname(os.path.realpath(__file__))

CACHE_FILE = os.path.join(current_dir, "papers.sqlite")


class Paper:
    """
    A Paper consists of 2 dicts: .bib and .extra_data
    - .bib is simply a bibtex dict
    - .extra_data stores everything else we can't properly store in a BibTeX file
    """

    def __init__(self, bib: dict = None, extra_data: dict = None):
        self.bib = bib
        self.extra_data = extra_data

        for field in bib:
            if bib[field] is None:
                bib[field] = ''

    @classmethod
    def fromRecord(cls, paper_record):
        res = Paper(json.loads(paper_record["bib"]),
                    json.loads(paper_record["extra_data"]))

        res.pmid = paper_record["pmid"]
        res.scholarid = paper_record["scholarid"]
        res.arxivid = paper_record["arxivid"]
        return res

    @property
    def id(self):
        return generateUniqueID(self)

    @property
    def doi(self):
        return self.bib.get("doi")

    @doi.setter
    def doi(self, doi):
        self.bib["doi"] = doi

    @property
    def arxivid(self):
        return self.extra_data.get("arxivid")

    @arxivid.setter
    def arxivid(self, arxivid):
        self.extra_data["arxivid"] = arxivid

    @property
    def pmid(self):
        return self.extra_data.get("pmid")

    @pmid.setter
    def pmid(self, pmid):
        self.extra_data["pmid"] = pmid

    @property
    def scholarid(self):
        return self.extra_data.get("scholarid")

    @scholarid.setter
    def scholarid(self, scholarid):
        self.extra_data["scholarid"] = scholarid

    @property
    def title(self):
        return self.bib.get("title")

    @title.setter
    def title(self, title):
        self.bib["title"] = title

    @property
    def norm_title(self):
        return normalizeTitle(self.title)

    @property
    def abstract(self):
        return self.bib.get("abstract")

    @property
    def year(self):
        return self.bib.get("year")

    @property
    def authors(self):
        return self.bib.get("author")

    @authors.setter
    def authors(self, authors):
        self.bib["author"] = authors

    @property
    def entrytype(self):
        return self.bib.get("ENTRYTYPE").lower()

    @property
    def venue(self):
        entrytype = self.entrytype
        if entrytype == "article":
            return self.bib.get("journal", "")
        elif entrytype in ["book", "booklet", "manual", "proceedings"]:
            # return self.bib.get("title", "")
            return ""
        elif entrytype in ["conference", "inproceedings", "incollection"]:
            return self.bib.get("booktitle", "")
        elif entrytype in ["mastersthesis", "phdthesis"]:
            return self.bib.get("school", "")
        elif entrytype in ["techreport"]:
            return self.bib.get("institution", "")
        elif entrytype in ["misc", "unpublished"]:
            return ""

    @property
    def has_pdf(self):
        for url in self.extra_data.get('urls', []):
            if url['type'] == 'pdf':
                return True
        return False

    @property
    def has_full_abstract(self):
        if not self.abstract:
            return False

        if self.abstract.endswith('…'):
            return False

        return True

    @property
    def has_abstract(self):
        return self.abstract is not None and self.abstract != ''

    @property
    def has_valid_id(self):
        return any([self.doi, self.pmid, self.arxivid, self.extra_data.get('ss_id')])

    @property
    def has_pdf_link(self):
        for url in self.extra_data.get('urls', []):
            if url.get('type') == 'pdf' or 'pdf' in url.get('url', ''):
                return True

        return False

    def asDict(self):
        return {
            "id": self.id,
            "title": self.title,
            "norm_title": self.norm_title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "bib": json.dumps(self.bib),
            "doi": self.doi,
            "arxivid": self.arxivid,
            "scholarid": self.scholarid,
            "pmid": self.pmid,
            "extra_data": json.dumps(self.extra_data)
        }

    def __repr__(self):
        return f"<%s - %s - %s> \n %s" % (
            self.bib.get("title", ""),
            self.bib.get("author", ""),
            self.bib.get("year", ""), str(self.bib))


class PaperStore:
    def __init__(self):
        self.conn = sqlite3.connect(CACHE_FILE)
        self.conn.row_factory = sqlite3.Row
        self.initaliseDB()

    def initaliseDB(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS "papers" (
                         "id" text primary key,
                         "doi" text unique,
                         "pmid" text unique,
                         "scholarid" text unique,
                         "arxivid" text unique,
                         "authors" text,
                         "year" integer,
                         "title" text,
                         "norm_title" text,
                         "venue" text,
                         "bib" text,
                         "extra_data" text
                           )
         """)

        self.conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_ids ON papers(id, doi)""")

        self.conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_papers_otherids ON papers(pmid, scholarid, arxivid)""")

        self.conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title, norm_title)""")

        self.conn.commit()

    # def runSelectStatement(self, sql, parameters):
    #     """
    #
    #     :param sql: SQL string to run
    #     :return: Cursor to the results
    #     """
    #     c = self.conn.cursor()
    #     c.execute(sql, parameters)
    #     return c

    def getPaper(self, id_string, id_type="doi"):
        """
        Looks for a paper given an id.

        :param id_string: the actual id
        :param id_type: the type of id (doi, arxivid, pmid, scholarid)
        :return: paper if found, or None
        """
        c = self.conn.cursor()

        c.execute("SELECT * FROM papers WHERE %s=?" % id_type, (id_string,))
        paper_record = c.fetchone()
        if not paper_record:
            return None

        res = Paper.fromRecord(paper_record)
        return res

    def findPapersByTitle(self, title):
        """
        Looks for a paper given a title.

        :param title:
        :return:
        """
        c = self.conn.cursor()
        norm_title = normalizeTitle(title)

        c.execute("SELECT * FROM papers WHERE norm_title=?", (norm_title,))
        paper_records = c.fetchall()
        if not paper_records:
            return None

        res = []
        for paper_record in paper_records:
            res.append(Paper.fromRecord(paper_record))
        return res

    def findPaperByApproximateTitle(self, paper, ok_title_distance=0.35, ok_author_distance=0.1):
        """
        Very simple ngram-based similarity matching

        :param title:
        :return:
        """
        c = self.conn.cursor()

        norm_title = normalizeTitle(paper.title)

        bits = norm_title.split()
        bits = [b for b in bits if b not in stopwords]

        query_string = " OR ".join(bits)

        c.execute('SELECT id, norm_title FROM papers_search WHERE norm_title MATCH ?', (query_string,))
        paper_ids = c.fetchall()
        if not paper_ids:
            return None

        paper_id_list = [res['id'] for res in paper_ids]
        id_query_string = ",".join(['"%s"' % res['id'] for res in paper_ids])

        c.execute('SELECT * FROM papers WHERE id IN (%s)' % id_query_string)
        paper_records = c.fetchall()
        if not paper_records:
            return None

        results = [Paper.fromRecord(r) for r in paper_records]

        sorted_results = rerankByTitleSimilarity(results, paper.title)

        top_res = sorted_results[0][1]

        title_distance = dist.distance(top_res.title.lower(), paper.title.lower())
        author_distance = computeAuthorDistance(paper, top_res)


        if title_distance <= ok_title_distance and author_distance <= ok_author_distance:
            print('\n[matched] ', paper.title)
            print('Best match:', top_res.title)
        else:
            print('\n[skipped] ', paper.title)
            print('Options:\n' + '\n'.join([r[1].title for r in sorted_results[:5]]), '\n')
            return None

        print('title distance:', title_distance, 'author distance:', author_distance)

        new_paper = top_res
        # new_paper.title = paper.title

        return new_paper

    def addPaper(self, paper: Paper):
        self.addPapers([paper])

    def addPapers(self, papers: list):
        to_add = [paper.asDict() for paper in papers]

        df = pd.DataFrame(to_add)
        df.to_sql("papers", self.conn, if_exists="append", index=False)

    def updatePapers(self, papers: list):
        for paper in papers:
            values = paper.asDict()
            try:
                self.conn.execute(
                    """REPLACE INTO papers (id, doi, pmid, scholarid, arxivid, authors, year, title, norm_title, venue, bib, extra_data) values (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (values['id'], values['doi'], values['pmid'], values['scholarid'],
                     values['arxivid'], values['authors'], values['year'],
                     values['title'], values['norm_title'], values['venue'],
                     values['bib'], values['extra_data']))
            except Exception as e:
                print(e.__class__.__name__, e)
            self.conn.commit()

    def createVirtualTable(self):
        self.conn.execute(
            """CREATE VIRTUAL TABLE IF NOT EXISTS papers_search USING fts5(id, norm_title, title);""")
        self.conn.execute(
            """REPLACE INTO papers_search (id, norm_title, title) SELECT id, norm_title, title from papers""")

        self.conn.commit()

    def deleteVirtualTable(self):
        self.conn.execute("DROP TABLE papers_search")
        self.conn.commit()

    def matchResultsWithPapers(self, results):
        """
        Tries to match each result with a paper already in the db.

        :param results:
        :return:
        """
        found = []
        missing = []
        self.createVirtualTable()
        for result in results:
            paper = Paper(result.bib, result.extra_data)

            paper_found = False
            for id_type in ["doi", "pmid", "arxivid", "scholarid"]:
                id_string = getattr(paper, id_type)
                if id_string:
                    paper_record = self.getPaper(id_string, id_type=id_type)
                    if paper_record:
                        result.paper = paper_record
                        found.append(result)
                        paper_found = True
                        break

            if not paper_found and paper.title:
                paper_records = self.findPapersByTitle(paper.title)
                if paper_records:
                    result.paper = paper_records[0]
                    found.append(result)
                    paper_found = True

                if not paper_found and paper.title:
                    paper_record = self.findPaperByApproximateTitle(paper)
                    if paper_record:
                        result.paper = paper_record
                        found.append(result)
                        paper_found = True

            if not paper_found:
                missing.append(result)

        self.deleteVirtualTable()
        return found, missing


def computeAuthorDistance(paper1, paper2):
    """
    Returns a measure of how much the authors of papers overlap

    :param paper1:
    :param paper2:
    :return:
    """
    authors1 = paper1.extra_data.get('x_authors', parseBibAuthors(paper1.bib['author']))
    authors2 = paper2.extra_data.get('x_authors', parseBibAuthors(paper2.bib['author']))

    score = 0
    if len(authors1) >= len(authors2):
        a_short = authors2
        a_long = authors1
    else:
        a_short = authors1
        a_long = authors2

    max_score = 0

    for index, author in enumerate(a_short):
        factor = (len(a_long) - index) ** 2
        if author['family'].lower() == a_long[index]['family'].lower():
            score += factor

        max_score += factor

    if max_score == 0:
        return 1

    distance = 1 - (score / max_score)
    return distance


def basicTitleCleaning(title):
    return re.sub(r'\s+', ' ', title, flags=re.MULTILINE)


def rerankByTitleSimilarity(results: list, title):
    scores = []
    for res in results:
        res.bib['title'] = basicTitleCleaning(res.bib['title'])
        scores.append((dist.distance(res.bib['title'].lower(), title.lower()), res))

    return sorted(scores, key=lambda x: x[0], reverse=False)

def removeListWrapper(value):
    while isinstance(value, list):
        value = value[0]
    return value

def test1():
    bibstr = """@ARTICLE{Cesar2013,
      author = {Jean César},
      title = {An amazing title},
      year = {2013},
      volume = {12},
      pages = {12--23},
      journal = {Nice Journal},
      abstract = {This is an abstract. This line should be long enough to test
         multilines...},
      comments = {A comment},
      keywords = {keyword1, keyword2}
    }
    """
    bib = bibtexparser.loads(bibstr)
    paper = Paper(bib.entries[0])
    paperstore = PaperStore()
    paperstore.addPapers([paper])


def test2():
    paperstore = PaperStore()
    paper = paperstore.getPaper('10.1148/radiol.2018171093')
    paper.arxivid = None
    paperstore.updatePapers([paper])


if __name__ == '__main__':
    test2()
dist = NormalizedLevenshtein()


