from rest_framework import viewsets, status
from rest_framework import permissions,pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from . import models,serializers
from django.shortcuts import get_object_or_404
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from .models import generate_insights_with_gpt4
load_dotenv()
client= OpenAI()

# Create your views here

class CustomPagination(pagination.PageNumberPagination):
    page_size = 10


class BlockNoteViewSet(viewsets.ModelViewSet):
    queryset = models.BlockNote.objects.all()
    serializer_class = serializers.BlockNoteSerializer
    permission_classes = (permissions.IsAuthenticated,)


    def get_queryset(self):
        filter = models.BlockNote.objects.filter(organization=self.request.user.organization_set.all()[0])
        return filter
    
    
    """
    def retrieve(self, request, *args, **kwargs):
        instance = get_object_or_404(models.BlockNote,pk=kwargs['pk'], user=request.user)
        notes = (instance.note_set.all())
        note_serializer = serializers.NoteSerializer(notes, many=True)
        return Response(note_serializer.data)
        #return Response(xyz)
    """
    
    
    def create(self, request, *args, **kwargs):
        serializer = serializers.CreateBlockNoteSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(
            user=request.user,
            organization=self.request.user.organization_set.all()[0]
                        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance= self.get_object()
        serializer = serializers.CreateBlockNoteSerializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance= self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class NoteViewSet(viewsets.ModelViewSet):
    permission_classes= (permissions.IsAuthenticated, )
    queryset= models.Note.objects.all()
    serializer_class= serializers.NoteSerializer


    def update(self, request, *args, **kwargs):
        partial= kwargs.pop('partial', False)
        instance= self.get_object()
        serializer= serializers.CreateNoteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance= self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_200_OK)
    

class ConvoViewSet(viewsets.ModelViewSet):
    queryset = models.Convo.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.ConvoSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        organization = self.request.user.organization_set.first()
        return models.Convo.objects.filter(organization=organization)
    

    def create(self, request, *args, **kwargs):
        org=(request.user.organization_set.all()[0])
        serializer = serializers.ConvoCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(organization= org)
        return Response(serializer.data,status=status.HTTP_201_CREATED)
    
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = serializers.ConvoCreateSerializer(
            instance=instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # should work ig idk test and see

        self.perform_destroy(instance)
        organization = self.request.user.organization_set.first()

        if models.Convo.objects.filter(organization=organization).count() < 1:
            models.Convo.objects.create(
                organization=organization,
                
            )
            
        return Response(status=status.HTTP_200_OK)
    


class ChannelViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = models.Channel.objects.all()
    serializer_class = serializers.ChannelSerializer

    def get_queryset(self):
        # Customize queryset based on the request or user
        user = self.request.user
        return models.Channel.objects.filter(organization=user.organization_set.first())
    

    def create(self, request, *args, **kwargs):
        serializer = serializers.ChannelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization= self.request.user.organization_set.all()[0])
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = serializers.ChannelCreateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        #instance.activated = False
        #instance.save()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_200_OK)
    



class PromptViewSet(viewsets.ModelViewSet):
    # permission_classes = (permissions.IsAuthenticated,)
    permission_classes = (permissions.AllowAny,)
    queryset = models.Prompt.objects.all().order_by("-created_at")
    serializer_class = serializers.PromptSerializer

    def get_queryset(self, *args, **kwargs):
        convo_id = self.kwargs.get("pk")  # Retrieve 'pk' from URL kwargs
        convo = get_object_or_404(models.Convo, id=convo_id)
        # n1=models.Prompt.objects.filter(convo=convo)
        # return models.Prompt.objects.filter(convo=convo)
        # print(convo.prompt_set.all())
        return convo.prompt_set.all()  # Return prompts associated with the

    def create(self, request, *args, **kwargs):
        start_time = datetime.now()
        serializer = serializers.PromptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        convo = get_object_or_404(models.Convo, pk=self.kwargs["pk"])

        channel_name = request.user.ws_channel_name
        #if not channel_name:
            #return Response(
                #{"detail": "User is not connected to any workspace"},
                #status=status.HTTP_400_BAD_REQUEST,
            #)

        # Create Prompt instance but do not save it yet
        prompt_instance = serializer.save(convo=convo, author=request.user)

        history_counts = convo.prompt_set.all().count()

        # This logic for thread creation and one iside of generate_inghts_with_gpt4 doesnt make sense
        if history_counts >= 2:
            print("2-1")
            thread = client.beta.threads.retrieve(thread_id=convo.thread_id)
        else:
            print("2-2")
            thread = client.beta.threads.create()
            convo.thread_id = thread.id
            convo.save()

        response_data = generate_insights_with_gpt4(
            user_query=prompt_instance.text_query,
            convo=convo.id,
            channel_name=channel_name,
            file=prompt_instance.file_query or None,
        )
        print(response_data.get("text", None),'fre')
        prompt_instance.response_text= response_data.get("text", None)
        prompt_instance.response_file= response_data.get("image", None)
        prompt_instance.save()

        end_time = datetime.now()

        print(f"Time taken: {end_time - start_time}")

        # TODO: Need to send related document in response.
        return Response(
            {
                "id": prompt_instance.id,
                "text_query": prompt_instance.text_query,
                "response_text": prompt_instance.response_text,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = serializers.PromptCreateSerializer(
            instance, request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=("POST",), detail=True, url_path="feedback")
    def prompt_feedback_upload(self, request, pk):
        prompt = get_object_or_404(models.Prompt, id=pk)
        serializer = serializers.PromptFeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user, prompt=prompt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=("POST",), detail=True, url_path="create-note")
    def create_note(self, request, pk):
        prompt = get_object_or_404(models.Prompt, id=pk)
        request.data["prompt"] = prompt.pk
        serializer = serializers.CreateNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(prompt=prompt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=("POST",), detail=True, url_path="create-note")
    def get_follow_up_questions(self, request, pk):
        prompt_obj = get_object_or_404(models.Prompt, id=pk)

        resp = models.followup_questions(
            query=prompt_obj.text_query, output=prompt_obj.response_text
        )
        prompt_obj.similar_questions = resp

        prompt_obj.save()
        return Response({"similar_questions": resp}, status=status.HTTP_200_OK)