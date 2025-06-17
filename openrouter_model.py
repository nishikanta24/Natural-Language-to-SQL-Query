import os
from dotenv import load_dotenv
import requests
import re
# Assuming prompt_builder is in the same directory or accessible via sys.path
from prompt_builder import interactive_schema_validation, process_schema_response

load_dotenv()

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

if not openrouter_api_key:
    raise EnvironmentError("OPENROUTER_API_KEY IS NOT FOUND IN ENV VARIABLES. Please set it in your .env file.")

class OpenRouterModel:
    def __init__(self, model_name: str):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        }
        self.model_name = model_name
    
    def invoke(self, prompt_messages: list):
        """
        Sends a list of messages to the OpenRouter API and returns the response.
        """
        payload = {
            "model": self.model_name,
            "messages": prompt_messages,
            "max_tokens": 500, # Max tokens for the model's response
            "temperature": 0.0, # Consistent output for SQL generation
            "stop": ["<|endoftext|>", "<|eot_id|>"] # Common stop tokens for some models
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0 and 'message' in result['choices'][0]:
                return result['choices'][0]['message'].get('content', '')
            
            return str(result) # Return full result string if content not found
        except requests.exceptions.RequestException as e:
            error_details = response.json() if response.content else "No response content"
            raise Exception(f"OpenRouter API Error: {response.status_code if 'response' in locals() else 'N/A'} - {e}\nDetails: {error_details}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during OpenRouter API invocation: {e}")

    def invoke_simple(self, prompt_text: str):
        """
        Simple text-to-text invocation for schema confirmation prompts or direct text queries.
        """
        prompt_messages = [{"role": "user", "content": prompt_text}]
        return self.invoke(prompt_messages)

# Initialize the OpenRouter model globally
try:
    llm = OpenRouterModel("deepseek/deepseek-chat-v3-0324:free") 
    print("✅ OpenRouter model initialized successfully")
except Exception as e:
    print(f"❌ FAILED TO LOAD OPENROUTER MODEL: {e}")
    # Re-raise to stop execution if LLM fails to load, as it's critical
    raise RuntimeError(f"FAILED TO LOAD OPENROUTER MODEL: {e}")

def extract_sql_from_response(response_text: str) -> list:
    """
    Extracts SQL queries from the model response.
    Handles both markdown code blocks and plain text SQL.
    """
    cleaned_response = response_text.strip()
    sql_queries = []
    
    # First, try to find SQL in markdown code blocks
    markdown_blocks = re.findall(r'```(?:sql)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
    for block in markdown_blocks:
        stripped_block = block.strip()
        if stripped_block:
            sql_queries.append(stripped_block)
    
    # If no markdown blocks found, look for plain SQL statements
    if not sql_queries:
        text_without_markdown = re.sub(r'```(?:sql)?\s*(.*?)\s*```', '', cleaned_response, flags=re.DOTALL)
        potential_plain_statements = [s.strip() for s in text_without_markdown.split(';') if s.strip()]
        
        for stmt in potential_plain_statements:
            if re.match(r'^(SELECT|INSERT|UPDATE|DELETE|CREATE|WITH)\b', stmt, re.IGNORECASE | re.DOTALL):
                if stmt not in sql_queries: # Avoid adding duplicates if split by semicolon includes existing markdown
                    sql_queries.append(stmt)

    # Filter to only valid SQL queries (ensure they contain SQL keywords)
    final_sql_queries = [
        q for q in sql_queries 
        if q and any(keyword in q.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'WITH'])
    ]

    return final_sql_queries if final_sql_queries else []

# The new, more flexible generate_sql function (as provided by you)
def generate_sql(prompt: str or list) -> list:
    """
    Generates SQL using the LLM.
    Accepts either a string (NL prompt) or a list of messages (for OpenRouter chat format).
    """
    try:
        print(f"🔄 Sending prompt to OpenRouter ({llm.model_name})...")

        # Convert string prompt to message format if necessary
        if isinstance(prompt, str):
            prompt_messages = [{"role": "user", "content": prompt.strip()}]
        elif isinstance(prompt, list):
            prompt_messages = prompt
        else:
            raise ValueError("Prompt must be a string or a list of messages (chat format).")

        # Check for at least one non-empty message before sending to LLM
        non_empty_msgs = [m for m in prompt_messages if m.get("content", "").strip()]
        if not non_empty_msgs:
            # Return an empty list or an error message to signify no SQL could be generated
            print("⚠️ Warning: Prompt contains no usable content for LLM after stripping. Skipping API call.")
            return ["-- Error: Prompt contained no valid input tokens. --"]

        raw_response = llm.invoke(prompt_messages)
        
        print(f"✅ Model responded successfully")
        print(f"📤 Raw response: {raw_response}")
        
        return extract_sql_from_response(raw_response)
        
    except Exception as e:
        error_msg = f"❌ Error generating SQL: {str(e)}"
        print(error_msg)
        print(f"❌ Full error details: {repr(e)}")
        print(f"❌ Error type: {type(e)}")
        return [f"-- Error: {str(e)} --"]

# --- Functions for interactive flow and automated testing ---

def interactive_sql_generation(nl_query: str, user_input_function=input) -> dict:
    """
    Complete interactive SQL generation with schema validation.
    
    Args:
        nl_query (str): Natural language query from user
        user_input_function: Function to get user input (default: input, can be mocked for testing)
    
    Returns:
        dict: Contains final SQL queries and validation info
    """
    try:
        print(f"🔄 Starting interactive SQL generation for: '{nl_query}'")
        
        # Step 1: Start schema validation
        result = interactive_schema_validation(nl_query)
        
        if result["step"] != "schema_confirmation":
            return {"error": "Failed to fetch schema", "sql_queries": []}
        
        # Step 2: Show schema to user and get confirmation
        print("\n" + "="*60)
        print(result["prompt"])
        print("="*60)
        
        max_attempts = 3
        current_attempt = 0
        
        while current_attempt < max_attempts:
            user_response = user_input_function("\n👤 Your response: ").strip()
            
            if not user_response:
                print("⚠️ Please provide a response.")
                current_attempt += 1 # Count as an attempt
                continue
            
            # Step 3: Process user response
            processed_result = process_schema_response(
                user_response, 
                result["schema"], 
                result["nl_query"]
            )
            
            if processed_result["step"] == "sql_generation":
                # Schema confirmed, generate SQL using the unified generate_sql
                print("\n✅ Schema confirmed! Generating SQL query...")
                
                # Use the new, unified generate_sql function here
                sql_queries = generate_sql(processed_result["prompt"]) 
                
                return {
                    "success": True,
                    "sql_queries": sql_queries,
                    "confirmed_schema": processed_result["schema"],
                    "nl_query": nl_query
                }
            
            elif processed_result["step"] == "schema_reconfirmation":
                # Schema was updated, ask for confirmation again
                print("\n🔄 Schema updated based on your corrections:")
                print("\n" + "="*60)
                print(processed_result["prompt"])
                print("="*60)
                
                # Update result for next iteration
                result = processed_result
                current_attempt += 1
                
            else:
                print("⚠️ Something went wrong with schema processing. Please try again.")
                current_attempt += 1
        
        # Max attempts reached, fallback to original schema and generate SQL
        print(f"❌ Maximum attempts ({max_attempts}) reached. Using original schema as fallback.")
        fallback_result = process_schema_response("CONFIRMED", result["schema"], nl_query)
        # Use the new, unified generate_sql function here for fallback
        sql_queries = generate_sql(fallback_result["prompt"]) 
        
        return {
            "success": False,
            "error": "Schema validation timeout",
            "sql_queries": sql_queries,
            "confirmed_schema": result["schema"],
            "nl_query": nl_query
        }
        
    except Exception as e:
        error_msg = f"❌ Error in interactive SQL generation: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": str(e),
            "sql_queries": [],
            "nl_query": nl_query
        }

# For automated testing without user interaction
def generate_sql_with_auto_confirm(nl_query: str) -> dict:
    """
    Generates SQL with automatic schema confirmation (for testing/automation).
    Skips the interactive schema validation step.
    """
    try:
        # Get schema validation result
        result = interactive_schema_validation(nl_query)
        
        if result["step"] != "schema_confirmation":
            return {"error": "Failed to fetch schema", "sql_queries": []}
        
        # Auto-confirm schema
        processed_result = process_schema_response("CONFIRMED", result["schema"], nl_query)
        
        if processed_result["step"] == "sql_generation":
            # Use the new, unified generate_sql function here
            sql_queries = generate_sql(processed_result["prompt"])
            return {
                "success": True,
                "sql_queries": sql_queries,
                "confirmed_schema": processed_result["schema"],
                "nl_query": nl_query
            }
        else:
            return {"error": "Schema confirmation failed after auto-confirm", "sql_queries": []}
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sql_queries": [],
            "nl_query": nl_query
        }