#from celery import shared_task
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from .models import CandidateProfile
from .pdf_extractor import PersonalInfo,Info,Skill,WorkEXP,Project
from marker.models import create_model_dict
from marker.converters.pdf import PdfConverter
from marker.output import text_from_rendered


load_dotenv()
class ResumeData(BaseModel):
    personal_info: PersonalInfo
    qualifications: list[Info]  # Fixed typo from "qualificaions"
    skills: list[Skill]
    work_experience: list[WorkEXP]
    projects: list[Project]  # Optional field with default empty list


def extract_structured_data(text):
    """Extract structured data from text using OpenAI's model."""
    print('Extracting structured information with LLM...')
    
    client = OpenAI()
    
    system_prompt = """
    You are a specialized resume parser. Extract structured information from the resume text provided.
    Follow these guidelines:
    1. Extract all personal information including name, contact details, and online profiles
    2. For LinkedIn or GitHub, extract the complete URL if available, otherwise just the username
    3. Normalize technical terms consistently (e.g., 'MySQL' not 'MYSQL')
    4. Extract all educational qualifications with institution names and relevant courses
    5. Extract all skills mentioned throughout the resume
    6. Extract work experience including company, job title, duration, and key responsibilities
    7. Extract any projects with skills used and descriptions
    8. For missing fields, use '-' as placeholder
    9. Be thorough and extract all information present in the resume
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


def save_json_to_file(data, output_file):
    """Save JSON data to a file."""
    try:
        print(f"Writing extracted info to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"Successfully wrote extracted info to {output_file}.")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file using Marker library."""
    print(f"Initializing PDF converter for {pdf_path}...")
    converter = PdfConverter(artifact_dict=create_model_dict())
    
    print("Converting PDF...")
    rendered = converter(pdf_path)
    
    print("Extracting text from rendered output...")
    text, _, images = text_from_rendered(rendered)
    print("Extraction complete.")
    
    return text


#@shared_task
def process_resume(resume_slug: str, file_path: str) -> None:
    extracted_text = extract_text_from_pdf(file_path)
    structured_data = extract_structured_data(extracted_text)
    data = structured_data.model_dump_json()
    resume = CandidateProfile.objects.get(slug=resume_slug)
    print(resume)
    resume.resume_data = data
    resume.save()
    print(resume.resume_data)