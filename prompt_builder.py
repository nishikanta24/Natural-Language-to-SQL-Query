import psycopg2
from psycopg2 import sql

# IMPORTANT: Import fetch_schema from db_connector.py
# This ensures that schema fetching uses your environment variables
# and the centralized connection logic.
from db_connector import fetch_schema


def format_schema_for_display(schema):
    """
    Formats the schema dictionary into a readable string for user confirmation.
    """
    if not schema:
        return "No tables found in the database."

    formatted = "📋 **Database Schema Detected:**\n\n"
    for table_name, columns in schema.items():
        formatted += f"**Table: {table_name}**\n"
        for col_name, col_type in columns:
            formatted += f"  - {col_name} ({col_type})\n"
        formatted += "\n"

    return formatted

def build_schema_confirmation_prompt(schema, nl_query):
    """
    Builds a prompt to show the schema to the user and ask for confirmation.
    """
    schema_display = format_schema_for_display(schema)

    prompt = f"""I need to generate a SQL query for your request: "{nl_query}"

First, let me show you the database schema I detected:

{schema_display}

**Please confirm:**
1. Are all the tables and columns listed above correct?
2. Are there any missing tables or columns I should know about?
3. Are there any columns listed that don't actually exist?

If everything looks correct, please respond with "CONFIRMED" and I'll generate the SQL query.

If there are any issues, please tell me specifically:
- "Table X doesn't exist, use Table Y instead"
- "Column A in Table B doesn't exist, use Column C instead"
- "Add Table Z with columns: col1, col2, col3"

Your response:"""

    return prompt

def parse_schema_corrections(user_response, original_schema):
    """
    Parses user corrections and updates the schema accordingly.
    Returns updated schema dictionary.
    """
    if user_response.strip().upper() == "CONFIRMED":
        return original_schema, True

    # Create a copy of the original schema to modify
    updated_schema = original_schema.copy()
    corrections_applied = []

    lines = user_response.strip().split('\n')
    for line in lines:
        line = line.strip().lower()

        # Handle table corrections
        if "table" in line and "doesn't exist" in line:
            # Extract table names (this is a simplified parser)
            words = line.split()
            if "use" in words:
                old_table = words[words.index("table") + 1]
                new_table = words[words.index("use") + 1]
                if old_table in updated_schema:
                    updated_schema[new_table] = updated_schema.pop(old_table)
                    corrections_applied.append(f"Renamed table '{old_table}' to '{new_table}'")

        # Handle column corrections
        elif "column" in line and "doesn't exist" in line:
            # Simplified column correction parser
            words = line.split()
            if "use" in words:
                old_col = words[words.index("column") + 1]
                new_col = words[words.index("use") + 1]
                # Find and replace column in all tables
                for table_name, columns in updated_schema.items():
                    updated_columns = []
                    for col_name, col_type in columns:
                        if col_name.lower() == old_col.lower():
                            updated_columns.append((new_col, col_type))
                            corrections_applied.append(f"Renamed column '{old_col}' to '{new_col}' in table '{table_name}'")
                        else:
                            updated_columns.append((col_name, col_type))
                    updated_schema[table_name] = updated_columns

    return updated_schema, False

def build_schema_context_string(schema):
    """
    Converts schema dictionary to a string format for the SQL generation prompt.
    """
    if not schema:
        return "No schema information available."

    schema_str = ""
    for table, columns in schema.items():
        if columns:  # Skip tables with no columns
            col_names = [col[0] for col in columns]  # Extract just column names
            schema_str += f"Table: {table}\nColumns: {', '.join(col_names)}\n\n"

    return schema_str

