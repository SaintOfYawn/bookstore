-- БД «КнигаМир» для SQLite: та же структура, что в bookstore_schema.sql (SQL Server), без схемы shop.
-- Создаётся командой: python create_db.py
PRAGMA foreign_keys = ON;

CREATE TABLE Positions (
    PositionID INTEGER NOT NULL,
    Title NVARCHAR(50) NOT NULL,
    Salary DECIMAL(10,2) NOT NULL,
    CONSTRAINT PK_Positions PRIMARY KEY (PositionID),
    CONSTRAINT UQ_Positions_Title UNIQUE (Title),
    CONSTRAINT CK_Positions_Salary CHECK (Salary > 0)
);

CREATE TABLE Employees (
    EmployeeID INTEGER NOT NULL,
    LastName NVARCHAR(40) NOT NULL,
    FirstName NVARCHAR(40) NOT NULL,
    MiddleName NVARCHAR(40) NULL,
    PositionID INT NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NOT NULL,
    HireDate DATE NOT NULL CONSTRAINT DF_Employees_HireDate DEFAULT (date('now')),
    IsActive BIT NOT NULL CONSTRAINT DF_Employees_IsActive DEFAULT (1),
    CONSTRAINT PK_Employees PRIMARY KEY (EmployeeID),
    CONSTRAINT UQ_Employees_Email UNIQUE (Email),
    CONSTRAINT FK_Employees_PositionID FOREIGN KEY (PositionID) REFERENCES Positions(PositionID) ON DELETE NO ACTION
);

CREATE TABLE Customers (
    CustomerID INTEGER NOT NULL,
    LastName NVARCHAR(40) NOT NULL,
    FirstName NVARCHAR(40) NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NULL,
    DiscountPercent TINYINT NOT NULL CONSTRAINT DF_Customers_DiscountPercent DEFAULT (0),
    RegisteredAt DATE NOT NULL CONSTRAINT DF_Customers_RegisteredAt DEFAULT (date('now')),
    CONSTRAINT PK_Customers PRIMARY KEY (CustomerID),
    CONSTRAINT UQ_Customers_Phone UNIQUE (Phone),
    CONSTRAINT CK_Customers_Discount CHECK (DiscountPercent BETWEEN 0 AND 30)
);

CREATE TABLE Authors (
    AuthorID INTEGER NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    MiddleName NVARCHAR(50) NULL,
    Country NVARCHAR(50) NULL,
    CONSTRAINT PK_Authors PRIMARY KEY (AuthorID)
);

CREATE TABLE Publishers (
    PublisherID INTEGER NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    City NVARCHAR(50) NULL,
    CONSTRAINT PK_Publishers PRIMARY KEY (PublisherID),
    CONSTRAINT UQ_Publishers_Name UNIQUE (Name)
);

CREATE TABLE Categories (
    CategoryID INTEGER NOT NULL,
    Name NVARCHAR(80) NOT NULL,
    ParentCategoryID INT NULL,
    CONSTRAINT PK_Categories PRIMARY KEY (CategoryID),
    CONSTRAINT UQ_Categories_Name UNIQUE (Name),
    CONSTRAINT FK_Categories_ParentCategoryID FOREIGN KEY (ParentCategoryID) REFERENCES Categories(CategoryID) ON DELETE NO ACTION
);

CREATE TABLE Books (
    BookID INTEGER NOT NULL,
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
    CONSTRAINT FK_Books_PublisherID FOREIGN KEY (PublisherID) REFERENCES Publishers(PublisherID) ON DELETE NO ACTION,
    CONSTRAINT FK_Books_CategoryID FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE NO ACTION,
    CONSTRAINT CK_Books_ISBN CHECK (length(ISBN) = 13 AND ISBN NOT GLOB '*[^0-9]*'),
    CONSTRAINT CK_Books_Year CHECK (PublishYear BETWEEN 1800 AND 2100),
    CONSTRAINT CK_Books_Pages CHECK (Pages > 0),
    CONSTRAINT CK_Books_Price CHECK (Price > 0),
    CONSTRAINT CK_Books_Stock CHECK (StockQty >= 0)
);

