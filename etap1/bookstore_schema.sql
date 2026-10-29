-- Книжный магазин «КнигаМир». СУБД: Microsoft SQL Server 2019/2022. Кодировка файла: UTF-8.
-- Этап 1. Создание базы данных, схемы и таблиц. Запускать в SSMS целиком (F5).
USE master;
GO
IF DB_ID(N'BookStoreDB') IS NOT NULL
BEGIN
    ALTER DATABASE BookStoreDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE BookStoreDB;
END
GO
CREATE DATABASE BookStoreDB COLLATE Cyrillic_General_CI_AS;
GO
USE BookStoreDB;
GO
CREATE SCHEMA shop AUTHORIZATION dbo;
GO

CREATE TABLE shop.Positions (
    PositionID INT IDENTITY(1,1) NOT NULL,
    Title NVARCHAR(50) NOT NULL,
    Salary DECIMAL(10,2) NOT NULL,
    CONSTRAINT PK_Positions PRIMARY KEY (PositionID),
    CONSTRAINT UQ_Positions_Title UNIQUE (Title),
    CONSTRAINT CK_Positions_Salary CHECK (Salary > 0)
);
GO

CREATE TABLE shop.Employees (
    EmployeeID INT IDENTITY(1,1) NOT NULL,
    LastName NVARCHAR(40) NOT NULL,
    FirstName NVARCHAR(40) NOT NULL,
    MiddleName NVARCHAR(40) NULL,
    PositionID INT NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NOT NULL,
    HireDate DATE NOT NULL CONSTRAINT DF_Employees_HireDate DEFAULT (CAST(GETDATE() AS DATE)),
    IsActive BIT NOT NULL CONSTRAINT DF_Employees_IsActive DEFAULT (1),
    CONSTRAINT PK_Employees PRIMARY KEY (EmployeeID),
    CONSTRAINT UQ_Employees_Email UNIQUE (Email),
    CONSTRAINT FK_Employees_PositionID FOREIGN KEY (PositionID) REFERENCES shop.Positions(PositionID) ON DELETE NO ACTION
);
GO

CREATE TABLE shop.Customers (
    CustomerID INT IDENTITY(1,1) NOT NULL,
    LastName NVARCHAR(40) NOT NULL,
    FirstName NVARCHAR(40) NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NULL,
    DiscountPercent TINYINT NOT NULL CONSTRAINT DF_Customers_DiscountPercent DEFAULT (0),
    RegisteredAt DATE NOT NULL CONSTRAINT DF_Customers_RegisteredAt DEFAULT (CAST(GETDATE() AS DATE)),
    CONSTRAINT PK_Customers PRIMARY KEY (CustomerID),
    CONSTRAINT UQ_Customers_Phone UNIQUE (Phone),
    CONSTRAINT CK_Customers_Discount CHECK (DiscountPercent BETWEEN 0 AND 30)
);
GO

CREATE TABLE shop.Authors (
    AuthorID INT IDENTITY(1,1) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    MiddleName NVARCHAR(50) NULL,
    Country NVARCHAR(50) NULL,
    CONSTRAINT PK_Authors PRIMARY KEY (AuthorID)
);
GO

CREATE TABLE shop.Publishers (
    PublisherID INT IDENTITY(1,1) NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    City NVARCHAR(50) NULL,
    CONSTRAINT PK_Publishers PRIMARY KEY (PublisherID),
    CONSTRAINT UQ_Publishers_Name UNIQUE (Name)
);
GO

CREATE TABLE shop.Categories (
    CategoryID INT IDENTITY(1,1) NOT NULL,
    Name NVARCHAR(80) NOT NULL,
    ParentCategoryID INT NULL,
    CONSTRAINT PK_Categories PRIMARY KEY (CategoryID),
    CONSTRAINT UQ_Categories_Name UNIQUE (Name),
    CONSTRAINT FK_Categories_ParentCategoryID FOREIGN KEY (ParentCategoryID) REFERENCES shop.Categories(CategoryID) ON DELETE NO ACTION
);
GO

CREATE TABLE shop.Books (
    BookID INT IDENTITY(1,1) NOT NULL,
    Title NVARCHAR(200) NOT NULL,
    ISBN CHAR(13) NOT NULL,
    PublisherID INT NOT NULL,
    CategoryID INT NOT NULL,
    PublishYear SMALLINT NOT NULL,
    Pages SMALLINT NOT NULL,
    Price DECIMAL(10,2) NOT NULL,
    StockQty INT NOT NULL CONSTRAINT DF_Books_StockQty DEFAULT (0),
    IsActive BIT NOT NULL CONSTRAINT DF_Books_IsActive DEFAULT (1),
    CONSTRAINT PK_Books PRIMARY KEY (BookID),
    CONSTRAINT UQ_Books_ISBN UNIQUE (ISBN),
    CONSTRAINT FK_Books_PublisherID FOREIGN KEY (PublisherID) REFERENCES shop.Publishers(PublisherID) ON DELETE NO ACTION,
    CONSTRAINT FK_Books_CategoryID FOREIGN KEY (CategoryID) REFERENCES shop.Categories(CategoryID) ON DELETE NO ACTION,
    CONSTRAINT CK_Books_ISBN CHECK (LEN(ISBN) = 13 AND ISBN NOT LIKE '%[^0-9]%'),
    CONSTRAINT CK_Books_Year CHECK (PublishYear BETWEEN 1800 AND 2100),
    CONSTRAINT CK_Books_Pages CHECK (Pages > 0),
    CONSTRAINT CK_Books_Price CHECK (Price > 0),
    CONSTRAINT CK_Books_Stock CHECK (StockQty >= 0)
);
GO

