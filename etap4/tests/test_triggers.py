"""Триггеры БД: аудит (AFTER), контроль бизнес-правил (BEFORE + RAISE), INSTEAD OF."""
import sqlite3

import pytest

from create_db import set_user


def audit(con, table, record_id=None):
    sql = 'SELECT Operation, OldValue, NewValue, ChangedBy FROM AuditLog WHERE TableName = ?'
    params = [table]
    if record_id is not None:
        sql += ' AND RecordID = ?'
        params.append(record_id)
    return con.execute(sql + ' ORDER BY AuditID', params).fetchall()


def stock(con, book_id):
    return con.execute('SELECT StockQty FROM Books WHERE BookID = ?', (book_id,)).fetchone()[0]


def new_order(con):
    cursor = con.execute("INSERT INTO Orders (CustomerID, EmployeeID, PaymentMethod) VALUES (1, 1, 'карта')")
    return cursor.lastrowid


# ------------------------------------------------------------------ аудит
def test_audit_update_price(con):
    con.execute('UPDATE Books SET Price = 1300 WHERE BookID = 1')
    rows = audit(con, 'Books', 1)
    assert len(rows) == 1 and rows[0][0] == 'UPDATE'
    assert 'Price=1290' in rows[0][1] and 'Price=1300' in rows[0][2]


def test_audit_user_from_context(con):
    con.execute('UPDATE Books SET Price = 1300 WHERE BookID = 1')
    set_user(con, 'manager')
    con.execute('UPDATE Books SET Price = 1310 WHERE BookID = 1')
    assert [r[3] for r in audit(con, 'Books', 1)] == ['system', 'manager']


def test_audit_insert_book(con):
    book_id = con.execute("INSERT INTO Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) "
                          "VALUES ('Тест', '9785000000011', 1, 2, 2024, 100, 100)").lastrowid
    rows = audit(con, 'Books', book_id)
    assert rows[0][0] == 'INSERT' and rows[0][1] is None and 'Title=Тест' in rows[0][2]


def test_audit_delete_book(con):
    con.execute('DELETE FROM Books WHERE BookID = 16')
    rows = audit(con, 'Books', 16)
    assert rows[0][0] == 'DELETE' and 'Алгоритмы' in rows[0][1] and rows[0][2] is None


def test_audit_multirow_update(con):
    con.execute('UPDATE Books SET Price = Price + 10 WHERE CategoryID = 3')
    assert len(audit(con, 'Books')) == 5


def test_no_audit_when_nothing_tracked_changed(con):
    con.execute('UPDATE Books SET Pages = Pages + 1 WHERE BookID = 1')
    assert audit(con, 'Books') == []


def test_audit_customer_discount(con):
    con.execute('UPDATE Customers SET DiscountPercent = 15 WHERE CustomerID = 1')
    rows = audit(con, 'Customers', 1)
    assert len(rows) == 1 and 'Discount=0' in rows[0][1] and 'Discount=15' in rows[0][2]


def test_audit_order_status(con):
    con.execute("UPDATE Orders SET Status = 'оплачен' WHERE OrderID = 14")
    rows = audit(con, 'Orders', 14)
    assert rows == [('UPDATE', 'Status=новый', 'Status=оплачен', 'system')]


# ------------------------------------------------------------------ контроль: остатки
def test_item_exceeding_stock_rejected(con):
    order_id = new_order(con)
    with pytest.raises(sqlite3.IntegrityError, match='Недостаточно книг на складе'):
        con.execute('INSERT INTO OrderItems VALUES (?, 8, 4, 540)', (order_id,))
    assert stock(con, 8) == 3
    assert con.execute('SELECT COUNT(*) FROM OrderItems WHERE OrderID = ?', (order_id,)).fetchone()[0] == 0


def test_item_for_out_of_stock_book_rejected(con):
    order_id = new_order(con)
    with pytest.raises(sqlite3.IntegrityError, match='Недостаточно книг'):
        con.execute('INSERT INTO OrderItems VALUES (?, 25, 1, 450)', (order_id,))


def test_item_equal_to_stock_accepted(con):
    order_id = new_order(con)
    con.execute('INSERT INTO OrderItems VALUES (?, 8, 3, 540)', (order_id,))
    assert stock(con, 8) == 0


def test_item_decreases_stock_and_is_audited(con):
    order_id = new_order(con)
    con.execute('INSERT INTO OrderItems VALUES (?, 13, 2, 1890)', (order_id,))
    assert stock(con, 13) == 12
    rows = audit(con, 'Books', 13)
    assert len(rows) == 1 and 'StockQty=14' in rows[0][1] and 'StockQty=12' in rows[0][2]


def test_multirow_insert_valid(con):
    order_id = new_order(con)
    con.execute('INSERT INTO OrderItems VALUES (?, 13, 2, 1890), (?, 8, 2, 540)', (order_id, order_id))
    assert (stock(con, 13), stock(con, 8)) == (12, 1)


