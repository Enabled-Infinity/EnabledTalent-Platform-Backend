from mistralai import Mistral
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()

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

def parse_resume(resume_url):
    # Initialize clients
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not found")
    
    mistral_client = Mistral(api_key=api_key)
    openai_client = OpenAI()
    
    # Process OCR
    print("Initializing OCR...")
    ocr_response = mistral_client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": resume_url
        },
        include_image_base64=True
    )
    
    # Extract text
    text = ""
    for page in ocr_response.pages:
        text += page.markdown
    
    # Extract structured information with LLM
    print('Extracting information with LLM...')
    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "Extract the Relevant Information from Resume Data"},
            {"role": "user", "content": "Return empty list or '-' where no data is found. Here is the data: " + text},
        ],
        response_format=ResumeData,
    )
    
    parsed_data = completion.choices[0].message.parsed
    
    return parsed_data

if __name__ == "__main__":
    # Example usage
    resume_url = "https://api.hiremod.io/media/Candidates-Resume/Jatin_Resume.pdf"
    parsed_resume = parse_resume(resume_url)
    
    # Write to file
    with open("parsed_resume.json", "w") as f:
        f.write(parsed_resume.model_dump_json(indent=2))
    
    print(f"Resume parsed successfully. Output written to parsed_resume.json")