from rest_framework import serializers
from . import models
from django.core.files.storage import FileSystemStorage
from .tasks import process_resume
from users.serializers import UserSerializer
from organization.serializers import OrganizationSerializer

class CreateCandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model= models.CandidateProfile
        fields= ['resume_file', 'willing_to_relocate', 'employment_type_preferences', 'work_mode_preferences',
                 'has_workvisa', 'expected_salary_range', 'video_pitch_url', 'is_available', 'disability_categories',
                 'accommodation_needs', 'workplace_accommodations']
        
    def create(self, validated_data):
        inst = super().create(validated_data)
        
        if resume_file := validated_data.get("resume_file"):
            fs = FileSystemStorage()
            filename = fs.save(resume_file.name, resume_file)
            file_path = fs.path(filename)
            print("filepath------", file_path)
            process_resume.delay(inst.slug, file_path)
            #process_resume(inst.slug, file_path)

        return inst
    

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model= models.Notes
        fields= ['identifier', 'note', 'note_file', 'section', 'selected_text', 'context', 'id']
        
class CandidateProfileSerializer(serializers.ModelSerializer):
    user= UserSerializer()
    organization= OrganizationSerializer()
    get_all_notes= NoteSerializer(many=True)
    class Meta:
        model= models.CandidateProfile
        fields= ['user', 'organization','id', 'slug', 'resume_file', 'resume_data', 'willing_to_relocate', 'employment_type_preferences',
                'work_mode_preferences', 'has_workvisa', 'expected_salary_range', 'video_pitch_url', 'is_available', 'get_all_notes',
                'disability_categories', 'accommodation_needs', 'workplace_accommodations']
        

        
class CreateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model= models.Notes
        fields= ['identifier', 'note', 'section', 'selected_text', 'context', 'note_file']


class PromptSerializer(serializers.Serializer):
    input_text = serializers.CharField()
    resume_slug = serializers.CharField()
    thread_id = serializers.CharField(required=False, allow_null=True)

class PromptResponseSerializer(serializers.Serializer):
    output = serializers.CharField()
    thread_id = serializers.CharField()

class CareerCoachSerializer(serializers.Serializer):
    input_text = serializers.CharField()
    resume_slug = serializers.CharField()
    thread_id = serializers.CharField(required=False, allow_null=True)

class CareerCoachResponseSerializer(serializers.Serializer):
    output = serializers.CharField()
    thread_id = serializers.CharField()