def build_sql_generation_prompt(nl_query, confirmed_schema):
    """
    Builds the final prompt for SQL generation using the confirmed schema.
    """
    # System message with PostgreSQL-specific instructions
    system_msg = """You are an expert SQL developer specialized in writing complex PostgreSQL queries from natural language input.

IMPORTANT PostgreSQL Syntax Rules:
1. Use || for string concatenation, NOT CONCAT()
    - Correct: first_name || ' ' || last_name
    - Incorrect: CONCAT(first_name, ' ', last_name)

2. Use PostgreSQL date arithmetic:
    - CURRENT_DATE - INTERVAL '30 days'
    - '2022-05-20'::date - INTERVAL '30 days'

3. Use PostgreSQL-specific functions when appropriate:
    - DATE_TRUNC() for date truncation
    - EXTRACT() for date parts
    - ROW_NUMBER() OVER() for ranking

4. Only use tables and columns that exist in the provided schema.
5. Return only the SQL query without additional explanation unless requested."""

    # Few-shot examples (same as before but with PostgreSQL syntax)
    few_shots = [
        {
            "user": "For each month in the last year, list the top 2 salespeople by total revenue generated.",
            "assistant": """WITH monthly_revenue AS (
    SELECT
        salesperson_id,
        DATE_TRUNC('month', sale_date) AS sale_month,
        SUM(amount) AS total_revenue
    FROM sales
    WHERE sale_date >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY salesperson_id, DATE_TRUNC('month', sale_date)
),
ranked_sales AS (
    SELECT *,
            RANK() OVER (PARTITION BY sale_month ORDER BY total_revenue DESC) AS rank
    FROM monthly_revenue
)
SELECT sale_month, salesperson_id, total_revenue
FROM ranked_sales
WHERE rank <= 2
ORDER BY sale_month, rank;"""
        },
        {
            "user": "Show me the full name of customers from the customers table.",
            "assistant": """SELECT first_name || ' ' || last_name AS full_name
FROM customers;"""
        }
    ]

    # Schema string formatting
    schema_str = build_schema_context_string(confirmed_schema)

    # Current NL query to translate
    # FIX: Removed surrounding double quotes and added .strip()
    final_user_input = f"""Given the following confirmed schema:

{schema_str}

Translate this natural language query into a PostgreSQL SQL statement:
{nl_query.strip()}

Remember to use PostgreSQL syntax (|| for concatenation, INTERVAL for dates, etc.)."""

    # Final prompt object (chat format)
    messages = [{"role": "system", "content": system_msg}]
    for ex in few_shots:
        messages.append({"role": "user", "content": ex["user"]})
        messages.append({"role": "assistant", "content": ex["assistant"]})
    messages.append({"role": "user", "content": final_user_input})

    return messages

def build_prompt(current_db_schema, nl_query): # Modified to accept schema directly
    """
    Original function - kept for backward compatibility but now deprecated.
    Use build_sql_generation_prompt() with confirmed schema instead.
    """
    # The schema is now passed in as an argument, so fetch_schema() is not called here.
    return build_sql_generation_prompt(nl_query, current_db_schema)

# New main function for the interactive flow
def interactive_schema_validation(nl_query):
    """
    Main function that handles the complete schema validation flow.
    Returns the final SQL generation prompt after schema confirmation.
    """
    # Step 1: Fetch schema
    # This now calls the imported fetch_schema from db_connector.py
    schema = fetch_schema()

    # Step 2: Build schema confirmation prompt
    confirmation_prompt = build_schema_confirmation_prompt(schema, nl_query)

    # Step 3: Get user response (this will be handled by the calling function)
    # For now, return the confirmation prompt so the main app can handle user interaction
    return {
        "step": "schema_confirmation",
        "prompt": confirmation_prompt,
        "schema": schema,
        "nl_query": nl_query
    }

def process_schema_response(user_response, original_schema, nl_query):
    """
    Processes the user's schema confirmation response and either:
    1. Generates the SQL query (if confirmed)
    2. Asks for corrections (if schema needs updates)
    """
    updated_schema, is_confirmed = parse_schema_corrections(user_response, original_schema)

    if is_confirmed:
        # Generate SQL with confirmed schema
        return {
            "step": "sql_generation",
            "prompt": build_sql_generation_prompt(nl_query, updated_schema),
            "schema": updated_schema
        }
    else:
        # Schema was corrected, show updated schema for final confirmation
        confirmation_prompt = build_schema_confirmation_prompt(updated_schema, nl_query)
        return {
            "step": "schema_reconfirmation",
            "prompt": confirmation_prompt,
            "schema": updated_schema,
            "nl_query": nl_query
        }




    