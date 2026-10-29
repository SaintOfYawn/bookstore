"""Создаёт файл базы данных bookstore.db из sql/bookstore_sqlite.sql."""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'bookstore.db')
SCRIPT = os.path.join(BASE, 'sql', 'bookstore_sqlite.sql')
ERRORLOG = os.path.join(BASE, 'sql', 'bookstore_errorlog.sql')
TRIGGERS = os.path.join(BASE, 'sql', 'bookstore_triggers.sql')


def create_database(path=DB_PATH, with_triggers=True):
    """Пересоздаёт базу данных и возвращает путь к файлу.

    Создаются таблицы и данные (этап 1), журнал ошибок (этап 2) и, если with_triggers=True,
    триггеры (этап 4).
    """
    if os.path.exists(path):
        os.remove(path)
    scripts = []
    names = [SCRIPT, ERRORLOG] + ([TRIGGERS] if with_triggers else [])
    for name in names:
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
    import sys
    print('База данных создана:', create_database(with_triggers='--no-triggers' not in sys.argv))
