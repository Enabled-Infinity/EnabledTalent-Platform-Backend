#!/bin/bash

# Activate virtual environment (if applicable)
source venv/bin/activate  # Adjust if using a different virtual env

# Run Django server in the background
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000 &

# Run Celery worker in the background
echo "Starting Celery worker..."
celery -A backends worker --pool threads


# Wait for all processes to complete
wait