CREATE TABLE BookAuthors (
    BookID INT NOT NULL,
    AuthorID INT NOT NULL,
    AuthorOrder TINYINT NOT NULL,
    CONSTRAINT PK_BookAuthors PRIMARY KEY (BookID, AuthorID),
    CONSTRAINT UQ_BookAuthors_Order UNIQUE (BookID, AuthorOrder),
    CONSTRAINT FK_BookAuthors_BookID FOREIGN KEY (BookID) REFERENCES Books(BookID) ON DELETE CASCADE,
    CONSTRAINT FK_BookAuthors_AuthorID FOREIGN KEY (AuthorID) REFERENCES Authors(AuthorID) ON DELETE NO ACTION,
    CONSTRAINT CK_BookAuthors_Order CHECK (AuthorOrder >= 1)
);

CREATE TABLE Suppliers (
    SupplierID INTEGER NOT NULL,
    Name NVARCHAR(100) NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NULL,
    CONSTRAINT PK_Suppliers PRIMARY KEY (SupplierID),
    CONSTRAINT UQ_Suppliers_Name UNIQUE (Name)
);

CREATE TABLE SupplyOrders (
    SupplyOrderID INTEGER NOT NULL,
    SupplierID INT NOT NULL,
    EmployeeID INT NOT NULL,
    OrderDate DATE NOT NULL CONSTRAINT DF_SupplyOrders_OrderDate DEFAULT (date('now')),
    Status NVARCHAR(20) NOT NULL CONSTRAINT DF_SupplyOrders_Status DEFAULT ('создан'),
    CONSTRAINT PK_SupplyOrders PRIMARY KEY (SupplyOrderID),
    CONSTRAINT FK_SupplyOrders_SupplierID FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID) ON DELETE NO ACTION,
    CONSTRAINT FK_SupplyOrders_EmployeeID FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID) ON DELETE NO ACTION,
    CONSTRAINT CK_SupplyOrders_Status CHECK (Status IN ('создан', 'отправлен', 'получен', 'отменён'))
);

CREATE TABLE SupplyItems (
    SupplyOrderID INT NOT NULL,
    BookID INT NOT NULL,
    Quantity INT NOT NULL,
    PurchasePrice DECIMAL(10,2) NOT NULL,
    CONSTRAINT PK_SupplyItems PRIMARY KEY (SupplyOrderID, BookID),
    CONSTRAINT FK_SupplyItems_SupplyOrderID FOREIGN KEY (SupplyOrderID) REFERENCES SupplyOrders(SupplyOrderID) ON DELETE CASCADE,
    CONSTRAINT FK_SupplyItems_BookID FOREIGN KEY (BookID) REFERENCES Books(BookID) ON DELETE NO ACTION,
    CONSTRAINT CK_SupplyItems_Quantity CHECK (Quantity > 0),
    CONSTRAINT CK_SupplyItems_Price CHECK (PurchasePrice > 0)
);

CREATE TABLE Orders (
    OrderID INTEGER NOT NULL,
    CustomerID INT NULL,
    EmployeeID INT NOT NULL,
    OrderDate DATETIME2(0) NOT NULL CONSTRAINT DF_Orders_OrderDate DEFAULT (datetime('now')),
    Status NVARCHAR(20) NOT NULL CONSTRAINT DF_Orders_Status DEFAULT ('новый'),
    PaymentMethod NVARCHAR(20) NOT NULL,
    CONSTRAINT PK_Orders PRIMARY KEY (OrderID),
    CONSTRAINT FK_Orders_CustomerID FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE SET NULL,
    CONSTRAINT FK_Orders_EmployeeID FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID) ON DELETE NO ACTION,
    CONSTRAINT CK_Orders_Status CHECK (Status IN ('новый', 'оплачен', 'выдан', 'отменён')),
    CONSTRAINT CK_Orders_Payment CHECK (PaymentMethod IN ('наличные', 'карта', 'онлайн'))
);

