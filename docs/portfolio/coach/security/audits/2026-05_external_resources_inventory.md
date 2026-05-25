═══════════════════════════════════════════════════════════════
[audits/2026-05_external_resources_inventory.md] 외부 자원 전체 인벤토리 (read-only)
═══════════════════════════════════════════════════════════════

## 메타

| 항목 | 값 |
|------|----|
| 일자 | 2026-05-22 ~ 2026-05-23 |
| 범주 | (1) 프론트 npm / (2) 백엔드 Python / (3) 런타임 / (4) 인프라 도커 이미지 |
| 입력원 | `package.json`, `package-lock.json`, `npm ls`, `pyproject.toml`, `poetry.lock`, `pip freeze`, Dockerfile, docker-compose, nginx.conf |
| 비용 | $0 |
| 후속 슬라이스 | C-1, C-2, C-3, ML-1 (시리즈 전반) |

본 문서는 "어떤 외부 자원에 의존하는가"의 시점 스냅샷. 취약점 스캔 결과는 `../advisories/2026-05_dependency-audit.md` 참조.

---

## A. 프론트엔드 npm

`package.json` 표기·resolved 버전 전수: [`2026-05_frontend_inventory.md` §B](2026-05_frontend_inventory.md#b-프레임워크툴링) 참조.

전이 의존성 포함 총 줄 수: **1443** (`npm ls --all | wc -l`).

---

## B. 백엔드 Python

### B-1. `pyproject.toml` 표기 그대로 (조사 시점)

**[tool.poetry.dependencies]**:
- `python = "^3.12"`
- `django = "^5.1.7"` · `python-dotenv = "^1.1.0"` · `django-cors-headers = "^4.9.0"`
- `requests = "^2.32.5"` · `djangorestframework-simplejwt = "^5.5.1"`
- `celery = "^5.5.3"` · `redis = "^7.0.1"` · `django-celery-beat = "^2.8.1"` · `django-celery-results = "^2.6.0"`
- `channels = "^4.3.1"` · `channels-redis = "^4.3.0"` · `django-redis = "^6.0.0"` · `daphne = "^4.2.1"`
- `pandas = "^2.3.3"` · `numpy = "^2.3.5"` · `psycopg2-binary = "^2.9.11"` · `neo4j = "^5.0.0"`
- `anthropic = "^0.48.0"` · `sentence-transformers = "^5.2.0"` · `rank-bm25 = "^0.2.2"`
- `google-genai = "^1.55.0"` · `httpx = "^0.28.1"`
- `msgpack = "^1.1.0"` · `openpyxl = "^3.1.5"` · `scikit-learn = "^1.8.0"` · `lightgbm = "^4.6.0"`
- `beautifulsoup4 = "^4.14.3"`
- `drf-spectacular = "^0.29.0"` · `drf-spectacular-sidecar = "^2026.4.14"`
- `yfinance = "^1.3.0"`

**[tool.poetry.group.dev.dependencies]**:
- `ipykernel = "^6.29.5"` · `pytest = "^9.0.2"` · `pytest-django = "^4.11.1"` · `pytest-asyncio = "^1.3.0"`

### B-2. lock 파일

| 파일 | 상태 |
|------|------|
| `poetry.lock` | **존재** (조사 시점 173 패키지) |
| `uv.lock`, `Pipfile.lock` | 부재 |
| `requirements.txt` | 존재 — `pinecone>=3.0.0`, `sentence-transformers>=2.2.0`만 (별도 KB 의존성, poetry와 분리) |

### B-3. `poetry.lock` 핵심 패키지 정확 버전 (조사 시점)

| 패키지 | 설치 버전 |
|--------|----------|
| django | 5.1.7 |
| djangorestframework | 3.16.1 |
| djangorestframework-simplejwt | 5.5.1 |
| pyjwt | 2.10.1 |
| django-cors-headers | 4.9.0 |
| celery | 5.5.3 |
| redis | 7.0.1 |
| django-celery-beat | 2.8.1 |
| django-celery-results | 2.6.0 |
| channels | 4.3.1 |
| channels-redis | 4.3.0 |
| django-redis | 6.0.0 |
| daphne | 4.2.1 |
| requests | 2.32.5 |
| urllib3 | 2.5.0 |
| httpx | 0.28.1 |
| cryptography | 46.0.3 |
| psycopg2-binary | 2.9.11 |
| neo4j | 5.28.2 |
| anthropic | 0.48.0 |
| google-genai | 1.55.0 |
| msgpack | 1.1.2 |
| openpyxl | 3.1.5 |
| pandas | 2.3.3 |
| numpy | 2.3.5 |
| scikit-learn | 1.8.0 |
| lightgbm | 4.6.0 |
| sentence-transformers | 5.2.0 |
| rank-bm25 | 0.2.2 |
| beautifulsoup4 | 4.14.3 |
| drf-spectacular | 0.29.0 |
| drf-spectacular-sidecar | 2026.4.14 |
| yfinance | 1.3.0 |
| python-dotenv | 1.1.0 |
| pytest | 9.0.2 |
| pytest-django | 4.11.1 |
| pytest-asyncio | 1.3.0 |
| ipykernel | 6.29.5 |

### B-4. freeze 부재 (실제 미설치 확정)

`poetry run pip freeze` 161 패키지 기준:
- `pillow` — **미설치**
- `gunicorn` — **미설치**
- `uvicorn` — **미설치** (ASGI는 `daphne 4.2.1`)

> 이 사실은 C-2 진입 시 "백엔드 의존성 보안 패치 후보"에서 pillow/gunicorn/uvicorn을 제외하는 근거.

---

## C. 런타임

### C-1. Node 런타임
- `docker/Dockerfile.frontend` 베이스: **`node:20-alpine`** (모든 stage: base/deps/builder/runner)
- `frontend/.nvmrc`: **부재**
- `frontend/package.json` `engines` 필드: **부재**
- `@types/node`: `^20` (devDependency)

### C-2. Python 런타임
- `docker/Dockerfile` 베이스: **`python:3.12-slim`**
- `.python-version`: **부재**
- `pyproject.toml`: `python = "^3.12"`

---

## D. 인프라 도커 이미지

### D-1. `docker/docker-compose.yml` (dev)
- postgres: **`postgres:15-alpine`**
- redis: **`redis:7-alpine`**
- neo4j: **`neo4j:5-community`**
- frontend: build from `docker/Dockerfile.frontend` (로컬 빌드)
- backend: build from `docker/Dockerfile` (로컬 빌드)

### D-2. `docker/docker-compose.prod.yml` (prod)
- postgres: **`postgres:15-alpine`**
- redis: **`redis:7-alpine`**
- nginx: **`nginx:alpine`**
- frontend, backend: 로컬 빌드 (이미지 태그 없음)
- neo4j 서비스 정의 없음 (확인 불가 — 별도 호스팅 가능성)

### D-3. nginx
- `docker/nginx/nginx.conf`: `upstream frontend { server frontend:3000; }`, `listen 80`, `server_name localhost` (HTTPS 블록은 `your-domain.com` 자리표시자, **주석 처리**)

---

## E. 다음 슬라이스 매핑 (참조용)

| 슬라이스 | 본 인벤토리에서 다루는 자원 |
|----------|---------------------------|
| C-1 (✅ 종결) | A. 프론트 npm (next, react, axios, js-cookie + 전이) |
| C-2 (✅ 종결) | B. 백엔드 Python (요청·암호·인증·서버·dev 14 패키지) |
| C-3 (⏸ 대기) | B. 백엔드 Python (django 5.1.7 → 5.2 LTS) |
| ML-1 (⏸ 후순위) | B. 백엔드 Python (torch, transformers) |
| (별도 결정) | C. 런타임 (node 20, python 3.12) + D. 도커 이미지 (postgres 15, redis 7, neo4j 5, nginx alpine) |
