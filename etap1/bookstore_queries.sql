-- Книжный магазин «КнигаМир». СУБД: Microsoft SQL Server 2019/2022. Кодировка файла: UTF-8.
-- Этап 1. Контрольные запросы (JOIN на 2-4 таблицы) и обращение к представлениям.
USE BookStoreDB;
GO

-- Q1. Фантастика: книга, издательство, цена (Books + Publishers + Categories)
SELECT b.Title, p.Name AS Publisher, b.Price, b.StockQty
FROM shop.Books b
JOIN shop.Publishers p ON p.PublisherID = b.PublisherID
JOIN shop.Categories c ON c.CategoryID = b.CategoryID
WHERE c.Name = N'Фантастика'
ORDER BY b.Title;
GO

-- Q2. Последние 5 заказов с покупателем и продавцом (Orders + Customers + Employees)
SELECT TOP (5) o.OrderID, o.OrderDate, o.Status,
       ISNULL(c.LastName, N'без карты') AS Customer, e.LastName AS Seller
FROM shop.Orders o
LEFT JOIN shop.Customers c ON c.CustomerID = o.CustomerID
JOIN shop.Employees e ON e.EmployeeID = o.EmployeeID
ORDER BY o.OrderDate DESC;
GO

-- Q3. Продано книг и выручка по категориям (Orders + OrderItems + Books + Categories)
SELECT c.Name AS Category, SUM(oi.Quantity) AS BooksSold, SUM(oi.Quantity * oi.UnitPrice) AS Revenue
FROM shop.Orders o
JOIN shop.OrderItems oi ON oi.OrderID = o.OrderID
JOIN shop.Books b ON b.BookID = oi.BookID
JOIN shop.Categories c ON c.CategoryID = b.CategoryID
WHERE o.Status IN (N'оплачен', N'выдан')
GROUP BY c.Name
ORDER BY Revenue DESC;
GO

-- Q4. Книги, у которых несколько авторов (Books + BookAuthors + Authors)
SELECT b.Title, COUNT(*) AS AuthorsCount
FROM shop.Books b
JOIN shop.BookAuthors ba ON ba.BookID = b.BookID
GROUP BY b.Title
HAVING COUNT(*) > 1;
GO

-- Q5. Выручка по дням, первые 5 дней (представление v_DailyRevenue)
SELECT TOP (5) SaleDate, OrdersCount, BooksSold, Revenue FROM shop.v_DailyRevenue ORDER BY SaleDate;
GO

-- Q6. Книги, которые нужно заказать (представление v_LowStock)
SELECT Title, Authors, StockQty, Availability FROM shop.v_LowStock ORDER BY StockQty, Title;
GO

-- Q7. Каталог: три книги Азимова и Стругацких (представление v_BookCatalog)
SELECT Title, Authors, Category, Price FROM shop.v_BookCatalog WHERE Authors LIKE N'%Азимов%' OR Authors LIKE N'%Стругацкий%' ORDER BY Title;
GO

