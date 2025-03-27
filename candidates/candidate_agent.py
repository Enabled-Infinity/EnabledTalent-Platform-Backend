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

client = OpenAI()

# FewShot Examples related to the JobPost table
examples = [
    {
        "query": "Find software development jobs that require Python skills",
        "sql": "SELECT title, job_desc, estimated_salary FROM main_jobpost WHERE job_desc LIKE '%Python%' OR title LIKE '%Python%' ORDER BY created_at DESC;"
    },
    {
        "query": "Show me marketing positions in remote work mode",
        "sql": "SELECT title, job_desc, estimated_salary FROM main_jobpost WHERE (title LIKE '%marketing%' OR job_desc LIKE '%marketing%') AND workplace_type = 3 ORDER BY created_at DESC;"
    },
    {
        "query": "Find frontend development jobs with React",
        "sql": "SELECT title, job_desc, estimated_salary FROM main_jobpost WHERE (job_desc LIKE '%React%' OR title LIKE '%React%') AND (job_desc LIKE '%frontend%' OR title LIKE '%frontend%') ORDER BY created_at DESC;"
    },
    {
        "query": "Get full-time software engineering positions in Bangalore",
        "sql": "SELECT title, job_desc, estimated_salary, location FROM main_jobpost WHERE location = 'Bangalore' AND job_type = 1 AND (title LIKE '%software%' OR job_desc LIKE '%software%') ORDER BY created_at DESC;"
    },
    {
        "query": "Find UI/UX design jobs in hybrid work mode",
        "sql": "SELECT title, job_desc, estimated_salary FROM main_jobpost WHERE (title LIKE '%UI/UX%' OR job_desc LIKE '%UI/UX%' OR title LIKE '%design%') AND workplace_type = 1 ORDER BY created_at DESC;"
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
    prefix="You are an AI assistant designed to help job seekers find suitable positions. Below are example queries with their corresponding SQL queries:\n",
    suffix="\nNow generate an SQL query for the given job seeker request: {query}",
    input_variables=["query"]
)

# SQL_PREFIX optimized for JobPost table
SQL_PREFIX = """You are an agent designed to interact with a SQL database for job searching.
Given a job seeker's question, create a syntactically correct SQLite query to find suitable job opportunities.
You must query the main_jobpost table to find jobs matching the search criteria.

The available columns in main_jobpost are: 
- id: Unique job ID
- title: Job title
- job_desc: Full job description
- workplace_type: Integer (1=Hybrid, 2=On-Site, 3=Remote)
- location: Job location
- job_type: Integer (1=Full-time, 2=Part-time, 3=Contract, 4=Temporary, 5=Other, 6=Volunteer, 7=Internship)
- estimated_salary: Expected salary range
- created_at: When the job was posted
- organization_id: Foreign key to organization table
- user_id: Foreign key to user table

Query best practices:
- Use LIKE with '%keyword%' for flexible text searching in title and job_desc
- Never use SELECT * - only select the specific columns needed
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.)
- Return results ordered by most recent first (created_at DESC)
- Limit results to manageable numbers (5-10 jobs)

Your response should be a syntactically correct SQLite query only.
"""

def query_jobs(query: str):
    # Initialize components
    llm = ChatOpenAI(model='gpt-4o')
    db = SQLDatabase.from_uri('sqlite:///db.sqlite3')
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
    
    # Format the results in a more structured way for better RAG context
    if outputs:
        formatted_outputs = []
        for output in outputs:
            # Check if the output is a database result
            if "Result:" in output:
                # Extract just the results part
                result_part = output.split("Result:")[1].strip()
                formatted_result = f"""
### Job Search Results
{result_part}

Use the above job information to answer the job seeker's query: "{query}"
                """
                formatted_outputs.append(formatted_result)
            else:
                formatted_outputs.append(output)
        return formatted_outputs
    else:
        return ["No relevant jobs found in the database matching your criteria."]
