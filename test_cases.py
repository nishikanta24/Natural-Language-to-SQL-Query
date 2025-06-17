test_cases = [
    {
        "nl_query": "List the top 3 customers with the most recent subscription dates, showing their full name, company, and subscription date.",
        "expected_sql": """
        SELECT
            first_name || ' ' || last_name AS full_name,
            company,
            subscription_date
        FROM
            customers
        ORDER BY
            subscription_date DESC
        LIMIT 3;
        """,
        "expected_result": [
            ['Amanda Santos', 'Camacho-Lamb', '2022-05-29'],
            ['Bethany Barrera', 'Swanson, Figueroa and Heath', '2022-05-29'],
            ['Joel Shea', 'Richmond-Horne', '2022-05-29']
        ]
    },
    {
        "nl_query": "Find the company with the highest average length of customer email addresses. Show the company name and that average length.",
        "expected_sql": """
        SELECT
            company,
            AVG(LENGTH(email)) AS avg_email_length
        FROM
            customers
        GROUP BY
            company
        ORDER BY
            avg_email_length DESC
        LIMIT 1;
        """,
        "expected_result": [
            ['Hart Group', 37.0]
        ]
    },
    {
        "nl_query": "For each country, rank customers by their subscription date (most recent first). Then, list the first_name, last_name, and subscription_date of the 2nd most recent subscriber in each country. If a country has fewer than 2 subscribers, do not include it. Limit the results to 5 entries.",
        "expected_sql": """
        WITH RankedCustomers AS (
            SELECT
                first_name,
                last_name,
                country,
                subscription_date,
                ROW_NUMBER() OVER (PARTITION BY country ORDER BY subscription_date DESC) as rn
            FROM
                customers
        )
        SELECT
            first_name,
            last_name,
            country,
            subscription_date
        FROM
            RankedCustomers
        WHERE
            rn = 2
        LIMIT 5;
        """,
        "expected_result": [
            ['Francis', 'Goodman', 'Afghanistan', '2022-02-08'],
            ['Bianca', 'Henry', 'Albania', '2020-04-13'],
            ['Jocelyn', 'Stephens', 'Algeria', '2021-08-08'],
            ['Kathryn', 'Hester', 'American Samoa', '2022-01-22'],
            ['Miranda', 'Robles', 'Andorra', '2020-10-16']
        ]
    },
    {
        "nl_query": "Identify any customers who have identical full names (first_name and last_name combined) but different customer_alphanum_ids. List their full name and count how many such duplicates exist.",
        "expected_sql": """
        WITH FullNames AS (
            SELECT
                first_name || ' ' || last_name AS full_name,
                COUNT(DISTINCT customer_alphanum_id) as id_count
            FROM
                customers
            GROUP BY
                first_name, last_name
            HAVING
                COUNT(DISTINCT customer_alphanum_id) > 1
        )
        SELECT
            full_name,
            id_count
        FROM
            FullNames;
        """,
        "expected_result": [] # Confirmed: No results
    },
    {
        "nl_query": "Find customers whose subscription date is within the last 30 days from today (assume today is '2022-05-20' for the example). List their first name, last name, and subscription date. Limit the results to 10 entries.",
        "expected_sql": """
        SELECT
            first_name,
            last_name,
            subscription_date
        FROM
            customers
        WHERE
            subscription_date >= '2022-05-20'::date - INTERVAL '30 days'
            AND subscription_date <= '2022-05-20'::date
        ORDER BY
            subscription_date DESC
        LIMIT 10;
        """,
        "expected_result": [
            ['Madison', 'Clark', '2022-05-19'],
            ['Angel', 'Conner', '2022-05-19'],
            ['Marcia', 'Horton', '2022-05-17'],
            ['Brady', 'Mcdaniel', '2022-05-17'],
            ['Jodi', 'Moran', '2022-05-17'],
            ['Latoya', 'Clements', '2022-05-16'],
            ['Jeremiah', 'Guerrero', '2022-05-11'],
            ['Reginald', 'Blankenship', '2022-05-10'],
            ['Logan', 'Riddle', '2022-05-08'],
            ['Riley', 'Aguirre', '2022-05-07']
        ]
    }
]