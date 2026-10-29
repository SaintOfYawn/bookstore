-- Этап 4. Триггеры БД «КнигаМир» (SQLite). Запускается после bookstore_sqlite.sql командой python create_db.py.
-- Соглашения: NEW — новая строка, OLD — старая; триггеры SQLite срабатывают для каждой строки (FOR EACH ROW),
-- поэтому многострочные операции обрабатываются корректно; RAISE(ABORT, ...) отменяет весь оператор.

-- ---------------------------------------------------------------- 1. Контекст и таблица аудита
-- Текущий пользователь приложения (в SQLite нет SYSTEM_USER): задаётся из Python, см. set_user() в create_db.py
CREATE TABLE AppContext (
    ParamName  TEXT NOT NULL PRIMARY KEY,
    ParamValue TEXT NOT NULL
);
INSERT INTO AppContext (ParamName, ParamValue) VALUES ('user', 'system');

CREATE TABLE AuditLog (
    AuditID    INTEGER PRIMARY KEY AUTOINCREMENT,
    TableName  TEXT NOT NULL,
    Operation  TEXT NOT NULL CHECK (Operation IN ('INSERT', 'UPDATE', 'DELETE')),
    RecordID   INTEGER NOT NULL,
    OldValue   TEXT NULL,
    NewValue   TEXT NULL,
    ChangedBy  TEXT NOT NULL,
    ChangedAt  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IX_AuditLog_Table_Record ON AuditLog (TableName, RecordID);

-- ---------------------------------------------------------------- 2. AFTER-триггеры аудита
-- Books: добавление, изменение (цена, остаток, название, признак продажи), удаление
CREATE TRIGGER trg_Books_Audit_Insert AFTER INSERT ON Books
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, NewValue, ChangedBy)
    VALUES ('Books', 'INSERT', NEW.BookID,
            'Title=' || NEW.Title || '; Price=' || NEW.Price || '; StockQty=' || NEW.StockQty,
            (SELECT ParamValue FROM AppContext WHERE ParamName = 'user'));
END;

CREATE TRIGGER trg_Books_Audit_Update AFTER UPDATE ON Books
WHEN OLD.Title IS NOT NEW.Title OR OLD.Price IS NOT NEW.Price
  OR OLD.StockQty IS NOT NEW.StockQty OR OLD.IsActive IS NOT NEW.IsActive
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, NewValue, ChangedBy)
    VALUES ('Books', 'UPDATE', NEW.BookID,
            'Title=' || OLD.Title || '; Price=' || OLD.Price || '; StockQty=' || OLD.StockQty || '; IsActive=' || OLD.IsActive,
            'Title=' || NEW.Title || '; Price=' || NEW.Price || '; StockQty=' || NEW.StockQty || '; IsActive=' || NEW.IsActive,
            (SELECT ParamValue FROM AppContext WHERE ParamName = 'user'));
END;

CREATE TRIGGER trg_Books_Audit_Delete AFTER DELETE ON Books
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, ChangedBy)
    VALUES ('Books', 'DELETE', OLD.BookID,
            'Title=' || OLD.Title || '; Price=' || OLD.Price || '; StockQty=' || OLD.StockQty,
            (SELECT ParamValue FROM AppContext WHERE ParamName = 'user'));
END;

-- Customers: изменение скидки и контактов (скидка влияет на выручку)
CREATE TRIGGER trg_Customers_Audit_Update AFTER UPDATE ON Customers
WHEN OLD.DiscountPercent IS NOT NEW.DiscountPercent OR OLD.Phone IS NOT NEW.Phone OR OLD.Email IS NOT NEW.Email
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, NewValue, ChangedBy)
    VALUES ('Customers', 'UPDATE', NEW.CustomerID,
            'Discount=' || OLD.DiscountPercent || '; Phone=' || OLD.Phone || '; Email=' || IFNULL(OLD.Email, 'NULL'),
            'Discount=' || NEW.DiscountPercent || '; Phone=' || NEW.Phone || '; Email=' || IFNULL(NEW.Email, 'NULL'),
            (SELECT ParamValue FROM AppContext WHERE ParamName = 'user'));
END;

