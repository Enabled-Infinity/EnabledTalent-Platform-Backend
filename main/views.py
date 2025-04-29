from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from . import models,serializers
from dotenv import load_dotenv
from openai import OpenAI
from rest_framework.views import APIView
from .jobpost_candidate_ranker import ranking_algo
from .serializers import AgentQuerySerializer, AgentResponseSerializer
from main.agent import query_candidates

load_dotenv()
client= OpenAI()


class JobPostViewSet(viewsets.ModelViewSet):
    permission_classes= (permissions.IsAuthenticated, )
    queryset= models.JobPost.objects.all()
    serializer_class= serializers.JobPostSerializer

    def get_queryset(self, *args, **kwargs):
        return models.JobPost.objects.filter(
            organization= self.request.user.organization_set.all()[0]
        )
    

    def create(self, request, *args, **kwargs):
        user= self.request.user
        serializer= serializers.JobPostCreateSerializer(
            data= request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user= user, organization= user.organization_set.all()[0])
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # For PATCH requests, always set partial=True
        if request.method == 'PATCH':
            partial = True
            
        serializer = serializers.JobPostCreateSerializer(
            instance=instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance= self.get_object()
        self.perform_destroy(instance)
        return Response(status= status.HTTP_200_OK)

    @action(methods=["POST"], detail=True, url_path="rank-candidates")
    def rank_candidates(self, request, pk=None):
        """
        Triggers the candidate ranking algorithm for a job post
        """
        job = self.get_object()
        
        try:
            # Run the ranking algorithm
            result = ranking_algo(job.id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": f"Error ranking candidates: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=["GET"], detail=True, url_path="ranking-data")
    def get_ranking_data(self, request, pk=None):
        """
        Returns the saved candidate ranking data for a job post
        """
        job = self.get_object()
        
        if not job.candidate_ranking_data:
            return Response(
                {"detail": "No ranking data available for this job post."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(job.candidate_ranking_data, status=status.HTTP_200_OK)

class AgentAPI(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = AgentQuerySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        # Get the query from validated data
        query = serializer.validated_data['query']
        
        # Use the agent to search for candidates
        results = query_candidates(query)
        
        # Return the response
        response_serializer = AgentResponseSerializer({
            'results': results
        })
        
        return Response(response_serializer.data)