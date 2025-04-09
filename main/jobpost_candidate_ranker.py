from openai import OpenAI
from dotenv import load_dotenv
from agent import query_candidates
from .models import JobPost

load_dotenv()
client= OpenAI()

