#!/bin/bash

# Background Task Services Startup Script
# This script helps start all necessary services for background task processing

echo "Starting Background Task Services..."
echo "=================================="

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis server..."
    if command -v brew &> /dev/null; then
        brew services start redis
    elif command -v systemctl &> /dev/null; then
        sudo systemctl start redis-server
    else
        echo "Please start Redis manually"
        exit 1
    fi
else
    echo "Redis is already running"
fi

# Wait a moment for Redis to start
sleep 2

# Start Celery worker
echo "Starting Celery worker..."
cd /Users/a91834/EnabledTalent/EnabledTalent-Backend/backends
celery -A backends worker --loglevel=info --detach

echo "Services started successfully!"
echo ""
echo "To monitor tasks, run: celery -A backends flower"
echo "To stop the worker, run: celery -A backends control shutdown"
echo "To check worker status, run: celery -A backends inspect active"
