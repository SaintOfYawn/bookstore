"""Процедуры серверной бизнес-логики «КнигаМир» (этап 2).

В SQLite нет хранимых процедур на сервере, поэтому процедура — это функция сервисного слоя:
она принимает соединение DB-API (из SQLAlchemy его даёт engine.raw_connection()), проверяет
параметры, выполняет SQL, при изменении нескольких таблиц работает в транзакции и при любой
ошибке пишет запись в ErrorLog и пробрасывает исключение вызывающему коду.

Стандарт именования: <таблица>_<действие> (snake_case), отчёты — report_<название>.
Коды ошибок (аналог THROW 5000x): 50001 — не найдено, 50002 — неверный параметр,
50003 — недостаточно книг, 50004 — нарушено бизнес-правило, 50005 — есть связанные данные.
"""
import functools
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime

NOT_FOUND, BAD_PARAM, NO_STOCK, RULE, HAS_LINKS = 50001, 50002, 50003, 50004, 50005
DATE_FORMAT = '%Y-%m-%d'
ORDER_STATUSES = ('новый', 'оплачен', 'выдан', 'отменён')
FINAL_STATUSES = ('выдан', 'отменён')
PAYMENT_METHODS = ('наличные', 'карта', 'онлайн')
MAX_DISCOUNT = 30
ISBN_LENGTH = 13
LOW_STOCK_LIMIT = 5


