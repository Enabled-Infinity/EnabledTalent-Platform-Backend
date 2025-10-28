#!/usr/bin/env python3
"""
Test script for the background task implementation
Run this after starting Celery worker to test the ranking functionality
"""

import os
import sys
import django
import time
import requests
from dotenv import load_dotenv

# Add the project directory to Python path
sys.path.append('/Users/a91834/EnabledTalent/EnabledTalent-Backend/backends')

# Load environment variables
load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backends.settings')
django.setup()

from main.tasks import rank_candidates_task
from main.models import JobPost

def test_background_task():
    """Test the background task directly"""
    print("Testing background task directly...")
    
    # Get the first job post
    try:
        job = JobPost.objects.first()
        if not job:
            print("No job posts found. Please create a job post first.")
            return
        
        print(f"Testing with job: {job.title} (ID: {job.id})")
        
        # Start the task
        task = rank_candidates_task.delay(job.id)
        print(f"Task started with ID: {task.id}")
        
        # Poll for results
        while not task.ready():
            print(f"Task status: {task.state}")
            if task.state == 'PROGRESS':
                print(f"Progress: {task.info}")
            time.sleep(2)
        
        if task.successful():
            result = task.result
            print("Task completed successfully!")
            print(f"Result keys: {result.keys()}")
        else:
            print(f"Task failed: {task.result}")
            
    except Exception as e:
        print(f"Error testing background task: {e}")

def test_api_endpoints():
    """Test the API endpoints (requires running server)"""
    print("\nTesting API endpoints...")
    
    # You would need to replace these with actual values
    base_url = "http://localhost:8000"  # Adjust as needed
    job_id = 1  # Replace with actual job ID
    
    try:
        # Test starting ranking task
        response = requests.post(f"{base_url}/api/jobposts/{job_id}/rank-candidates/")
        if response.status_code == 202:
            data = response.json()
            task_id = data['task_id']
            print(f"Task started via API: {task_id}")
            
            # Poll task status
            while True:
                status_response = requests.get(f"{base_url}/api/jobposts/task-status/{task_id}/")
                status_data = status_response.json()
                
                print(f"Task status: {status_data['status']}")
                
                if status_data['status'] == 'SUCCESS':
                    print("Task completed via API!")
                    break
                elif status_data['status'] == 'FAILURE':
                    print(f"Task failed: {status_data['error']}")
                    break
                
                time.sleep(2)
        else:
            print(f"Failed to start task: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to API server. Make sure Django server is running.")
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    print("Background Task Test Script")
    print("=" * 40)
    
    # Test direct task execution
    test_background_task()
    
    # Test API endpoints (uncomment if server is running)
    # test_api_endpoints()
    
    print("\nTest completed!")