CREATE TABLE OrderItems (
    OrderID INT NOT NULL,
    BookID INT NOT NULL,
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(10,2) NOT NULL,
    CONSTRAINT PK_OrderItems PRIMARY KEY (OrderID, BookID),
    CONSTRAINT FK_OrderItems_OrderID FOREIGN KEY (OrderID) REFERENCES Orders(OrderID) ON DELETE CASCADE,
    CONSTRAINT FK_OrderItems_BookID FOREIGN KEY (BookID) REFERENCES Books(BookID) ON DELETE NO ACTION,
    CONSTRAINT CK_OrderItems_Quantity CHECK (Quantity > 0),
    CONSTRAINT CK_OrderItems_Price CHECK (UnitPrice > 0)
);

INSERT INTO Positions (PositionID, Title, Salary) VALUES
    (1, 'Продавец-кассир', 45000),
    (2, 'Старший продавец', 58000),
    (3, 'Менеджер по закупкам', 65000),
    (4, 'Администратор магазина', 80000);

INSERT INTO Employees (EmployeeID, LastName, FirstName, MiddleName, PositionID, Phone, Email, HireDate, IsActive) VALUES
    (1, 'Орлова', 'Мария', 'Игоревна', 1, '+7 (495) 123-45-01', 'orlova@knigamir.example', '2023-03-01', 1),
    (2, 'Смирнов', 'Алексей', 'Петрович', 1, '+7 (495) 123-45-02', 'smirnov@knigamir.example', '2023-09-15', 1),
    (3, 'Козлова', 'Елена', 'Викторовна', 2, '+7 (495) 123-45-03', 'kozlova@knigamir.example', '2022-05-10', 1),
    (4, 'Новиков', 'Дмитрий', 'Сергеевич', 3, '+7 (495) 123-45-04', 'novikov@knigamir.example', '2021-11-22', 1),
    (5, 'Фёдорова', 'Анна', 'Павловна', 4, '+7 (495) 123-45-05', 'fedorova@knigamir.example', '2020-02-03', 1),
    (6, 'Васильев', 'Игорь', 'Олегович', 1, '+7 (495) 123-45-06', 'vasiliev@knigamir.example', '2024-06-17', 0);

INSERT INTO Customers (CustomerID, LastName, FirstName, Phone, Email, DiscountPercent, RegisteredAt) VALUES
    (1, 'Иванов', 'Пётр', '+7 (911) 207-11-21', 'user1@mail.example', 0, '2025-01-27'),
    (2, 'Петрова', 'Ольга', '+7 (912) 214-12-22', 'user2@mail.example', 5, '2025-02-13'),
    (3, 'Сидоров', 'Максим', '+7 (913) 221-13-23', 'user3@mail.example', 0, '2025-03-02'),
    (4, 'Кузнецова', 'Наталья', '+7 (914) 228-14-24', NULL, 10, '2025-03-19'),
    (5, 'Попов', 'Артём', '+7 (915) 235-15-25', 'user5@mail.example', 0, '2025-04-05'),
    (6, 'Лебедева', 'Виктория', '+7 (916) 242-16-26', 'user6@mail.example', 5, '2025-04-22'),
    (7, 'Морозов', 'Кирилл', '+7 (917) 249-17-27', 'user7@mail.example', 0, '2025-05-09'),
    (8, 'Волкова', 'Дарья', '+7 (918) 256-18-28', NULL, 15, '2025-05-26'),
    (9, 'Соколов', 'Андрей', '+7 (919) 263-19-29', 'user9@mail.example', 0, '2025-06-12'),
    (10, 'Павлова', 'Екатерина', '+7 (920) 270-20-30', 'user10@mail.example', 5, '2025-06-29'),
    (11, 'Зайцев', 'Никита', '+7 (921) 277-21-31', 'user11@mail.example', 0, '2025-07-16'),
    (12, 'Белова', 'Юлия', '+7 (922) 284-22-32', NULL, 10, '2025-08-02'),
    (13, 'Крылов', 'Роман', '+7 (923) 291-23-33', 'user13@mail.example', 0, '2025-08-19'),
    (14, 'Горбунова', 'Ирина', '+7 (924) 298-24-34', 'user14@mail.example', 0, '2025-09-05'),
    (15, 'Комаров', 'Владимир', '+7 (925) 305-25-35', 'user15@mail.example', 5, '2025-09-22'),
    (16, 'Титова', 'Светлана', '+7 (926) 312-26-36', NULL, 0, '2025-10-09'),
    (17, 'Жуков', 'Евгений', '+7 (927) 319-27-37', 'user17@mail.example', 10, '2025-10-26'),
    (18, 'Беляева', 'Алёна', '+7 (928) 326-28-38', 'user18@mail.example', 0, '2025-11-12'),
    (19, 'Мальцев', 'Тимофей', '+7 (929) 333-29-39', 'user19@mail.example', 5, '2025-11-29'),
    (20, 'Ершова', 'Полина', '+7 (930) 340-30-40', NULL, 0, '2025-12-16');

