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
examples = [
    {
        "query": "Find backend developers with 3+ years of experience and experience in Python",
        "sql": "SELECT resume_data, skills, experience, slug FROM candidates_profile WHERE resume_data->>'$.skills' LIKE '%backend%' AND resume_data->>'$.skills' LIKE '%Python%' AND resume_data->>'$.experience' >= 3 ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    },
    {
        "query": "Show me marketing specialists with at least 5 years of experience",
        "sql": "SELECT resume_data, slug FROM candidates_profile WHERE resume_data->>'$.role' LIKE '%marketing%' AND resume_data->>'$.experience' >= 5 ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    },
    {
        "query": "Find candidates proficient in React and frontend development with 2+ years of experience who are willing to relocate",
        "sql": "SELECT resume_data, willing_to_relocate, slug FROM candidates_profile WHERE resume_data->>'$.skills' LIKE '%React%' AND resume_data->>'$.skills' LIKE '%frontend%' AND resume_data->>'$.experience' >= 2 AND willing_to_relocate = true ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    },
    {
        "query": "Get Python developers located in Bangalore with 4+ years of experience who prefer remote work",
        "sql": "SELECT resume_data, work_mode_preferences, slug FROM candidates_profile WHERE resume_data->>'$.skills' LIKE '%Python%' AND resume_data->>'$.location' = 'Bangalore' AND resume_data->>'$.experience' >= 4 AND work_mode_preferences @> '[\"Remote\"]' ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    },
    {
        "query": "Find UI/UX designers who need accommodation for their disability",
        "sql": "SELECT resume_data, disability_categories, accommodation_needs, slug FROM candidates_profile WHERE resume_data->>'$.role' LIKE '%UI/UX%' AND accommodation_needs = 'YES' ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    },
    {
        "query": "Get candidates with a work visa who are looking for full-time employment",
        "sql": "SELECT resume_data, has_workvisa, employment_type_preferences, slug FROM candidates_profile WHERE has_workvisa = true AND employment_type_preferences @> '[\"Full-time\"]' ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    },
    {
        "query": "Find candidates with an expected salary range between 80K and 100K who have submitted a video pitch",
        "sql": "SELECT resume_data, expected_salary_range, video_pitch_url, slug FROM candidates_profile WHERE expected_salary_range BETWEEN '80000' AND '100000' AND video_pitch_url IS NOT NULL ORDER BY resume_data->>'$.experience' DESC LIMIT 10;"
    }
]

# Create the example template
example_template = """
User Query: {query}
SQL Query: {sql}
"""

example_prompt = PromptTemplate(
    input_variables=["query", "sql"],
    template=example_template
)

# Create FewShotPromptTemplate
few_shot_prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix="You are an AI assistant designed to help with recruitment queries. Below are example queries with their corresponding SQL queries:\n",
    suffix="\nNow generate an SQL query for the given recruiter request: {query}",
    input_variables=["query"]
)

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
    db = SQLDatabase.from_uri('postgresql://hiremod_user:scL9mjdYqMmY4V61mpKiQg6YiyHDM3Jx@dpg-cvig6apr0fns738ej910-a.oregon-postgres.render.com/hiremod_sz2r')
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    # Format the prompt
    formatted_prompt = few_shot_prompt.format(query=query)
    system_message = SystemMessage(content=SQL_PREFIX + "\n" + formatted_prompt)

    # Create the agent
    agent_executor = create_react_agent(llm, tools, messages_modifier=system_message)
    
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