-- Orders: смена статуса заказа
CREATE TRIGGER trg_Orders_Audit_Status AFTER UPDATE OF Status ON Orders
WHEN OLD.Status IS NOT NEW.Status
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, NewValue, ChangedBy)
    VALUES ('Orders', 'UPDATE', NEW.OrderID, 'Status=' || OLD.Status, 'Status=' || NEW.Status,
            (SELECT ParamValue FROM AppContext WHERE ParamName = 'user'));
END;

-- ---------------------------------------------------------------- 3. Триггеры контроля бизнес-правил
-- Правило 1: в позицию заказа нельзя добавить больше книг, чем есть на складе (CHECK не видит другую таблицу)
CREATE TRIGGER trg_OrderItems_CheckStock BEFORE INSERT ON OrderItems
WHEN NEW.Quantity > IFNULL((SELECT StockQty FROM Books WHERE BookID = NEW.BookID), 0)
BEGIN
    SELECT RAISE(ABORT, 'Недостаточно книг на складе');
END;

-- Правило 1а: после добавления позиции остаток списывается
CREATE TRIGGER trg_OrderItems_DecreaseStock AFTER INSERT ON OrderItems
BEGIN
    UPDATE Books SET StockQty = StockQty - NEW.Quantity WHERE BookID = NEW.BookID;
END;

-- Правило 2: завершённый заказ изменить нельзя; выдать можно только оплаченный заказ
CREATE TRIGGER trg_Orders_StatusFlow BEFORE UPDATE OF Status ON Orders
WHEN OLD.Status IS NOT NEW.Status
BEGIN
    SELECT RAISE(ABORT, 'Нельзя изменить статус завершённого заказа')
    WHERE OLD.Status IN ('выдан', 'отменён');
    SELECT RAISE(ABORT, 'Заказ нужно сначала оплатить')
    WHERE OLD.Status = 'новый' AND NEW.Status = 'выдан';
END;

-- Правило 2а: при отмене заказа книги возвращаются на склад
CREATE TRIGGER trg_Orders_Cancel_ReturnStock AFTER UPDATE OF Status ON Orders
WHEN NEW.Status = 'отменён' AND OLD.Status IS NOT 'отменён'
BEGIN
    UPDATE Books
    SET StockQty = StockQty + (SELECT oi.Quantity FROM OrderItems oi
                               WHERE oi.OrderID = NEW.OrderID AND oi.BookID = Books.BookID)
    WHERE BookID IN (SELECT BookID FROM OrderItems WHERE OrderID = NEW.OrderID);
END;

-- Правило 3: цену книги нельзя повысить более чем в 1,5 раза за одно изменение (защита от опечаток)
CREATE TRIGGER trg_Books_PriceChangeLimit BEFORE UPDATE OF Price ON Books
WHEN NEW.Price > OLD.Price * 1.5
BEGIN
    SELECT RAISE(ABORT, 'Цену нельзя повысить более чем на 50 % за раз');
END;

-- Правило 4: поставка принимается один раз; при получении остатки увеличиваются
CREATE TRIGGER trg_SupplyOrders_Received_IncreaseStock AFTER UPDATE OF Status ON SupplyOrders
WHEN NEW.Status = 'получен' AND OLD.Status IS NOT 'получен'
BEGIN
    UPDATE Books
    SET StockQty = StockQty + (SELECT si.Quantity FROM SupplyItems si
                               WHERE si.SupplyOrderID = NEW.SupplyOrderID AND si.BookID = Books.BookID)
    WHERE BookID IN (SELECT BookID FROM SupplyItems WHERE SupplyOrderID = NEW.SupplyOrderID);
END;

-- ---------------------------------------------------------------- 4. INSTEAD OF-триггер
-- Удаление книги через представление заменяется переводом в архив (IsActive = 0): история продаж сохраняется
CREATE VIEW v_ActiveBooks AS
SELECT BookID, Title, ISBN, PublisherID, CategoryID, Price, StockQty FROM Books WHERE IsActive = 1;

CREATE TRIGGER trg_ActiveBooks_InsteadOfDelete INSTEAD OF DELETE ON v_ActiveBooks
BEGIN
    UPDATE Books SET IsActive = 0 WHERE BookID = OLD.BookID;
END;