INSERT INTO Authors (AuthorID, LastName, FirstName, MiddleName, Country) VALUES
    (1, 'Толстой', 'Лев', 'Николаевич', 'Россия'),
    (2, 'Достоевский', 'Фёдор', 'Михайлович', 'Россия'),
    (3, 'Булгаков', 'Михаил', 'Афанасьевич', 'Россия'),
    (4, 'Пушкин', 'Александр', 'Сергеевич', 'Россия'),
    (5, 'Стругацкий', 'Аркадий', 'Натанович', 'Россия'),
    (6, 'Стругацкий', 'Борис', 'Натанович', 'Россия'),
    (7, 'Азимов', 'Айзек', NULL, 'США'),
    (8, 'Брэдбери', 'Рэй', NULL, 'США'),
    (9, 'Кристи', 'Агата', NULL, 'Великобритания'),
    (10, 'Мартин', 'Роберт', NULL, 'США'),
    (11, 'Дейт', 'Крис', 'Дж.', 'США'),
    (12, 'Кормен', 'Томас', 'Х.', 'США'),
    (13, 'Лейзерсон', 'Чарльз', 'Э.', 'США'),
    (14, 'Ривест', 'Рональд', 'Л.', 'США'),
    (15, 'Штайн', 'Клиффорд', NULL, 'США'),
    (16, 'Карнеги', 'Дейл', NULL, 'США'),
    (17, 'Милн', 'Алан', 'Александр', 'Великобритания'),
    (18, 'Хокинг', 'Стивен', NULL, 'Великобритания'),
    (19, 'Дойл', 'Артур', 'Конан', 'Великобритания'),
    (20, 'Оруэлл', 'Джордж', NULL, 'Великобритания'),
    (21, 'Бен-Ган', 'Ицик', NULL, 'Израиль'),
    (22, 'Карпова', 'Тамара', 'Сергеевна', 'Россия'),
    (23, 'Бхаргава', 'Адитья', NULL, 'США'),
    (24, 'Твен', 'Марк', NULL, 'США'),
    (25, 'Ремарк', 'Эрих', 'Мария', 'Германия'),
    (26, 'Сэлинджер', 'Джером', 'Дэвид', 'США');

INSERT INTO Publishers (PublisherID, Name, City) VALUES
    (1, 'Эксмо', 'Москва'),
    (2, 'АСТ', 'Москва'),
    (3, 'Питер', 'Санкт-Петербург'),
    (4, 'Манн, Иванов и Фербер', 'Москва'),
    (5, 'Азбука', 'Санкт-Петербург'),
    (6, 'Альпина Паблишер', 'Москва'),
    (7, 'Вильямс', 'Москва'),
    (8, 'БХВ-Петербург', 'Санкт-Петербург');

