"""Процедуры этапа 2: выборки, изменение данных, транзакции, отчёты, журнал ошибок."""
import pytest

import procedures as proc
from procedures import ProcedureError


def stock(con, book_id):
    return con.execute('SELECT StockQty FROM Books WHERE BookID = ?', (book_id,)).fetchone()[0]


def count(con, table):
    return con.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]


def errors(con):
    return con.execute('SELECT ProcedureName, ErrorCode FROM ErrorLog ORDER BY ErrorID').fetchall()


def code_of(function, *args, **kwargs):
    with pytest.raises(ProcedureError) as error:
        function(*args, **kwargs)
    return error.value.code


# ------------------------------------------------------------------ выборки
def test_books_get_all(pcon):
    rows = proc.books_get_all(pcon)
    titles = [r['Title'] for r in rows]
    assert len(rows) == 25 and titles == sorted(titles)


def test_books_get_all_only_active(pcon):
    pcon.execute('UPDATE Books SET IsActive = 0 WHERE BookID = 1')
    assert len(proc.books_get_all(pcon)) == 24 and len(proc.books_get_all(pcon, only_active=False)) == 25


def test_books_get_by_id(pcon):
    book = proc.books_get_by_id(pcon, 1)
    assert (book['Title'], book['Publisher'], book['Category']) == ('Война и мир', 'Азбука', 'Классика')


def test_books_get_by_id_not_found(pcon):
    assert code_of(proc.books_get_by_id, pcon, 9999) == 50001


def test_books_get_by_title_prefix(pcon):
    assert [r['Title'] for r in proc.books_get_by_title(pcon, 'Чист')] == ['Чистая архитектура', 'Чистый код']


@pytest.mark.parametrize('prefix', ['%', '_', 'Несуществующая'])
def test_books_get_by_title_no_match(pcon, prefix):
    assert proc.books_get_by_title(pcon, prefix) == []


@pytest.mark.parametrize('prefix', ['', '   ', None])
def test_books_get_by_title_empty_prefix(pcon, prefix):
    assert code_of(proc.books_get_by_title, pcon, prefix) == 50002


@pytest.mark.parametrize('category, in_stock, expected', [
    ('Фантастика', False, 5), ('Художественная литература', False, 14),
    ('Художественная литература', True, 13), (None, False, 25), ('Нет такой', False, 0)])
def test_books_get_by_category(pcon, category, in_stock, expected):
    assert len(proc.books_get_by_category(pcon, category, in_stock)) == expected


def test_customers_get_by_phone(pcon):
    phone = pcon.execute('SELECT Phone FROM Customers WHERE CustomerID = 1').fetchone()[0]
    assert proc.customers_get_by_phone(pcon, phone)['CustomerID'] == 1
    assert code_of(proc.customers_get_by_phone, pcon, '+7 (000) 000-00-00') == 50001


def test_authors_get_by_name(pcon):
    rows = proc.authors_get_by_name(pcon, 'Стругацк')
    assert [(r['FirstName'], r['BooksCount']) for r in rows] == [('Аркадий', 2), ('Борис', 2)]


def test_orders_get_by_customer(pcon):
    rows = proc.orders_get_by_customer(pcon, 1)
    assert [(r['OrderID'], r['Total']) for r in rows] == [(1, 2240), (9, 2980), (14, 2840)]


def test_orders_get_by_customer_period(pcon):
    assert [r['OrderID'] for r in proc.orders_get_by_customer(pcon, 1, '2026-09-11', '2026-09-11')] == [9]
    assert proc.orders_get_by_customer(pcon, 1, '2020-01-01', '2020-01-31') == []


def test_orders_get_by_customer_errors(pcon):
    assert code_of(proc.orders_get_by_customer, pcon, 999) == 50001
    assert code_of(proc.orders_get_by_customer, pcon, 1, 'вчера') == 50002


