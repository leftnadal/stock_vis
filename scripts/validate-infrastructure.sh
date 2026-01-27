#!/bin/bash

# ============================================================
# Stock-Vis Infrastructure Validation Script
# ============================================================
#
# Purpose: 뉴스 기능 인프라 설정 검증
# Usage: bash scripts/validate-infrastructure.sh
#
# ============================================================

set -e

echo "=========================================="
echo "Stock-Vis Infrastructure Validation"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================
# 1. 환경 변수 확인
# ============================================================

echo "1. Checking Environment Variables..."
echo ""

check_env_var() {
    var_name=$1
    if [ -z "${!var_name}" ]; then
        echo -e "${RED}✗${NC} $var_name is not set"
        return 1
    else
        echo -e "${GREEN}✓${NC} $var_name is set"
        return 0
    fi
}

# .env 파일 로드
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file found"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}✗${NC} .env file not found"
    echo "   Please create .env from .env.example"
    exit 1
fi

# 필수 환경 변수 확인
required_vars=(
    "FINNHUB_API_KEY"
    "MARKETAUX_API_KEY"
    "NEO4J_URI"
    "NEO4J_USERNAME"
    "NEO4J_PASSWORD"
)

missing_vars=0
for var in "${required_vars[@]}"; do
    check_env_var "$var" || ((missing_vars++))
done

echo ""

if [ $missing_vars -gt 0 ]; then
    echo -e "${RED}Missing $missing_vars required environment variables${NC}"
    exit 1
fi

# ============================================================
# 2. Docker 서비스 확인
# ============================================================

echo "2. Checking Docker Services..."
echo ""

# Docker 실행 확인
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Docker is not running"
    exit 1
else
    echo -e "${GREEN}✓${NC} Docker is running"
fi

# Docker Compose 파일 확인
if [ ! -f docker/docker-compose.yml ]; then
    echo -e "${RED}✗${NC} docker-compose.yml not found"
    exit 1
else
    echo -e "${GREEN}✓${NC} docker-compose.yml found"
fi

# docker-compose.yml 구문 검증
cd docker
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} docker-compose.yml syntax is valid"
else
    echo -e "${RED}✗${NC} docker-compose.yml has syntax errors"
    exit 1
fi
cd ..

echo ""

# ============================================================
# 3. Neo4j 초기화 스크립트 확인
# ============================================================

echo "3. Checking Neo4j Scripts..."
echo ""

if [ -f scripts/init-neo4j.cypher ]; then
    echo -e "${GREEN}✓${NC} init-neo4j.cypher found"

    # 파일 크기 확인
    file_size=$(wc -c < scripts/init-neo4j.cypher)
    if [ $file_size -gt 0 ]; then
        echo -e "${GREEN}✓${NC} init-neo4j.cypher is not empty (${file_size} bytes)"
    else
        echo -e "${RED}✗${NC} init-neo4j.cypher is empty"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} init-neo4j.cypher not found"
    exit 1
fi

echo ""

# ============================================================
# 4. Django 설정 검증
# ============================================================

echo "4. Checking Django Settings..."
echo ""

# Python 가상환경 확인
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python3 is available"
    python_version=$(python3 --version)
    echo "   $python_version"
else
    echo -e "${RED}✗${NC} Python3 not found"
    exit 1
fi

# config/settings.py 확인
if [ -f config/settings.py ]; then
    echo -e "${GREEN}✓${NC} config/settings.py found"

    # News API 설정 확인
    if grep -q "NEWS_RATE_LIMITS" config/settings.py; then
        echo -e "${GREEN}✓${NC} NEWS_RATE_LIMITS configured"
    else
        echo -e "${RED}✗${NC} NEWS_RATE_LIMITS not found in settings.py"
        exit 1
    fi

    if grep -q "NEO4J_URI" config/settings.py; then
        echo -e "${GREEN}✓${NC} NEO4J_URI configured"
    else
        echo -e "${RED}✗${NC} NEO4J_URI not found in settings.py"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} config/settings.py not found"
    exit 1
fi

echo ""

# ============================================================
# 5. 문서 확인
# ============================================================

echo "5. Checking Documentation..."
echo ""

if [ -f docs/ENVIRONMENT-VARIABLES.md ]; then
    echo -e "${GREEN}✓${NC} ENVIRONMENT-VARIABLES.md found"

    # 뉴스 API 문서 확인
    if grep -q "Finnhub" docs/ENVIRONMENT-VARIABLES.md; then
        echo -e "${GREEN}✓${NC} Finnhub documentation added"
    else
        echo -e "${YELLOW}⚠${NC} Finnhub documentation not found"
    fi

    if grep -q "Marketaux" docs/ENVIRONMENT-VARIABLES.md; then
        echo -e "${GREEN}✓${NC} Marketaux documentation added"
    else
        echo -e "${YELLOW}⚠${NC} Marketaux documentation not found"
    fi

    if grep -q "Neo4j" docs/ENVIRONMENT-VARIABLES.md; then
        echo -e "${GREEN}✓${NC} Neo4j documentation added"
    else
        echo -e "${YELLOW}⚠${NC} Neo4j documentation not found"
    fi
else
    echo -e "${YELLOW}⚠${NC} ENVIRONMENT-VARIABLES.md not found"
fi

echo ""

# ============================================================
# 완료
# ============================================================

echo "=========================================="
echo -e "${GREEN}Infrastructure Validation Complete!${NC}"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Start Neo4j service:"
echo "   cd docker && docker-compose up -d neo4j"
echo ""
echo "2. Initialize Neo4j database:"
echo "   cat scripts/init-neo4j.cypher | docker exec -i stockvis-neo4j cypher-shell -u neo4j -p password"
echo ""
echo "3. Verify Neo4j browser:"
echo "   open http://localhost:7474"
echo ""
echo "4. Install Neo4j Python driver:"
echo "   poetry add neo4j"
echo ""
