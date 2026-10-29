-- Этап 2. Журнал ошибок процедур: в него записывает декоратор @procedure при любой ошибке.
CREATE TABLE ErrorLog (
    ErrorID       INTEGER PRIMARY KEY AUTOINCREMENT,
    ProcedureName TEXT NOT NULL,
    ErrorCode     INTEGER NOT NULL,
    Message       TEXT NOT NULL,
    LoggedAt      TEXT NOT NULL DEFAULT (datetime('now'))
);