# ------------------------------------------------------------------ добавление, изменение, удаление
def new_book(**changes):
    values = dict(title='Новая книга', isbn='9785000000555', publisher_id=1, category_id=2,
                  publish_year=2024, pages=100, price=250.5, stock_qty=3)
    values.update(changes)
    return values


def test_books_create_returns_id(pcon):
    book_id = proc.books_create(pcon, **new_book(title='  Новая книга  '))
    book = proc.books_get_by_id(pcon, book_id)
    assert book_id == 26 and book['Title'] == 'Новая книга' and book['StockQty'] == 3


@pytest.mark.parametrize('changes, code', [
    ({'title': ''}, 50002), ({'title': '   '}, 50002), ({'isbn': '123'}, 50002), ({'isbn': '97850000001AB'}, 50002),
    ({'price': 0}, 50002), ({'price': 'abc'}, 50002), ({'price': float('nan')}, 50002), ({'price': float('inf')}, 50002),
    ({'stock_qty': -1}, 50002), ({'publisher_id': 999}, 50001), ({'category_id': 999}, 50001),
    ({'isbn': '9785170371037'}, 50004)])
def test_books_create_validation(pcon, changes, code):
    assert code_of(proc.books_create, pcon, **new_book(**changes)) == code
    assert count(pcon, 'Books') == 25


def test_books_update_price(pcon):
    assert proc.books_update_price(pcon, 1, 1300) == 1290
    assert proc.books_get_by_id(pcon, 1)['Price'] == 1300


def test_books_update_price_errors(pcon):
    assert code_of(proc.books_update_price, pcon, 1, -5) == 50002
    assert code_of(proc.books_update_price, pcon, 9999, 100) == 50001


def test_books_delete_return_codes(pcon):
    assert proc.books_delete(pcon, 16) == 0 and count(pcon, 'Books') == 24
    assert proc.books_delete(pcon, 1) == 50005 and proc.books_delete(pcon, 9999) == 50001


def test_customers_create_returns_id(pcon):
    customer_id = proc.customers_create(pcon, 'Тестов', 'Тест', '+7 (900) 000-00-01', discount_percent=10)
    assert customer_id == 21 and count(pcon, 'Customers') == 21


@pytest.mark.parametrize('kwargs, code', [
    ({'last_name': ''}, 50002), ({'phone': ''}, 50002), ({'discount_percent': 31}, 50002),
    ({'discount_percent': -1}, 50002), ({'phone': '+7 (911) 207-11-21'}, 50004)])
def test_customers_create_validation(pcon, kwargs, code):
    values = dict(last_name='Тестов', first_name='Тест', phone='+7 (900) 000-00-01')
    values.update(kwargs)
    assert code_of(proc.customers_create, pcon, **values) == code


def test_customers_update_discount(pcon):
    assert proc.customers_update_discount(pcon, 1, 15) == 0
    assert pcon.execute('SELECT DiscountPercent FROM Customers WHERE CustomerID = 1').fetchone()[0] == 15
    assert code_of(proc.customers_update_discount, pcon, 1, 31) == 50002
    assert code_of(proc.customers_update_discount, pcon, 999, 5) == 50001


# ------------------------------------------------------------------ заказы и транзакции
def test_orders_create(pcon):
    order_id = proc.orders_create(pcon, 1, 1, 'карта')
    assert order_id == 31 and pcon.execute('SELECT Status FROM Orders WHERE OrderID = 31').fetchone()[0] == 'новый'
    assert proc.orders_create(pcon, None, 1, 'наличные') == 32


@pytest.mark.parametrize('args, code', [((999, 1, 'карта'), 50001), ((1, 999, 'карта'), 50001), ((1, 1, 'бартер'), 50002)])
def test_orders_create_errors(pcon, args, code):
    assert code_of(proc.orders_create, pcon, *args) == code and count(pcon, 'Orders') == 30


