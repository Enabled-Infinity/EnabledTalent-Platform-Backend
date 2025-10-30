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
    skills_synonames= client.responses.parse(model="gpt-4o", input=[{'role': 'developer', "content": "You're an Keyword/Synoname generating assistant which generates similar keywords for any given particular skill, Example: Sample Input=Python Backend Developer, Sample Output= Python, Django, Flask, ORM, databases, FastAPI, etc, etc"},
                                                                               {'role': 'user', 'content': f"Generate keywords to search resume in the database for the given Skills {job_skills}"},
                                            ],
                                            text_format=SkillOutput)
    expanded_skills= (skills_synonames.output_parsed)
    print(expanded_skills.skills)

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
{job_query.job_desc if isinstance(job_query.job_desc, str) else json.dumps(job_query.job_desc, indent=2)}

Skills Required:
{job_skills}
"""

    # Fetch candidates base queryset
    candidates_qs = CandidateProfile.objects.filter(
        is_available=True,
        resume_data__isnull=False
    ).only(
        'id', 'slug', 'resume_data', 'willing_to_relocate',
        'expected_salary_range', 'employment_type_preferences',
        'disclosure_preference', 'work_mode_preferences', 'workplace_accommodations',
        'has_workvisa'
    )
    
    if job_query.visa_required:
        candidates_qs = candidates_qs.filter(has_workvisa=True)

    # Map job choices to readable strings to compare with candidate preferences
    work_mode_map = {
        1: 'Hybrid',
        2: 'On-site',
        3: 'Remote',
    }
    job_work_mode = work_mode_map.get(job_query.workplace_type)
    job_type_map = {
        1: 'Full-time',
        2: 'Part-time',
        3: 'Contract',
        4: 'Temperory',
        5: 'Other',
        6: 'Volunteer',
        7: 'Internship',
    }
    job_type_text = job_type_map.get(job_query.job_type)

    # Build expanded skills set (lowercased) for quick matching
    expanded_skill_set = set(s.lower().strip() for s in (expanded_skills.skills or []))
    job_skill_set = set(s.lower().strip() for s in job_skills.split(',')) if job_skills else set()

    # Lightweight heuristic scoring to preselect candidates before LLM
    scored_candidates = []
    for c in candidates_qs:
        resume_json = c.resume_data or {}
        # Try common structures from resume parsing
        resume_skills = []
        if isinstance(resume_json, dict):
            if isinstance(resume_json.get('skills'), list):
                resume_skills = resume_json.get('skills', [])
            elif isinstance(resume_json.get('Skills'), list):
                resume_skills = resume_json.get('Skills', [])
        # Fallback: try to derive skills from text if provided
        resume_text_blob = json.dumps(resume_json).lower() if resume_json else ''

        resume_skill_set = set(str(s).lower().strip() for s in resume_skills)
        # Skill overlap score
        skill_overlap = len(expanded_skill_set.intersection(resume_skill_set))
        if skill_overlap == 0 and expanded_skill_set:
            # Simple fuzzy: count occurrences of any expanded skill token in text blob
            skill_overlap = sum(1 for s in expanded_skill_set if s and s in resume_text_blob)

        # Work mode preference match
        work_mode_bonus = 0
        try:
            if job_work_mode and c.work_mode_preferences:
                work_mode_bonus = 1 if any(job_work_mode.lower() == str(w).lower() for w in c.work_mode_preferences) else 0
        except Exception:
            work_mode_bonus = 0

        # Employment type match
        employment_bonus = 0
        try:
            if job_type_text and c.employment_type_preferences:
                employment_bonus = 1 if any(job_type_text.lower() == str(t).lower() for t in c.employment_type_preferences) else 0
        except Exception:
            employment_bonus = 0

        # Aggregate heuristic score
        score = (skill_overlap * 3) + work_mode_bonus + employment_bonus

        # Keep only somewhat relevant
        if score > 0:
            scored_candidates.append((score, c))

    # Sort by score desc and cap the number to control LLM cost
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    # Ensure we have at least 3; if not, broaden by taking a few available profiles
    TOP_CANDIDATES_LIMIT = 5  # control LLM cost
    MIN_CANDIDATES = 3
    selected = [c for _, c in scored_candidates[:TOP_CANDIDATES_LIMIT]]
    if len(selected) < MIN_CANDIDATES:
        needed = MIN_CANDIDATES - len(selected)
        fallback = candidates_qs.exclude(id__in=[c.id for c in selected])[:needed]
        selected.extend(list(fallback))

    candidates_profiles = []
    candidate_data = []
    for c in selected:
        profile = f"""
        Candidate Profile - ID: {c.id}
        ------------------------------
        Slug/Handle: {c.slug}
        
        Summary:
        Resume Data:
        {json.dumps(c.resume_data, indent=2) if c.resume_data else "No resume data available"}
        
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
            "resume_data": json.dumps(c.resume_data) if c.resume_data else "No resume data available",
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
        "job": job_description,
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
    
    try:
        encoding = tiktoken.encoding_for_model("gpt-5")
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
                model="gpt-5",
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