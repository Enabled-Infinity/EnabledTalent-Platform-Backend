from celery import shared_task
from .models import JobPost
from .jobpost_candidate_ranker import ranking_algo


@shared_task(bind=True, max_retries=3)
def rank_candidates_task(self, job_id):
    """
    Background task to rank candidates for a job post.
    """
    try:
        print(f"Starting candidate ranking task for job {job_id}")
        
        # Get the job post
        job_post = JobPost.objects.get(id=job_id)
        
        # Update ranking status to 'in progress'
        job_post.ranking_status = 'ranking'
        job_post.save(update_fields=['ranking_status'])
        
        # Run the ranking algorithm
        result = ranking_algo(job_id)
        
        # Update the job post with results
        job_post.candidate_ranking_data = {
            "ranked_candidates": result.get("ranked_candidates", []),
            "token_usage": result.get("token_usage", {}),
            "estimated_cost": result.get("estimated_cost", 0),
            "last_updated": result.get("last_updated", "")
        }
        job_post.ranking_status = 'ranked'
        job_post.save()
        
        print(f"Candidate ranking completed successfully for job {job_id}")
        return {
            "status": "success", 
            "job_id": job_id,
            "ranked_candidates_count": len(result.get("ranked_candidates", [])),
            "total_cost": result.get("estimated_cost", 0)
        }
        
    except Exception as exc:
        print(f"Candidate ranking failed for job {job_id}: {str(exc)}")
        
        # Update ranking status to 'failed'
        try:
            job_post = JobPost.objects.get(id=job_id)
            job_post.ranking_status = 'failed'
            job_post.save(update_fields=['ranking_status'])
        except JobPost.DoesNotExist:
            print(f"Job post {job_id} not found")
        
        # Retry the task if it's not the last attempt
        if self.request.retries < self.max_retries:
            print(f"Retrying candidate ranking task for job {job_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))  # Exponential backoff
        
        return {"status": "failed", "error": str(exc)}


@shared_task
def cleanup_failed_ranking_tasks():
    """
    Cleanup task to reset stuck ranking statuses.
    """
    print("Starting cleanup of failed ranking tasks")
    
    # Reset ranking status for records that have been stuck in 'ranking' status for more than 2 hours
    from django.utils import timezone
    from datetime import timedelta
    
    stuck_jobs = JobPost.objects.filter(
        ranking_status='ranking',
        updated_at__lt=timezone.now() - timedelta(hours=2)
    )
    
    count = stuck_jobs.count()
    stuck_jobs.update(ranking_status='not_ranked', ranking_task_id=None)
    
    print(f"Reset ranking status for {count} stuck job posts")
    return {"reset_count": count}
