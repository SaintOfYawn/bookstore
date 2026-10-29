"""Демонстрация этапа 4: нарушение бизнес-правила — срабатывание триггера — запись в аудите."""
import os
import sqlite3
import tempfile

from create_db import create_database, set_user


def show_audit(con, last=3):
    rows = con.execute('SELECT AuditID, TableName, Operation, RecordID, OldValue, NewValue, ChangedBy '
                       'FROM AuditLog ORDER BY AuditID DESC LIMIT ?', (last,)).fetchall()
    for row in reversed(rows):
        print('   аудит #%d %s %s запись %d | было: %s | стало: %s | кто: %s'
              % (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))


def attempt(con, title, sql, params=()):
    try:
        con.execute(sql, params)
        con.commit()
        print('%s -> выполнено' % title)
    except sqlite3.IntegrityError as error:
        print('%s -> ОШИБКА: %s' % (title, error))


def main():
    path = create_database(os.path.join(tempfile.mkdtemp(), 'demo.db'))
    con = sqlite3.connect(path)
    con.execute('PRAGMA foreign_keys = ON')
    set_user(con, 'Орлова М. И.')
    order_id = con.execute("INSERT INTO Orders (CustomerID, EmployeeID, PaymentMethod) VALUES (1, 1, 'карта')").lastrowid
    print('1. Оформляется заказ №%d. На складе книги «Я, робот» (код 8): %d шт.'
          % (order_id, con.execute('SELECT StockQty FROM Books WHERE BookID = 8').fetchone()[0]))
    attempt(con, '2. Продать 5 шт. «Я, робот»', 'INSERT INTO OrderItems VALUES (?, 8, 5, 540)', (order_id,))
    attempt(con, '3. Продать 2 шт. «Я, робот»', 'INSERT INTO OrderItems VALUES (?, 8, 2, 540)', (order_id,))
    print('   остаток теперь: %d шт.' % con.execute('SELECT StockQty FROM Books WHERE BookID = 8').fetchone()[0])
    show_audit(con, 1)
    attempt(con, '4. Поднять цену «Чистого кода» (1890 руб.) вдвое', 'UPDATE Books SET Price = 3780 WHERE BookID = 13')
    attempt(con, '5. Поднять цену «Чистого кода» до 2000 руб.', 'UPDATE Books SET Price = 2000 WHERE BookID = 13')
    show_audit(con, 1)
    attempt(con, '6. Выдать неоплаченный заказ №14', "UPDATE Orders SET Status = 'выдан' WHERE OrderID = 14")
    attempt(con, '7. Отправить в архив «Войну и мир» через представление', 'DELETE FROM v_ActiveBooks WHERE BookID = 1')
    print('   строка в Books сохранена, IsActive =', con.execute('SELECT IsActive FROM Books WHERE BookID = 1').fetchone()[0])
    show_audit(con, 1)
    con.close()


if __name__ == '__main__':
    main()
