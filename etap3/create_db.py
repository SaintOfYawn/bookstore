"""Создаёт файл базы данных bookstore.db из sql/bookstore_sqlite.sql."""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'bookstore.db')
SCRIPT = os.path.join(BASE, 'sql', 'bookstore_sqlite.sql')


def create_database(path=DB_PATH):
    """Пересоздаёт базу данных из SQL-скрипта и возвращает путь к файлу."""
    if os.path.exists(path):
        os.remove(path)
    with open(SCRIPT, encoding='utf-8') as file:
        script = file.read()
    con = sqlite3.connect(path)
    try:
        con.executescript(script)
        con.commit()
    finally:
        con.close()
    return path


if __name__ == '__main__':
    print('База данных создана:', create_database())
