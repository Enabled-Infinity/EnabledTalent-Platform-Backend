from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from organization.models import Organization
from django.shortcuts  import get_object_or_404
import uuid
from openai import OpenAI
from dotenv import load_dotenv
from users.models import User
from openai import AssistantEventHandler
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing_extensions import override
from .candidate_agent import query_jobs

load_dotenv()
client= OpenAI()
channel_layer= get_channel_layer()

# Create your models here.

class CandidateProfile(models.Model):
    user= models.OneToOneField(User, on_delete=models.CASCADE)
    organization= models.ForeignKey(Organization, on_delete= models.CASCADE, blank=True, null=True)
    resume_file= models.FileField(upload_to='Candidates-Resume', validators=[FileExtensionValidator(allowed_extensions=['pdf'])])
    resume_data= models.JSONField(blank=True, null=True) 
    willing_to_relocate= models.BooleanField(default=True)
    slug= models.SlugField(max_length=255, unique=True, blank=True)

    employment_type_preferences= models.JSONField(default=list)
    work_mode_preferences= models.JSONField(default=list)
    has_workvisa= models.BooleanField(default=False)  # No null=True needed

    expected_salary_range = models.CharField(max_length=20, blank=True, null=True)
    video_pitch_url = models.FileField(upload_to='Candidates-VideoPitches', validators=[FileExtensionValidator(allowed_extensions=['mp4','mov','wmv','avi','avchd','flv','f4v','swf','mkv'])],
                                       null=True, blank=True)
    is_available = models.BooleanField(default=True)
    assistant_id = models.CharField(max_length=255, blank=True, null=True, help_text="OpenAI Assistant ID for personalized job search")

    def __str__(self):
        return f"Candidate"
    
    @property
    def get_all_notes(self):
        notes= self.notes_set.all()
        return notes
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Create a unique slug based on title and a random string
            base_slug = slugify(self.resume_file.name)
            unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID
            self.slug = f"{base_slug}-{unique_id}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering= ['organization', 'id']


class Notes(models.Model):
    #user
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
            {"role": "system", "content": f"""You are an AI assistant helping users understand a resume.
             Resume Details: {resume.resume_data}
             Additional Notes: {notes if notes else "No notes added yet."}"""}
        ]
    
    # Add the new user query
    messages.append({"role": "user", "content": user_query})
    
    # Get response from LLM
    response = client.chat.completions.create(
        model="gpt-4o",
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

# Adding new models for candidate-side conversations

class CandidateEventHandler(AssistantEventHandler):
    def __init__(self, *, user, thread, stream_ws=False):
        self.user = user
        self.thread = thread
        self.stream_ws = stream_ws
        super().__init__()

    @override
    def on_text_created(self, text) -> None:
        print("CANDIDATE CHAT STARTED.....")
        print(f"\nassistant > ", end="", flush=True)
        self.user.refresh_from_db()
          
    @override
    def on_text_delta(self, delta, snapshot):
        print("received from candidate chat.....")
        print("CHANNEL NAME", self.user.ws_channel_name)
        print(delta.value, end="", flush=True)
        if self.user.ws_channel_name and self.stream_ws:
            async_to_sync(channel_layer.send)(self.user.ws_channel_name, {"type": "prompt_text_receive", "data": {"text": delta.value}})
          
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)
        
    def on_end(self):
        # Retrieve messages added by the Assistant to the thread
        all_messages = client.beta.threads.messages.list(
            thread_id=self.thread.id
        )
        # Return the content of the first message added by the Assistant
        assistant_response = all_messages.data[0].content[0]
        return {'text': assistant_response.text.value}

class CandidateConvo(models.Model):
    thread_id= models.CharField(max_length=100, blank=True, null=True)
    user= models.ForeignKey(User, on_delete=models.CASCADE)
    title= models.CharField(max_length=100, default='New Job Search')
    archived= models.BooleanField(default=False)
    created_at= models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']

class CandidatePrompt(models.Model):
    convo= models.ForeignKey(CandidateConvo, on_delete=models.CASCADE)
    text_query = models.TextField(max_length=10_000)
    response_text = models.TextField(blank=True, null=True)
    similar_jobs = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']

    def __str__(self):
        return str(self.convo)

def create_candidate_message(user_query, thread):
    # Create a message without file attachment (can be modified later if needed)
    message = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_query
    )
    return message