def test_multirow_insert_rolled_back_entirely(con):
    order_id = new_order(con)
    with pytest.raises(sqlite3.IntegrityError, match='Недостаточно книг'):
        con.execute('INSERT INTO OrderItems VALUES (?, 13, 2, 1890), (?, 8, 5, 540)', (order_id, order_id))
    assert con.execute('SELECT COUNT(*) FROM OrderItems WHERE OrderID = ?', (order_id,)).fetchone()[0] == 0
    assert (stock(con, 13), stock(con, 8)) == (14, 3)


# ------------------------------------------------------------------ контроль: статусы заказа
def test_finished_order_cannot_change(con):
    with pytest.raises(sqlite3.IntegrityError, match='завершённого'):
        con.execute("UPDATE Orders SET Status = 'новый' WHERE OrderID = 2")


def test_cancelled_order_cannot_be_reopened(con):
    with pytest.raises(sqlite3.IntegrityError, match='завершённого'):
        con.execute("UPDATE Orders SET Status = 'оплачен' WHERE OrderID = 6")


def test_new_order_cannot_be_issued_unpaid(con):
    with pytest.raises(sqlite3.IntegrityError, match='сначала оплатить'):
        con.execute("UPDATE Orders SET Status = 'выдан' WHERE OrderID = 14")
    assert con.execute('SELECT Status FROM Orders WHERE OrderID = 14').fetchone()[0] == 'новый'


def test_normal_status_flow(con):
    con.execute("UPDATE Orders SET Status = 'оплачен' WHERE OrderID = 14")
    con.execute("UPDATE Orders SET Status = 'выдан' WHERE OrderID = 14")
    assert con.execute('SELECT Status FROM Orders WHERE OrderID = 14').fetchone()[0] == 'выдан'
    assert [r[2] for r in audit(con, 'Orders', 14)] == ['Status=оплачен', 'Status=выдан']


def test_cancel_returns_stock(con):
    before = (stock(con, 2), stock(con, 23))
    con.execute("UPDATE Orders SET Status = 'отменён' WHERE OrderID = 1")
    assert (stock(con, 2), stock(con, 23)) == (before[0] + 3, before[1] + 1)


def test_repeated_cancel_does_not_return_stock_twice(con):
    con.execute("UPDATE Orders SET Status = 'отменён' WHERE OrderID = 1")
    after_first = stock(con, 2)
    con.execute("UPDATE Orders SET Status = 'отменён' WHERE OrderID = 1")   # статус не меняется — триггеры не срабатывают
    assert stock(con, 2) == after_first


# ------------------------------------------------------------------ контроль: цена и поставки
def test_price_increase_over_limit_rejected(con):
    with pytest.raises(sqlite3.IntegrityError, match='более чем на 50'):
        con.execute('UPDATE Books SET Price = 1936 WHERE BookID = 1')
    assert con.execute('SELECT Price FROM Books WHERE BookID = 1').fetchone()[0] == 1290


def test_price_increase_by_exactly_limit_and_decrease_allowed(con):
    con.execute('UPDATE Books SET Price = 1935 WHERE BookID = 1')
    con.execute('UPDATE Books SET Price = 1000 WHERE BookID = 1')
    assert con.execute('SELECT Price FROM Books WHERE BookID = 1').fetchone()[0] == 1000


def test_multirow_price_update_rolled_back(con):
    with pytest.raises(sqlite3.IntegrityError):
        con.execute('UPDATE Books SET Price = Price * 2 WHERE CategoryID = 3')
    assert con.execute('SELECT Price FROM Books WHERE BookID = 5').fetchone()[0] == 480


def test_supply_received_increases_stock_once(con):
    con.execute("UPDATE SupplyOrders SET Status = 'получен' WHERE SupplyOrderID = 6")
    assert (stock(con, 7), stock(con, 13)) == (30, 29)
    con.execute("UPDATE SupplyOrders SET Status = 'получен' WHERE SupplyOrderID = 6")
    assert (stock(con, 7), stock(con, 13)) == (30, 29)


# ------------------------------------------------------------------ INSTEAD OF
def test_delete_through_view_archives_book(con):
    sales_before = con.execute('SELECT COUNT(*) FROM OrderItems WHERE BookID = 1').fetchone()[0]
    con.execute('DELETE FROM v_ActiveBooks WHERE BookID = 1')
    assert con.execute('SELECT IsActive FROM Books WHERE BookID = 1').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM v_ActiveBooks WHERE BookID = 1').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM OrderItems WHERE BookID = 1').fetchone()[0] == sales_before
    assert 'IsActive=1' in audit(con, 'Books', 1)[0][1] and 'IsActive=0' in audit(con, 'Books', 1)[0][2]


def test_multirow_delete_through_view(con):
    con.execute('DELETE FROM v_ActiveBooks WHERE CategoryID = 3')
    assert con.execute('SELECT COUNT(*) FROM Books').fetchone()[0] == 25
    assert con.execute('SELECT COUNT(*) FROM v_ActiveBooks').fetchone()[0] == 20


def test_direct_delete_of_sold_book_still_forbidden(con):
    with pytest.raises(sqlite3.IntegrityError):
        con.execute('DELETE FROM Books WHERE BookID = 1')


# ------------------------------------------------------------------ состав БД
def test_all_triggers_created(con):
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert len(names) == 12 and 'trg_ActiveBooks_InsteadOfDelete' in names
