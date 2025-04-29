from openai import OpenAI
from dotenv import load_dotenv
from .models import JobPost
from candidates.models import CandidateProfile
from django.shortcuts import get_object_or_404
import tiktoken
import json
import datetime
from pydantic import BaseModel
load_dotenv()
client = OpenAI()

"""
def raw_ranking_algo(job_id: int):
    job_query= get_object_or_404(JobPost, id=job_id)
    connection= psycopg2.connect('postgresql://hiremod_user:scL9mjdYqMmY4V61mpKiQg6YiyHDM3Jx@dpg-cvig6apr0fns738ej910-a.oregon-postgres.render.com/hiremod_sz2r')
    cursor = connection.cursor()
    if job_query.visa_required:
        cursor.execute("SELECT * FROM candidates_candidateprofile WHERE is_available = true AND visa_required = true")
    else:
        cursor.execute("SELECT * FROM candidates_candidateprofile WHERE is_available = true")
    tables = cursor.fetchall()
    for table in tables:
        print('ID', table[0]) #id
        #print(table[2]) #resume_data
        print(table)
        print('\n')
        print('\n')
    return 'okok'
""" 


"""
def ranking_algo_unstructured(job_id: int):
    job_query = get_object_or_404(JobPost, id=job_id)
    job_desc= f'''
    Job title: {job_query.title}
    Job Description: {job_query.job_desc}
    Workplace Type: {job_query.workplace_type}
    Location: {job_query.job_type}
    Skills: {job_query.skills}
'''

    candidates = CandidateProfile.objects.filter(is_available=True, resume_data__isnull=False)
    if job_query.visa_required:
        candidates = candidates.filter(has_workvisa=True)

    candidates_profiles= []
    for c in candidates:
        print('ID', c.id)
        print('Slug:', c.slug)
        print('Resume Data:', c.resume_data)
        print('Willing to relocate:', c.willing_to_relocate)
        print('Expected Salary:', c.expected_salary_range)
        print('employment_type_preferences', c.employment_type_preferences)
        print('disclosure_preference', c.disclosure_preference)
        print('workplace_accommodations', c.workplace_accommodations)
        
    return 'done'
"""

class SkillOutput(BaseModel):
    skills: list[str]




from .models import WORKPLACE_TYPES,WORK_TYPES
def ranking_algo(job_id: int):
    job_query = get_object_or_404(JobPost, id=job_id)

    # Convert job types and workplace types to readable text (assuming choices are defined)
    workplace_type_display = dict(WORKPLACE_TYPES).get(job_query.workplace_type, "Not specified")
    job_type_display = dict(WORK_TYPES).get(job_query.job_type, "Not specified")

    # Extract skills into a comma-separated string
    job_skills = ", ".join([skill.name for skill in job_query.skills.all()])

    job_description = f"""
Job Overview
============
Title: {job_query.title}
Location: {job_query.location}
Workplace Type: {workplace_type_display}
Job Type: {job_type_display}
Estimated Salary: {job_query.estimated_salary}
Visa Sponsorship Required: {'Yes' if job_query.visa_required else 'No'}

Job Description:
{job_query.job_desc.strip()}

Skills Required:
{job_skills}
"""

    skills_synonames= client.beta.chat.completions.parse(model="gpt-4o", messages=[{'role': 'system', "content": "You're an Keyword/Synoname generating assistant which generates similar keywords for any given particular skill, Example: Sample Input=Python Backend Developer, Sample Output= Python, Django, Flask, ORM, databases, FastAPI, etc, etc"},
                                                                               {'role': 'user', 'content': f"Generate keywords to search resume in the database for the given Skills {job_skills}"},
                                            ],
                                            response_format=SkillOutput)
    expanded_skills= (skills_synonames.choices[0].message.content)
    print(expanded_skills)
    # Fetch candidates
    candidates = CandidateProfile.objects.filter(is_available=True, resume_data__isnull=False)
    if job_query.visa_required:
        candidates = candidates.filter(has_workvisa=True)

    candidates_profiles = []
    candidate_data = []
    for c in candidates:
        profile = f"""
Candidate Profile - ID: {c.id}
------------------------------
Slug/Handle: {c.slug}

Summary:
Resume Data:
{c.resume_data.strip()}

Willing to Relocate: {'Yes' if c.willing_to_relocate else 'No'}
Expected Salary: {c.expected_salary_range}

Preferred Employment Types: {', '.join(c.employment_type_preferences) if c.employment_type_preferences else 'Not specified'}
Disclosure Preference: {c.disclosure_preference if c.disclosure_preference else 'Not disclosed'}
Workplace Accommodations: {c.workplace_accommodations if c.workplace_accommodations else 'None specified'}

This candidate is currently available and actively looking for opportunities.
"""
        candidates_profiles.append(profile.strip())
        candidate_data.append({
            "id": c.id,
            "slug": c.slug,
            "resume_data": c.resume_data.strip(),
            "profile": profile.strip()
        })

    # Rank candidates based on matching with job description
    ranked_candidates, total_tokens, total_cost = rank_candidates_by_match(job_description, candidate_data)
    
    result_data= {
        "ranked_candidates": ranked_candidates,
        "token_usage": total_tokens,
        "estimated_cost": total_cost,
        "last_updated": str(datetime.datetime.now())
    }
    job_query.candidate_ranking_data = result_data
    job_query.save()

    return {
        "job": job_description.strip(),
        "ranked_candidates": ranked_candidates,
        "token_usage": total_tokens,
        "estimated_cost": total_cost
    }