INSERT INTO Categories (CategoryID, Name, ParentCategoryID) VALUES
    (1, 'Художественная литература', NULL),
    (2, 'Классика', 1),
    (3, 'Фантастика', 1),
    (4, 'Детективы', 1),
    (5, 'Компьютерная литература', NULL),
    (6, 'Программирование', 5),
    (7, 'Базы данных', 5),
    (8, 'Бизнес и саморазвитие', NULL),
    (9, 'Детские книги', NULL),
    (10, 'Научно-популярная литература', NULL);

INSERT INTO Books (BookID, Title, ISBN, PublisherID, CategoryID, PublishYear, Pages, Price, StockQty, IsActive) VALUES
    (1, 'Война и мир', '9785170371037', 5, 2, 2021, 1360, 1290, 25, 1),
    (2, 'Преступление и наказание', '9785170741069', 5, 2, 2020, 608, 590, 30, 1),
    (3, 'Мастер и Маргарита', '9785171111090', 2, 2, 2022, 480, 650, 40, 1),
    (4, 'Евгений Онегин', '9785171481124', 1, 2, 2019, 288, 420, 18, 1),
    (5, 'Пикник на обочине', '9785171851156', 2, 3, 2021, 224, 480, 22, 1),
    (6, 'Понедельник начинается в субботу', '9785172221187', 2, 3, 2020, 320, 520, 12, 1),
    (7, 'Основание', '9785172591211', 1, 3, 2022, 288, 560, 15, 1),
    (8, 'Я, робот', '9785172961243', 1, 3, 2021, 320, 540, 3, 1),
    (9, '451 градус по Фаренгейту', '9785173331274', 2, 3, 2023, 256, 510, 28, 1),
    (10, 'Убийство в Восточном экспрессе', '9785173701305', 1, 4, 2022, 320, 490, 35, 1),
    (11, 'Собака Баскервилей', '9785174071339', 5, 4, 2021, 256, 430, 20, 1),
    (12, '1984', '9785174441361', 2, 1, 2022, 320, 460, 45, 1),
    (13, 'Чистый код', '9785174811393', 3, 6, 2022, 464, 1890, 14, 1),
    (14, 'Чистая архитектура', '9785175181426', 3, 6, 2021, 352, 1750, 4, 1),
    (15, 'Введение в системы баз данных', '9785175551458', 7, 7, 2019, 1328, 2890, 9, 1),
    (16, 'Алгоритмы: построение и анализ', '9785175921480', 7, 6, 2020, 1328, 3490, 7, 1),
    (17, 'Как завоёвывать друзей и оказывать влияние на людей', '9785176291513', 6, 8, 2021, 352, 690, 50, 1),
    (18, 'Винни-Пух и все-все-все', '9785176661545', 5, 9, 2020, 320, 560, 33, 1),
    (19, 'Краткая история времени', '9785177031576', 2, 10, 2021, 256, 590, 17, 1),
    (20, 'Основы T-SQL', '9785177401607', 3, 7, 2020, 640, 2190, 6, 1),
    (21, 'Базы данных: модели, разработка, реализация', '9785177771632', 3, 7, 2019, 304, 1590, 5, 1),
    (22, 'Грокаем алгоритмы', '9785178141663', 3, 6, 2022, 288, 1490, 11, 1),
    (23, 'Приключения Тома Сойера', '9785178511695', 5, 9, 2020, 352, 470, 26, 1),
    (24, 'Три товарища', '9785178881729', 2, 2, 2021, 480, 620, 16, 1),
    (25, 'Над пропастью во ржи', '9785179251750', 1, 2, 2022, 320, 450, 0, 1);

INSERT INTO BookAuthors (BookID, AuthorID, AuthorOrder) VALUES
    (1, 1, 1),
    (2, 2, 1),
    (3, 3, 1),
    (4, 4, 1),
    (5, 5, 1),
    (5, 6, 2),
    (6, 5, 1),
    (6, 6, 2),
    (7, 7, 1),
    (8, 7, 1),
    (9, 8, 1),
    (10, 9, 1),
    (11, 19, 1),
    (12, 20, 1),
    (13, 10, 1),
    (14, 10, 1),
    (15, 11, 1),
    (16, 12, 1),
    (16, 13, 2),
    (16, 14, 3),
    (16, 15, 4),
    (17, 16, 1),
    (18, 17, 1),
    (19, 18, 1),
    (20, 21, 1),
    (21, 22, 1),
    (22, 23, 1),
    (23, 24, 1),
    (24, 25, 1),
    (25, 26, 1);

