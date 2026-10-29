"""Сервисный слой: результат после рефакторинга совпадает с прежним."""
import pytest

import services


@pytest.mark.parametrize('category', [None, 'Фантастика', 'Художественная литература', 'Нет такой'])
def test_catalog_report_same_as_old(engine, category):
    assert services.catalog_report(engine, category) == services.catalog_report_old(engine, category)


def test_catalog_report_values(engine):
    rows = services.catalog_report(engine, 'Фантастика', card_discount=10)
    robot = [r for r in rows if r['Title'] == 'Я, робот'][0]
    assert robot['PriceWithCard'] == 486.0 and robot['Availability'] == 'заканчивается'


def test_catalog_report_without_discount(engine):
    rows = services.catalog_report(engine, 'Фантастика', card_discount=None)
    assert all(r['PriceWithCard'] is None for r in rows)


def test_books_up_to_price(engine):
    rows = services.books_up_to_price(engine, 400, 10)
    assert [r['Title'] for r in rows] == ['Евгений Онегин', 'Собака Баскервилей']


def test_sales_by_category_sorted_by_revenue(engine):
    rows = services.sales_by_category(engine, '2026-09-01', '2026-10-31')
    revenues = [r['Revenue'] for r in rows]
    assert revenues == sorted(revenues, reverse=True) and len(rows) >= 1


def test_customer_order_totals(engine):
    assert services.customer_order_totals(engine, 1, '2026-09-01', '2026-10-31') == {'Orders': 3, 'Total': 8060}


def test_customer_order_totals_empty_period(engine):
    assert services.customer_order_totals(engine, 1, '2020-01-01', '2020-01-31') == {'Orders': 0, 'Total': 0}
