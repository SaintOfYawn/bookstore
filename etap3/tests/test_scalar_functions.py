"""Скалярные функции: прямые вызовы Python и вызовы из SQL."""
import pytest

from bookstore_functions import availability, days_between, price_with_discount, short_name


@pytest.mark.parametrize('price, percent, expected', [
    (100, 20, 80.0), (1290, 10, 1161.0), (100, 0, 100.0), (100, 100, 0.0),
    (None, 20, None), (100, None, None), (100, -5, None), (100, 101, None),
])
def test_price_with_discount(price, percent, expected):
    assert price_with_discount(price, percent) == expected


@pytest.mark.parametrize('last, first, middle, expected', [
    ('Орлова', 'Мария', 'Игоревна', 'Орлова М. И.'), ('Иванов', 'Пётр', None, 'Иванов П.'),
    ('Иванов', '', None, 'Иванов'), (None, 'Пётр', None, None), ('  ', 'Пётр', None, None),
])
def test_short_name(last, first, middle, expected):
    assert short_name(last, first, middle) == expected


@pytest.mark.parametrize('stock, expected', [
    (0, 'нет в наличии'), (-1, 'нет в наличии'), (3, 'заканчивается'), (4, 'заканчивается'),
    (5, 'в наличии'), (40, 'в наличии'), (None, None),
])
def test_availability(stock, expected):
    assert availability(stock, 5) == expected


def test_availability_without_limit():
    assert availability(3, None) is None


@pytest.mark.parametrize('first, second, expected', [
    ('2026-09-01T10:00:00', '2026-10-12', 41), ('2026-10-12', '2026-10-12', 0),
    ('2026-10-12', '2026-10-10', -2), (None, '2026-10-12', None), ('abc', '2026-10-12', None),
])
def test_days_between(first, second, expected):
    assert days_between(first, second) == expected


def test_functions_work_in_select(con):
    row = con.execute('SELECT fn_price_with_discount(100, 20), fn_price_with_discount(NULL, 20)').fetchone()
    assert row == (80.0, None)


def test_functions_in_computed_column(con):
    rows = con.execute('SELECT Title, fn_availability(StockQty, 5) FROM Books '
                       'WHERE BookID IN (3, 8, 25) ORDER BY BookID').fetchall()
    assert rows == [('Мастер и Маргарита', 'в наличии'), ('Я, робот', 'заканчивается'),
                    ('Над пропастью во ржи', 'нет в наличии')]


def test_function_in_where_and_order_by(con):
    rows = con.execute('SELECT Title FROM Books WHERE fn_price_with_discount(Price, 10) <= 400 '
                       'ORDER BY fn_price_with_discount(Price, 10)').fetchall()
    assert rows == [('Евгений Онегин',), ('Собака Баскервилей',)]


def test_short_name_in_sql(con):
    row = con.execute('SELECT fn_short_name(LastName, FirstName, MiddleName) FROM Employees '
                      'WHERE EmployeeID = 1').fetchone()
    assert row == ('Орлова М. И.',)


def test_order_age_in_sql(con):
    row = con.execute("SELECT fn_days_between(OrderDate, '2026-10-12') FROM Orders WHERE OrderID = 1").fetchone()
    assert row == (41,)
