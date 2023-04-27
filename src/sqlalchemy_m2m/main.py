import logging
import logging.config
import argparse
from typing import Any, Callable

import yaml
import sqlparse
import pydantic
import psycopg2
import psycopg2.extras
import psycopg2.extensions
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm

import sqlalchemy as sa
import sqlalchemy.orm as sa_orm
import sqlalchemy.ext.hybrid as sa_hybrid


### Logging

with open('logging.conf.yml', 'r') as f:
    logging.config.dictConfig(yaml.safe_load(f))

logger = logging.getLogger(__name__)
logger_db = logging.getLogger(f'{__name__}/db')


### Settings from .env file

class Settings(pydantic.BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    class Config:  # type: ignore
        env_file = '.env'


settings = Settings()  # type: ignore


### Database connection

class LoggingConnection(psycopg2.extras.LoggingConnection):
    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(*args, **kwargs)
        self.initialize(logger_db)

    def _logtologger(self, msg: str | bytes, cur: psycopg2.extensions.cursor):
        msg = self.filter(msg, cur)
        if msg:
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8")
                msg = sqlparse.format(msg, reindent=True, keyword_case="upper")

            self._logobj.info(msg)  # type: ignore


engine = sqlalchemy.create_engine(
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}",
    connect_args={'connection_factory': LoggingConnection},
)
session = sqlalchemy.orm.scoped_session(
    sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = session.query_property()
def Base__repr__(self: Any) -> str:
    args = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
    return f'{self.__class__.__name__}({args})'
Base.__repr__ = Base__repr__


class Book(Base):
    __tablename__ = "book"
    __table_args__ = {"schema": "m2m"}

    book_id = sa.Column(sa.UUID(), primary_key=True)
    title = sa.Column(sa.String(), nullable=False)

    authors = sa_orm.relationship("Author", secondary=lambda: BookAuthor.__table__, backref=sa_orm.backref("books"), viewonly=True)


class Author(Base):
    __tablename__ = "author"
    __table_args__ = {"schema": "m2m"}

    author_id = sa.Column(sa.UUID(), primary_key=True)
    name = sa.Column(sa.String(), nullable=False)


class BookAuthor(Base):
    __tablename__ = "book_author"
    __table_args__ = {"schema": "m2m"}

    book_id = sa.Column(sa.UUID(), sa.ForeignKey(Book.book_id), primary_key=True)
    author_id = sa.Column(sa.UUID(), sa.ForeignKey(Author.author_id), primary_key=True)
    position = sa.Column(sa.Integer(), nullable=False)

    book = sa_orm.relationship(Book, backref=sa_orm.backref("book_authors"))
    author = sa_orm.relationship(Author, backref=sa_orm.backref("book_authors"))


### Main

def main1():
    with engine.connect() as conn:
        result = conn.execute(sa.text("SELECT 1"))
        print(result.fetchone())


def main2():
    '''
    exactly one book
    '''
    book = Book.query.filter(Book.book_id == '1FB112D1-54C9-4308-99C6-0163BFD0172D').one()
    print(book)


def main3():
    '''
    query with 'in' clause
    '''
    books = Book.query.filter(
        Book.book_id.in_([
            '554BC347-F36C-4766-B66F-D651C84C56BA',
            '554BC347-F36C-4766-B66F-D651C84C56BA',
        ])
    ).all()
    print(books)


def main4():
    '''
    many to many (N+1)

    SELECT m2m.book.book_id AS m2m_book_book_id,
       m2m.book.title AS m2m_book_title
    FROM m2m.book;

    SELECT m2m.author.author_id AS m2m_author_author_id,
        m2m.author.name AS m2m_author_name
    FROM m2m.author,
        m2m.book_author
    WHERE '1fb112d1-54c9-4308-99c6-0163bfd0172d'::UUID::UUID = m2m.book_author.book_id
    AND m2m.author.author_id = m2m.book_author.author_id;

    SELECT m2m.author.author_id AS m2m_author_author_id,
        m2m.author.name AS m2m_author_name
    FROM m2m.author,
        m2m.book_author
    WHERE '554bc347-f36c-4766-b66f-d651c84c56ba'::UUID::UUID = m2m.book_author.book_id
    AND m2m.author.author_id = m2m.book_author.author_id;
    '''
    books = Book.query.all()
    print(books)

    for book in books:
        print(f'{book.book_id}: {book.authors}')  # N+1 problem


def main5():
    '''
    many to many (joined)

    SELECT m2m.book.book_id AS m2m_book_book_id,
        m2m.book.title AS m2m_book_title,
        author_1.author_id AS author_1_author_id,
        author_1.name AS author_1_name
    FROM m2m.book
    LEFT OUTER JOIN (m2m.book_author AS book_author_1
                    JOIN m2m.author AS author_1 ON author_1.author_id = book_author_1.author_id) ON m2m.book.book_id = book_author_1.book_id;
    '''
    books = Book.query.options(sa_orm.joinedload(Book.authors)).all()
    print(books)

    for book in books:
        print(f'{book.book_id}: {book.authors}')


def main6():
    '''
    many to many (selectin)

    SELECT m2m.book.book_id AS m2m_book_book_id,
        m2m.book.title AS m2m_book_title
    FROM m2m.book;

    SELECT book_1.book_id AS book_1_book_id,
        m2m.author.author_id AS m2m_author_author_id,
        m2m.author.name AS m2m_author_name
    FROM m2m.book AS book_1
    JOIN m2m.book_author AS book_author_1 ON book_1.book_id = book_author_1.book_id
    JOIN m2m.author ON m2m.author.author_id = book_author_1.author_id
    WHERE book_1.book_id IN ('1fb112d1-54c9-4308-99c6-0163bfd0172d'::UUID::UUID,
                            '554bc347-f36c-4766-b66f-d651c84c56ba'::UUID::UUID);
    '''
    books = Book.query.options(sa_orm.selectinload(Book.authors)).all()
    print(books)

    for book in books:
        print(f'{book.book_id}: {book.authors}')


def parse_args(fn_mapping: dict[str, Callable[[], None]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=fn_mapping.keys())

    return parser.parse_args()


def main():
    mapping = {
        'main-1': main1,
        'main-2': main2,
        'main-3': main3,
        'main-4': main4,
        'main-5': main5,
        'main-6': main6,
    }

    args = parse_args(mapping)
    fn = mapping[args.command]
    fn()
