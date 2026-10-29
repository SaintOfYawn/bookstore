"""Пользовательские функции базы данных «КнигаМир».

Скалярные функции регистрируются в соединении SQLite (create_function) и вызываются
из SQL как fn_*. Inline табличные функции возвращают параметризованный запрос select()
SQLAlchemy. Многооператорная табличная функция обрабатывает данные в DataFrame Pandas.
"""
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import (Column, Date, Integer, MetaData, Float, String, Table, event,
                        func, or_, select)

LOW_STOCK_LIMIT = 5          # остаток меньше этого значения — книга заканчивается
DATE_FORMAT = '%Y-%m-%d'
PAID_STATUSES = ('оплачен', 'выдан')

# ---------------------------------------------------------------- скалярные функции


def price_with_discount(price, percent):
    """Цена со скидкой, округлённая до копеек.

    Параметры: price — цена, percent — скидка 0–100 %.
    Возвращает число или None (если аргумент None или скидка вне диапазона 0–100).
    Пример: price_with_discount(100, 20) -> 80.0
    """
    if price is None or percent is None:
        return None
    if not 0 <= percent <= 100:
        return None
    return round(price * (100 - percent) / 100, 2)


def short_name(last_name, first_name, middle_name):
    """ФИО в краткой форме «Фамилия И. О.».

    Возвращает None, если фамилия не задана; имя и отчество необязательны.
    Пример: short_name('Орлова', 'Мария', 'Игоревна') -> 'Орлова М. И.'
    """
    if not last_name or not last_name.strip():
        return None
    parts = [last_name.strip()]
    for part in (first_name, middle_name):
        if part and part.strip():
            parts.append(part.strip()[0].upper() + '.')
    return ' '.join(parts)


def availability(stock, low_limit):
    """Признак наличия книги: «нет в наличии», «заканчивается» или «в наличии».

    Параметры: stock — остаток, low_limit — порог «заканчивается».
    Возвращает None, если любой аргумент равен None.
    Пример: availability(3, 5) -> 'заканчивается'
    """
    if stock is None or low_limit is None:
        return None
    if stock <= 0:
        return 'нет в наличии'
    if stock < low_limit:
        return 'заканчивается'
    return 'в наличии'


def days_between(date_from, date_to):
    """Число дней между двумя датами (строки ISO; время игнорируется).

    Возвращает None, если дата не задана или не распознана.
    Пример: days_between('2026-09-01T10:00:00', '2026-10-12') -> 41
    """
    if date_from is None or date_to is None:
        return None
    try:
        start = datetime.strptime(str(date_from)[:10], DATE_FORMAT)
        end = datetime.strptime(str(date_to)[:10], DATE_FORMAT)
    except ValueError:
        return None
    return (end - start).days


SCALAR_FUNCTIONS = (
    ('fn_price_with_discount', 2, price_with_discount),
    ('fn_short_name', 3, short_name),
    ('fn_availability', 2, availability),
    ('fn_days_between', 2, days_between),
)


def register_functions(dbapi_connection):
    """Регистрирует скалярные функции в соединении sqlite3."""
    for name, args_count, function in SCALAR_FUNCTIONS:
        dbapi_connection.create_function(name, args_count, function, deterministic=True)


def make_engine(engine):
    """Подключает регистрацию функций к каждому новому соединению движка SQLAlchemy."""
    @event.listens_for(engine, 'connect')
    def on_connect(dbapi_connection, record):
        dbapi_connection.execute('PRAGMA foreign_keys = ON')
        register_functions(dbapi_connection)
    return engine


# ---------------------------------------------------------------- описание таблиц
metadata = MetaData()
books = Table('Books', metadata,
              Column('BookID', Integer, primary_key=True), Column('Title', String),
              Column('PublisherID', Integer), Column('CategoryID', Integer),
              Column('Price', Float), Column('StockQty', Integer), Column('IsActive', Integer))
publishers = Table('Publishers', metadata,
                   Column('PublisherID', Integer, primary_key=True), Column('Name', String))
categories = Table('Categories', metadata,
                   Column('CategoryID', Integer, primary_key=True), Column('Name', String),
                   Column('ParentCategoryID', Integer))
customers = Table('Customers', metadata,
                  Column('CustomerID', Integer, primary_key=True), Column('LastName', String),
                  Column('FirstName', String), Column('DiscountPercent', Integer))
orders = Table('Orders', metadata,
               Column('OrderID', Integer, primary_key=True), Column('CustomerID', Integer),
               Column('EmployeeID', Integer), Column('OrderDate', String), Column('Status', String))
order_items = Table('OrderItems', metadata,
                    Column('OrderID', Integer, primary_key=True), Column('BookID', Integer, primary_key=True),
                    Column('Quantity', Integer), Column('UnitPrice', Float))

# ---------------------------------------------------------------- inline табличные функции


