-- Книжный магазин «КнигаМир». СУБД: Microsoft SQL Server 2019/2022. Кодировка файла: UTF-8.
-- Этап 1. Проверка ограничений целостности и правил каскадного удаления.
-- Каждый тест выполняется в транзакции, которая откатывается: данные не меняются.
USE BookStoreDB;
GO
SET NOCOUNT ON;
GO

-- T01. Цена книги равна 0 (ожидается отказ: CK_Books_Price)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) VALUES (N'Тест', '9785000000011', 1, 2, 2024, 100, 0);
    PRINT N'T01: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T01: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T02. Повторный ISBN (ожидается отказ: UQ_Books_ISBN)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) VALUES (N'Тест', '9785170371037', 1, 2, 2024, 100, 100);
    PRINT N'T02: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T02: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T03. ISBN из 12 цифр (ожидается отказ: CK_Books_ISBN)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) VALUES (N'Тест', '978500000001', 1, 2, 2024, 100, 100);
    PRINT N'T03: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T03: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T04. ISBN с буквами (ожидается отказ: CK_Books_ISBN)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) VALUES (N'Тест', '97850000001AB', 1, 2, 2024, 100, 100);
    PRINT N'T04: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T04: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T05. Несуществующее издательство (ожидается отказ: FK_Books_PublisherID)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) VALUES (N'Тест', '9785000000011', 999, 2, 2024, 100, 100);
    PRINT N'T05: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T05: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T06. Отрицательный остаток (ожидается отказ: CK_Books_Stock)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price, StockQty) VALUES (N'Тест', '9785000000011', 1, 2, 2024, 100, 100, -1);
    PRINT N'T06: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T06: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T07. Название книги NULL (ожидается отказ: NOT NULL)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price) VALUES (NULL, '9785000000011', 1, 2, 2024, 100, 100);
    PRINT N'T07: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T07: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T08. Количество в заказе равно 0 (ожидается отказ: CK_OrderItems_Quantity)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.OrderItems (OrderID, BookID, Quantity, UnitPrice) VALUES (1, 25, 0, 450);
    PRINT N'T08: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T08: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T09. Недопустимый статус заказа (ожидается отказ: CK_Orders_Status)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Orders (CustomerID, EmployeeID, Status, PaymentMethod) VALUES (1, 1, N'потерян', N'карта');
    PRINT N'T09: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T09: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T10. Скидка 50 % (ожидается отказ: CK_Customers_Discount)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Customers (LastName, FirstName, Phone, DiscountPercent) VALUES (N'Тестов', N'Тест', '+7 (900) 000-00-01', 50);
    PRINT N'T10: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T10: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T11. Повторный e-mail сотрудника (ожидается отказ: UQ_Employees_Email)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Employees (LastName, FirstName, PositionID, Phone, Email) VALUES (N'Тестов', N'Тест', 1, '+7 (900) 000-00-02', 'orlova@knigamir.example');
    PRINT N'T11: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T11: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T12. Удаление издательства, у которого есть книги (ожидается отказ: FK_Books_PublisherID)
BEGIN TRAN;
BEGIN TRY
    DELETE FROM shop.Publishers WHERE PublisherID = 1;
    PRINT N'T12: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T12: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T13. Повторный e-mail покупателя (фильтрованный индекс) (ожидается отказ: UX_Customers_Email)
BEGIN TRAN;
BEGIN TRY
    INSERT INTO shop.Customers (LastName, FirstName, Phone, Email) VALUES (N'Тестов', N'Тест', '+7 (900) 000-00-03', 'user1@mail.example');
    PRINT N'T13: ОШИБКА - вставка/удаление прошло, ограничение не сработало';
END TRY
BEGIN CATCH
    PRINT N'T13: отклонено - ' + ERROR_MESSAGE();
END CATCH;
IF @@TRANCOUNT > 0 ROLLBACK;
GO

-- T14. Каскад: при удалении заказа удаляются его позиции (ON DELETE CASCADE)
BEGIN TRAN;
SELECT COUNT(*) AS ItemsBefore FROM shop.OrderItems WHERE OrderID = 1;
DELETE FROM shop.Orders WHERE OrderID = 1;
SELECT COUNT(*) AS ItemsAfter FROM shop.OrderItems WHERE OrderID = 1;
ROLLBACK;
GO

-- T15. SET NULL: при удалении покупателя его заказы сохраняются, CustomerID становится NULL
BEGIN TRAN;
SELECT COUNT(*) AS OrdersBefore FROM shop.Orders WHERE CustomerID = 1;
DELETE FROM shop.Customers WHERE CustomerID = 1;
SELECT COUNT(*) AS OrdersWithoutCustomer FROM shop.Orders WHERE CustomerID IS NULL;
ROLLBACK;
GO

-- T16. DEFAULT: значения по умолчанию подставляются автоматически
BEGIN TRAN;
INSERT INTO shop.Books (Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price)
VALUES (N'Тестовая книга', '9785000000011', 1, 2, 2024, 100, 100);
SELECT Title, StockQty, IsActive FROM shop.Books WHERE ISBN = '9785000000011';
INSERT INTO shop.Orders (CustomerID, EmployeeID, PaymentMethod) VALUES (1, 1, N'карта');
SELECT TOP (1) OrderID, Status, OrderDate FROM shop.Orders ORDER BY OrderID DESC;
ROLLBACK;
GO
