═══════════════════════════════════════════════════════════════
[audits/2026-05_c3_django_52_impact.md] Django 5.1.7 → 5.2 LTS 마이그레이션 영향 조사
═══════════════════════════════════════════════════════════════

## 메타

| 항목 | 값 |
|------|----|
| 일자 | 2026-05-24 |
| 조사 시점 Django | **5.1.7** (poetry.lock + `python manage.py check`로 확인) |
| 입력원 | `python manage.py check[/--deploy/showmigrations]`, grep, 패키지 메타데이터 (`importlib.metadata`) |
| 변경 | 없음 (read-only) |
| 비용 | $0 |
| 후속 슬라이스 | C-3 (Django 5.2 LTS 마이그레이션) |

---

## A. 현재 상태 베이스라인

### A-1. `python manage.py check`
- 출력: `System check identified no issues (0 silenced).`
- **0 issues** ✓

### A-2. `python manage.py check --deploy`
- 출력 합계: **186 issues** (0 silenced)
- 내역:
  - **`drf_spectacular.W002`**: 181건 (APIView serializer 미지정 — Django 5.2와 무관, drf-spectacular 운영성 경고)
  - **`security.W004`**: 1건 (`SECURE_HSTS_SECONDS` 미설정)
  - **`security.W008`**: 1건 (`SECURE_SSL_REDIRECT`가 True 아님)
  - **`security.W012`**: 1건 (`SESSION_COOKIE_SECURE` 미설정)
  - **`security.W016`**: 1건 (`CSRF_COOKIE_SECURE` 미설정)
  - **`security.W018`**: 1건 (`DEBUG=True`)

### A-3. Django deprecation 경고
- `python -W all manage.py check 2>&1 | grep -iE "deprecat|RemovedInDjango"`:
  - **Django DeprecationWarning / RemovedInDjango60Warning: 0건**
  - Pydantic v2 `PydanticDeprecatedSince20` 1건이 `thesis/services/builder_state.py:74`에 — Django 무관

### A-4. settings 파일
- `config/settings.py` (운영)
- `config/settings_test.py` (테스트)
- 분할 settings(settings/base.py 등) 없음

---

## B. Django 5.2 변경점 vs 코드 실사용

### B-1. 모델

**13개 모델 파일/디렉터리**:
- `models.py` 단일 파일 (8개 앱): `rag_analysis`, `serverless`, `stocks`, `news`, `users`, `portfolio`, `sec_pipeline`, `graph_analysis`
- `models/` 디렉터리 분할 (5개 앱): `metrics`, `chainsight`, `macro`, `thesis`, `marketpulse`, `validation`

| 항목 | 사용 여부 | 위치 |
|------|----------|------|
| 커스텀 `models.Manager` / `models.QuerySet` | **없음** | grep 매칭 0 |
| `Meta.constraints` (UniqueConstraint/CheckConstraint) | **사용함** | `portfolio/models.py` (UniqueConstraint 4건) |
| `Meta.indexes` (`models.Index`) | **사용함** (다수) | `metrics/models/benchmark.py`, `metric_snapshot.py`, `batch_job.py` 등 |
| `CompositePrimaryKey` (5.2 신규) | **없음** | - |
| `GeneratedField` | **없음** | - |

### B-2. settings.py 5.2 영향 키

| 항목 | 상태 |
|------|------|
| `MIDDLEWARE` | 7개 표준 Django + `corsheaders.middleware.CorsMiddleware`. **커스텀 미들웨어 없음**, `LoginRequiredMiddleware`(5.1 신규) 미사용 |
| `STORAGES` 신표기 | **부재** |
| `DEFAULT_FILE_STORAGE` 구식 표기 | **부재** |
| `STATICFILES_STORAGE` 구식 표기 | **부재** |
| `FORMS_URLFIELD_ASSUME_HTTPS` (5.2 신규) | **부재** (Django 기본값) |
| `PASSWORD_RESET_TIMEOUT` | **부재** (Django 기본값) |
| `models.URLField` 사용 | **9건** — `serverless/models.py:1036,1252`, `stocks/models.py:29,893`, `news/models.py:44,63`, `sec_pipeline/models.py:31`, `marketpulse/models/news.py:33,38` + `serializers.URLField` 1건 (`marketpulse/api/serializers/overview.py:28`) |
| `forms.URLField` | **부재** |

### B-3. 인증/요청
- `AUTH_USER_MODEL = 'users.User'` (`config/settings.py:308`)
- `AUTHENTICATION_BACKENDS`: **명시 부재** (Django 기본)
- 커스텀 auth backend (`class ... Backend`, `BaseBackend` 상속): **부재**
- `LoginRequiredMiddleware`: **미사용**
- `request.user` 관련 커스텀 미들웨어: **부재**

### B-4. DRF·외부 통합 패키지 (조사 시점 poetry.lock)

| 패키지 | 설치 버전 |
|--------|----------|
| djangorestframework | 3.16.1 |
| drf-spectacular | 0.29.0 |
| django-cors-headers | 4.9.0 |
| channels | 4.3.1 |
| daphne | 4.2.1 |
| celery | 5.5.3 |
| django-celery-beat | 2.8.1 |
| django-celery-results | 2.6.0 |
| django-redis | 6.0.0 |

### B-5. ORM 쿼리