def customer_orders(customer_id, date_from, date_to):
    """Заказы покупателя за период с суммой каждого заказа.

    Параметры: customer_id — код покупателя; date_from, date_to — даты 'ГГГГ-ММ-ДД' (включительно).
    Возвращает select() со столбцами OrderID, OrderDate, Status, Total.
    Пример: sub = customer_orders(5, '2026-09-01', '2026-09-30').subquery()
    """
    total = func.sum(order_items.c.Quantity * order_items.c.UnitPrice).label('Total')
    return (select(orders.c.OrderID, orders.c.OrderDate, orders.c.Status, total)
            .join(order_items, order_items.c.OrderID == orders.c.OrderID)
            .where(orders.c.CustomerID == customer_id,
                   func.date(orders.c.OrderDate).between(date_from, date_to))
            .group_by(orders.c.OrderID, orders.c.OrderDate, orders.c.Status))


def books_by_category(category_name=None):
    """Книги в продаже выбранной категории, включая вложенные категории.

    Параметр: category_name — название категории; None — все категории.
    Возвращает select() со столбцами BookID, Title, Publisher, Category, Price, StockQty.
    Пример: books_by_category('Фантастика')
    """
    parent = categories.alias('parent')
    query = (select(books.c.BookID, books.c.Title, publishers.c.Name.label('Publisher'),
                    categories.c.Name.label('Category'), books.c.Price, books.c.StockQty)
             .join(publishers, publishers.c.PublisherID == books.c.PublisherID)
             .join(categories, categories.c.CategoryID == books.c.CategoryID)
             .outerjoin(parent, parent.c.CategoryID == categories.c.ParentCategoryID)
             .where(books.c.IsActive == 1))
    if category_name:
        query = query.where(or_(categories.c.Name == category_name, parent.c.Name == category_name))
    return query


def top_sellers(date_from, date_to):
    """Продажи книг за период (оплаченные и выданные заказы): количество и выручка.

    Параметры: date_from, date_to — даты 'ГГГГ-ММ-ДД' (включительно).
    Возвращает select() со столбцами BookID, Sold, Revenue.
    Пример: sub = top_sellers('2026-09-01', '2026-09-30').subquery()
    """
    return (select(order_items.c.BookID,
                   func.sum(order_items.c.Quantity).label('Sold'),
                   func.sum(order_items.c.Quantity * order_items.c.UnitPrice).label('Revenue'))
            .join(orders, orders.c.OrderID == order_items.c.OrderID)
            .where(orders.c.Status.in_(PAID_STATUSES),
                   func.date(orders.c.OrderDate).between(date_from, date_to))
            .group_by(order_items.c.BookID))


# ---------------------------------------------------------------- многооператорная табличная функция
STOCK_SQL = 'SELECT BookID, Title, StockQty FROM Books WHERE IsActive = 1'
SALES_SQL = ("SELECT oi.BookID, SUM(oi.Quantity) AS Sold FROM OrderItems oi "
             "JOIN Orders o ON o.OrderID = oi.OrderID "
             "WHERE o.Status IN ('оплачен', 'выдан') "
             "AND date(o.OrderDate) BETWEEN :date_from AND :date_to GROUP BY oi.BookID")
STATUS_ORDER = {'нет в наличии': 0, 'заказать срочно': 1, 'заканчивается': 2, 'достаточно': 3}


def stock_forecast(connection, as_of, days=30, low_limit=LOW_STOCK_LIMIT, lead_days=14):
    """Прогноз остатков: на сколько дней хватит книги и что с ней делать.

    Шаги: 1) остатки из БД; 2) продажи за последние days дней; 3) объединение;
    4) средние продажи в день и запас в днях; 5) статус по ветвлениям (numpy.select).
    Параметры: connection — соединение (SQLAlchemy или sqlite3); as_of — дата отчёта
    'ГГГГ-ММ-ДД'; days — глубина анализа продаж; low_limit — порог «заканчивается»;
    lead_days — срок поставки в днях.
    Возвращает DataFrame: BookID, Title, StockQty, Sold, PerDay, DaysLeft, Status.
    Пример: stock_forecast(engine.connect(), '2026-10-12')
    """
    end = datetime.strptime(as_of, DATE_FORMAT)
    start = end - timedelta(days=days)
    stock = pd.read_sql(STOCK_SQL, connection)
    sales = pd.read_sql(SALES_SQL, connection,
                        params={'date_from': start.strftime(DATE_FORMAT), 'date_to': as_of})
    result = stock.merge(sales, on='BookID', how='left')
    result['Sold'] = result['Sold'].fillna(0).astype(int)
    result['PerDay'] = (result['Sold'] / days).round(2)
    with np.errstate(divide='ignore'):
        days_left = np.where(result['PerDay'] > 0, result['StockQty'] / result['PerDay'], np.inf)
    result['DaysLeft'] = pd.Series(days_left).round(1).replace(np.inf, np.nan)
    conditions = [result['StockQty'] <= 0, days_left < lead_days, result['StockQty'] < low_limit]
    choices = ['нет в наличии', 'заказать срочно', 'заканчивается']
    result['Status'] = np.select(conditions, choices, default='достаточно')
    result['_order'] = result['Status'].map(STATUS_ORDER)
    result = result.sort_values(['_order', 'DaysLeft', 'Title']).drop(columns='_order')
    return result.reset_index(drop=True)
