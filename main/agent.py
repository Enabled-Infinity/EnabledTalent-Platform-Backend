from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts import PromptTemplate
from langgraph.prebuilt import create_react_agent
from openai import OpenAI
load_dotenv()

client= OpenAI()
# FewShot Examples related to the candidates_profile table
# Create the example template

# SQL_PREFIX optimized for candidates_profile table
SQL_PREFIX = """You are an agent designed to interact with a SQL database for recruitment purposes.
Given a recruiter's question, create a syntactically correct SQLite query to find suitable candidates.
You must query the candidate_profiles table to find candidates matching the search criteria.

The available columns in candidate_profiles are: 
- resume_data: Contains whole information about the candidate in structured resume information
- willing_to_relocate: Boolean indicating relocation willingness
- employment_type_preferences: JSON field with preferences like full-time, contract, etc.
- work_mode_preferences: JSON field with preferences like remote, hybrid, onsite
- has_workvisa: Boolean indicating candidate does have workvisa or not
- disability_categories: JSON field with disability categories the candidate identifies with
- accommodation_needs: String with choices from YES, NO, or PREFER_TO_DISCUSS_LATER
- disclosure_preference: String with candidate's preferred timing for disclosure
- workplace_accommodations: JSON field with workplace accommodations needed by the candidate
- expected_salary_range: Salary expectations
- video_pitch_url: URL to candidate's video pitch if available
- is_available: Boolean indicating if candidate is actively looking
- slug: Unique identifier for each candidate (IMPORTANT: always include this field in your SELECT statements)

Query best practices:
- Use LIKE with '%keyword%' for flexible text searching in resume_data
- Include only candidates where is_available = True
- Always include the slug field in your SELECT statements
- Never use SELECT * - only select the specific columns needed
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.)
- Return results ordered by most relevant first (e.g., most experience for senior roles)
- Always check the resume_data column for skills, experience, and qualifications or any data related to candidate
- Limit results to manageable numbers (10-20 candidates)

Your response should be a syntactically correct SQLite query only.
"""

def query_candidates(query: str):
    # Initialize components
    llm = ChatOpenAI(model='gpt-4o')
    db = SQLDatabase.from_uri('postgresql://postgres:Iamreal123@db-instance.cbgqek6s0vqs.eu-north-1.rds.amazonaws.com:5432/enabledtalent')
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    # Format the prompt
    system_message = SystemMessage(content=SQL_PREFIX)

    # Create the agent
    agent_executor = create_react_agent(llm, tools, prompt=system_message)
    
    # Invoke the agent
    results = agent_executor.invoke({"messages": [HumanMessage(content=query)]})

    # Extract and process results
    outputs = [str(result.content) for result in results['messages'] if isinstance(result, ToolMessage)]
    
    # Format the results in a more structured way
    if outputs:
        formatted_outputs = []
        for output in outputs:
            # Check if the output is a database result
            if "Result:" in output:
                # Extract just the results part
                result_part = output.split("Result:")[1].strip()
                formatted_result = result_part
                formatted_outputs.append(formatted_result)
            else:
                formatted_outputs.append(output)
        
        # Process the results with an LLM for better presentation
        summary_prompt = f"""
        You are a recruitment assistant analyzing database query results.
        
        Original Recruiter Query: {query}
        
        Database Results:
        {formatted_outputs}
        
        Provide a concise and structured summary for the recruiter. Highlight key skills, experience, and any special factors (e.g., visa status, relocation preferences). Include links to candidate profiles using the format [[resume:/api/candidates/SLUG/]].
        """
        
        # Get LLM processed summary
        summary_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": summary_prompt}]
        )
        
        processed_results = {
            "raw_results": formatted_outputs,
            "processed_summary": summary_response.choices[0].message.content
        }
        
        return processed_results
    else:
        return {"raw_results": [], "processed_summary": "No relevant candidates found in the database matching the query criteria."}