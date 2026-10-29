import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sqlite3

import pytest

from bookstore_functions import register_functions
from create_db import create_database


@pytest.fixture
def db_path(tmp_path):
    """Тестовая база данных во временной папке."""
    return create_database(str(tmp_path / 'test_bookstore.db'))


@pytest.fixture
def con(db_path):
    """Соединение sqlite3 с зарегистрированными функциями fn_*."""
    connection = sqlite3.connect(db_path)
    connection.execute('PRAGMA foreign_keys = ON')
    register_functions(connection)
    yield connection
    connection.close()


@pytest.fixture
def engine(db_path):
    """Движок SQLAlchemy; функции fn_* регистрируются при каждом подключении."""
    from sqlalchemy import create_engine
    from bookstore_functions import make_engine
    eng = make_engine(create_engine('sqlite:///' + db_path))
    yield eng
    eng.dispose()
