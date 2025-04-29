from rest_framework import serializers
from . import models
from users.serializers import UserSerializer
from organization.serializers import OrganizationSerializer



class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model= models.Skills
        fields= ['name']

class JobPostCreateSerializer(serializers.ModelSerializer):
    skills = serializers.ListField(write_only=True)  # Accept skills as list of strings or objects

    class Meta:
        model = models.JobPost
        fields = ['title', 'job_desc', 'workplace_type', 'location', 'job_type', 'skills', 'estimated_salary', 'visa_required']

    def create(self, validated_data):
        skill_data = validated_data.pop('skills', [])
        job_post = models.JobPost.objects.create(**validated_data)

        for skill_item in skill_data:
            # Handle both string format and object format
            if isinstance(skill_item, dict) and 'name' in skill_item:
                skill_name = skill_item['name']
            else:
                skill_name = skill_item
            
            skill, _ = models.Skills.objects.get_or_create(name=skill_name)  
            job_post.skills.add(skill)

        return job_post
    
    def update(self, instance, validated_data):
        # Update basic fields
        for attr, value in validated_data.items():
            if attr != 'skills':
                setattr(instance, attr, value)
        
        # Handle skills if provided
        if 'skills' in validated_data:
            skill_data = validated_data.pop('skills', [])
            skill_objs = []

            for skill_item in skill_data:
                # Handle both string format and object format
                if isinstance(skill_item, dict) and 'name' in skill_item:
                    skill_name = skill_item['name']
                else:
                    skill_name = skill_item
                
                skill, _ = models.Skills.objects.get_or_create(name=skill_name)
                skill_objs.append(skill)

            instance.skills.set(skill_objs)  # Update ManyToManyField
        
        instance.save()
        return instance

class JobPostSerializer(serializers.ModelSerializer):
    user= UserSerializer()
    organization= OrganizationSerializer()
    skills= SkillSerializer(many=True)
    class Meta:
        model= models.JobPost
        fields= ['user','organization', 'title', 'job_desc', 'workplace_type',
                 'location', 'job_type', 'skills', 'id', 'estimated_salary', 'visa_required', 'candidate_ranking_data']

class AgentQuerySerializer(serializers.Serializer):
    query = serializers.CharField(help_text="The recruiter's query to search for candidates")

class AgentResponseSerializer(serializers.Serializer):
    results = serializers.JSONField(help_text="The results of the agent's query")