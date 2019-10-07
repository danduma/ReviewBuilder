import sqlite3
import os
import re
from os.path import exists
import pandas as pd
import bibtexparser

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

def normalizeTitle(title):
    """
        Returns a "normalized" title for easy matching
    """
    title = title.lower()
    title = title.replace("-  ", "").replace("- ", "")
    title = re.sub(r"[\"\#\$\%\&\\\'\(\)\*\+\,\-\.\/\:\;\<\=\>\?\¿\!\¡\@\[\]\^\_\`\{\|\}\~]", " ", title)
    title = re.sub(r"\s+", " ", title)
    title = title.strip()
    title = title[:200]
    return title


class Paper:
    def __init__(self, bib:dict=None, extra_data:dict=None, pmid=None, scholarid=None, arxivid=None):
        self.bib = bib
        self.extra_data = extra_data
        self.pmid = pmid
        self.scholarid = scholarid
        self.arxivid = arxivid

    @property
    def doi(self):
        return self.bib.get("doi")

    @doi.setter
    def doi(self, doi):
        self.bib["doi"] = doi

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

    def asDict(self):
        return {"title": self.title,
                "norm_title": self.norm_title,
                "authors": self.authors,
                "year": self.year,
                "venue": self.venue,
                "bib": str(self.bib),
                "doi": self.doi,
                "arxivid": self.arxivid,
                "scholarid": self.scholarid,
                "pmid": self.pmid,
                "extra_data": str(self.extra_data)
                }


class PaperStore:
    def __init__(self):
        self.conn = sqlite3.connect(CACHE_FILE)
        self.conn.row_factory = sqlite3.Row
        self.initaliseDB()

    def initaliseDB(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS "papers" (
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
            """CREATE INDEX IF NOT EXISTS idx_papers ON papers(doi, pmid, scholarid, arxivid, title, norm_title)""")

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

        res = Paper(paper_record["bib"], paper_record["extra_data"],
                    pmid=paper_record["pmid"],
                    scholarid=paper_record["scholarid"],
                    arxivid=paper_record["arxivid"],
                    )
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
            res.append(Paper(paper_record["bib"], paper_record["extra_data"],
                             pmid=paper_record["pmid"],
                             scholarid=paper_record["scholarid"],
                             arxivid=paper_record["arxivid"],
                             ))
        return res

    def addPaper(self, paper: Paper):
        self.addPapers([paper])

    def addPapers(self, papers: list):
        to_add = [paper.asDict() for paper in papers]

        df = pd.DataFrame(to_add)
        df.to_sql("papers", self.conn, if_exists="append", index=False)

    def updatePapers(self, papers: list):
        for paper in papers:
            c = self.conn.cursor()
            c.execute(
                """REPLACE INTO papers (doi, pmid, scholarid, arxivid, authors, year, title, norm_title, venue, bib, extra_data) values (?,?,?,?,?,?,?,?,?,?,?)""",
                (paper.doi, paper.pmid, paper.scholarid, paper.arxivid,
                 paper.authors, paper.year, paper.title,
                 paper.norm_title, paper.venue,
                 str(paper.bib), str(paper.extra_data)))
            c.close()

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


def test():
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


if __name__ == '__main__':
    test()
