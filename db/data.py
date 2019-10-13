import sqlite3
import os, re, json
import pandas as pd
import bibtexparser
import unicodedata

from db.bibtex import parseBibAuthors

current_dir = os.path.dirname(os.path.realpath(__file__))

CACHE_FILE = os.path.join(current_dir, "papers.sqlite")


# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy import Column, Integer, String
# Base = declarative_base()
#
# class Paper(Base):
#     __tablename__ = 'papers'
#     id = Column(Integer, primary_key=True)
#     doi = Column(String, unique=True)
#     pmid = Column(String, unique=True)
#     scholarid = Column(String, unique=True)

def unicodeToASCII(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode("utf-8")
    return only_ascii


def normalizeTitle(title):
    """
        Returns a "normalized" title for easy matching
    """
    title = title.lower()
    title = re.sub(r"–", " ", title)
    title = unicodeToASCII(title)
    title = title.replace("-  ", "").replace("- ", "")
    title = re.sub(r"[\"\#\$\%\&\\\'\(\)\*\+\,\-\.\/\:\;\<\=\>\?\¿\!\¡\@\[\]\^\_\`\{\|\}\~]", " ", title)
    title = re.sub(r"\s+", " ", title)
    title = title.strip()
    title = title[:200]
    return title


def generateUniqueID(paper):
    """
    Returns a simple string id that is the mashup of the title and authors

    :param paper:
    :return:
    """
    author_bit = ''
    if paper.extra_data.get('xref_author'):
        authors = paper.extra_data['xref_author']
    else:
        try:
            authors = parseBibAuthors(paper.authors)
        except:
            print("Failed to parse authors string", paper.authors)
            authors = [{'given': '', 'family': ''}]

    for author in authors:
        if author.get('family'):
            author_bit += author.get('family', '_')[0] + author.get('given', '_')[0]

    title_bit = normalizeTitle(paper.title)
    title_bit = re.sub("\s+", "", title_bit)
    full_id = title_bit + "_" + author_bit
    full_id = full_id.lower()
    return full_id


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

        res.pmid = paper_record["pmid"],
        res.scholarid = paper_record["scholarid"],
        res.arxivid = paper_record["arxivid"],
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
    def has_pdf_link(self):
        for url in self.extra_data.get('urls',[]):
            if url.get('type')=='pdf' or 'pdf' in url.get('url',''):
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

    def addPaper(self, paper: Paper):
        self.addPapers([paper])

    def addPapers(self, papers: list):
        to_add = [paper.asDict() for paper in papers]

        df = pd.DataFrame(to_add)
        df.to_sql("papers", self.conn, if_exists="append", index=False)

    def updatePapers(self, papers: list):
        for paper in papers:
            values = paper.asDict()
            self.conn.execute(
                """REPLACE INTO papers (id, doi, pmid, scholarid, arxivid, authors, year, title, norm_title, venue, bib, extra_data) values (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values['id'], values['doi'], values['pmid'], values['scholarid'],
                 values['arxivid'], values['authors'], values['year'],
                 values['title'], values['norm_title'], values['venue'],
                 values['bib'], values['extra_data']))
            self.conn.commit()

    def matchResultsWithPapers(self, results):
        """
        Tries to match each result with a paper already in the db.

        :param results:
        :return:
        """
        found = []
        missing = []
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

            if not paper_found:
                paper_records = self.findPapersByTitle(paper.title)
                # FIXME: should also match by author, within a year or 2, etc.
                if paper_records:
                    result.paper = paper_records[0]
                    found.append(result)
                    paper_found = True

            if not paper_found:
                missing.append(result)

        return found, missing


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
