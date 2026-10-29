"""Многооператорная табличная функция stock_forecast (DataFrame Pandas)."""
import pytest

from bookstore_functions import stock_forecast

AS_OF = '2026-10-12'


def row(frame, book_id):
    return frame[frame['BookID'] == book_id].iloc[0]


def test_columns_and_size(con):
    frame = stock_forecast(con, AS_OF)
    assert list(frame.columns) == ['BookID', 'Title', 'StockQty', 'Sold', 'PerDay', 'DaysLeft', 'Status']
    assert len(frame) == 25


def test_out_of_stock_first(con):
    frame = stock_forecast(con, AS_OF)
    assert frame.iloc[0]['BookID'] == 25 and frame.iloc[0]['Status'] == 'нет в наличии'


def test_low_stock_status(con):
    frame = stock_forecast(con, AS_OF)
    assert row(frame, 8)['Status'] == 'заканчивается' and row(frame, 8)['DaysLeft'] == 23.1


def test_urgent_when_lead_time_is_long(con):
    frame = stock_forecast(con, AS_OF, lead_days=30)
    assert row(frame, 8)['Status'] == 'заказать срочно'
    assert row(frame, 14)['Status'] == 'заканчивается'


def test_book_without_sales_has_no_days_left(con):
    frame = stock_forecast(con, AS_OF)
    book = row(frame, 3)
    assert book['Sold'] == 0 and book['PerDay'] == 0 and book['DaysLeft'] != book['DaysLeft']  # NaN
    assert book['Status'] == 'достаточно'


def test_status_counts(con):
    counts = stock_forecast(con, AS_OF)['Status'].value_counts().to_dict()
    assert counts == {'достаточно': 22, 'заканчивается': 2, 'нет в наличии': 1}


def test_period_without_sales(con):
    frame = stock_forecast(con, '2020-01-31')
    assert (frame['Sold'] == 0).all() and set(frame['Status']) == {'нет в наличии', 'достаточно', 'заканчивается'}
