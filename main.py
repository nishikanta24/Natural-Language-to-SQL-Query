import os
from dotenv import load_dotenv

# Load environment variables at the very beginning of the application
load_dotenv()

# We no longer need to import fetch_schema or build_prompt directly here
# as interactive_sql_generation in openrouter_model handles the entire flow.
from openrouter_model import interactive_sql_generation 

def main_application_flow(user_question: str):
    """
    Orchestrates the interactive process of generating SQL with schema validation.
    """
    print("--- Starting SQL Generation Process ---")
    print(f"\nUser Question: '{user_question}'")

    try:
        # Call the interactive SQL generation function.
        # This function handles schema fetching, user confirmation, 
        # and SQL generation internally.
        result = interactive_sql_generation(user_question)

        if result["success"]:
            print("\n✅ SQL Queries Generated Successfully:")
            for sql_q in result["sql_queries"]:
                print(f"```sql\n{sql_q}\n```") # Format for better readability
            
            # Here you would typically execute these queries against your database
            # Example (uncomment and implement if execution is desired in main):
            # from db_connector import get_db_connection
            # try:
            #     conn = get_db_connection()
            #     cur = conn.cursor()
            #     for sql_q in result["sql_queries"]:
            #         print(f"Executing SQL: {sql_q}")
            #         cur.execute(sql_q)
            #         # Fetch results if it's a SELECT query
            #         if sql_q.strip().upper().startswith('SELECT'):
            #             query_results = cur.fetchall()
            #             print("Query Results:", query_results)
            #     conn.commit() # Commit changes for INSERT/UPDATE/DELETE
            #     cur.close()
            #     conn.close()
            #     print("✅ SQL execution complete.")
            # except Exception as e:
            #     print(f"❌ Error during SQL execution: {e}")
            #     if conn:
            #         conn.rollback() # Rollback in case of error
            #     
            return result["sql_queries"]
        else:
            print(f"\n❌ SQL generation process failed: {result.get('error', 'Unknown error')}")
            # If there was an error and partial queries exist, return them.
            return result.get("sql_queries", []) 
            
    except Exception as e:
        print(f"❌ An unexpected error occurred in the main flow: {e}")
        return [f"-- Error in main_application_flow: {e} --"]


if __name__ == "__main__":
    print("--- Starting NL2SQL Application ---")

    # Example usage:
    question1 = "List the first name and email of all customers who subscribed in 2023."
    generated_sql_1 = main_application_flow(question1)

    print("\n" + "="*80 + "\n") # Separator

    question2 = "Count the total number of entries in the customers table."
    generated_sql_2 = main_application_flow(question2)

    print("\n" + "="*80 + "\n") # Separator

    question3 = "List the top 3 customers with the most recent subscription dates, showing their full name, company, and subscription date."
    generated_sql_3 = main_application_flow(question3)

    print("\n--- NL2SQL Application Finished ---")

