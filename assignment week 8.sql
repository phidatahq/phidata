--Question 1--
INSERT INTO Customers (customer_id, name, city) VALUES (NULL, 'Alice Smith', 'New York City');

--Question 2--
UPDATE Customers SET city = 'New York City' WHERE name = 'John Doe';

--Question 3--
SELECT * FROM Customers WHERE city = 'Chicago';

--Question 4--
DELETE FROM Customers WHERE customer_id = 1;
