#!/bin/bash

echo "Starting Stock-Vis Services..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Redis 시작
echo -e "${YELLOW}Starting Redis...${NC}"
if command -v redis-server &> /dev/null; then
    redis-server --daemonize yes
    echo -e "${GREEN}✓ Redis started${NC}"
else
    echo -e "${RED}Redis is not installed. Please install Redis first.${NC}"
    exit 1
fi

# Redis 연결 확인
sleep 2
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}Failed to connect to Redis${NC}"
    exit 1
fi

# Celery Worker 시작
echo -e "${YELLOW}Starting Celery Worker...${NC}"
celery -A config worker -l info --detach

# Celery Beat 시작
echo -e "${YELLOW}Starting Celery Beat...${NC}"
celery -A config beat -l info --detach

# Django 서버 시작
echo -e "${YELLOW}Starting Django Server...${NC}"
python manage.py runserver &

# Frontend 서버 시작
echo -e "${YELLOW}Starting Next.js Frontend...${NC}"
cd frontend && npm run dev &

echo -e "${GREEN}All services started successfully!${NC}"
echo ""
echo "Services running at:"
echo "  - Backend API: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - Redis: localhost:6379"
echo ""
echo "To stop all services, run: ./stop_services.sh"