INSERT INTO Suppliers (SupplierID, Name, Phone, Email) VALUES
    (1, 'Книжный оптовик', '+7 (495) 200-10-01', 'sales@opt1.example'),
    (2, 'Литера-Опт', '+7 (495) 200-10-02', 'order@litera-opt.example'),
    (3, 'Печатный двор', '+7 (812) 300-20-03', NULL),
    (4, 'Читай-Опт', '+7 (495) 200-10-04', 'info@chitai-opt.example'),
    (5, 'Бумажный мир', '+7 (343) 400-30-05', 'zakaz@bumazhny-mir.example');

INSERT INTO SupplyOrders (SupplyOrderID, SupplierID, EmployeeID, OrderDate, Status) VALUES
    (1, 2, 4, '2026-08-09', 'получен'),
    (2, 3, 4, '2026-08-15', 'получен'),
    (3, 4, 4, '2026-08-21', 'получен'),
    (4, 5, 4, '2026-08-27', 'получен'),
    (5, 1, 4, '2026-09-02', 'получен'),
    (6, 2, 4, '2026-09-08', 'отправлен'),
    (7, 3, 4, '2026-09-14', 'создан'),
    (8, 4, 4, '2026-09-20', 'отменён');

INSERT INTO SupplyItems (SupplyOrderID, BookID, Quantity, PurchasePrice) VALUES
    (1, 4, 30, 252.0),
    (1, 11, 5, 258.0),
    (1, 17, 10, 414.0),
    (2, 20, 20, 1314.0),
    (2, 18, 30, 336.0),
    (3, 18, 20, 336.0),
    (3, 24, 30, 372.0),
    (3, 25, 20, 270.0),
    (4, 8, 30, 324.0),
    (4, 1, 5, 774.0),
    (5, 4, 5, 252.0),
    (5, 10, 20, 294.0),
    (5, 15, 15, 1734.0),
    (6, 7, 15, 336.0),
    (6, 13, 15, 1134.0),
    (7, 12, 30, 276.0),
    (7, 13, 5, 1134.0),
    (7, 24, 15, 372.0),
    (8, 3, 30, 390.0),
    (8, 18, 15, 336.0);

INSERT INTO Orders (OrderID, CustomerID, EmployeeID, OrderDate, Status, PaymentMethod) VALUES
    (1, 1, 3, '2026-09-01T18:33:00', 'оплачен', 'наличные'),
    (2, 16, 1, '2026-09-03T01:27:00', 'выдан', 'карта'),
    (3, 18, 2, '2026-09-04T06:16:00', 'выдан', 'онлайн'),
    (4, 7, 2, '2026-09-05T10:27:00', 'выдан', 'карта'),
    (5, NULL, 3, '2026-09-06T19:29:00', 'выдан', 'карта'),
    (6, 16, 2, '2026-09-08T00:49:00', 'отменён', 'онлайн'),
    (7, 4, 2, '2026-09-09T05:58:00', 'выдан', 'онлайн'),
    (8, 9, 2, '2026-09-10T05:41:00', 'выдан', 'карта'),
    (9, 1, 1, '2026-09-11T12:28:00', 'выдан', 'наличные'),
    (10, NULL, 1, '2026-09-12T17:39:00', 'выдан', 'онлайн'),
    (11, 19, 3, '2026-09-13T22:20:00', 'выдан', 'карта'),
    (12, 17, 2, '2026-09-15T06:38:00', 'выдан', 'наличные'),
    (13, 5, 3, '2026-09-16T16:24:00', 'выдан', 'наличные'),
    (14, 1, 1, '2026-09-17T21:59:00', 'новый', 'онлайн'),
    (15, NULL, 3, '2026-09-19T05:29:00', 'оплачен', 'онлайн'),
    (16, 11, 2, '2026-09-20T10:39:00', 'выдан', 'онлайн'),
    (17, 7, 3, '2026-09-21T16:02:00', 'выдан', 'наличные'),
    (18, 7, 2, '2026-09-22T16:28:00', 'выдан', 'онлайн'),
    (19, 17, 1, '2026-09-24T01:50:00', 'отменён', 'наличные'),
    (20, NULL, 1, '2026-09-25T10:55:00', 'новый', 'карта'),
    (21, 14, 2, '2026-09-26T17:31:00', 'выдан', 'карта'),
    (22, 17, 2, '2026-09-27T17:33:00', 'выдан', 'наличные'),
    (23, 18, 3, '2026-09-29T03:26:00', 'отменён', 'наличные'),
    (24, 19, 3, '2026-09-30T09:35:00', 'выдан', 'наличные'),
    (25, NULL, 3, '2026-10-01T18:48:00', 'новый', 'онлайн'),
    (26, 4, 2, '2026-10-03T00:08:00', 'оплачен', 'наличные'),
    (27, 11, 2, '2026-10-03T23:32:00', 'оплачен', 'онлайн'),
    (28, 9, 1, '2026-10-05T06:16:00', 'выдан', 'наличные'),
    (29, 10, 1, '2026-10-06T13:01:00', 'выдан', 'наличные'),
    (30, NULL, 2, '2026-10-08T01:02:00', 'выдан', 'карта');