CREATE TABLE shop.BookAuthors (
    BookID INT NOT NULL,
    AuthorID INT NOT NULL,
    AuthorOrder TINYINT NOT NULL,
    CONSTRAINT PK_BookAuthors PRIMARY KEY (BookID, AuthorID),
    CONSTRAINT UQ_BookAuthors_Order UNIQUE (BookID, AuthorOrder),
    CONSTRAINT FK_BookAuthors_BookID FOREIGN KEY (BookID) REFERENCES shop.Books(BookID) ON DELETE CASCADE,
    CONSTRAINT FK_BookAuthors_AuthorID FOREIGN KEY (AuthorID) REFERENCES shop.Authors(AuthorID) ON DELETE NO ACTION,
    CONSTRAINT CK_BookAuthors_Order CHECK (AuthorOrder >= 1)
);
GO

CREATE TABLE shop.Suppliers (
    SupplierID INT IDENTITY(1,1) NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NULL,
    CONSTRAINT PK_Suppliers PRIMARY KEY (SupplierID),
    CONSTRAINT UQ_Suppliers_Name UNIQUE (Name)
);
GO

CREATE TABLE shop.SupplyOrders (
    SupplyOrderID INT IDENTITY(1,1) NOT NULL,
    SupplierID INT NOT NULL,
    EmployeeID INT NOT NULL,
    OrderDate DATE NOT NULL CONSTRAINT DF_SupplyOrders_OrderDate DEFAULT (CAST(GETDATE() AS DATE)),
    Status NVARCHAR(20) NOT NULL CONSTRAINT DF_SupplyOrders_Status DEFAULT (N'создан'),
    CONSTRAINT PK_SupplyOrders PRIMARY KEY (SupplyOrderID),
    CONSTRAINT FK_SupplyOrders_SupplierID FOREIGN KEY (SupplierID) REFERENCES shop.Suppliers(SupplierID) ON DELETE NO ACTION,
    CONSTRAINT FK_SupplyOrders_EmployeeID FOREIGN KEY (EmployeeID) REFERENCES shop.Employees(EmployeeID) ON DELETE NO ACTION,
    CONSTRAINT CK_SupplyOrders_Status CHECK (Status IN (N'создан', N'отправлен', N'получен', N'отменён'))
);
GO

CREATE TABLE shop.SupplyItems (
    SupplyOrderID INT NOT NULL,
    BookID INT NOT NULL,
    Quantity INT NOT NULL,
    PurchasePrice DECIMAL(10,2) NOT NULL,
    CONSTRAINT PK_SupplyItems PRIMARY KEY (SupplyOrderID, BookID),
    CONSTRAINT FK_SupplyItems_SupplyOrderID FOREIGN KEY (SupplyOrderID) REFERENCES shop.SupplyOrders(SupplyOrderID) ON DELETE CASCADE,
    CONSTRAINT FK_SupplyItems_BookID FOREIGN KEY (BookID) REFERENCES shop.Books(BookID) ON DELETE NO ACTION,
    CONSTRAINT CK_SupplyItems_Quantity CHECK (Quantity > 0),
    CONSTRAINT CK_SupplyItems_Price CHECK (PurchasePrice > 0)
);
GO

CREATE TABLE shop.Orders (
    OrderID INT IDENTITY(1,1) NOT NULL,
    CustomerID INT NULL,
    EmployeeID INT NOT NULL,
    OrderDate DATETIME2(0) NOT NULL CONSTRAINT DF_Orders_OrderDate DEFAULT (SYSDATETIME()),
    Status NVARCHAR(20) NOT NULL CONSTRAINT DF_Orders_Status DEFAULT (N'новый'),
    PaymentMethod NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_Orders PRIMARY KEY (OrderID),
    CONSTRAINT FK_Orders_CustomerID FOREIGN KEY (CustomerID) REFERENCES shop.Customers(CustomerID) ON DELETE SET NULL,
    CONSTRAINT FK_Orders_EmployeeID FOREIGN KEY (EmployeeID) REFERENCES shop.Employees(EmployeeID) ON DELETE NO ACTION,
    CONSTRAINT CK_Orders_Status CHECK (Status IN (N'новый', N'оплачен', N'выдан', N'отменён')),
    CONSTRAINT CK_Orders_Payment CHECK (PaymentMethod IN (N'наличные', N'карта', N'онлайн'))
);
GO

CREATE TABLE shop.OrderItems (
    OrderID INT NOT NULL,
    BookID INT NOT NULL,
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(10,2) NOT NULL,
    CONSTRAINT PK_OrderItems PRIMARY KEY (OrderID, BookID),
    CONSTRAINT FK_OrderItems_OrderID FOREIGN KEY (OrderID) REFERENCES shop.Orders(OrderID) ON DELETE CASCADE,
    CONSTRAINT FK_OrderItems_BookID FOREIGN KEY (BookID) REFERENCES shop.Books(BookID) ON DELETE NO ACTION,
    CONSTRAINT CK_OrderItems_Quantity CHECK (Quantity > 0),
    CONSTRAINT CK_OrderItems_Price CHECK (UnitPrice > 0)
);
GO