def generate_job_insights_with_gpt4(user_query: str, convo_id: int, *, user):
    get_convo = get_object_or_404(CandidateConvo, id=convo_id)
    history = get_convo.candidateprompt_set.all()
    all_prompts = history.count()
    
    # Get the candidate profile
    try:
        candidate_profile = CandidateProfile.objects.get(user=user)
    except CandidateProfile.DoesNotExist:
        # Handle case where user doesn't have a profile yet
        raise ValueError("User does not have a candidate profile")
        
    # Get or create a personalized assistant for this candidate
    if not hasattr(candidate_profile, 'assistant_id') or not candidate_profile.assistant_id:
        # Create a new assistant with personalized instructions
        resume_data = candidate_profile.resume_data if candidate_profile.resume_data else "{}"
        employment_prefs = candidate_profile.employment_type_preferences if candidate_profile.employment_type_preferences else "[]"
        work_mode_prefs = candidate_profile.work_mode_preferences if candidate_profile.work_mode_preferences else "[]"
        
        # Create a personalized system prompt
        personalized_instructions = f"""You are an AI job search assistant for a specific candidate.
        
Candidate Profile Information:
- Resume Data: {resume_data}
- Employment Type Preferences: {employment_prefs}
- Work Mode Preferences: {work_mode_prefs}
- Willing to Relocate: {"Yes" if candidate_profile.willing_to_relocate else "No"}
- Has Work Visa: {"Yes" if candidate_profile.has_workvisa else "No"}
- Expected Salary Range: {candidate_profile.expected_salary_range or "Not specified"}

When providing job recommendations:
1. Prioritize jobs that match the candidate's skills, experience, and preferences
2. Consider the candidate's willingness to relocate when suggesting jobs in different locations
3. Highlight why each job might be a good fit based on the candidate's profile
4. Be professional, encouraging, and honest about job requirements
5. If the candidate's preferences conflict with job requirements, note this in your response
6. When suggesting jobs, also offer advice on how the candidate might enhance their chances

Remember that your goal is to help this specific candidate find the most suitable job opportunities.
"""
        
        # Create the assistant
        assistant = client.beta.assistants.create(
            name=f"Job Assistant for {user.username}",
            description=f"Personalized job search assistant for {user.username}",
            model="gpt-4o",
            instructions=personalized_instructions
        )
        
        # Store the assistant ID on the candidate profile
        # We need to add assistant_id field to CandidateProfile model
        # For now, we'll store it as an attribute
        candidate_profile.assistant_id = assistant.id
        candidate_profile.save()
    
    # Get job context using the query_jobs function
    rag_context = query_jobs(user_query)

    if all_prompts >= 2:
        thread = client.beta.threads.retrieve(thread_id=get_convo.thread_id)
    else:
        # Create a new thread and save the thread ID
        thread = client.beta.threads.create()
        get_convo.thread_id = thread.id
        get_convo.save()
    
    # Step 1: Create the user message
    create_candidate_message(user_query, thread)
    
    # Step 2: Add RAG context as system messages
    for context in rag_context:
        print(context)
        rag_message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""
This is a job search database result. As the AI job search assistant, use this job data to help answer the job seeker's query: 

{context}

When responding, maintain a professional tone, focus on factual information about the jobs, and highlight the most relevant details for the job seeker's query based on their specific profile and preferences.
""",
            metadata={'message_type': 'rag_context'}
        )
    
    event_handler = CandidateEventHandler(user=user, thread=thread, stream_ws=True)
    
    # Step 3: Create a run to process the messages with the assistant
    # Use the candidate's personalized assistant
    assistant_id = candidate_profile.assistant_id
    
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant_id,
        event_handler=event_handler,
    ) as stream:
        stream.until_done()
        
    # Retrieve messages added by the Assistant to the thread
    all_messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )

    # Return the content of the first message added by the Assistant
    assistant_response = all_messages.data[0].content[0]
    return {'text': assistant_response.text.value}

def parse_followup_job_suggestions(text):
    suggestions = []
    for line in text.split("\n"):
        if len(line) > 0 and line[0].isdigit():
            suggestions.append(line)
    return suggestions

def followup_job_suggestions(query, output, user=None):
    thread = client.beta.threads.create()
    
    # Get the candidate's assistant_id if available
    assistant_id = "asst_PMZqLX1p49iFc60eVCfR77dy"  # Default fallback assistant
    
    if user:
        try:
            candidate_profile = CandidateProfile.objects.get(user=user)
            if candidate_profile.assistant_id:
                assistant_id = candidate_profile.assistant_id
        except CandidateProfile.DoesNotExist:
            pass  # Use the default assistant if no profile exists

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"This is a job search query: {query}. This is the search result: {output}. Suggest 3-5 follow-up searches the job seeker might want to try. Format each suggestion as a numbered item like '1. Search for...'"
    )

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant_id,
        event_handler=CandidateEventHandler(user=None, thread=thread, stream_ws=False),
    ) as stream:
        stream.until_done()

    all_messages = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_response = all_messages.data[0].content[0]
    output = assistant_response.text.value

    return parse_followup_job_suggestions(output)