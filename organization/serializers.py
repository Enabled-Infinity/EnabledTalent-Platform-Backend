from rest_framework import serializers
from .models import Organization,OrganizationInvite
from users.serializers import UserSerializer

class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model= Organization
        fields= ['name','industry','linkedin_url', 'headquarter_location', 'about', 'employee_size', 'url', 'avatar']

class OrganizationSerializer(serializers.ModelSerializer):
    root_user = UserSerializer()
    users = UserSerializer(many=True)
    class Meta:
        model= Organization
        fields= ['root_user','headquarter_location', 'about', 'employee_size', 'users', 'name', 'url', 'industry', 'linkedin_url', 'created_at', 'avatar', 'id']


class OrganizationInviteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationInvite
        fields = ["email"]


class OrganizationInviteSerializer(serializers.ModelSerializer):
    organization= OrganizationSerializer(read_only=True)
    class Meta:
        model = OrganizationInvite
        fields= ["organization","invite_code","email","accepted","created_at"]