def test_orders_add_item_decreases_stock(pcon):
    order_id = proc.orders_create(pcon, 1, 1, 'карта')
    assert proc.orders_add_item(pcon, order_id, 13, 2) == 3780
    assert stock(pcon, 13) == 12


def test_orders_add_item_whole_stock(pcon):
    order_id = proc.orders_create(pcon, 1, 1, 'карта')
    proc.orders_add_item(pcon, order_id, 8, 3)
    assert stock(pcon, 8) == 0


@pytest.mark.parametrize('book_id, quantity, code', [(8, 4, 50003), (25, 1, 50003), (13, 0, 50002), (13, -1, 50002), (999, 1, 50001)])
def test_orders_add_item_errors(pcon, book_id, quantity, code):
    order_id = proc.orders_create(pcon, 1, 1, 'карта')
    before = stock(pcon, book_id) if book_id != 999 else None
    assert code_of(proc.orders_add_item, pcon, order_id, book_id, quantity) == code
    assert count(pcon, 'OrderItems') == 58 and (before is None or stock(pcon, book_id) == before)


def test_orders_add_item_to_finished_order_and_duplicate(pcon):
    assert code_of(proc.orders_add_item, pcon, 2, 13, 1) == 50004
    order_id = proc.orders_create(pcon, 1, 1, 'карта')
    proc.orders_add_item(pcon, order_id, 13, 1)
    assert code_of(proc.orders_add_item, pcon, order_id, 13, 1) == 50004
    assert code_of(proc.orders_add_item, pcon, 9999, 13, 1) == 50001


def test_orders_place_success(pcon):
    order_id = proc.orders_place(pcon, 1, 1, 'карта', [(13, 2), (8, 1)])
    assert count(pcon, 'OrderItems') == 60 and (stock(pcon, 13), stock(pcon, 8)) == (12, 2)
    assert order_id == 31


def test_orders_place_is_atomic(pcon):
    assert code_of(proc.orders_place, pcon, 1, 1, 'карта', [(13, 2), (8, 9)]) == 50003
    assert count(pcon, 'Orders') == 30 and count(pcon, 'OrderItems') == 58
    assert (stock(pcon, 13), stock(pcon, 8)) == (14, 3)


def test_orders_place_empty(pcon):
    assert code_of(proc.orders_place, pcon, 1, 1, 'карта', []) == 50002


def test_orders_set_status_flow(pcon):
    assert proc.orders_set_status(pcon, 14, 'оплачен') == 0
    assert proc.orders_set_status(pcon, 14, 'выдан') == 0
    assert pcon.execute('SELECT Status FROM Orders WHERE OrderID = 14').fetchone()[0] == 'выдан'


@pytest.mark.parametrize('order_id, status, code', [
    (14, 'выдан', 50004), (2, 'новый', 50004), (6, 'оплачен', 50004), (14, 'потерян', 50002), (9999, 'оплачен', 50001)])
def test_orders_set_status_errors(pcon, order_id, status, code):
    assert code_of(proc.orders_set_status, pcon, order_id, status) == code


def test_orders_cancel_returns_stock(pcon):
    before = (stock(pcon, 2), stock(pcon, 23))
    proc.orders_set_status(pcon, 1, 'отменён')
    assert (stock(pcon, 2), stock(pcon, 23)) == (before[0] + 3, before[1] + 1)
    proc.orders_set_status(pcon, 1, 'отменён')                      # повтор — без изменений
    assert (stock(pcon, 2), stock(pcon, 23)) == (before[0] + 3, before[1] + 1)


def test_supply_receive(pcon):
    assert proc.supply_receive(pcon, 6) == 2
    assert (stock(pcon, 7), stock(pcon, 13)) == (30, 29)
    assert code_of(proc.supply_receive, pcon, 6) == 50004


@pytest.mark.parametrize('supply_id, code', [(8, 50004), (999, 50001)])
def test_supply_receive_errors(pcon, supply_id, code):
    assert code_of(proc.supply_receive, pcon, supply_id) == code


