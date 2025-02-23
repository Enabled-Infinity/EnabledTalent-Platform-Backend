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
        "sql": "SELECT name, skills, experience FROM candidates_profile WHERE skills LIKE '%backend%' AND skills LIKE '%Python%' AND experience >= 3 ORDER BY experience DESC;"
    },
    {
        "query": "Show me marketing specialists with at least 5 years of experience",
        "sql": "SELECT name, skills, experience FROM candidates_profile WHERE role LIKE '%marketing%' AND experience >= 5 ORDER BY experience DESC;"
    },
    {
        "query": "Find candidates proficient in React and frontend development with 2+ years of experience",
        "sql": "SELECT name, skills, experience FROM candidates_profile WHERE skills LIKE '%React%' AND skills LIKE '%frontend%' AND experience >= 2 ORDER BY experience DESC;"
    },
    {
        "query": "Get Python developers located in Bangalore with 4+ years of experience",
        "sql": "SELECT name, location, skills, experience FROM candidates_profile WHERE skills LIKE '%Python%' AND location = 'Bangalore' AND experience >= 4 ORDER BY experience DESC;"
    },
    {
        "query": "Find UI/UX designers in Delhi with experience in Figma",
        "sql": "SELECT name, skills, location FROM candidates_profile WHERE role LIKE '%UI/UX%' AND skills LIKE '%Figma%' AND location = 'Delhi' ORDER BY experience DESC;"
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
SQL_PREFIX = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct SQLite query to run, then look at the results of the query and return the answer.
You must query the candidate_profiles table only and use only the relevant columns needed for the query.
The available columns in candidate_profiles are: resume_data, current_location,willing_to_relocate,empoloyment_type_preference, work_mode_preference, min_expected_salary,max_expected_salary,preferred_job_titles, preferred_industries, availability_to_start
Never query for all columns (*) from a specific table—only ask for the relevant ones.
Use LIKE with '%keyword%' for flexible text matching in skills and role.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP, etc.).
Note- Never query candidate who's not_available column is False/No/Null/0
"""

def query_candidates(query: str):
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
    # Extract and return results
    outputs = [str(result.content) for result in results['messages'] if isinstance(result, ToolMessage)]
    print(outputs,'efrefr')
    return outputs



def chat_with_assistant(query: str):    
    # First, check if this is a candidate search query
    candidate_results = query_candidates(query)

    # If we got candidate results, format them as context
    if candidate_results:
        context = "\n".join(candidate_results)
    else:
        context = "No relevant candidates found."

    # Generate a natural language response with AI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful recruitment assistant. Use structured candidate search data when available."},
            {"role": "user", "content": f"Query: {query}\n\nCandidate Search Results:\n{context}"}
        ],
        temperature=0.1
    )

    return response.choices[0].message.content