INSERT INTO OrderItems (OrderID, BookID, Quantity, UnitPrice) VALUES
    (1, 2, 3, 590),
    (1, 23, 1, 470),
    (2, 4, 2, 420),
    (2, 21, 2, 1590),
    (3, 18, 3, 560),
    (3, 21, 2, 1590),
    (4, 2, 1, 590),
    (5, 7, 2, 560),
    (5, 9, 2, 510),
    (6, 10, 1, 490),
    (7, 15, 2, 2890),
    (7, 6, 2, 520),
    (8, 7, 2, 560),
    (9, 19, 3, 590),
    (9, 18, 1, 560),
    (9, 3, 1, 650),
    (10, 22, 1, 1490),
    (10, 25, 1, 450),
    (11, 18, 2, 560),
    (11, 8, 3, 540),
    (12, 22, 3, 1490),
    (12, 6, 1, 520),
    (12, 5, 3, 480),
    (13, 1, 1, 1290),
    (13, 4, 1, 420),
    (13, 13, 1, 1890),
    (14, 11, 2, 430),
    (14, 22, 1, 1490),
    (14, 10, 1, 490),
    (15, 5, 3, 480),
    (15, 19, 1, 590),
    (16, 22, 1, 1490),
    (16, 23, 3, 470),
    (17, 21, 3, 1590),
    (18, 5, 3, 480),
    (19, 13, 2, 1890),
    (19, 9, 3, 510),
    (20, 6, 1, 520),
    (20, 12, 1, 460),
    (21, 11, 2, 430),
    (21, 17, 2, 690),
    (22, 8, 1, 540),
    (22, 1, 2, 1290),
    (23, 12, 1, 460),
    (24, 20, 1, 2190),
    (25, 19, 3, 590),
    (25, 10, 1, 490),
    (26, 6, 1, 520),
    (26, 4, 1, 420),
    (26, 22, 1, 1490),
    (27, 10, 1, 490),
    (28, 25, 1, 450),
    (28, 9, 1, 510),
    (28, 14, 1, 1750),
    (29, 11, 2, 430),
    (29, 25, 3, 450),
    (30, 20, 2, 2190),
    (30, 15, 1, 2890);

CREATE UNIQUE INDEX UX_Customers_Email ON Customers (Email) WHERE Email IS NOT NULL;
CREATE INDEX IX_Orders_OrderDate ON Orders (OrderDate);
CREATE INDEX IX_OrderItems_BookID ON OrderItems (BookID);
CREATE INDEX IX_Books_CategoryID ON Books (CategoryID);
