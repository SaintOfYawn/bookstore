-- Книжный магазин «КнигаМир». СУБД: Microsoft SQL Server 2019/2022. Кодировка файла: UTF-8.
-- Этап 1. Индексы и представления (запускать после bookstore_schema.sql).
USE BookStoreDB;
GO

-- поиск книги по названию в каталоге и на кассе
CREATE NONCLUSTERED INDEX IX_Books_Title ON shop.Books (Title);
GO
-- выбор книг категории (внешний ключ без индекса); INCLUDE покрывает список «название — цена»
CREATE NONCLUSTERED INDEX IX_Books_CategoryID ON shop.Books (CategoryID) INCLUDE (Title, Price);
GO
-- выбор книг издательства; ускоряет проверку внешнего ключа при удалении издательства
CREATE NONCLUSTERED INDEX IX_Books_PublisherID ON shop.Books (PublisherID);
GO
-- поиск автора по фамилии
CREATE NONCLUSTERED INDEX IX_Authors_LastName ON shop.Authors (LastName, FirstName);
GO
-- отчёты и выборки по периоду продаж
CREATE NONCLUSTERED INDEX IX_Orders_OrderDate ON shop.Orders (OrderDate) INCLUDE (Status);
GO
-- история заказов покупателя
CREATE NONCLUSTERED INDEX IX_Orders_CustomerID ON shop.Orders (CustomerID);
GO
-- продажи конкретной книги; первичный ключ (OrderID, BookID) для такого поиска не подходит
CREATE NONCLUSTERED INDEX IX_OrderItems_BookID ON shop.OrderItems (BookID);
GO
-- поставки конкретной книги
CREATE NONCLUSTERED INDEX IX_SupplyItems_BookID ON shop.SupplyItems (BookID);
GO

-- уникальность e-mail покупателя (допускаются покупатели без e-mail)
CREATE UNIQUE NONCLUSTERED INDEX UX_Customers_Email ON shop.Customers (Email) WHERE Email IS NOT NULL;
GO

-- Витрина 1: каталог книг с авторами, категорией, издательством и наличием
CREATE OR ALTER VIEW shop.v_BookCatalog AS
SELECT b.BookID, b.Title,
       STRING_AGG(CONCAT(a.LastName, N' ', LEFT(a.FirstName, 1), N'.'), N', ') WITHIN GROUP (ORDER BY ba.AuthorOrder) AS Authors,
       c.Name AS Category, p.Name AS Publisher, b.PublishYear, b.Price, b.StockQty,
       CASE WHEN b.StockQty = 0 THEN N'нет в наличии'
            WHEN b.StockQty < 5 THEN N'заканчивается'
            ELSE N'в наличии' END AS Availability
FROM shop.Books b
JOIN shop.BookAuthors ba ON ba.BookID = b.BookID
JOIN shop.Authors a ON a.AuthorID = ba.AuthorID
JOIN shop.Categories c ON c.CategoryID = b.CategoryID
JOIN shop.Publishers p ON p.PublisherID = b.PublisherID
WHERE b.IsActive = 1
GROUP BY b.BookID, b.Title, c.Name, p.Name, b.PublishYear, b.Price, b.StockQty;
GO

-- Витрина 2: заказы с суммой, скидкой и итогом к оплате
CREATE OR ALTER VIEW shop.v_OrderTotals AS
SELECT o.OrderID, o.OrderDate, o.Status,
       ISNULL(c.LastName + N' ' + c.FirstName, N'без карты') AS Customer,
       e.LastName AS Seller,
       SUM(oi.Quantity) AS BooksCount,
       SUM(oi.Quantity * oi.UnitPrice) AS TotalAmount,
       ISNULL(c.DiscountPercent, 0) AS DiscountPercent,
       CAST(SUM(oi.Quantity * oi.UnitPrice) * (100 - ISNULL(c.DiscountPercent, 0)) / 100.0 AS DECIMAL(12, 2)) AS PayAmount
FROM shop.Orders o
JOIN shop.OrderItems oi ON oi.OrderID = o.OrderID
JOIN shop.Employees e ON e.EmployeeID = o.EmployeeID
LEFT JOIN shop.Customers c ON c.CustomerID = o.CustomerID
GROUP BY o.OrderID, o.OrderDate, o.Status, c.LastName, c.FirstName, e.LastName, c.DiscountPercent;
GO

-- Витрина 3: выручка по дням (только оплаченные и выданные заказы, с учётом скидки)
CREATE OR ALTER VIEW shop.v_DailyRevenue AS
SELECT CAST(o.OrderDate AS DATE) AS SaleDate,
       COUNT(DISTINCT o.OrderID) AS OrdersCount,
       SUM(oi.Quantity) AS BooksSold,
       CAST(SUM(oi.Quantity * oi.UnitPrice * (100 - ISNULL(c.DiscountPercent, 0)) / 100.0) AS DECIMAL(12, 2)) AS Revenue
FROM shop.Orders o
JOIN shop.OrderItems oi ON oi.OrderID = o.OrderID
LEFT JOIN shop.Customers c ON c.CustomerID = o.CustomerID
WHERE o.Status IN (N'оплачен', N'выдан')
GROUP BY CAST(o.OrderDate AS DATE);
GO

-- Витрина 4: книги, которые нужно заказать у поставщика
CREATE OR ALTER VIEW shop.v_LowStock AS
SELECT BookID, Title, Authors, Publisher, StockQty, Availability
FROM shop.v_BookCatalog
WHERE StockQty < 5;
GO
