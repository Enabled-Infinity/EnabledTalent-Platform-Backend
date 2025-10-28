from django.core.management.base import BaseCommand
from main.tasks import rank_candidates_task
from main.models import JobPost

class Command(BaseCommand):
    help = 'Test the background ranking task'

    def add_arguments(self, parser):
        parser.add_argument('job_id', type=int, help='Job ID to rank candidates for')

    def handle(self, *args, **options):
        job_id = options['job_id']
        
        try:
            job = JobPost.objects.get(id=job_id)
            self.stdout.write(f"Starting ranking task for job: {job.title}")
            
            # Start the background task
            task = rank_candidates_task.delay(job_id)
            self.stdout.write(f"Task started with ID: {task.id}")
            
            # Wait for completion
            import time
            while not task.ready():
                self.stdout.write(f"Task status: {task.state}")
                time.sleep(2)
            
            if task.successful():
                result = task.result
                self.stdout.write(
                    self.style.SUCCESS(f"Task completed successfully!")
                )
                self.stdout.write(f"Result keys: {list(result.keys())}")
            else:
                self.stdout.write(
                    self.style.ERROR(f"Task failed: {task.result}")
                )
                
        except JobPost.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Job with ID {job_id} does not exist")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {e}")
            )
