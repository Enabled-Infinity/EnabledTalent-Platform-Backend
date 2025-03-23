import argparse
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from pydantic import BaseModel
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Extract structured data from resume PDF')
    parser.add_argument('--pdf', type=str, default=None, help='Path to resume PDF')
    parser.add_argument('--output_dir', type=str, default="outputscript1", help='Output directory path')
    return parser.parse_args()

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

def save_text_to_file(text, output_file):
    """Save extracted text to a file."""
    try:
        print(f"Writing extracted text to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully wrote extracted text to {output_file}.")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")

def save_json_to_file(data, output_file):
    """Save JSON data to a file."""
    try:
        print(f"Writing extracted info to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"Successfully wrote extracted info to {output_file}.")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")

# Define Pydantic models for structured data extraction
class PersonalInfo(BaseModel):
    name: str
    gender: str
    contact_no: str
    email: str
    github: str
    linkedin: str
    website: str

class Info(BaseModel):
    """Info can be Educational Qualification or Course"""
    title: str
    description: str

class Skill(BaseModel):
    name: str

class WorkEXP(BaseModel):
    company_name: str
    job_title: str
    duration: str
    key_responsbilities: list[str]

class Project(BaseModel):
    title: str
    skills_used: list[Skill]
    description: str

class ResumeData(BaseModel):
    personal_info: PersonalInfo
    qualifications: list[Info]  # Fixed typo from "qualificaions"
    skills: list[Skill]
    work_experience: list[WorkEXP]
    projects: list[Project] = []  # Optional field with default empty list

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

def main():
    """Main function to orchestrate the resume parsing process."""
    args = parse_arguments()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get all PDF files from the resumes directory
    resume_dir = "./resumes"
    pdf_files = [f for f in os.listdir(resume_dir) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(resume_dir, pdf_file)
        base_name = os.path.splitext(pdf_file)[0]
        
        # Define output paths
        text_output = os.path.join(args.output_dir, f"{base_name}.txt")
        json_output = os.path.join(args.output_dir, f"{base_name}.json")
        
        try:
            print(f"\nProcessing {pdf_file}...")
            
            # Extract text from PDF
            extracted_text = extract_text_from_pdf(pdf_path)
            
            # Save extracted text to file
            save_text_to_file(extracted_text, text_output)
            
            # Extract structured data using LLM
            structured_data = extract_structured_data(extracted_text)
            
            # Convert to JSON and save
            json_data = structured_data.model_dump_json(indent=4)
            save_json_to_file(json_data, json_output)
            
            print(f"Successfully processed {pdf_file}")
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue
    
    print("\nAll resume processing completed!")

if __name__ == "_main_":
    main()