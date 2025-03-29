#!/usr/bin/env python
"""
Sample payload for CandidateProfile API.
This script demonstrates the proper format for sending data to create or update a CandidateProfile.
"""

# Sample payload for creating/updating a CandidateProfile
sample_payload = {
    "user": 1,  # User ID
    "organization": 2,  # Organization ID (optional)
    "willing_to_relocate": True,
    "has_workvisa": False,
    "expected_salary_range": "80,000-100,000",
    "is_available": True,
    
    # Array of employment type preferences
    "employment_type_preferences": [
        "Full-time",
        "Contract",
        "Freelance"
    ],
    
    # Array of work mode preferences
    "work_mode_preferences": [
        "Remote",
        "Hybrid"
    ]
}

# Sample for updating just the preferences
update_preferences_payload = {
    "employment_type_preferences": ["Part-time", "Internship"],
    "work_mode_preferences": ["On-site"]
}

# Example of how this would be used in Django views
"""
# In a Django view:
from django.http import JsonResponse
import json

def update_candidate_profile(request, profile_id):
    if request.method == 'PATCH':
        data = json.loads(request.body)
        profile = CandidateProfile.objects.get(id=profile_id)
        
        # Update arrays
        if 'employment_type_preferences' in data:
            profile.employment_type_preferences = data['employment_type_preferences']
        
        if 'work_mode_preferences' in data:
            profile.work_mode_preferences = data['work_mode_preferences']
            
        profile.save()
        return JsonResponse({"status": "success"})
"""

# How to access the array data in Django templates or Python code
"""
# In Python:
profile = CandidateProfile.objects.get(id=1)

# Access the arrays
employment_types = profile.employment_type_preferences  # Returns a Python list
work_modes = profile.work_mode_preferences  # Returns a Python list

# Check if a value is in the arrays
is_fulltime = "Full-time" in profile.employment_type_preferences
is_remote = "Remote" in profile.work_mode_preferences

# In Django template:
{% for type in profile.employment_type_preferences %}
    <li>{{ type }}</li>
{% endfor %}
"""

if __name__ == "__main__":
    print("Sample payload for CandidateProfile:")
    print(sample_payload)
    print("\nEmployment types:", sample_payload["employment_type_preferences"])
    print("Work modes:", sample_payload["work_mode_preferences"]) 