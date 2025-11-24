#!/bin/bash

echo "Stopping Stock-Vis Services..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Celery 프로세스 종료
echo -e "${YELLOW}Stopping Celery processes...${NC}"
pkill -f "celery.*config" 2>/dev/null
echo -e "${GREEN}✓ Celery stopped${NC}"

# Django 서버 종료
echo -e "${YELLOW}Stopping Django server...${NC}"
pkill -f "manage.py runserver" 2>/dev/null
echo -e "${GREEN}✓ Django stopped${NC}"

# Next.js 서버 종료
echo -e "${YELLOW}Stopping Next.js server...${NC}"
pkill -f "next dev" 2>/dev/null
echo -e "${GREEN}✓ Next.js stopped${NC}"

# Redis 종료 (선택적 - 주석 해제하려면 아래 줄의 # 제거)
# echo -e "${YELLOW}Stopping Redis...${NC}"
# redis-cli shutdown 2>/dev/null
# echo -e "${GREEN}✓ Redis stopped${NC}"

echo -e "${GREEN}All services stopped successfully!${NC}"