| 항목 | 사용 여부 | 위치 |
|------|----------|------|
| `connection.cursor()` (raw SQL) | **5건** (운영성) | `api_request/admin_views.py:299`, `config/views.py:89`, `serverless/services/admin_status_service.py:832`, `chainsight/services/seed_selection.py:151`, `marketpulse/api/views/health.py:29` |
| `.extra(...)` | **부재** | - |
| `Manager.raw(...)` | **부재** (운영 코드) | - |
| `transaction.atomic` | **사용함** (다수) | `api_request/stock_service.py`, `rag_analysis/views.py`, `serverless/services/{data_sync,supply_chain_service,institutional_holdings_service,sector_heatmap_service,regulatory_service,relationship_keyword_enricher}.py` 등 |
| DB 라우터 (`DATABASE_ROUTERS`) | **부재** | - |

### B-6. 템플릿·폼

| 항목 | 사용 여부 | 위치 |
|------|----------|------|
| Django `forms` (`from django import forms`) | **부재** | - |
| Django 템플릿 `render()` / `django.template` | **7건** | `metrics/{tasks.py, views.py, management/commands/send_daily_report.py}`, `config/views.py`, `news/views.py`, `sec_pipeline/views.py`, `graph_analysis/views.py` |
| `templates/` 디렉터리 | 2곳 — `templates/admin/`, `metrics/templates/email/agent_report.html` |

### B-7. async 뷰 / ASGI

| 항목 | 상태 |
|------|------|
| `config/asgi.py` | 존재 — `ProtocolTypeRouter` + `AuthMiddlewareStack` + `AllowedHostsOriginValidator` (channels 표준) |
| WebSocket consumer | `stocks/consumers.py` — `AsyncWebsocketConsumer` 상속 (`StockPriceConsumer`, `PortfolioConsumer`), `channels.db.database_sync_to_async` 사용 |
| `stocks/routing.py` | 존재 |
| Django **async view** (`async def view(request)`) | **부재** (channels consumer만 async) |
| Django **async ORM** (`aget`/`asave`/`afilter` 등) | **부재** |

---

## C. 마이그레이션 파일 현황

### C-1. 앱별 마이그레이션 파일 수

| 앱 | 파일 수 |
|----|--------|
| serverless | 13 |
| thesis | 9 |
| stocks | 8 |
| chainsight | 8 |
| users | 7 |
| news | 6 |
| metrics | 6 |
| macro | 6 |
| rag_analysis | 5 |
| marketpulse | 5 |
| validation | 4 |
| sec_pipeline | 1 |
| portfolio | 1 |
| graph_analysis | 1 |
| **합계 (앱 마이그레이션)** | **80** |

### C-2. `showmigrations` 결과
- 총 라인: **145건** (앱 80 + Django 기본 admin/auth/contenttypes/sessions/django_celery_beat/django_celery_results 등 65건)
- 적용됨 `[X]`: **145건**
- 미적용 `[ ]`: **0건** ✓

### C-3. squash 마이그레이션
- `*squashed*` 파일명 grep: **0건**

---

## D. 테스트·CI Django 버전 의존

### D-1. pytest-django 설정 (`pytest.ini`)
```
DJANGO_SETTINGS_MODULE = config.settings_test
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
```
- `tests/conftest.py` 존재 (구체 내용은 본 조사 범위 밖)

### D-2. Django 버전 분기 코드
- `django.VERSION` / `django.get_version` / `DJANGO_VERSION` grep: **0건** (운영 코드)
- settings override가 Django 버전 특정 동작에 의존하는 흔적: **확인 불가** (테스트 내부 fixture 전수 조사 범위 밖)

---

## E. 의존성 Django 5.2 지원 여부 (메타데이터 분류자)

`Framework :: Django :: 5.2` 분류자 확인 결과 (`importlib.metadata` 조회):

| 패키지 | 설치 버전 | Django 분류자 | 5.2 지원 |
|--------|----------|---------------|---------|
| djangorestframework | 3.16.1 | `4.2 / 5.0 / 5.1 / 5.2` | ✅ |
| django-cors-headers | 4.9.0 | `4.2 / 5.0 / 5.1 / 5.2 / 6.0` | ✅ |
| django-celery-beat | 2.8.1 | `3.2 / 4.1 / 4.2 / 5.0 / 5.1 / 5.2` | ✅ |
| django-celery-results | 2.6.0 | `3.2 / 4.1 / 4.2 / 5.0 / 5.1 / 5.2` | ✅ |
| django-redis | 6.0.0 | `4.2 / 5.0 / 5.1 / 5.2` | ✅ |
| channels | 4.3.1 | `4.2 / 5.1 / 5.2` | ✅ |
| drf-spectacular | 0.29.0 | `2.2 / 3.2 / 4.0 / 4.1 / 4.2 / 5.0 / 5.1 / 5.2` | ✅ |
| daphne | 4.2.1 | `(no Django classifier)` | **확인 불가** (분류자에 Django 명시 없음) |

---

## 요약 (사실만)

- Django check: 0 issues / Django deprecation 경고: 0건
- 5.2 변경점이 강하게 닿을 만한 영역(`STORAGES`/`PASSWORD_RESET_TIMEOUT`/`forms`/async view/async ORM/`LoginRequiredMiddleware`/`CompositePrimaryKey`/`GeneratedField`/`.extra()`/DB 라우터) — **모두 미사용**
- 5.2 변경점이 약하게 닿는 영역(`URLField`/`Meta.constraints`/`Meta.indexes`/`models.URLField`/`transaction.atomic`/`connection.cursor()`/Django 템플릿 render) — **사용 중** (수량 표기 위 §B 참조)
- 마이그레이션: 145/145 적용 / squash 0 / 미적용 0
- 테스트 Django 버전 분기 코드: 운영 코드 0건 (테스트 fixture 전수는 확인 불가)
- DRF·외부 통합 8개 패키지 중 7개에 `Framework :: Django :: 5.2` 분류자 확인, daphne 1개는 Django 분류자 부재(확인 불가)
