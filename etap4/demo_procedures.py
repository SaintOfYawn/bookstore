"""Демонстрация этапа 2: транзакционные процедуры, откат при ошибке и журнал ошибок."""
import os
import sqlite3
import tempfile

import procedures as proc
from create_db import create_database


def stock(con, book_id):
    return con.execute('SELECT StockQty FROM Books WHERE BookID = ?', (book_id,)).fetchone()[0]


def main():
    path = create_database(os.path.join(tempfile.mkdtemp(), 'demo.db'), with_triggers=False)
    con = sqlite3.connect(path)
    con.execute('PRAGMA foreign_keys = ON')
    print('Остатки: «Чистый код» (13) = %d, «Я, робот» (8) = %d; заказов в базе: %d'
          % (stock(con, 13), stock(con, 8), con.execute('SELECT COUNT(*) FROM Orders').fetchone()[0]))
    order_id = proc.orders_place(con, 1, 1, 'карта', [(13, 2), (8, 1)])
    print('1. orders_place(...) -> заказ №%d; остатки: %d и %d' % (order_id, stock(con, 13), stock(con, 8)))
    try:
        proc.orders_place(con, 1, 1, 'карта', [(13, 1), (8, 9)])
    except proc.ProcedureError as error:
        print('2. orders_place(... 9 шт. «Я, робот») -> ОШИБКА %d: %s' % (error.code, error.message))
    print('   после отката: заказов %d, остатки %d и %d (изменения первой позиции отменены)'
          % (con.execute('SELECT COUNT(*) FROM Orders').fetchone()[0], stock(con, 13), stock(con, 8)))
    print('3. orders_set_status(%d, "отменён") -> %d; остатки возвращены: %d и %d'
          % (order_id, proc.orders_set_status(con, order_id, 'отменён'), stock(con, 13), stock(con, 8)))
    print('4. supply_receive(6) -> принято позиций: %d; остатки «Основания» (7) = %d' % (proc.supply_receive(con, 6), stock(con, 7)))
    try:
        proc.supply_receive(con, 6)
    except proc.ProcedureError as error:
        print('5. supply_receive(6) повторно -> ОШИБКА %d: %s' % (error.code, error.message))
    print('Журнал ошибок:')
    for row in con.execute('SELECT ErrorID, ProcedureName, ErrorCode, Message FROM ErrorLog'):
        print('   #%d %s, код %d: %s' % row)
    con.close()


if __name__ == '__main__':
    main()
