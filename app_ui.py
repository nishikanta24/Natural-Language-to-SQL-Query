import streamlit as st
from db_connector import fetch_schema
from prompt_builder import build_prompt
from openrouter_model import generate_sql # UPDATED: Changed import from hf_model

def main():
    st.set_page_config(page_title="SQL Query Generator", page_icon="🔍", layout="wide")
    
    st.title("🔍 Ask Your Database in English")
    st.markdown("---")

    # Fetch schema with error handling
    @st.cache_data(ttl=600)
    def get_schema():
        try:
            schema = fetch_schema()
            st.success("✅ Database schema fetched successfully!") 
            return schema
        except Exception as e:
            st.error(f"Failed to fetch database schema: {e}")
            return {}
    
    schema = get_schema()
    
    if not schema:
        st.error("No database schema available. Please check your database connection.")
        return

    # Display schema in an expandable section
    with st.expander("📊 View Database Schema", expanded=False):
        for table, columns in schema.items():
            st.subheader(f"Table: {table}")
            cols_info = []
            for col, typ in columns:
                cols_info.append(f"• **{col}**: {typ}")
            st.markdown("\n".join(cols_info))
            st.markdown("---")

    # Main input section
    st.subheader("💬 Enter Your Question")
    question = st.text_area(
        "Write your question in natural language:",
        placeholder="e.g., Show me all customers from New York",
        height=100
    )

    col1, col2 = st.columns([1, 4])
    
    with col1:
        generate_button = st.button("🚀 Generate SQL", type="primary")
    
    with col2:
        clear_button = st.button("🗑️ Clear")
    
    if clear_button:
        st.rerun()

    if generate_button:
        if not question.strip():
            st.warning("⚠️ Please enter a question!")
        else:
            with st.spinner("🤖 Generating SQL query..."):
                try:
                    prompt = build_prompt(schema, question)
                    print("\n🛠️ DEBUG: Prompt sent to LLM:\n")
                    print(prompt)
                    print("\n🛠️ END DEBUG\n")
                    
                    # Show the built prompt in debug mode
                    with st.expander("🔧 Debug: View Generated Prompt", expanded=False):
                        st.text(prompt)
                    
                    # sql_queries will now be a list of strings
                    sql_queries = generate_sql(prompt) 
                    
                    # Check if any valid queries were returned (not empty and not an error list)
                    if sql_queries and not (len(sql_queries) == 1 and sql_queries[0].startswith("-- Error")):
                        st.success(f"✅ Generated {len(sql_queries)} SQL query(s) successfully!")
                        st.subheader("📝 Generated SQL Query(s)")
                        
                        # Iterate and display each query
                        for i, query in enumerate(sql_queries):
                            st.markdown(f"**Query {i+1}:**")
                            st.code(query, language="sql")
                            if i < len(sql_queries) - 1: # Add separator between queries, but not after the last one
                                st.markdown("---") 
                        
                        # Option to download all queries
                        all_queries_text = "\n\n".join(sql_queries) # Join with double newline for readability
                        st.download_button(
                            label="📋 Download All SQL Queries",
                            data=all_queries_text,
                            file_name="generated_queries.sql",
                            mime="text/sql"
                        )
                    else:
                        st.error("❌ Failed to generate SQL query. Please try rephrasing your question or check the model's response.")
                        # Display the error message if it's the only item in the list
                        if sql_queries and sql_queries[0].startswith("-- Error"):
                            st.code(sql_queries[0]) 
                        
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")

    # Footer
    st.markdown("---")
    st.markdown("*Powered by DeepSeek AI via OpenRouter* 🌐") # UPDATED: Footer text

if __name__ == "__main__":
    main()
