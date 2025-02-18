from rest_framework import serializers
from . import models
from users.serializers import UserSerializer
from organization.serializers import OrganizationSerializer
 
class APICredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.APICredentials
        fields = ['key_1', 'key_2', 'key_3', 'key_4', 'key_5', 'key_6']


class ChannelSerializer(serializers.ModelSerializer):
    credentials = APICredentialsSerializer()

    class Meta:
        model = models.Channel
        fields = ['id', 'channel_type', 'organization', 'credentials', 'created_at']

class ChannelCreateSerializer(serializers.ModelSerializer):
    credentials = APICredentialsSerializer()

    class Meta:
        model = models.Channel
        fields = ["channel_type", "credentials"]

class ConvoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Convo
        fields = ['title', 'archived','id']




class CreateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Note
        fields = ["note_text", "color","blocknote","note_tag"]

class NoteSerializer(serializers.ModelSerializer):
    #prompt = serializers.SerializerMethodField()

    class Meta:
        model = models.Note
        depth = 3
        fields = ['note_text','note_tag', 'created_at', 'color', 'prompt', 'blocknote', 'id']

    #def get_prompt(self, obj):
        #return PromptSerializer(obj.prompt).data

class CreateBlockNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BlockNote
        fields = ("title", "description", "image")

class BlockNoteSerializer(serializers.ModelSerializer):
    #user = UserSerializer()
    #workspace = WorkSpaceSerializer()
    related_notes= NoteSerializer(many=True,read_only=True)
    
    class Meta:
        model = models.BlockNote
        fields = ("user", "description", "organization", "title", "image", "id", "created_at","related_notes")


class PromptCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Prompt
        fields = ("text_query", "file_query")

class ConvoSerializer(serializers.ModelSerializer):
    all_notes = NoteSerializer(many=True)

    class Meta:
        model = models.Convo
        fields = ('id', 'thread_id', 'title', 'archived', 'created_at', 'all_notes')


class PromptSerializer(serializers.ModelSerializer):
    convo= ConvoSerializer()
    class Meta:
        model = models.Prompt
        fields = ('id', 'convo', 'author', 'text_query', 'file_query', 'response_text', 'similar_questions', 'chart_data', 'created_at')


class PromptFeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PromptFeedback
        fields = ('category', 'note')