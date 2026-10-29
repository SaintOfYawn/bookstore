"""Сервисный слой: отчёты каталога до и после применения пользовательских функций."""
from sqlalchemy import func, select, text

from bookstore_functions import (books, books_by_category, categories, customer_orders,
                                 LOW_STOCK_LIMIT, top_sellers)


# ---- До: расчёты размазаны по методу (стиль этапа 2) ------------------------------------
def catalog_report_old(engine, category=None, card_discount=10):
    """Каталог с ценой по карте и признаком наличия — вся логика внутри метода."""
    sql = ('SELECT b.Title, p.Name AS Publisher, b.Price, b.StockQty FROM Books b '
           'JOIN Publishers p ON p.PublisherID = b.PublisherID '
           'JOIN Categories c ON c.CategoryID = b.CategoryID '
           'LEFT JOIN Categories parent ON parent.CategoryID = c.ParentCategoryID '
           'WHERE b.IsActive = 1')
    params = {}
    if category:
        sql += ' AND (c.Name = :category OR parent.Name = :category)'
        params['category'] = category
    sql += ' ORDER BY b.Title'
    result = []
    with engine.connect() as con:
        for row in con.execute(text(sql), params):
            if row.Price is None or card_discount is None or not 0 <= card_discount <= 100:
                price_with_card = None
            else:
                price_with_card = round(row.Price * (100 - card_discount) / 100, 2)
            if row.StockQty is None:
                availability = None
            elif row.StockQty <= 0:
                availability = 'нет в наличии'
            elif row.StockQty < LOW_STOCK_LIMIT:
                availability = 'заканчивается'
            else:
                availability = 'в наличии'
            result.append({'Title': row.Title, 'Publisher': row.Publisher, 'Price': row.Price,
                           'PriceWithCard': price_with_card, 'Availability': availability})
    return result


# ---- После: используются inline-функция и скалярные функции ----------------------------
def catalog_report(engine, category=None, card_discount=10):
    """Каталог с ценой по карте и признаком наличия."""
    base = books_by_category(category).subquery()
    query = (select(base.c.Title, base.c.Publisher, base.c.Price,
                    func.fn_price_with_discount(base.c.Price, card_discount).label('PriceWithCard'),
                    func.fn_availability(base.c.StockQty, LOW_STOCK_LIMIT).label('Availability'))
             .order_by(base.c.Title))
    with engine.connect() as con:
        return [dict(row._mapping) for row in con.execute(query)]


def books_up_to_price(engine, limit, discount):
    """Книги, цена которых со скидкой не выше limit (скалярная функция в WHERE и ORDER BY)."""
    discounted = func.fn_price_with_discount(books.c.Price, discount)
    query = (select(books.c.Title, books.c.Price, discounted.label('PriceWithCard'))
             .where(books.c.IsActive == 1, discounted <= limit)
             .order_by(discounted, books.c.Title))
    with engine.connect() as con:
        return [dict(row._mapping) for row in con.execute(query)]


def sales_by_category(engine, date_from, date_to):
    """Продано книг и выручка по категориям: табличная функция top_sellers в подзапросе и JOIN."""
    sold = top_sellers(date_from, date_to).subquery()
    query = (select(categories.c.Name.label('Category'), func.sum(sold.c.Sold).label('Sold'),
                    func.sum(sold.c.Revenue).label('Revenue'))
             .join(books, books.c.CategoryID == categories.c.CategoryID)
             .join(sold, sold.c.BookID == books.c.BookID)
             .group_by(categories.c.Name)
             .order_by(func.sum(sold.c.Revenue).desc()))
    with engine.connect() as con:
        return [dict(row._mapping) for row in con.execute(query)]


def customer_order_totals(engine, customer_id, date_from, date_to):
    """Количество и сумма заказов покупателя за период: customer_orders в подзапросе."""
    sub = customer_orders(customer_id, date_from, date_to).subquery()
    query = (select(func.count(sub.c.OrderID).label('Orders'),
                    func.coalesce(func.sum(sub.c.Total), 0).label('Total'))
             .select_from(sub))
    with engine.connect() as con:
        row = con.execute(query).one()
    return {'Orders': row.Orders, 'Total': row.Total}
