from celery import shared_task
from django.shortcuts import get_object_or_404
from .models import JobPost
from .jobpost_candidate_ranker import ranking_algo
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def rank_candidates_task(self, job_id):
    """
    Background task to rank candidates for a job post.
    Returns task status and results.
    """
    try:
        # Update task state to STARTED
        self.update_state(
            state='STARTED',
            meta={'message': 'Starting candidate ranking process...'}
        )
        
        # Get the job post
        job = get_object_or_404(JobPost, id=job_id)
        
        # Update task state to PROGRESS
        self.update_state(
            state='PROGRESS',
            meta={'message': 'Processing candidates and generating rankings...'}
        )
        
        # Run the ranking algorithm
        result = ranking_algo(job_id)
        
        # Update task state to SUCCESS with results
        self.update_state(
            state='SUCCESS',
            meta={
                'message': 'Candidate ranking completed successfully',
                'result': result
            }
        )
        
        return {
            'status': 'SUCCESS',
            'message': 'Candidate ranking completed successfully',
            'result': result
        }
        
    except Exception as exc:
        # Update task state to FAILURE
        self.update_state(
            state='FAILURE',
            meta={
                'message': f'Error during candidate ranking: {str(exc)}',
                'error': str(exc)
            }
        )
        
        logger.error(f"Error in rank_candidates_task for job {job_id}: {str(exc)}")
        
        return {
            'status': 'FAILURE',
            'message': f'Error during candidate ranking: {str(exc)}',
            'error': str(exc)
        }
