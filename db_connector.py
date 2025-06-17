import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database using environment variables.
    Raises an exception if connection fails.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        print("✅ Database connection successful.")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        raise # Re-raise the exception after logging

def fetch_schema():
    """
    Connects to the database, retrieves the schema (table names and their columns
    with data types), and returns it as a dictionary.

    Returns:
        dict: A dictionary where keys are table names (str) and values are
              lists of (column_name, data_type) tuples.
              Example: {'customers': [('id', 'integer'), ('name', 'text')]}
    """
    conn = None # Initialize conn to None
    cur = None  # Initialize cur to None
    schema = {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch all table names from the public schema
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()

        # For each table, fetch its column names and data types
        for (table_name,) in tables:
            cur.execute(sql.SQL("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """), [table_name])
            columns = cur.fetchall()
            schema[table_name] = columns # Already in (col_name, col_type) tuple format
        
        print("✅ Database schema fetched successfully.")
        return schema
    except Exception as e:
        print(f"❌ Error fetching schema: {e}")
        return {} # Return empty schema on error
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    # This block runs only when db_connector.py is executed directly
    print("--- Fetching Database Schema ---")
    schema = fetch_schema()
    if schema:
        for table, cols in schema.items():
            print(f"\nTable: {table}")
            for col_name, col_type in cols:
                print(f"  - {col_name} ({col_type})")
    else:
        print("No schema information retrieved. Check database connection and permissions.")

            
    