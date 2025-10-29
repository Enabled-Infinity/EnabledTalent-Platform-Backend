from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from . import models,serializers
from dotenv import load_dotenv
from openai import OpenAI
from rest_framework.views import APIView
from .tasks import rank_candidates_task
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
        ).select_related('user', 'organization').prefetch_related('skills')
    

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
        Triggers the candidate ranking algorithm for a job post in background
        """
        job = self.get_object()
        
        # Check if already ranked
        if job.ranking_status == 'ranked' and job.candidate_ranking_data:
            return Response(
                {
                    "message": "Candidates already ranked",
                    "ranking_status": job.ranking_status,
                    "data": job.candidate_ranking_data
                },
                status=status.HTTP_200_OK
            )
        
        # Check if currently ranking
        if job.ranking_status == 'ranking':
            return Response(
                {
                    "message": "Candidate ranking already in progress",
                    "ranking_status": job.ranking_status,
                    "task_id": job.ranking_task_id
                },
                status=status.HTTP_202_ACCEPTED
            )
        
        try:
            # Start background task
            task = rank_candidates_task.delay(job.id)
            
            # Update job with task ID
            job.ranking_task_id = task.id
            job.save(update_fields=['ranking_task_id'])
            
            return Response(
                {
                    "message": "Candidate ranking started in background",
                    "ranking_status": "ranking",
                    "task_id": task.id
                },
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            return Response(
                {"error": f"Error starting candidate ranking: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=["GET"], detail=True, url_path="ranking-data")
    def get_ranking_data(self, request, pk=None):
        """
        Returns the saved candidate ranking data for a job post
        """
        job = self.get_object()
        
        # Cache key for ranking data
        cache_key = f"job_ranking_data_{job.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        if not job.candidate_ranking_data:
            return Response(
                {"detail": "No ranking data available for this job post."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cache the ranking data for 1 hour
        cache.set(cache_key, job.candidate_ranking_data, 3600)
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