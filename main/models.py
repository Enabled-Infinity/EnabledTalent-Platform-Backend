from django.db import models
from organization.models import Organization
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()

WORKPLACE_TYPES= (
    (1, 'Hybrid'),
    (2, 'On-Site'),
    (3, 'Remote')
)

WORK_TYPES= (
    (1, 'Full-time'),
    (2, 'Part-time'),
    (3, 'Contract'),
    (4, 'Temperory'),
    (5, 'Other'),
    (6, 'Volunteer'),
    (7, 'Internship')
)

class Skills(models.Model):
    name= models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name= 'Skills'
        verbose_name_plural= 'Skills'

class JobPost(models.Model):
    user= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    organization= models.ForeignKey(Organization, on_delete= models.CASCADE)

    title= models.CharField(max_length=100)
    job_desc= models.TextField()
    workplace_type= models.IntegerField(choices=WORKPLACE_TYPES)
    location= models.CharField(max_length=100)
    job_type= models.IntegerField(choices=WORK_TYPES)
    skills= models.ManyToManyField(Skills)
    estimated_salary= models.CharField(max_length=100)
    created_at= models.DateTimeField(auto_now_add=True)
    visa_required= models.BooleanField(default=False)
    candidate_ranking_data = models.JSONField(null=True, blank=True, help_text="Stores candidate ranking results")

    def __str__(self):
        return self.title