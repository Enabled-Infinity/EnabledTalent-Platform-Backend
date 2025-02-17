from django.db import models, transaction
from openai import OpenAI
from dotenv import load_dotenv
from users.models import User
from django.utils.crypto import get_random_string
from django.core.validators import validate_image_file_extension

load_dotenv()

client= OpenAI()


INDUSTRIES= (
    (1, "IT SERVICES"),
    (2, "Product Based"),
    (3, "Finance"),
    (4, "Sport")
)

# Create your models here.
class Organization(models.Model):
    root_user= models.OneToOneField(User, on_delete=models.CASCADE,related_name="organization_root_user")
    users= models.ManyToManyField(User)
    name= models.CharField(max_length=100)
    industry= models.IntegerField(choices=INDUSTRIES)
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