from PyPDF2 import PdfReader
from dotenv import load_dotenv
from pydantic import BaseModel
from io import BytesIO
from openai import OpenAI
import requests

load_dotenv()
client= OpenAI()



def extract_text_from_pdf(pdf_path):
    print(f"Reading {pdf_path}...")
    
    reader = PdfReader(pdf_path)
    number_of_pages = len(reader.pages)
    text=""
    print("Converting PDF...")
    for p in range(number_of_pages):
     page = reader.pages[p]
     text += page.extract_text()
    print("Extraction complete.")
    
    return text

def extract_text_from_pdf_url(pdf_url):
    """Extract text from a PDF URL using PyPDF2 library."""
    print(f"Downloading PDF from {pdf_url}...")
    
    # Download the PDF content
    response = requests.get(pdf_url)
    response.raise_for_status()  # Raise exception for HTTP errors
    
    # Create a file-like object from the content
    pdf_file = BytesIO(response.content)
    
    # Extract text using PyPDF2
    reader = PdfReader(pdf_file)
    number_of_pages = len(reader.pages)
    text = ""
    print("Converting PDF...")
    for p in range(number_of_pages):
        page = reader.pages[p]
        text += page.extract_text()
    print("Extraction complete.")
    return text

class PersonalInfo(BaseModel):
    name: str
    gender: str
    contact_no: str
    email: str
    github: str
    linkedin: str
    website: str

class Info(BaseModel):
    title: str
    description: str

class WorkEXP(BaseModel):
    company_name: str
    job_title: str
    duration: str
    key_responsbilities: list[str]

class Skill(BaseModel):
    name: str

class Projects(BaseModel):
    title: str
    skills_used: list[Skill]
    description: str

class ResumeData(BaseModel):
    personal_info: PersonalInfo
    qualificaions: list[Info]
    skills: list[Skill]
    work_experience: list[WorkEXP]


def extract_structured_data(text):
    """Extract structured data from text using OpenAI's model."""
    print('Extracting structured information with LLM...')
    
    client = OpenAI()
    
    system_prompt = """
                        You are a professional resume parser. Your job is to extract structured information from resume text with a high degree of accuracy and completeness.

                        Instructions:
                        1. Extract only information explicitly stated in the resume. Do not assume or invent details.
                        2. If information is missing, use "-" as a placeholder.
                        3. Capture:
                        - Personal info: name, email, phone, LinkedIn, GitHub, website (if mentioned)
                        - Education: title, description, institution, dates.
                        - Skills: list all mentioned
                        - WorkEXP(Work experience): company name, role, duration, responsibilities.

                        Guidelines:
                        - Normalize tech terms (e.g., React.js, PostgreSQL).
                        - Be concise and structured.
                        - If some fields like GitHub/LinkedIn aren't URLs but are mentioned (e.g., "github.com/jeby"), include them as-is.
                    """
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract structured information from this resume text: " + text},
        ],
        response_format=ResumeData,
    )
    
    return completion.choices[0].message.parsed

def parse_resume(resume_url):
    """Parse a resume from a URL."""
    print(f"Parsing resume from URL: {resume_url}")
    
    try:
        # Extract text from PDF URL
        text = extract_text_from_pdf_url(resume_url)
        
        # Extract structured data from text
        structured_data = extract_structured_data(text)
        #print(structured_data)
        
        # If resume_id is provided, update the specific fields in the Resume model
        return structured_data
        
    except Exception as e:
        print(f"Error parsing resume: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    resume_url = "https://api.hiremod.io/media/Candidates-Resume/Jatin_Resume.pdf"
    parsed_resume = parse_resume(resume_url)
    
    # Write to file
    with open("parsed_resume.json", "w") as f:
        f.write(parsed_resume.model_dump_json(indent=2))
    
    print(f"Resume parsed successfully. Output written to parsed_resume.json")