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
import threading
import traceback

load_dotenv()
client= OpenAI()


def background_ranking_task(job_id):
    """
    Background task to run the ranking algorithm and update job status
    """
    try:
        # Update status to processing
        job = models.JobPost.objects.get(id=job_id)
        job.ranking_status = 'processing'
        job.save()
        
        # Run the ranking algorithm
        result = ranking_algo(job_id)
        
        # Update status to completed
        job.ranking_status = 'completed'
        job.save()
        
        print(f"Background ranking completed for job {job_id}")
        
    except Exception as e:
        # Update status to failed
        try:
            job = models.JobPost.objects.get(id=job_id)
            job.ranking_status = 'failed'
            job.save()
        except:
            pass
        
        print(f"Background ranking failed for job {job_id}: {str(e)}")
        print(traceback.format_exc())


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
        Triggers the candidate ranking algorithm for a job post in background
        """
        job = self.get_object()
        
        # Check if ranking is already in progress
        if job.ranking_status == 'processing':
            return Response(
                {"detail": "Candidate ranking is already in progress. Please wait for completion."},
                status=status.HTTP_202_ACCEPTED
            )
        
        # Check if ranking is already completed
        if job.ranking_status == 'completed':
            return Response(
                {"detail": "Candidate ranking is already completed. Use the ranking-data endpoint to get results."},
                status=status.HTTP_200_OK
            )
        
        try:
            # Start background thread
            thread = threading.Thread(target=background_ranking_task, args=(job.id,))
            thread.daemon = True
            thread.start()
            
            return Response(
                {
                    "detail": "Candidate ranking started in background. Use the ranking-data endpoint to check status and get results.",
                    "status": "processing"
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": f"Error starting candidate ranking: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(methods=["GET"], detail=True, url_path="ranking-data")
    def get_ranking_data(self, request, pk=None):
        """
        Returns the saved candidate ranking data for a job post or current status
        """
        job = self.get_object()
        
        # Return different responses based on ranking status
        if job.ranking_status == 'not_started':
            return Response(
                {
                    "status": "not_started",
                    "detail": "Candidate ranking has not been started yet. Use the rank-candidates endpoint to begin."
                },
                status=status.HTTP_200_OK
            )
        
        elif job.ranking_status == 'processing':
            return Response(
                {
                    "status": "processing",
                    "detail": "Candidate ranking is currently in progress. Please check again later."
                },
                status=status.HTTP_202_ACCEPTED
            )
        
        elif job.ranking_status == 'failed':
            return Response(
                {
                    "status": "failed",
                    "detail": "Candidate ranking failed. Please try again using the rank-candidates endpoint."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        elif job.ranking_status == 'completed':
            if not job.candidate_ranking_data:
                return Response(
                    {
                        "status": "completed",
                        "detail": "Ranking completed but no data available."
                    },
                    status=status.HTTP_200_OK
                )
            
            return Response(
                {
                    "status": "completed",
                    "data": job.candidate_ranking_data
                },
                status=status.HTTP_200_OK
            )
        
        # Fallback for any unexpected status
        return Response(
            {
                "status": job.ranking_status,
                "detail": f"Unknown ranking status: {job.ranking_status}"
            },
            status=status.HTTP_200_OK
        )

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