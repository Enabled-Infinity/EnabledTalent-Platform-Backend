# Background Task Setup Guide

## Overview
The candidate ranking system now uses Celery for background task processing to prevent timeout issues. The ranking algorithm runs in the background while the API returns immediately with a task ID.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install celery redis
```

### 2. Install and Start Redis
**On macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**On Windows:**
Download Redis from https://github.com/microsoftarchive/redis/releases

### 3. Start Celery Worker
In your project directory, run:
```bash
cd backends
celery -A backends worker --loglevel=info
```

### 4. Start Celery Beat (Optional - for scheduled tasks)
```bash
celery -A backends beat --loglevel=info
```

### 5. Monitor Tasks (Optional)
```bash
celery -A backends flower
```

## API Usage

### Start Ranking Task
**POST** `/api/jobposts/{job_id}/rank-candidates/`

**Response:**
```json
{
    "message": "Candidate ranking task started successfully",
    "task_id": "abc123-def456-ghi789",
    "status": "PENDING",
    "job_id": 1
}
```

### Check Task Status
**GET** `/api/jobposts/task-status/{task_id}/`

**Response (PENDING):**
```json
{
    "task_id": "abc123-def456-ghi789",
    "status": "PENDING",
    "message": "Task is waiting to be processed"
}
```

**Response (SUCCESS):**
```json
{
    "task_id": "abc123-def456-ghi789",
    "status": "SUCCESS",
    "message": "Task completed successfully",
    "result": {
        "job": "...",
        "ranked_candidates": [...],
        "token_usage": {...},
        "estimated_cost": 0.15
    }
}
```

**Response (FAILURE):**
```json
{
    "task_id": "abc123-def456-ghi789",
    "status": "FAILURE",
    "message": "Task failed",
    "error": "Error message here"
}
```

## Frontend Integration

### JavaScript Example
```javascript
// Start the ranking task
async function startRanking(jobId) {
    const response = await fetch(`/api/jobposts/${jobId}/rank-candidates/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    });
    
    const data = await response.json();
    return data.task_id;
}

// Poll for task completion
async function pollTaskStatus(taskId) {
    const response = await fetch(`/api/jobposts/task-status/${taskId}/`);
    const data = await response.json();
    
    if (data.status === 'SUCCESS') {
        return data.result;
    } else if (data.status === 'FAILURE') {
        throw new Error(data.error);
    } else {
        // Still processing, poll again after delay
        await new Promise(resolve => setTimeout(resolve, 2000));
        return pollTaskStatus(taskId);
    }
}

// Complete workflow
async function rankCandidates(jobId) {
    try {
        const taskId = await startRanking(jobId);
        console.log('Task started:', taskId);
        
        const result = await pollTaskStatus(taskId);
        console.log('Ranking completed:', result);
        return result;
    } catch (error) {
        console.error('Ranking failed:', error);
    }
}
```

## Configuration

### Celery Settings (settings.py)
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
```

### Production Considerations
- Use a production Redis instance
- Configure Celery workers with appropriate concurrency
- Set up monitoring and logging
- Consider using Celery Beat for scheduled tasks
- Use Flower for task monitoring in production
