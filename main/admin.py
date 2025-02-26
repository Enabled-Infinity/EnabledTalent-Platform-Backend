from django.contrib import admin
from .models import CandidateProfile,APICredentials,Channel, Note, BlockNote, Convo, Prompt, PromptFeedback, Skills, JobPost

admin.site.register(APICredentials)
admin.site.register(Channel)
admin.site.register(Note)
admin.site.register(BlockNote)
admin.site.register(Convo)
admin.site.register(Prompt)
admin.site.register(PromptFeedback)
admin.site.register(CandidateProfile)
admin.site.register(Skills)
admin.site.register(JobPost)