import os
import sys
from dotenv import load_dotenv
# Add the current directory to the Python path if running from a different location
# This helps in importing local modules like openrouter_model, test_cases, metrics
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Load environment variables for database connection and API keys
load_dotenv()

# We now import generate_sql_with_auto_confirm for automated evaluation
from openrouter_model import generate_sql_with_auto_confirm 
from test_cases import test_cases
from metrics import calculate_exact_match_accuracy, calculate_execution_accuracy, execute_sql_and_fetch
import pandas as pd # Import pandas for displaying dataframes

def run_evaluation():
    print("--- Starting NL2SQL Model Evaluation ---")

    # --- IMPORTANT: Get column names AND DATA for expected results ---
    # This loop runs the expected SQL once for each test case to fetch its data and column names.
    # This is necessary for robust result comparison in calculate_execution_accuracy.
    print("Pre-fetching data and column names for expected results from database...")
    for i, test_case in enumerate(test_cases):
        # Execute the expected SQL to get its data and column names
        data, cols = execute_sql_and_fetch(test_case["expected_sql"].strip())
        
        # Store the fetched data and columns in the test_case dictionary
        test_case["expected_result"] = data if data is not None else []
        test_case["expected_result_cols"] = cols if cols is not None else []

        if data is None:
            print(f"    WARNING: Expected SQL for Test Case {i+1} failed to execute or returned None. Treating expected result as empty.")
        elif not cols and test_case["expected_result"]: # If no columns but data exists, create generic names
            print(f"    WARNING: Could not fetch columns for Test Case {i+1} from expected SQL. Inferring from data if available.")
            test_case["expected_result_cols"] = [f"col_{j}" for j in range(len(test_case["expected_result"][0]))]
        
    exact_match_scores = []
    execution_accuracy_scores = []

    print("\n--- Running Test Cases ---")
    for i, test_case in enumerate(test_cases):
        nl_query = test_case["nl_query"]
        expected_sql = test_case["expected_sql"].strip()
        
        expected_result_data = test_case["expected_result"]
        expected_result_cols = test_case["expected_result_cols"]

        print(f"\n--- Test Case {i+1} ---")
        print(f"NL Query: {nl_query}")
        print(f"Expected SQL:\n{expected_sql}")

        # Generate SQL from model using the auto-confirm function
        print(f"🔄 Sending NL Query to LLM for SQL generation (with auto-schema-confirm)...")
        # generate_sql_with_auto_confirm returns a dictionary with 'success', 'sql_queries', etc.
        generated_response = generate_sql_with_auto_confirm(nl_query) 
        
        # Extract the first generated SQL query, or an empty string if none
        generated_sql = generated_response["sql_queries"][0] if generated_response["sql_queries"] else "" 

        print(f"Generated SQL:\n{generated_sql}")

        # --- Fetch and Display Generated SQL Result ---
        print("\n--- Generated SQL Query Answer ---")
        generated_data, generated_cols = execute_sql_and_fetch(generated_sql)
        if generated_data is not None and generated_cols is not None:
            if generated_cols: # Only print pandas DF if columns exist
                generated_df = pd.DataFrame(generated_data, columns=generated_cols)
                print(generated_df.to_string(index=False)) # Use to_string for full display
            else: # If no columns but data, just print rows
                print("No columns returned. Data:", generated_data)
        else:
            print("Failed to execute generated SQL or no results.")

        # --- Display Correct SQL Query Answer (already pre-fetched) ---
        print("\n--- Correct SQL Query Answer ---")
        if expected_result_data is not None and expected_result_cols is not None:
            if expected_result_cols: # Only print pandas DF if columns exist
                expected_df = pd.DataFrame(expected_result_data, columns=expected_result_cols)
                print(expected_df.to_string(index=False)) # Use to_string for full display
            else: # If no columns but data, just print rows
                print("No columns returned. Data:", expected_result_data)
        else:
            print("Expected SQL result data not available.")

        # Calculate Exact Match Accuracy
        em_score = calculate_exact_match_accuracy(generated_sql, expected_sql)
        exact_match_scores.append(em_score)
        print(f"\nExact Match Accuracy: {em_score:.2f}")

        # Calculate Execution Accuracy
        # Pass generated_data and generated_cols directly to avoid re-execution
        exec_acc_score = calculate_execution_accuracy(
            generated_sql,
            expected_sql, 
            expected_result_data,
            expected_result_cols,
            generated_data=generated_data, # Pass fetched data
            generated_cols=generated_cols # Pass fetched columns
        )
        execution_accuracy_scores.append(exec_acc_score)
        print(f"Execution Accuracy: {exec_acc_score:.2f}")

    # Report Summary
    avg_em = sum(exact_match_scores) / len(exact_match_scores) if test_cases else 0
    avg_exec_acc = sum(execution_accuracy_scores) / len(execution_accuracy_scores) if test_cases else 0

    print("\n--- Evaluation Summary ---")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Average Exact Match Accuracy: {avg_em:.2%}")
    print(f"Average Execution Accuracy: {avg_exec_acc:.2%}")
    print("--------------------------")

if __name__ == "__main__":
    run_evaluation()