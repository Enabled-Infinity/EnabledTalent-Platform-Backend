import fitz  # PyMuPDF
from django.db import models
from django.core.validators import FileExtensionValidator
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

class CandidateProfile(models.Model):
    resume_file = models.FileField(upload_to='Candidates-Resume', validators=[FileExtensionValidator(allowed_extensions=['pdf'])])
    resume_data = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True)
    current_location = models.CharField(max_length=200)
    linkedin_url = models.URLField(unique=True)
    willing_to_relocate = models.BooleanField(default=True)

    employment_type_preference = models.JSONField(default=list)
    work_mode_preference = models.JSONField(default=list)
    preferred_job_titles = models.JSONField(default=list)
    preferred_industries = models.JSONField(default=list)
    visa_work_auth_details = models.JSONField(default=list, blank=True)  # No null=True needed

    min_expected_salary = models.CharField(max_length=20)
    max_expected_salary = models.CharField(max_length=20)
    availability_to_start = models.CharField(max_length=100)

    github_url = models.URLField(unique=True)
    video_pitch_url = models.FileField(upload_to='Candidates-VideoPitches', validators=[FileExtensionValidator(allowed_extensions=['mp4','mov','wmv','avi','avchd','flv','f4v','swf','mkv'])])
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Candidate {self.phone_number}"

    def save(self, *args, **kwargs):
        """Automatically extract and structure resume text when saving."""
        if self.resume_file and not self.resume_data:  # Process if resume_data is empty
            self.resume_data = self.pdf_to_text(self.resume_file)
        super().save(*args, **kwargs)

    def pdf_to_text(self, pdf_file):
        """Extracts text from a PDF file object."""
        try:
            document = fitz.open(stream=pdf_file.read(), filetype="pdf")  # Read from file directly
            text = "\n\n".join([page.get_text("text").strip() for page in document])
            llm_data= process_with_llm(text)
            print(llm_data)
            self.resume_data= llm_data
            return llm_data
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

def process_with_llm(raw_text):
    """Processes resume text into structured output."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are an AI assistant specializing in resume structuring. Extract relevant details from resumes under these sections:

                Qualification: [List educational background]
                Skills: [List relevant technical and soft skills]
                Job/Work Experience: [Company, job title, duration, key responsibilities]
                Current Job Details: [Role, company, responsibilities]
                Other Projects: [List notable side projects]
                Certifications: [Mention certifications]
                Achievements: [List awards, recognitions]
                Availability to Start: [Extract notice period]
                Total Experience: [Calculate based on job dates]
                Employment Gaps: [Flag significant gaps]

                Strictly follow this format without adding fake details.
                """},
                {"role": "user", "content": f"Extract and structure this resume:\n\n{raw_text}"}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error processing with LLM: {e}")
        return raw_text  # Return raw text if LLM fails