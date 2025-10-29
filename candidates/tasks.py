from celery import shared_task
from django.core.files.storage import default_storage
from .models import CandidateProfile
from .resume_parser import parse_resume


@shared_task(bind=True, max_retries=3, time_limit=1800, soft_time_limit=1500)
def parse_resume_task(self, candidate_profile_id):
    """
    Background task to parse resume asynchronously.
    """
    try:
        print(f"Starting resume parsing task for candidate {candidate_profile_id}")
        
        # Get the candidate profile with optimized query
        candidate_profile = CandidateProfile.objects.select_related('user').get(id=candidate_profile_id)
        
        # Check if resume file exists
        if not candidate_profile.resume_file:
            print(f"No resume file found for candidate {candidate_profile_id}")
            candidate_profile.parsing_status = 'failed'
            candidate_profile.save(update_fields=['parsing_status'])
            return {"status": "failed", "error": "No resume file found"}
        
        # Update parsing status to 'in progress'
        candidate_profile.parsing_status = 'parsing'
        candidate_profile.save(update_fields=['parsing_status'])
        
        # Get the file path or URL depending on storage backend
        try:
            # For local storage
            resume_url = default_storage.path(candidate_profile.resume_file.name)
        except NotImplementedError:
            # For S3 or other remote storage
            resume_url = default_storage.url(candidate_profile.resume_file.name)
        
        # Parse the resume
        parsed_data = parse_resume(resume_url)
        
        # Convert Pydantic model to dictionary
        resume_data_dict = parsed_data.model_dump()
        
        # Update the resume record with the parsed data
        candidate_profile.resume_data = resume_data_dict
        candidate_profile.parsing_status = 'parsed'
        candidate_profile.save()
        
        print(f"Resume parsing completed successfully for candidate {candidate_profile_id}")
        return {"status": "success", "data": resume_data_dict}
        
    except Exception as exc:
        print(f"Resume parsing failed for candidate {candidate_profile_id}: {str(exc)}")
        
        # Update parsing status to 'failed'
        try:
            candidate_profile = CandidateProfile.objects.get(id=candidate_profile_id)
            candidate_profile.parsing_status = 'failed'
            candidate_profile.save(update_fields=['parsing_status'])
        except CandidateProfile.DoesNotExist:
            print(f"Candidate profile {candidate_profile_id} not found")
        
        # Retry the task if it's not the last attempt
        if self.request.retries < self.max_retries:
            print(f"Retrying resume parsing task for candidate {candidate_profile_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))  # Exponential backoff
        
        return {"status": "failed", "error": str(exc)}


@shared_task
def cleanup_failed_parsing_tasks():
    """
    Cleanup task to reset stuck parsing statuses.
    """
    print("Starting cleanup of failed parsing tasks")
    
    # Reset parsing status for records that have been stuck in 'parsing' status for more than 1 hour
    from django.utils import timezone
    from datetime import timedelta
    
    stuck_candidates = CandidateProfile.objects.filter(
        parsing_status='parsing',
        updated_at__lt=timezone.now() - timedelta(hours=1)
    )
    
    count = stuck_candidates.count()
    stuck_candidates.update(parsing_status='not_parsed')
    
    print(f"Reset parsing status for {count} stuck candidates")
    return {"reset_count": count}
