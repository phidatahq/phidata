-- Here are some sample queries for reference

-- The total pay for all agencies in 2023
-- query start
SELECT SUM(total_regular_gross_pay + total_overtime_pay + total_other_pay) AS total_pay
FROM nyc_payroll_aggregated
WHERE fiscal_year = 2023
-- query end

-- Top 5 agencies by total pay in 2023
-- query start
SELECT agency_name, SUM(total_regular_gross_pay + total_overtime_pay + total_other_pay) AS total_pay
FROM nyc_payroll_aggregated
GROUP BY agency_name
ORDER BY total_pay DESC
LIMIT 5
-- query end

-- The total pay for DEPARTMENT OF PROBATION in 2023
-- query start
SELECT SUM(total_regular_gross_pay + total_overtime_pay + total_other_pay) AS total_pay
FROM nyc_payroll_aggregated
WHERE agency_name = 'DEPARTMENT OF PROBATION' AND fiscal_year = 2023
-- query end

-- Overtime pay by agency in 2023
-- query start
SELECT
    agency_name,
    SUM(total_ot_paid) AS total_overtime_pay
FROM
    wegovnyc_citywide_payroll
WHERE
    fiscal_year = 2023
GROUP BY
    agency_name
ORDER BY
    total_overtime_pay DESC
LIMIT 10
-- query end

-- Highest paid employee 2023
-- query start
SELECT first_name, last_name, agency_name, total_ot_paid + total_other_pay + regular_gross_paid AS total_pay
FROM wegovnyc_citywide_payroll
WHERE fiscal_year = 2023
ORDER BY total_pay DESC
LIMIT 1
-- query end

-- Agency with the highest overtime wages 2023
-- query start
SELECT agency_name, SUM(total_ot_paid) AS total_overtime_pay
FROM wegovnyc_citywide_payroll
WHERE fiscal_year = 2023 AND total_ot_paid IS NOT NULL
GROUP BY agency_name
ORDER BY total_overtime_pay DESC
LIMIT 1
-- query end

-- Employee earning the hisghest overtime pay in 2023
-- query start
SELECT first_name, last_name, agency_name, total_ot_paid
FROM wegovnyc_citywide_payroll
WHERE fiscal_year = 2023
ORDER BY total_ot_paid
DESC LIMIT 1
-- query end

-- How many agencies are there in NYC
-- query start
SELECT COUNT(DISTINCT agency_name) AS number_of_agencies
FROM nyc_payroll_aggregated
-- query end

-- Employees per agency in 2023
-- query start
SELECT agency_name, COUNT(*) AS number_of_employees
FROM wegovnyc_citywide_payroll
WHERE fiscal_year = 2023
GROUP BY agency_name
ORDER BY number_of_employees DESC
-- query end
