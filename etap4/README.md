# БД «КнигаМир» (этапы 2–4, ПМ.11)

```
pip install -r requirements.txt
python create_db.py                 # база со всеми объектами: таблицы, ErrorLog, триггеры
python create_db.py --no-triggers   # состояние этапа 2: без триггеров (остатки меняют процедуры)
pytest                              # процедуры (80), функции (57), триггеры (28)
python demo_procedures.py           # этап 2: транзакция, откат, журнал ошибок
python demo_triggers.py             # этап 4: нарушение правила — триггер — запись в аудите
```

- `procedures.py` — процедуры сервисного слоя (этап 2): выборки, изменение данных, транзакции, отчёты;
- `bookstore_functions.py`, `services.py` — пользовательские функции (этап 3);
- `sql/` — таблицы и данные (`bookstore_sqlite.sql`), журнал ошибок, триггеры (этап 4);
- `tests/` — тесты pytest.
