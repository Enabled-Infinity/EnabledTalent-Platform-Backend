from rest_framework import serializers
from .models import Organization,OrganizationInvite
from users.serializers import UserSerializer

class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model= Organization
        fields= ['name','industry','linkedin_url']

class OrganizationSerializer(serializers.ModelSerializer):
    root_user = UserSerializer()
    users = UserSerializer(many=True)
    class Meta:
        model= Organization
        fields= ['root_user', 'users', 'name', 'industry', 'linkedin_url', 'created_at']


class OrganizationInviteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationInvite
        fields = ["email"]


class OrganizationInviteSerializer(serializers.ModelSerializer):
    organization= OrganizationSerializer(read_only=True)
    class Meta:
        model = OrganizationInvite
        fields= ["organization","invite_code","email","accepted","created_at"]