# ------------------------------------------------------------------ результаты «OUTPUT»
def test_orders_count_by_customer(pcon):
    assert proc.orders_count_by_customer(pcon, 1) == 3
    assert code_of(proc.orders_count_by_customer, pcon, 999) == 50001


def test_books_stock_summary(pcon):
    assert proc.books_stock_summary(pcon, 'Фантастика') == (5, 80)
    assert proc.books_stock_summary(pcon, 'Нет такой') == (0, 0)


# ------------------------------------------------------------------ отчёты
def test_report_revenue_by_period(pcon):
    rows = proc.report_revenue_by_period(pcon, '2026-09-01', '2026-09-30')
    assert len(rows) == 19 and sum(r['BooksSold'] for r in rows) == 68
    assert round(sum(r['Revenue'] for r in rows), 2) == 56286.5
    expected = pcon.execute("SELECT ROUND(SUM(oi.Quantity * oi.UnitPrice * (100 - IFNULL(c.DiscountPercent, 0)) / 100.0), 2) "
                            "FROM Orders o JOIN OrderItems oi USING (OrderID) LEFT JOIN Customers c USING (CustomerID) "
                            "WHERE o.Status IN ('оплачен', 'выдан') AND date(o.OrderDate) BETWEEN '2026-09-01' AND '2026-09-30'").fetchone()[0]
    assert round(sum(r['Revenue'] for r in rows), 2) == expected


def test_report_revenue_empty_and_invalid(pcon):
    assert proc.report_revenue_by_period(pcon, '2020-01-01', '2020-01-31') == []
    assert code_of(proc.report_revenue_by_period, pcon, '2026-09-30', '2026-09-01') == 50002
    assert code_of(proc.report_revenue_by_period, pcon, 'abc', '2026-09-01') == 50002


def test_report_top_books(pcon):
    rows = proc.report_top_books(pcon, '2026-09-01', '2026-09-30', 3)
    assert [(r['Title'], r['Sold']) for r in rows][:2] == [('Пикник на обочине', 9), ('Базы данных: модели, разработка, реализация', 7)]
    assert len(rows) == 3 and code_of(proc.report_top_books, pcon, '2026-09-01', '2026-09-30', 0) == 50002


def test_report_low_stock(pcon):
    assert [(r['BookID'], r['StockQty']) for r in proc.report_low_stock(pcon)] == [(25, 0), (8, 3), (14, 4)]
    assert len(proc.report_low_stock(pcon, 6)) == 4


# ------------------------------------------------------------------ журнал ошибок
def test_errors_are_logged(pcon):
    code_of(proc.books_get_by_id, pcon, 9999)
    code_of(proc.orders_place, pcon, 1, 1, 'карта', [(8, 9)])
    assert errors(pcon) == [('books_get_by_id', 50001), ('orders_place', 50003)]


def test_success_is_not_logged(pcon):
    proc.books_get_all(pcon)
    proc.orders_place(pcon, 1, 1, 'карта', [(13, 1)])
    assert errors(pcon) == []


# ------------------------------------------------------------------ совместная работа с триггерами этапа 4
def test_with_triggers_stock_changes_once(tcon):
    order_id = proc.orders_create(tcon, 1, 1, 'карта')
    proc.orders_add_item(tcon, order_id, 13, 2)
    assert stock(tcon, 13) == 12


def test_with_triggers_cancel_and_supply_change_stock_once(tcon):
    before = stock(tcon, 2)
    proc.orders_set_status(tcon, 1, 'отменён')
    assert stock(tcon, 2) == before + 3
    proc.supply_receive(tcon, 6)
    assert (stock(tcon, 7), stock(tcon, 13)) == (30, 29)


def test_with_triggers_atomic_place(tcon):
    assert code_of(proc.orders_place, tcon, 1, 1, 'карта', [(13, 2), (8, 9)]) == 50003
    assert count(tcon, 'Orders') == 30 and stock(tcon, 13) == 14
