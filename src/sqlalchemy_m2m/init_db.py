from .main import *

def init_db():
    Base.metadata.create_all(bind=engine)

    Book.query.delete()
    Author.query.delete()
    BookAuthor.query.delete()

    entities = [
        Book(book_id='1FB112D1-54C9-4308-99C6-0163BFD0172D', title='book 1'),
        Book(book_id='554BC347-F36C-4766-B66F-D651C84C56BA', title='book 2'),

        Author(author_id='BED827FF-6847-41BD-88A0-B77FDD74BEA3', name='author 1'),
        Author(author_id='467021FD-AE39-4BA0-BC7B-3E5B21EF69F9', name='author 2'),
        Author(author_id='F66C5C85-5044-4433-B631-C01C64A7A4F6', name='author 3'),

        BookAuthor(book_id='1FB112D1-54C9-4308-99C6-0163BFD0172D', author_id='BED827FF-6847-41BD-88A0-B77FDD74BEA3', position=1), # 本1 著者1
        BookAuthor(book_id='1FB112D1-54C9-4308-99C6-0163BFD0172D', author_id='467021FD-AE39-4BA0-BC7B-3E5B21EF69F9', position=2), # 本1 著者2
        BookAuthor(book_id='554BC347-F36C-4766-B66F-D651C84C56BA', author_id='BED827FF-6847-41BD-88A0-B77FDD74BEA3', position=1), # 本2 著者1
        BookAuthor(book_id='554BC347-F36C-4766-B66F-D651C84C56BA', author_id='F66C5C85-5044-4433-B631-C01C64A7A4F6', position=2), # 本2 著者3
    ]

    session.add_all(entities)
    session.commit()


if __name__ == '__main__':
    init_db()
