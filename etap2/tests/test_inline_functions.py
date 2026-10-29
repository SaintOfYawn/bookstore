"""Inline табличные функции (select() SQLAlchemy) в запросах, JOIN и подзапросах."""
from sqlalchemy import func, select

from bookstore_functions import books_by_category, customer_orders, orders, top_sellers


def test_customer_orders(engine):
    with engine.connect() as con:
        rows = con.execute(customer_orders(1, '2026-09-01', '2026-10-31').order_by(orders.c.OrderID)).all()
    assert [(r.OrderID, r.Total) for r in rows] == [(1, 2240), (9, 2980), (14, 2840)]


def test_customer_orders_empty_period(engine):
    with engine.connect() as con:
        assert con.execute(customer_orders(1, '2020-01-01', '2020-01-31')).all() == []


def test_customer_orders_last_day_included(engine):
    with engine.connect() as con:
        rows = con.execute(customer_orders(1, '2026-09-11', '2026-09-11')).all()
    assert [r.OrderID for r in rows] == [9]


def test_customer_orders_as_subquery(engine):
    sub = customer_orders(1, '2026-09-01', '2026-10-31').subquery()
    with engine.connect() as con:
        total = con.execute(select(func.sum(sub.c.Total))).scalar()
    assert total == 8060


def test_books_by_category_leaf(engine):
    with engine.connect() as con:
        rows = con.execute(books_by_category('Фантастика')).all()
    assert len(rows) == 5 and {r.Category for r in rows} == {'Фантастика'}


def test_books_by_category_includes_children(engine):
    with engine.connect() as con:
        rows = con.execute(books_by_category('Художественная литература')).all()
    assert len(rows) == 14


def test_books_by_category_all_and_unknown(engine):
    with engine.connect() as con:
        assert len(con.execute(books_by_category()).all()) == 25
        assert con.execute(books_by_category('Нет такой')).all() == []


def test_top_sellers(engine):
    with engine.connect() as con:
        rows = {r.BookID: (r.Sold, r.Revenue) for r in con.execute(top_sellers('2026-09-01', '2026-09-30'))}
    assert rows[21] == (7, 11130) and rows[22] == (5, 7450) and rows[15] == (2, 5780)


def test_top_sellers_joined_with_books(engine):
    sub = top_sellers('2026-09-01', '2026-09-30').subquery()
    from bookstore_functions import books
    query = (select(books.c.Title, sub.c.Sold).join(sub, sub.c.BookID == books.c.BookID)
             .order_by(sub.c.Sold.desc(), books.c.Title).limit(1))
    with engine.connect() as con:
        row = con.execute(query).one()
        assert (row.Title, row.Sold) == ('Пикник на обочине', 9)
