from django.db import models, transaction
from openai import OpenAI
from dotenv import load_dotenv
from users.models import User
from django.utils.crypto import get_random_string
from django.core.validators import validate_image_file_extension

load_dotenv()

client= OpenAI()


INDUSTRIES= (
    ("IT SERVICES", "IT SERVICES"),
    ("Product Based", "Product Based"),
    ("Finance", "Finance"),
    ("Sport", "Sport")
)

# Recruitment assistant instructions
INSTRUCTIONS = """
You are an advanced recruitment assistant designed to help HR professionals and hiring managers find the best candidates.

Your capabilities include:
1. Searching candidate profiles using specific criteria (skills, experience, location, etc.)
2. Analyzing resumes and providing insights on candidate qualifications
3. Answering questions about available talent pools
4. Suggesting potential matches for open positions
5. Providing recruitment strategy recommendations

When responding to queries:
- Always prioritize candidate data from the connected database when available
- Present candidate information in a structured, easy-to-understand format
- Suggest follow-up questions when appropriate to help refine searches
- If asked about candidates with criteria not in the database, politely explain the limitations
- Maintain professional language appropriate for HR contexts
- Focus on factual information about candidates based on their profiles
- Respect privacy by not sharing sensitive candidate information

Remember that you're helping recruitment professionals make important hiring decisions, so accuracy and relevancy are critical.
"""

# Create your models here.
class Organization(models.Model):
    root_user= models.OneToOneField(User, on_delete=models.CASCADE,related_name="organization_root_user")
    users= models.ManyToManyField(User)
    name= models.CharField(max_length=100)
    industry= models.CharField(max_length=100, choices=INDUSTRIES)
    assistant_id = models.CharField(max_length=40,blank=True)
    #url= models.URLField(unique=True, blank=True, null=True)
    linkedin_url= models.URLField(unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    """
    avatar= models.ImageField(
        upload_to='organization-avatars', 
        default='default-org.jpeg',
        null=True,
        blank=True,
        validators=[validate_image_file_extension],
    )
    """
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs) -> None:
        is_being_created = self._state.adding
        self.clean()
        super().save(*args, **kwargs)

        if is_being_created:
            assistant = client.beta.assistants.create(
                name=self.name,
                instructions=INSTRUCTIONS,
                tools=[{"type": "file_search"}], #{"type": "code_interpreter"}, 
                model="gpt-4o",
            )
            self.assistant_id = assistant.id
            self.save(update_fields=['assistant_id'])

            def add_member():
                # Add the root_user of the organization as a member
                self.users.add(self.root_user)

            # https://stackoverflow.com/a/78053539/13953998
            transaction.on_commit(add_member)

def create_organization_invite():
    return get_random_string(10)

class OrganizationInvite(models.Model):
    organization= models.ForeignKey(Organization, on_delete=models.CASCADE)
    invite_code = models.CharField(max_length=20, default=create_organization_invite)
    email= models.EmailField(null=False, blank=False)
    accepted= models.BooleanField(default=False)
    created_at= models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return str(self.organization)