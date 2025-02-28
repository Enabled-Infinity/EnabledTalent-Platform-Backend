from django.contrib import admin
from .models import Organization, OrganizationInvite
# Register your models here.

admin.site.register(Organization)
admin.site.register(OrganizationInvite)