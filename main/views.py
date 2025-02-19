from rest_framework import viewsets, status
from rest_framework import permissions,pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from . import models,serializers


# Create your views here

class CustomPagination(pagination.PageNumberPagination):
    page_size = 10


class BlockNoteViewSet(viewsets.ModelViewSet):
    queryset = models.BlockNote.objects.all()
    serializer_class = serializers.BlockNoteSerializer
    permission_classes = (permissions.IsAuthenticated,)


    def get_queryset(self):
        filter = models.BlockNote.objects.filter(user=self.request.user)
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
        serializer = serializers.ConvoCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
    
    @action(methods=("GET",), detail=True, url_path="organization-convos")
    def get_subspace_convos(self, request, pk):
        return Response(serializers.ConvoSerializer(models.Convo.objects.filter(subspace_id=int(pk)), many=True).data)


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
        serializer.save()
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
    

