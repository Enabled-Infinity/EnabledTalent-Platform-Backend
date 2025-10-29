from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from organization.models import Organization
from django.shortcuts  import get_object_or_404
import uuid
from openai import OpenAI
from dotenv import load_dotenv
from users.models import User

load_dotenv()
client= OpenAI()

# Create your models here.

NEEDS= (
    ("YES", "YES"),
    ("NO", "NO"),
    ("PREFER_TO_DISCUSS_LATER", "PREFER_TO_DISCUSS_LATER")
)

DISCLOSURE_PREFERENCE= (
    ("DURING_APPLICATION", "DURING_APPLICATION"),
    ("DURING_INTERVIEW", "DURING_INTERVIEW"),
    ("AFTER_JOB_OFFER", "AFTER_JOB_OFFER"),
    ("AFTER_STARTING_WORK", "AFTER_STARTING_WORK"),
    ("NOT_APPLICABLE", "NOT_APPLICABLE")
)
class CandidateProfile(models.Model):
    PARSING_STATUS = (
        ('not_parsed', 'Not Parsed'),
        ('parsing', 'Parsing in Progress'),
        ('parsed', 'Parsed Successfully'),
        ('failed', 'Parsing Failed'),
    )
    user= models.OneToOneField(User, on_delete=models.CASCADE)
    organization= models.ForeignKey(Organization, on_delete= models.CASCADE, blank=True, null=True)
    resume_file= models.FileField(upload_to='Candidates-Resume', validators=[FileExtensionValidator(allowed_extensions=['pdf'])])
    resume_data= models.JSONField(blank=True, null=True) 
    willing_to_relocate= models.BooleanField(default=True)
    slug= models.SlugField(max_length=255, unique=True, blank=True)
    parsing_status = models.CharField(max_length=20, choices=PARSING_STATUS, default='not_parsed')

    employment_type_preferences= models.JSONField(default=list, help_text="Array of employment types like ['Full-time', 'Part-time', 'Contract']")
    work_mode_preferences= models.JSONField(default=list, help_text="Array of work modes like ['Remote', 'On-site', 'Hybrid']")
    has_workvisa= models.BooleanField(default=False)  # No null=True needed
    disability_categories= models.JSONField(default=list, help_text='Array for Disability criterias"s ')
    accommodation_needs= models.CharField(max_length=100, choices=NEEDS)
    disclosure_preference= models.CharField(max_length=100, choices= DISCLOSURE_PREFERENCE)
    workplace_accommodations= models.JSONField(default=list, help_text="Accommodations for WorkPlace")

    expected_salary_range = models.CharField(max_length=20, blank=True, null=True)
    video_pitch_url = models.FileField(upload_to='Candidates-VideoPitches', validators=[FileExtensionValidator(allowed_extensions=['mp4','mov','wmv','avi','avchd','flv','f4v','swf','mkv'])],
                                       null=True, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Candidate {self.user.email} Profile"
    
    @property
    def get_all_notes(self):
        notes= self.notes_set.all()
        return notes
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.resume_file.name)
            unique_id = str(uuid.uuid4())[:8] 
            self.slug = f"{base_slug}-{unique_id}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering= ['organization', 'id']


class Notes(models.Model):
    resume= models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    identifier= models.TextField()
    section= models.TextField(null=True, blank=True)
    selected_text= models.TextField(null=True, blank=True)
    context= models.JSONField(null=True, blank=True)
    note= models.CharField(max_length=100)
    note_file= models.FileField(upload_to='Notes-File', validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'jpeg', 'png', 'svg'])], blank=True, null=True)
    created_at= models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.note
    

conversation_threads = {}

def get_resume_context(resume_slug: str, user_query: str, thread_id=None, messages=None):
    resume = get_object_or_404(CandidateProfile, slug=resume_slug)
    notes = "\n".join(note.note for note in resume.notes_set.all())
    
    # Build messages array with conversation history if available
    if not messages:
        messages = [
            {"role": "system", "content": f"""
            You are a helpful assistant explaining a resume in a conversational way. Be friendly, brief, and direct.
            
            Resume Details: {resume.resume_data}
            Additional Notes: {notes if notes else "No notes added yet."}
            
            IMPORTANT RULES:
            - Keep responses to 1-3 sentences maximum
            - Use simple, everyday language like talking to a friend  
            - Avoid bullet points, long lists, or formal structure
            - Be direct and specific, not generic
            - Sound like a human explaining to another human, not an AI
            - Don't repeat the question back to them
            
            Example style: "This candidate has 5 years in Python development with strong experience in web apps. They've worked at both startups and large companies."
            """}
        ]
    
    # Add the new user query
    messages.append({"role": "user", "content": user_query})
    
    # Get response from LLM
    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages
    )
    
    # Add the assistant's response to the conversation history
    assistant_message = response.choices[0].message
    messages.append({"role": "assistant", "content": assistant_message.content})

    return {
        "response": assistant_message.content,
        "thread_id": thread_id,
        "messages": messages
    }

def get_career_coach(resume_slug: str, user_query: str, thread_id=None, messages=None):
    resume = get_object_or_404(CandidateProfile, slug=resume_slug)
    notes = "\n".join(note.note for note in resume.notes_set.all())
    
    # Build messages array with conversation history if available
    if not messages:
        messages = [
            {"role": "system", "content": f"""
            You are a friendly career coach having a casual conversation. Be conversational, warm, and brief.
            
            Resume Details: {resume.resume_data}
            Additional Notes: {notes if notes else "No notes added yet."}
            
            IMPORTANT RULES:
            - Keep responses to 1-3 sentences maximum
            - Use simple, everyday language like talking to a friend
            - Avoid bullet points, long lists, or formal structure
            - Be direct and specific, not generic
            - Sound like a human mentor, not an AI assistant
            - Don't repeat the question back to them
            
            Example style: "Based on your Python experience, I'd focus on data analyst roles at tech companies. Your project portfolio shows you can handle real problems."
            """}
        ]
    
    # Add the new user query
    messages.append({"role": "user", "content": user_query})
    
    # Get response from LLM
    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages
    )
    
    # Add the assistant's response to the conversation history
    assistant_message = response.choices[0].message
    messages.append({"role": "assistant", "content": assistant_message.content})

    return {
        "response": assistant_message.content,
        "thread_id": thread_id,
        "messages": messages
    }