class ProcedureError(Exception):
    """Ошибка процедуры: code — код (50001…50005), message — понятный текст."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------- служебные средства
def rows_of(con, sql, params=()):
    """Выполняет SELECT и возвращает список словарей {столбец: значение}."""
    cursor = con.execute(sql, params)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


@contextmanager
def transaction(con):
    """Транзакция на SAVEPOINT: COMMIT при успехе, откат всех изменений блока при ошибке."""
    con.execute('SAVEPOINT proc')
    try:
        yield
    except BaseException:
        con.execute('ROLLBACK TO proc')
        con.execute('RELEASE proc')
        raise
    con.execute('RELEASE proc')
    con.commit()


def log_error(con, name, code, message):
    """Записывает ошибку процедуры в ErrorLog (отдельной зафиксированной операцией)."""
    con.execute('INSERT INTO ErrorLog (ProcedureName, ErrorCode, Message) VALUES (?, ?, ?)',
                (name, code, message))
    con.commit()


def procedure(function):
    """Декоратор процедуры: ошибку журналирует в ErrorLog и пробрасывает вызывающему коду."""
    @functools.wraps(function)
    def wrapper(con, *args, **kwargs):
        try:
            return function(con, *args, **kwargs)
        except (ProcedureError, sqlite3.Error) as error:
            log_error(con, function.__name__, getattr(error, 'code', 50000), str(error))
            raise
    return wrapper


def has_trigger(con, name):
    """True, если в базе есть триггер с таким именем (этап 4 переносит часть логики в триггеры)."""
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type = 'trigger' AND name = ?", (name,)).fetchone()
    return row is not None


def _exists(con, table, key, value):
    return con.execute('SELECT 1 FROM %s WHERE %s = ?' % (table, key), (value,)).fetchone() is not None


def _check_exists(con, table, key, value, label):
    if value is None or not _exists(con, table, key, value):
        raise ProcedureError(NOT_FOUND, '%s не найден(а): %s' % (label, value))


def _positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProcedureError(BAD_PARAM, '%s должно быть целым числом больше 0' % label)
    return value


def _parse_date(value, label):
    try:
        return datetime.strptime(value, DATE_FORMAT).strftime(DATE_FORMAT)
    except (TypeError, ValueError):
        raise ProcedureError(BAD_PARAM, '%s: ожидается дата ГГГГ-ММ-ДД' % label) from None


def _parse_price(value):
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise ProcedureError(BAD_PARAM, 'Цена должна быть числом') from None
    if not math.isfinite(price) or price <= 0:
        raise ProcedureError(BAD_PARAM, 'Цена должна быть конечным числом больше 0')
    return price


def _escape_like(value):
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


# ================================================================ 1. Процедуры выборки
@procedure
def books_get_all(con, only_active=True):
    """Все книги (по умолчанию только находящиеся в продаже), отсортированные по названию."""
    sql = 'SELECT BookID, Title, ISBN, Price, StockQty, IsActive FROM Books'
    if only_active:
        sql += ' WHERE IsActive = 1'
    return rows_of(con, sql + ' ORDER BY Title')


@procedure
def books_get_by_id(con, book_id):
    """Книга с названием издательства и категории; ProcedureError 50001, если книги нет."""
    rows = rows_of(con,
                   'SELECT b.BookID, b.Title, b.ISBN, b.Price, b.StockQty, b.IsActive, '
                   'p.Name AS Publisher, c.Name AS Category FROM Books b '
                   'JOIN Publishers p ON p.PublisherID = b.PublisherID '
                   'JOIN Categories c ON c.CategoryID = b.CategoryID WHERE b.BookID = ?', (book_id,))
    if not rows:
        raise ProcedureError(NOT_FOUND, 'Книга не найдена: %s' % book_id)
    return rows[0]


@procedure
def books_get_by_title(con, title_prefix):
    """Книги, название которых начинается с заданной строки (символы % и _ — обычные)."""
    if not title_prefix or not title_prefix.strip():
        raise ProcedureError(BAD_PARAM, 'Укажите начало названия книги')
    return rows_of(con, "SELECT BookID, Title, Price, StockQty FROM Books WHERE Title LIKE ? ESCAPE '\\' "
                        'ORDER BY Title', (_escape_like(title_prefix.strip()) + '%',))


@procedure
def books_get_by_category(con, category_name=None, only_in_stock=False):
    """Книги в продаже выбранной категории, включая вложенные; None — все категории."""
    sql = ('SELECT b.BookID, b.Title, p.Name AS Publisher, c.Name AS Category, b.Price, b.StockQty '
           'FROM Books b JOIN Publishers p ON p.PublisherID = b.PublisherID '
           'JOIN Categories c ON c.CategoryID = b.CategoryID '
           'LEFT JOIN Categories parent ON parent.CategoryID = c.ParentCategoryID WHERE b.IsActive = 1')
    params = []
    if category_name:
        sql += ' AND (c.Name = ? OR parent.Name = ?)'
        params += [category_name, category_name]
    if only_in_stock:
        sql += ' AND b.StockQty > 0'
    return rows_of(con, sql + ' ORDER BY b.Title', params)


@procedure
def customers_get_by_phone(con, phone):
    """Покупатель по номеру телефона; ProcedureError 50001, если не найден."""
    rows = rows_of(con, 'SELECT CustomerID, LastName, FirstName, Phone, Email, DiscountPercent '
                        'FROM Customers WHERE Phone = ?', (phone,))
    if not rows:
        raise ProcedureError(NOT_FOUND, 'Покупатель не найден: %s' % phone)
    return rows[0]


@procedure
def authors_get_by_name(con, last_name_prefix):
    """Авторы, фамилия которых начинается с заданной строки, и число их книг."""
    if not last_name_prefix or not last_name_prefix.strip():
        raise ProcedureError(BAD_PARAM, 'Укажите начало фамилии автора')
    return rows_of(con, 'SELECT a.AuthorID, a.LastName, a.FirstName, COUNT(ba.BookID) AS BooksCount '
                        'FROM Authors a LEFT JOIN BookAuthors ba ON ba.AuthorID = a.AuthorID '
                        "WHERE a.LastName LIKE ? ESCAPE '\\' GROUP BY a.AuthorID ORDER BY a.LastName, a.FirstName",
                   (_escape_like(last_name_prefix.strip()) + '%',))


@procedure
def orders_get_by_customer(con, customer_id, date_from=None, date_to=None):
    """Заказы покупателя с суммой; период необязателен (даты ГГГГ-ММ-ДД включительно)."""
    _check_exists(con, 'Customers', 'CustomerID', customer_id, 'Покупатель')
    sql = ('SELECT o.OrderID, o.OrderDate, o.Status, SUM(oi.Quantity * oi.UnitPrice) AS Total '
           'FROM Orders o JOIN OrderItems oi ON oi.OrderID = o.OrderID WHERE o.CustomerID = ?')
    params = [customer_id]
    if date_from is not None:
        sql += ' AND date(o.OrderDate) >= ?'
        params.append(_parse_date(date_from, 'Дата начала'))
    if date_to is not None:
        sql += ' AND date(o.OrderDate) <= ?'
        params.append(_parse_date(date_to, 'Дата окончания'))
    return rows_of(con, sql + ' GROUP BY o.OrderID ORDER BY o.OrderDate', params)


# ================================================================ 2. Добавление, изменение, удаление
@procedure
def books_create(con, title, isbn, publisher_id, category_id, publish_year, pages, price, stock_qty=0):
    """Добавляет книгу и возвращает её код (аналог OUTPUT-параметра @BookID)."""
    if not title or not title.strip():
        raise ProcedureError(BAD_PARAM, 'Введите название книги')
    if not isinstance(isbn, str) or len(isbn) != ISBN_LENGTH or not isbn.isdigit():
        raise ProcedureError(BAD_PARAM, 'ISBN должен содержать %d цифр' % ISBN_LENGTH)
    price = _parse_price(price)
    if isinstance(stock_qty, bool) or not isinstance(stock_qty, int) or stock_qty < 0:
        raise ProcedureError(BAD_PARAM, 'Остаток должен быть целым числом не меньше 0')
    _check_exists(con, 'Publishers', 'PublisherID', publisher_id, 'Издательство')
    _check_exists(con, 'Categories', 'CategoryID', category_id, 'Категория')
    if _exists(con, 'Books', 'ISBN', isbn):
        raise ProcedureError(RULE, 'Книга с таким ISBN уже есть')
    with transaction(con):
        cursor = con.execute('INSERT INTO Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, '
                             'Price, StockQty) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                             (title.strip(), isbn, publisher_id, category_id, publish_year, pages, price, stock_qty))
    return cursor.lastrowid


@procedure
def books_update_price(con, book_id, new_price):
    """Меняет цену книги; возвращает прежнюю цену."""
    new_price = _parse_price(new_price)
    book = books_get_by_id.__wrapped__(con, book_id)
    with transaction(con):
        con.execute('UPDATE Books SET Price = ? WHERE BookID = ?', (new_price, book_id))
    return book['Price']


@procedure
def books_delete(con, book_id):
    """Удаляет книгу без истории. Возвращает код: 0 — удалена, 50001 — нет такой, 50005 — есть продажи/поставки."""
    if not _exists(con, 'Books', 'BookID', book_id):
        return NOT_FOUND
    linked = con.execute('SELECT (SELECT COUNT(*) FROM OrderItems WHERE BookID = ?) + '
                         '(SELECT COUNT(*) FROM SupplyItems WHERE BookID = ?)', (book_id, book_id)).fetchone()[0]
    if linked:
        return HAS_LINKS
    with transaction(con):
        con.execute('DELETE FROM Books WHERE BookID = ?', (book_id,))
    return 0


@procedure
def customers_create(con, last_name, first_name, phone, email=None, discount_percent=0):
    """Регистрирует покупателя и возвращает его код (аналог OUTPUT-параметра)."""
    if not last_name or not last_name.strip() or not first_name or not first_name.strip():
        raise ProcedureError(BAD_PARAM, 'Укажите фамилию и имя покупателя')
    if not phone or not phone.strip():
        raise ProcedureError(BAD_PARAM, 'Укажите телефон покупателя')
    if isinstance(discount_percent, bool) or not isinstance(discount_percent, int) \
            or not 0 <= discount_percent <= MAX_DISCOUNT:
        raise ProcedureError(BAD_PARAM, 'Скидка должна быть целым числом от 0 до %d' % MAX_DISCOUNT)
    if _exists(con, 'Customers', 'Phone', phone.strip()):
        raise ProcedureError(RULE, 'Покупатель с таким телефоном уже есть')
    with transaction(con):
        cursor = con.execute('INSERT INTO Customers (LastName, FirstName, Phone, Email, DiscountPercent) '
                             'VALUES (?, ?, ?, ?, ?)',
                             (last_name.strip(), first_name.strip(), phone.strip(), email, discount_percent))
    return cursor.lastrowid


@procedure
def customers_update_discount(con, customer_id, discount_percent):
    """Меняет скидку покупателя; возвращает прежнюю скидку."""
    if isinstance(discount_percent, bool) or not isinstance(discount_percent, int) \
            or not 0 <= discount_percent <= MAX_DISCOUNT:
        raise ProcedureError(BAD_PARAM, 'Скидка должна быть целым числом от 0 до %d' % MAX_DISCOUNT)
    _check_exists(con, 'Customers', 'CustomerID', customer_id, 'Покупатель')
    old = con.execute('SELECT DiscountPercent FROM Customers WHERE CustomerID = ?', (customer_id,)).fetchone()[0]
    with transaction(con):
        con.execute('UPDATE Customers SET DiscountPercent = ? WHERE CustomerID = ?', (discount_percent, customer_id))
    return old


def _create_order(con, customer_id, employee_id, payment_method):
    if customer_id is not None:
        _check_exists(con, 'Customers', 'CustomerID', customer_id, 'Покупатель')
    _check_exists(con, 'Employees', 'EmployeeID', employee_id, 'Сотрудник')
    if payment_method not in PAYMENT_METHODS:
        raise ProcedureError(BAD_PARAM, 'Способ оплаты: %s' % ', '.join(PAYMENT_METHODS))
    cursor = con.execute('INSERT INTO Orders (CustomerID, EmployeeID, PaymentMethod) VALUES (?, ?, ?)',
                         (customer_id, employee_id, payment_method))
    return cursor.lastrowid


def _add_item(con, order_id, book_id, quantity):
    _positive_int(quantity, 'Количество')
    status = con.execute('SELECT Status FROM Orders WHERE OrderID = ?', (order_id,)).fetchone()
    if status is None:
        raise ProcedureError(NOT_FOUND, 'Заказ не найден: %s' % order_id)
    if status[0] != 'новый':
        raise ProcedureError(RULE, 'Позиции можно добавлять только в новый заказ')
    book = con.execute('SELECT Price, StockQty, IsActive FROM Books WHERE BookID = ?', (book_id,)).fetchone()
    if book is None or not book[2]:
        raise ProcedureError(NOT_FOUND, 'Книга не найдена или снята с продажи: %s' % book_id)
    if con.execute('SELECT 1 FROM OrderItems WHERE OrderID = ? AND BookID = ?', (order_id, book_id)).fetchone():
        raise ProcedureError(RULE, 'Эта книга уже есть в заказе')
    if quantity > book[1]:
        raise ProcedureError(NO_STOCK, 'Недостаточно книг на складе: есть %d, нужно %d' % (book[1], quantity))
    con.execute('INSERT INTO OrderItems (OrderID, BookID, Quantity, UnitPrice) VALUES (?, ?, ?, ?)',
                (order_id, book_id, quantity, book[0]))
    if not has_trigger(con, 'trg_OrderItems_DecreaseStock'):     # с триггерами этапа 4 остаток спишет триггер
        con.execute('UPDATE Books SET StockQty = StockQty - ? WHERE BookID = ?', (quantity, book_id))
    return quantity * book[0]


@procedure
def orders_create(con, customer_id, employee_id, payment_method):
    """Создаёт пустой заказ в статусе «новый» и возвращает его номер (аналог OUTPUT-параметра)."""
    with transaction(con):
        return _create_order(con, customer_id, employee_id, payment_method)


@procedure
def orders_add_item(con, order_id, book_id, quantity):
    """Добавляет позицию в новый заказ по текущей цене, списывает остаток; возвращает сумму позиции."""
    with transaction(con):
        return _add_item(con, order_id, book_id, quantity)


@procedure
def orders_place(con, customer_id, employee_id, payment_method, items):
    """Оформляет заказ целиком: создаёт заказ и все позиции в одной транзакции.

    items — список пар (код книги, количество). Любая ошибка откатывает заказ полностью.
    Возвращает номер заказа.
    """
    if not items:
        raise ProcedureError(BAD_PARAM, 'Заказ не может быть пустым')
    with transaction(con):
        order_id = _create_order(con, customer_id, employee_id, payment_method)
        for book_id, quantity in items:
            _add_item(con, order_id, book_id, quantity)
    return order_id


@procedure
def orders_set_status(con, order_id, new_status):
    """Меняет статус заказа по правилам; при отмене возвращает книги на склад. Возвращает код 0."""
    if new_status not in ORDER_STATUSES:
        raise ProcedureError(BAD_PARAM, 'Допустимые статусы: %s' % ', '.join(ORDER_STATUSES))
    row = con.execute('SELECT Status FROM Orders WHERE OrderID = ?', (order_id,)).fetchone()
    if row is None:
        raise ProcedureError(NOT_FOUND, 'Заказ не найден: %s' % order_id)
    old_status = row[0]
    if new_status == old_status:
        return 0
    if old_status in FINAL_STATUSES:
        raise ProcedureError(RULE, 'Нельзя изменить статус завершённого заказа')
    if old_status == 'новый' and new_status == 'выдан':
        raise ProcedureError(RULE, 'Заказ нужно сначала оплатить')
    with transaction(con):
        con.execute('UPDATE Orders SET Status = ? WHERE OrderID = ?', (new_status, order_id))
        if new_status == 'отменён' and not has_trigger(con, 'trg_Orders_Cancel_ReturnStock'):
            con.execute('UPDATE Books SET StockQty = StockQty + (SELECT oi.Quantity FROM OrderItems oi '
                        'WHERE oi.OrderID = ? AND oi.BookID = Books.BookID) '
                        'WHERE BookID IN (SELECT BookID FROM OrderItems WHERE OrderID = ?)', (order_id, order_id))
    return 0


@procedure
def supply_receive(con, supply_order_id):
    """Принимает поставку: статус «получен» и увеличение остатков; возвращает число принятых позиций."""
    row = con.execute('SELECT Status FROM SupplyOrders WHERE SupplyOrderID = ?', (supply_order_id,)).fetchone()
    if row is None:
        raise ProcedureError(NOT_FOUND, 'Заказ поставщику не найден: %s' % supply_order_id)
    if row[0] == 'получен':
        raise ProcedureError(RULE, 'Поставка уже принята')
    if row[0] == 'отменён':
        raise ProcedureError(RULE, 'Нельзя принять отменённый заказ поставщику')
    with transaction(con):
        con.execute("UPDATE SupplyOrders SET Status = 'получен' WHERE SupplyOrderID = ?", (supply_order_id,))
        if not has_trigger(con, 'trg_SupplyOrders_Received_IncreaseStock'):
            con.execute('UPDATE Books SET StockQty = StockQty + (SELECT si.Quantity FROM SupplyItems si '
                        'WHERE si.SupplyOrderID = ? AND si.BookID = Books.BookID) '
                        'WHERE BookID IN (SELECT BookID FROM SupplyItems WHERE SupplyOrderID = ?)',
                        (supply_order_id, supply_order_id))
    return con.execute('SELECT COUNT(*) FROM SupplyItems WHERE SupplyOrderID = ?', (supply_order_id,)).fetchone()[0]


# ================================================================ 3. Процедуры с результатом-«OUTPUT»
@procedure
def orders_count_by_customer(con, customer_id):
    """Количество заказов покупателя, кроме отменённых (аналог OUTPUT-параметра @Количество)."""
    _check_exists(con, 'Customers', 'CustomerID', customer_id, 'Покупатель')
    return con.execute("SELECT COUNT(*) FROM Orders WHERE CustomerID = ? AND Status <> 'отменён'",
                       (customer_id,)).fetchone()[0]


@procedure
def books_stock_summary(con, category_name=None):
    """Возвращает пару (число наименований, число экземпляров на складе) по категории или по всем книгам."""
    rows = books_get_by_category.__wrapped__(con, category_name)
    return len(rows), sum(row['StockQty'] for row in rows)


# ================================================================ 4. Отчётные процедуры
@procedure
def report_revenue_by_period(con, date_from, date_to):
    """Выручка по дням за период (оплаченные и выданные заказы, с учётом скидки покупателя)."""
    date_from = _parse_date(date_from, 'Дата начала')
    date_to = _parse_date(date_to, 'Дата окончания')
    if date_from > date_to:
        raise ProcedureError(BAD_PARAM, 'Дата начала не может быть позже даты окончания')
    return rows_of(con,
                   'SELECT date(o.OrderDate) AS SaleDate, COUNT(DISTINCT o.OrderID) AS OrdersCount, '
                   'SUM(oi.Quantity) AS BooksSold, '
                   'ROUND(SUM(oi.Quantity * oi.UnitPrice * (100 - IFNULL(c.DiscountPercent, 0)) / 100.0), 2) AS Revenue '
                   'FROM Orders o JOIN OrderItems oi ON oi.OrderID = o.OrderID '
                   'LEFT JOIN Customers c ON c.CustomerID = o.CustomerID '
                   "WHERE o.Status IN ('оплачен', 'выдан') AND date(o.OrderDate) BETWEEN ? AND ? "
                   'GROUP BY date(o.OrderDate) ORDER BY SaleDate', (date_from, date_to))


@procedure
def report_top_books(con, date_from, date_to, limit=5):
    """Самые продаваемые книги за период: количество и выручка (без учёта скидки)."""
    date_from = _parse_date(date_from, 'Дата начала')
    date_to = _parse_date(date_to, 'Дата окончания')
    _positive_int(limit, 'Размер списка')
    return rows_of(con,
                   'SELECT b.Title, a.LastName AS Author, SUM(oi.Quantity) AS Sold, '
                   'SUM(oi.Quantity * oi.UnitPrice) AS Revenue FROM OrderItems oi '
                   'JOIN Orders o ON o.OrderID = oi.OrderID JOIN Books b ON b.BookID = oi.BookID '
                   'JOIN BookAuthors ba ON ba.BookID = b.BookID AND ba.AuthorOrder = 1 '
                   'JOIN Authors a ON a.AuthorID = ba.AuthorID '
                   "WHERE o.Status IN ('оплачен', 'выдан') AND date(o.OrderDate) BETWEEN ? AND ? "
                   'GROUP BY b.BookID ORDER BY Sold DESC, Revenue DESC, b.Title LIMIT ?',
                   (date_from, date_to, limit))


@procedure
def report_low_stock(con, threshold=LOW_STOCK_LIMIT):
    """Книги в продаже с остатком меньше порога — список к заказу поставщику."""
    _positive_int(threshold, 'Порог остатка')
    return rows_of(con, 'SELECT b.BookID, b.Title, p.Name AS Publisher, b.StockQty FROM Books b '
                        'JOIN Publishers p ON p.PublisherID = b.PublisherID '
                        'WHERE b.IsActive = 1 AND b.StockQty < ? ORDER BY b.StockQty, b.Title', (threshold,))
