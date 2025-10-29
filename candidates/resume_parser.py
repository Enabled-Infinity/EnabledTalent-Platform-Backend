import fitz  # PyMuPDF - MUCH faster than PyPDF2
from dotenv import load_dotenv
from pydantic import BaseModel
from io import BytesIO
from openai import OpenAI
import requests

load_dotenv()
client= OpenAI()



def extract_text_from_pdf(pdf_path):
    """Extract text using PyMuPDF - 5-10x faster than PyPDF2"""
    print(f"Reading {pdf_path}...")
    
    doc = fitz.open(pdf_path)
    text = ""
    print("Converting PDF...")
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
    print("Extraction complete.")
    
    return text

def extract_text_from_pdf_url(pdf_url):
    """Extract text from a PDF URL using PyMuPDF - 5-10x faster than PyPDF2."""
    print(f"Downloading PDF from {pdf_url}...")
    
    # Download the PDF content with timeout
    response = requests.get(pdf_url, timeout=30)
    response.raise_for_status()
    
    # Create a file-like object from the content
    pdf_file = BytesIO(response.content)
    
    # Extract text using PyMuPDF (fitz) - much faster
    doc = fitz.open(stream=pdf_file, filetype="pdf")
    text = ""
    print("Converting PDF...")
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
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
    qualifications: list[Info]
    skills: list[Skill]
    work_experience: list[WorkEXP]


def extract_structured_data(text):
    """Extract structured data from text using OpenAI's model."""
    print('Extracting structured information with LLM...')
    
    # Truncate text to 10k characters to speed up LLM processing
    # This should capture most of the resume content without overwhelming the model
    if len(text) > 10000:
        text = text[:10000]
        print(f'Text truncated to 10k characters for faster processing')
    
    # Optimized, shorter prompt for faster LLM response
    system_prompt = """Extract structured resume information. Use "-" for missing fields. Format:
- Personal: name, email, phone, LinkedIn, GitHub, website
- Education: degree type, institution, field, graduation year
- Skills: technical and soft skills
- Experience: company, role, duration, responsibilities
Be concise and accurate."""
    
    try:
        completion = client.responses.parse(
            model="gpt-4o",  # Using gpt-4o instead of non-existent gpt-5
            input=[
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": f"Parse this resume:\n\n{text}"},
            ],
            text_format=ResumeData,
            timeout=60,  # Add timeout to prevent hanging
        )
        print('LLM extraction complete')
        return completion.output_parsed
    except Exception as e:
        print(f'LLM extraction error: {str(e)}')
        raise

def parse_resume(resume_url):
    """Parse a resume from a URL."""
    print(f"Parsing resume from URL: {resume_url}")
    
    try:
        # Extract text from PDF URL
        print('aaya2')
        text = extract_text_from_pdf_url(resume_url)
        
        # Extract structured data from text
        structured_data = extract_structured_data(text)
        print('aaya3')
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