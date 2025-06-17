import os
from db_connector import get_db_connection
import pandas as pd
import re
import psycopg2
import numpy as np # Import numpy for better NaN handling and float comparisons

def normalize_sql(sql_query: str) -> str:
    """Normalizes a SQL query string for exact match comparison."""
    if not isinstance(sql_query, str):
        return ""
    sql_query = re.sub(r'\s+', ' ', sql_query).strip()
    sql_query = re.sub(r'\s*([,;=<>!+-/()\\[\]])\s*', r'\1', sql_query)
    return sql_query.lower()

def calculate_exact_match_accuracy(generated_sql: str, expected_sql: str) -> float:
    """Calculates exact match accuracy."""
    normalized_generated = normalize_sql(generated_sql)
    normalized_expected = normalize_sql(expected_sql)
    return 1.0 if normalized_generated == normalized_expected else 0.0

def execute_sql_and_fetch(sql_query: str):
    """Executes a SQL query using your existing DB connection and returns results."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            print("    Failed to get database connection.")
            return None, None
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            return [list(row) for row in rows], column_names
    except psycopg2.Error as e:
        # Added specific error message for SQL execution issues
        print(f"SQL execution error: {e.pgcode} - {e.pgerror} for query:\n{sql_query}")
        return None, None
    finally:
        if conn:
            conn.close()

def compare_results(generated_data: list, generated_cols: list, expected_data: list, expected_cols: list) -> bool:
    """Compares two sets of SQL query results robustly, focusing on result equivalence."""
    # Handle cases where one or both queries failed to execute or returned no data
    if generated_data is None and expected_data is None:
        return True # Both failed/returned None, treat as a match for this specific scenario
    if generated_data is None or expected_data is None:
        print("    Result comparison failed: One of the result sets is None (query likely failed).")
        return False
    
    # Handle empty results explicitly: If both are empty lists, they match.
    if not generated_data and not expected_data:
        return True
    
    # If one is empty and the other is not, they don't match.
    if (not generated_data and expected_data) or (generated_data and not expected_data):
        print("    Result set size mismatch: One result set is empty, the other is not.")
        return False

    try:
        gen_df = pd.DataFrame(generated_data, columns=generated_cols)
        exp_df = pd.DataFrame(expected_data, columns=expected_cols)

        # Normalize column names to lowercase for robust comparison
        gen_df.columns = [col.lower() for col in gen_df.columns]
        exp_df.columns = [col.lower() for col in exp_df.columns]

        # Check if column sets are identical (order doesn't matter here)
        if set(gen_df.columns) != set(exp_df.columns):
            print(f"    Column set mismatch. Generated: {sorted(gen_df.columns)}, Expected: {sorted(exp_df.columns)}")
            return False

        # Ensure consistent column order for comparison by selecting and reordering
        common_cols = sorted(list(set(gen_df.columns) & set(exp_df.columns)))
        gen_df = gen_df[common_cols]
        exp_df = exp_df[common_cols]

        # Type conversion and normalization for robust comparison of values
        for col in common_cols:
            # Handle numeric types for floating point comparison tolerance
            if pd.api.types.is_numeric_dtype(gen_df[col]) and pd.api.types.is_numeric_dtype(exp_df[col]):
                # Convert to float and round for consistent precision
                gen_df[col] = gen_df[col].astype(float).round(6) 
                exp_df[col] = exp_df[col].astype(float).round(6)
            
            # Handle datetime/date types for consistent string representation
            elif pd.api.types.is_datetime64_any_dtype(gen_df[col]) or pd.api.types.is_datetime64_any_dtype(exp_df[col]):
                # Convert to string format 'YYYY-MM-DD' after normalizing to remove time
                gen_df[col] = pd.to_datetime(gen_df[col]).dt.normalize().dt.strftime('%Y-%m-%d').fillna('')
                exp_df[col] = pd.to_datetime(exp_df[col]).dt.normalize().dt.strftime('%Y-%m-%d').fillna('')
            
            # Ensure all other types are consistent and handle potential None/NaN values by converting to empty string
            else:
                gen_df[col] = gen_df[col].astype(str).fillna('').replace('nan', '')
                exp_df[col] = exp_df[col].astype(str).fillna('').replace('nan', '')
        
        # Convert DataFrames to sorted lists of tuples for robust multiset comparison.
        # This correctly handles row order differences and duplicate rows.
        generated_tuples = [tuple(row) for row in gen_df.sort_values(by=common_cols).values]
        expected_tuples = [tuple(row) for row in exp_df.sort_values(by=common_cols).values]

        return generated_tuples == expected_tuples

    except Exception as e:
        print(f"Error during robust result comparison: {e}")
        return False

def calculate_execution_accuracy(generated_sql: str, expected_sql: str, 
                                 expected_result_data: list, expected_result_cols: list,
                                 generated_data: list = None, generated_cols: list = None) -> float:
    """
    Calculates execution accuracy.
    Optionally accepts pre-fetched generated_data and generated_cols to avoid re-execution.
    """
    # If generated_data/cols are not pre-provided, execute the generated SQL
    if generated_data is None or generated_cols is None:
        generated_data, generated_cols = execute_sql_and_fetch(generated_sql)

    if generated_data is None:
        print("    Generated SQL failed to execute.")
        return 0.0

    # Use the robust compare_results function
    return 1.0 if compare_results(generated_data, generated_cols, expected_result_data, expected_result_cols) else 0.0