def rank_candidates_by_match(job_description, candidate_data):
    """
    Ranks candidates based on how well their resume matches the job description.
    Returns a list of candidate IDs ordered by relevance score.
    """
    ranked_results = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0
    
    # Initialize the tokenizer for GPT-4o
    try:
        encoding = tiktoken.encoding_for_model("gpt-4o")
    except:
        # Fallback to cl100k_base which is often used for newer models
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # Cost per 1000 tokens (adjust these rates based on OpenAI's current pricing)
    input_cost_per_1k = 0.01  # $0.01 per 1K input tokens for GPT-4o
    output_cost_per_1k = 0.03  # $0.03 per 1K output tokens for GPT-4o
    
    for candidate in candidate_data:
        prompt = f"""
You are an AI Talent Matcher. Compare the following job description with the candidate's resume data.
Rate how well the candidate's qualifications match the job requirements on a scale of 0-100, 
where 100 is a perfect match. Focus on skills, experience, and overall fit.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate["resume_data"]}

Return only a JSON object with the following structure:
{{
  "score": <numeric_score_between_0_and_100>,
  "reasons": [<list_of_3_key_matching_points_or_mismatches>]
}}
"""
        
        # Count input tokens
        system_message = "You are an AI Talent Matcher that evaluates candidate fit for jobs."
        system_tokens = len(encoding.encode(system_message))
        prompt_tokens = len(encoding.encode(prompt))
        input_tokens = system_tokens + prompt_tokens
        total_input_tokens += input_tokens
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_message},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Get response content and count output tokens
            response_content = response.choices[0].message.content
            output_tokens = len(encoding.encode(response_content))
            total_output_tokens += output_tokens
            
            # Calculate cost for this API call
            input_cost = (input_tokens / 1000) * input_cost_per_1k
            output_cost = (output_tokens / 1000) * output_cost_per_1k
            call_cost = input_cost + output_cost
            total_cost += call_cost
            
            # Parse the result
            result = json.loads(response_content)
            
            ranked_results.append({
                "candidate_id": candidate["id"],
                "candidate_slug": candidate["slug"],
                "score": result["score"],
                "reasons": result["reasons"],
                "tokens_used": input_tokens + output_tokens,
                "cost": call_cost
            })
            
        except Exception as e:
            print(f"Error ranking candidate {candidate['id']}: {str(e)}")
            # Add with a zero score if there's an error
            ranked_results.append({
                "candidate_id": candidate["id"],
                "candidate_slug": candidate["slug"],
                "score": 0,
                "reasons": ["Error during ranking"],
                "tokens_used": input_tokens,
                "cost": (input_tokens / 1000) * input_cost_per_1k
            })
    
    # Sort candidates by score in descending order
    ranked_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Total token usage information
    total_tokens = {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens
    }
    
    # Return the sorted list of candidates with token usage and cost information
    return ranked_results, total_tokens, total_cost