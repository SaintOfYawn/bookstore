"""Создаёт файл базы данных bookstore.db из sql/bookstore_sqlite.sql."""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'bookstore.db')
SCRIPT = os.path.join(BASE, 'sql', 'bookstore_sqlite.sql')
TRIGGERS = os.path.join(BASE, 'sql', 'bookstore_triggers.sql')


def create_database(path=DB_PATH):
    """Пересоздаёт базу данных (таблицы, данные, триггеры) и возвращает путь к файлу."""
    if os.path.exists(path):
        os.remove(path)
    scripts = []
    for name in (SCRIPT, TRIGGERS):
        with open(name, encoding='utf-8') as file:
            scripts.append(file.read())
    con = sqlite3.connect(path)
    try:
        for script in scripts:
            con.executescript(script)
        con.commit()
    finally:
        con.close()
    return path


def set_user(connection, name):
    """Задаёт текущего пользователя приложения для записей аудита."""
    connection.execute("UPDATE AppContext SET ParamValue = ? WHERE ParamName = 'user'", (name,))
    connection.commit()


if __name__ == '__main__':
    print('База данных создана:', create_database())
