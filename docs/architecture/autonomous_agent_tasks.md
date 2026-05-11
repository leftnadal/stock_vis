# Stock-Vis 자율 에이전트 작업 설계

> 작성: 2026-04-14 | 기준: data_structure_remodeling_V1 브랜치

---

## 현황 요약

| 항목 | 수치 |
|------|------|
| 총 테스트 | 1,693개 (549 passed, 1 failed, 4 errors) |
| 테스트 0개 앱 | **validation** (3,457줄), **sec_pipeline** (3,466줄), **rag_analysis** (14,608줄), **users** (2,820줄) |
| TS 컴파일 에러 | 4개 (mock.ts description/recommendation_reason 누락, NewsCard null 타입) |
| FE 컴포넌트 | 190개 / **테스트 0개** (Vitest/RTL 미설치) |
| 기존 테스트 실패 | 1 FAILED (news) + 4 ERROR (serverless) |
| Celery Beat 스케줄 | 50+ 항목 |
| API 문서 자동생성 | **미설정** (drf-spectacular/Swagger 없음) |
| Circuit Breaker | **0건** |
| Gemini fallback | **1건** |

---

## 제약 조건

- DB 마이그레이션(`makemigrations`, `migrate`) 자율 실행 금지
- Neo4j 스키마 변경 자율 실행 금지
- FMP API 호출 포함 작업은 rate limit 고려 (Starter $29: 10 calls/min)
- `.env`, `settings.py` 시크릿 수정 금지
- 모든 작업은 별도 Git 브랜치에서 실행

## 우선순위 기준

1. 리스크 LOW + 반복 가치 높은 것 먼저
2. 테스트가 이미 있는 영역 우선
3. 테스트 커버리지 낮은 쪽 보강 우선

---

## 작업 1: TypeScript 컴파일 에러 수정

| 필드 | 내용 |
|------|------|
| **작업명** | TS 컴파일 에러 4개 수정 (mock.ts + NewsCard) |
| **실행 방식** | 서브에이전트 (`@frontend`) |
| **대상 파일** | `frontend/lib/thesis/mock.ts`, `frontend/components/news/NewsCard.tsx` |
| **선행 조건** | 브랜치 분리 (`fix/ts-compile-errors`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~5분, 토큰 < 10K |
| **검증 방법** | `cd frontend && npx tsc --noEmit` 에러 0 |

**프롬프트 초안:**

```
frontend/lib/thesis/mock.ts의 MOCK_DASHBOARD 지표 3개에
description: '', recommendation_reason: '' 추가.

frontend/components/news/NewsCard.tsx의 article.image_url
타입을 string | null에서 non-null assertion 또는 조건부 처리.

npx tsc --noEmit으로 검증.
```

---

## 작업 2: 기존 테스트 실패 5건 수정

| 필드 | 내용 |
|------|------|
| **작업명** | 깨진 테스트 1 FAILED + 4 ERROR 수정 |
| **실행 방식** | 서브에이전트 (`@qa-architect`) |
| **대상 파일** | `tests/news/test_collect_category_news.py`, `tests/serverless/test_keyword_service.py` |
| **선행 조건** | 브랜치 분리 (`fix/broken-tests`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 30K |
| **검증 방법** | `pytest tests/ -q --tb=short` 전체 통과 |

**프롬프트 초안:**

```
pytest에서 5건 실패/에러 수정.

(1) tests/news/test_collect_category_news.py::test_collect_category_news_by_id
    — FAILED 원인 분석 후 테스트 또는 소스 수정.

(2) tests/serverless/test_keyword_service.py 4건 ERROR
    — import 에러 또는 fixture 누락 확인.

소스 코드 변경은 최소화하고 테스트 코드를 현재 구현에 맞게 수정.
수정 후 pytest tests/news/test_collect_category_news.py tests/serverless/test_keyword_service.py -v로 검증.
```

---

## 작업 3: validation 앱 테스트 작성 (0개 → 목표 40개)

| 필드 | 내용 |
|------|------|
| **작업명** | validation 앱 단위 테스트 신규 작성 |
| **실행 방식** | `claude -p` (headless, 브랜치 격리) |
| **대상 파일** | `tests/unit/validation/` (신규), `validation/services/` (읽기) |
| **선행 조건** | 브랜치 분리 (`test/validation-unit-tests`), validation 모델 마이그레이션 완료 |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~30분, 토큰 < 80K |
| **검증 방법** | `pytest tests/unit/validation/ -v` 40+개 통과 |

**프롬프트 초안:**

```
validation/ 앱의 단위 테스트를 tests/unit/validation/ 에 작성.

대상:
(1) services/peer_engine.py — compute-on-read 엔진 핵심 로직
(2) services/preset_generator.py — 프리셋 생성
(3) services/benchmark.py — 벤치마크 비교

패턴: pytest 클래스, @pytest.mark.django_db, 외부 API(FMP)는 mock.
기존 tests/unit/thesis/ 스타일 참조.
DB 모델 생성은 factory 또는 직접 create.
최소 40개 테스트.

작성 후 pytest tests/unit/validation/ -v 실행.
```

---

## 작업 4: sec_pipeline 앱 테스트 작성 (0개 → 목표 30개)

| 필드 | 내용 |
|------|------|
| **작업명** | sec_pipeline 앱 단위 테스트 신규 작성 |
| **실행 방식** | `claude -p` (headless, 브랜치 격리) |
| **대상 파일** | `tests/unit/sec_pipeline/` (신규), `sec_pipeline/` (읽기) |
| **선행 조건** | 브랜치 분리 (`test/sec-pipeline-tests`), sec_pipeline 마이그레이션 완료 |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~25분, 토큰 < 60K |
| **검증 방법** | `pytest tests/unit/sec_pipeline/ -v` 30+개 통과 |

**프롬프트 초안:**

```
sec_pipeline/ 앱의 단위 테스트를 tests/unit/sec_pipeline/ 에 작성.

대상:
(1) services/edgar_client.py — SEC EDGAR API 호출 (mock)
(2) services/extractor.py — 10-K 텍스트에서 supply chain/business model 추출
(3) models.py — 모델 CRUD

패턴: pytest 클래스, @pytest.mark.django_db, HTTP 호출 mock.
최소 30개 테스트.

작성 후 pytest tests/unit/sec_pipeline/ -v 실행.
```

---

## 작업 5: users 앱 테스트 보강 (0개 → 목표 25개)

| 필드 | 내용 |
|------|------|
| **작업명** | users 앱 단위 테스트 신규 작성 |
| **실행 방식** | `claude -p` (headless, 브랜치 격리) |
| **대상 파일** | `tests/unit/users/` (신규), `users/` (읽기) |
| **선행 조건** | 브랜치 분리 (`test/users-unit-tests`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~20분, 토큰 < 50K |
| **검증 방법** | `pytest tests/unit/users/ -v` 25+개 통과 |

**프롬프트 초안:**

```
users/ 앱의 단위 테스트를 tests/unit/users/ 에 작성.

대상:
(1) JWT 인증 플로우 (login, refresh, blacklist)
(2) Portfolio CRUD + 가치 계산
(3) Watchlist 추가/제거

패턴: pytest 클래스, @pytest.mark.django_db, APIClient로 API 테스트.
기존 tests/unit/test_watchlist.py 스타일 참조.
최소 25개 테스트.

작성 후 pytest tests/unit/users/ -v 실행.
```

---

## 작업 6: Celery Beat 스케줄 중복/충돌 감사

| 필드 | 내용 |
|------|------|
| **작업명** | beat_schedule 50+개 항목의 시간 충돌 + rate limit 위반 감사 |
| **실행 방식** | 서브에이전트 (`@infra`) |
| **대상 파일** | `config/celery.py` (읽기), `docs/infra/` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~10분, 토큰 < 20K |
| **검증 방법** | 생성된 md 파일에 시간대별 API 호출 히트맵 존재 |

**프롬프트 초안:**

```
config/celery.py의 beat_schedule을 분석하여:

(1) 같은 시각에 FMP API 호출하는 태스크가 겹쳐 rate limit(10/min) 초과하는 구간 식별
(2) 같은 시각에 Gemini API 호출하는 태스크가 겹쳐 15 RPM 초과하는 구간 식별
(3) neo4j queue에 몰리는 시간대 식별
(4) 개선안을 docs/infra/beat_schedule_audit.md로 출력

코드 수정 없이 분석만.
```

---

## 작업 7: Frontend 타입 안전성 강화

| 필드 | 내용 |
|------|------|
| **작업명** | FE 컴포넌트 null/undefined 타입 안전성 일괄 수정 |
| **실행 방식** | `claude -p` 1회 |
| **대상 파일** | `frontend/components/`, `frontend/lib/` |
| **선행 조건** | 브랜치 분리 (`fix/fe-type-safety`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~10분, 토큰 < 20K |
| **검증 방법** | `npx tsc --noEmit` exit code 0 |

**프롬프트 초안:**

```
cd frontend && npx tsc --noEmit 2>&1로 에러 목록 추출.

각 에러를 수정: null 체크 추가, optional chaining, 타입 narrowing.
새로운 기능 추가 금지, 타입 에러만 수정.

수정 후 npx tsc --noEmit 에러 0 확인.
```

---

## 작업 8: Dead Code / Unused Import 정리

| 필드 | 내용 |
|------|------|
| **작업명** | BE 전체 unused import + dead code 정리 |
| **실행 방식** | `claude -p` (headless) |
| **대상 파일** | `validation/`, `chainsight/`, `sec_pipeline/`, `thesis/`, `macro/` |
| **선행 조건** | 브랜치 분리 (`chore/dead-code-cleanup`) |
| **리스크 등급** | **MED** (re-export 누락 가능) |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 30K |
| **검증 방법** | `pytest tests/ -q` 전체 통과 + diff 리뷰 |

**프롬프트 초안:**

```
Python 파일에서 unused import 탐지 후 제거.

대상 앱: validation/, chainsight/, sec_pipeline/, thesis/, macro/.
도구: pyflakes 또는 수동 grep.
삭제 전 해당 심볼이 __all__이나 다른 모듈에서 re-export되는지 확인.

삭제 후 pytest tests/ -x -q로 기존 테스트 통과 확인.
```

---

## 작업 9: API 응답 일관성 감사

| 필드 | 내용 |
|------|------|
| **작업명** | 전체 DRF ViewSet/APIView 응답 형식 일관성 감사 |
| **실행 방식** | 서브에이전트 (`@backend`) |
| **대상 파일** | `*/views.py`, `*/api/views.py` (읽기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 40K |
| **검증 방법** | 생성된 md에 앱별 응답 패턴 매트릭스 존재 |

**프롬프트 초안:**

```
모든 views.py를 읽고 Response() 반환 형식을 분석:

(1) success/error 래핑 패턴 사용 여부
(2) HTTP 상태 코드 일관성
(3) 에러 응답 형식 통일 여부
(4) pagination 적용 여부

결과를 docs/architecture/api_consistency_audit.md로 출력.
코드 수정 없이 분석만.
```

---

## 작업 10: INDICATOR_CATALOG 동기화 검증

| 필드 | 내용 |
|------|------|
| **작업명** | BE 카탈로그 <-> FE 미러 <-> matcher 3곳 동기화 검증 |
| **실행 방식** | 서브에이전트 (`@qa-architect`) |
| **대상 파일** | `thesis/services/prompt_builder.py`, `thesis/services/indicator_matcher.py`, `frontend/` |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~10분, 토큰 < 25K |
| **검증 방법** | 감사 문서에 불일치 항목 0이면 PASS |

**프롬프트 초안:**

```
지표 카탈로그 3곳 동기화 검증:

(1) thesis/services/prompt_builder.py INDICATOR_CATALOG
(2) thesis/services/indicator_matcher.py KEYWORD_RULES
(3) frontend에서 indicator type/name 사용하는 곳

불일치 항목 목록화. 특히:
- 카탈로그에 있지만 matcher에 없는 지표
- description이 비어있는 항목
- data_params 형식 불일치

결과를 docs/thesis_control/indicator_catalog_audit.md로 출력.
```

---

---

# Part 2: 추가 관점 (8개)

> 추가 분석: 2026-04-14

## 추가 현황

| 항목 | 수치 |
|------|------|
| FE 컴포넌트 테스트 | 190개 중 **0개** (thesis 40개, news 24개, chainsight 13개, validation 9개 모두 0) |
| rag_analysis | 14,608줄, Neo4j 참조 18파일, **Neo4j 없이 테스트 가능한 서비스 4개** (cache, context, entity_extractor, context_compressor) |
| FK 관계 | 63개, select_related/prefetch_related 사용 20건 vs QuerySet 접근 195건 |
| 반응형 브레이크포인트 | 173건 사용, 고정 폭 컴포넌트 26건 |
| 설계 문서 | 59개 plan, 68개 task_done |
| circuit breaker | **0** (grep 결과 86은 chainsight 모델 필드명 매칭) |
| Gemini fallback | **1건만** |

---

## 작업 11: FE 핵심 컴포넌트 테스트 — thesis 관제실

| 필드 | 내용 |
|------|------|
| **작업명** | thesis 관제실 컴포넌트 5개 스냅샷/인터랙션 테스트 |
| **실행 방식** | `claude -p` (headless, 브랜치 격리) |
| **대상 파일** | `frontend/components/thesis/dashboard/` (읽기), `frontend/__tests__/thesis/` (신규) |
| **선행 조건** | **수동 필수**: `cd frontend && npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom` + vitest.config.ts 생성. 브랜치 분리 (`test/fe-thesis-components`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~25분, 토큰 < 60K |
| **검증 방법** | `cd frontend && npx vitest run --reporter=verbose` |

**프롬프트 초안:**

```
frontend/components/thesis/dashboard/ 의 핵심 컴포넌트 5개에 대해
Vitest + React Testing Library 테스트 작성.

대상:
(1) IndicatorRow.tsx — 펼침/접힘 토글, 값 포맷팅, description 표시
(2) RealValueIndicatorCard.tsx — 값/변동률 렌더링, null 처리
(3) QuarterlySparkline.tsx — 분기 데이터 렌더링
(4) HeatmapGrid.tsx — 셀 렌더링, 색상 매핑
(5) DashboardHeader.tsx 또는 ThesisSummaryCard — 전체 점수 표시

패턴: render() → screen.getByText() / getByRole() / fireEvent.
mock 데이터는 frontend/lib/thesis/mock.ts 참조.
API 호출은 msw 또는 vi.mock()으로 차단.

각 컴포넌트당 최소 3개 테스트 (렌더링, 인터랙션, 엣지케이스).
작성 후 npx vitest run 실행.
```

---

## 작업 12: FE 핵심 컴포넌트 테스트 — validation + chainsight

| 필드 | 내용 |
|------|------|
| **작업명** | validation 9개 + chainsight 13개 컴포넌트 중 핵심 6개 테스트 |
| **실행 방식** | `claude -p` (headless, 브랜치 격리) |
| **대상 파일** | `frontend/components/validation/`, `frontend/components/chainsight/` (읽기), `frontend/__tests__/` (신규) |
| **선행 조건** | 작업 11 선행조건 완료 (Vitest + RTL 설치), 브랜치 분리 (`test/fe-validation-chainsight`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~20분, 토큰 < 50K |
| **검증 방법** | `cd frontend && npx vitest run --reporter=verbose` |

**프롬프트 초안:**

```
frontend/components/validation/ 과 frontend/components/chainsight/ 에서
핵심 컴포넌트 6개에 대해 Vitest + RTL 테스트 작성.

대상:
(1) PeerContextBar.tsx — 프리셋 탭 클릭, 커스텀 입력, 선택 상태
(2) MetricCard.tsx — 값 렌더링, 벤치마크 바, 등급 배지
(3) ValidationSummary.tsx — 전체 점수, 카테고리별 표시
(4) GraphVisualization.tsx — 노드/엣지 렌더링 (canvas mock)
(5) ChainProfileCard.tsx — 프로파일 데이터 표시
(6) RelationList.tsx — 관계 목록 렌더링

각 컴포넌트당 최소 3개 테스트.
작성 후 npx vitest run 실행.
```

---

## 작업 13: rag_analysis 최소 테스트 (Neo4j 독립 서비스)

| 필드 | 내용 |
|------|------|
| **작업명** | rag_analysis Neo4j-free 서비스 4개 단위 테스트 (목표 35개) |
| **실행 방식** | `claude -p` (headless, 브랜치 격리) |
| **대상 파일** | `tests/unit/rag_analysis/` (신규), `rag_analysis/services/cache.py`, `context.py`, `entity_extractor.py`, `context_compressor.py` (읽기) |
| **선행 조건** | 브랜치 분리 (`test/rag-analysis-unit-tests`) |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~25분, 토큰 < 60K |
| **검증 방법** | `pytest tests/unit/rag_analysis/ -v` 35+개 통과 |

**제외 이유 (이전 라운드):**
rag_analysis는 14,608줄 중 18파일이 Neo4j를 직접 import하여
테스트 시 Neo4j 연결이 필요. 하지만 아래 4개 서비스는 **Neo4j 참조 0**으로
완전히 독립 테스트 가능:

| 파일 | 줄 수 | Neo4j 참조 | 테스트 가능 |
|------|------|:---:|:---:|
| `cache.py` | 362 | 0 | O |
| `context.py` | 250 | 0 | O |
| `entity_extractor.py` | 259 | 0 | O |
| `context_compressor.py` | 324 | 0 | O |
| **합계** | **1,195** | **0** | |

**프롬프트 초안:**

```
rag_analysis/services/ 중 Neo4j 의존성 없는 4개 서비스의 단위 테스트 작성.
tests/unit/rag_analysis/ 디렉토리에 생성.

대상 (Neo4j import 0인 파일만):
(1) cache.py — BasicCacheService: get/set/invalidate 그래프, LLM, 분석 캐시
(2) context.py — DateAwareContextFormatter: 컨텍스트 포맷팅, 날짜 처리
(3) entity_extractor.py — EntityExtractor: 텍스트에서 종목/지표 엔티티 추출
(4) context_compressor.py — ContextCompressor: 컨텍스트 압축, 토큰 예산 관리

절대 금지:
- Neo4j 연결 필요한 서비스 (neo4j_service, neo4j_driver) 테스트 금지
- from neo4j import 금지

패턴: pytest, @pytest.mark.django_db (cache.py만), LLM 호출 mock.
최소 35개 테스트.
작성 후 pytest tests/unit/rag_analysis/ -v 실행.
```

---

## 작업 14: 데이터 무결성 감사 (FK orphan + Neo4j 동기화 갭)

| 필드 | 내용 |
|------|------|
| **작업명** | PostgreSQL FK orphan + Neo4j<->PG 동기화 불일치 감사 |
| **실행 방식** | 서브에이전트 (`@backend`) |
| **대상 파일** | `*/models*.py`, `*/signals.py`, `*/tasks.py` (읽기), `docs/architecture/data_integrity_audit.md` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** (읽기 전용 분석) |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 40K |
| **검증 방법** | 감사 문서에 orphan 위험 모델 + 동기화 갭 목록 존재 |

**프롬프트 초안:**

```
데이터 무결성 감사. 코드 수정 없이 분석만.

(1) FK Orphan 위험:
   - on_delete=SET_NULL인 FK를 찾고, NULL이 된 후 정리하는 로직 존재 여부
   - on_delete=CASCADE 체인이 깊은 경우 (3단계 이상) 삭제 영향 범위

(2) Stale 데이터:
   - DailyPrice, IndicatorReading 등 시계열 데이터의 보존 정책
   - 아카이브/정리 태스크 존재 여부

(3) Neo4j <-> PostgreSQL 동기화:
   - rag_analysis/signals.py: Stock post_save → sync_stock_to_neo4j
   - news/tasks.py: sync_news_to_neo4j
   - sec_pipeline/tasks.py: sync_dirty_to_neo4j
   각각의 실패 시 재시도 + 불일치 감지 메커니즘 분석

(4) 중복 레코드 위험:
   - unique_together / UniqueConstraint 설정 현황
   - upsert (update_or_create) 패턴 사용 현황

결과를 docs/architecture/data_integrity_audit.md로 출력.
```

---

## 작업 15: API 성능 감사 (N+1 쿼리 + 인덱스)

| 필드 | 내용 |
|------|------|
| **작업명** | N+1 쿼리 탐지 + 인덱스 누락 + 느린 serializer 분석 |
| **실행 방식** | 서브에이전트 (`@backend`) |
| **대상 파일** | `*/views.py`, `*/serializers.py`, `*/models*.py` (읽기), `docs/architecture/performance_audit.md` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** (읽기 전용 분석) |
| **권한 모드** | auto |
| **예상 소요** | ~20분, 토큰 < 50K |
| **검증 방법** | 감사 문서에 N+1 위험 엔드포인트 목록 + 개선안 존재 |

**현황:** QuerySet 접근 195건 vs select_related/prefetch_related 20건 (비율 10:1)

**프롬프트 초안:**

```
API 성능 감사. 코드 수정 없이 분석만.

(1) N+1 쿼리 탐지:
   - 모든 views.py에서 QuerySet을 루프 안에서 FK 접근하는 패턴 찾기
   - 특히: thesis/views/monitoring_views.py DashboardView (indicator → readings → premise 체인)
   - validation/api/views.py (preset → peers 루프)
   - news/views.py (article → sentiment → keywords)
   각각에 select_related/prefetch_related 추가 제안

(2) 인덱스 누락:
   - filter(), order_by()에서 자주 사용되는 필드 중 db_index 없는 것
   - 복합 인덱스 후보 (filter A + order_by B 패턴)

(3) 느린 Serializer:
   - SerializerMethodField에서 추가 쿼리 발생하는 곳
   - Nested serializer가 many=True로 전체 로드하는 곳

(4) 페이지네이션 누락:
   - 목록 API에서 .all() 또는 .filter()를 페이지네이션 없이 반환하는 곳

결과를 docs/architecture/performance_audit.md로 출력.
위험도 HIGH/MED/LOW로 분류하고, 수정 난이도도 함께 표시.
```

---

## 작업 16: 보안 감사 (시크릿 + SQL + CORS + JWT)

| 필드 | 내용 |
|------|------|
| **작업명** | OWASP Top 10 기반 보안 취약점 스캔 |
| **실행 방식** | 서브에이전트 (`@qa-architect`) |
| **대상 파일** | 전체 `.py`, `.ts`, `.tsx`, `config/settings.py` (읽기), `docs/architecture/security_audit.md` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** (읽기 전용 분석) |
| **권한 모드** | auto |
| **예상 소요** | ~20분, 토큰 < 50K |
| **검증 방법** | 감사 문서에 발견 항목별 심각도 + 수정 방법 존재 |

**현황:**
- 하드코딩 시크릿: 테스트 파일에만 존재 (실제 키 아님 — LOW)
- raw SQL: 4건 (admin_views, config/views, chainsight — 검토 필요)
- CORS: `CORS_ALLOW_ALL_ORIGINS = True` (DEBUG 시, 프로덕션은 False)
- JWT: Access 60분, Refresh 7일, 블랙리스트 활성화

**프롬프트 초안:**

```
OWASP Top 10 기반 보안 감사. 코드 수정 없이 분석만.

(1) 인증/인가:
   - permission_classes 누락된 APIView/ViewSet (기본 AllowAny 되는 곳)
   - IsAuthenticated vs IsAuthenticatedOrReadOnly 일관성
   - JWT 토큰 관리: refresh 토큰 재사용 방지, 블랙리스트 동작

(2) 인젝션:
   - cursor.execute() 사용처 4곳의 파라미터 바인딩 여부
   - f-string으로 쿼리 조합하는 곳 (ORM 밖)
   - Gemini 프롬프트에 사용자 입력 직접 삽입하는 곳

(3) 시크릿 관리:
   - .env 외부에 API 키 하드코딩 여부
   - settings.py에서 SECRET_KEY 처리
   - .gitignore에 .env 포함 여부

(4) CORS / XSS:
   - CORS_ALLOW_ALL_ORIGINS이 프로덕션에서 False인지 확인
   - React dangerouslySetInnerHTML 사용 여부
   - LLM 응답을 HTML로 렌더링하는 곳 (XSS 벡터)

(5) 에러 노출:
   - DEBUG=True가 프로덕션 가드되는지
   - 에러 응답에 스택트레이스 노출 여부

결과를 docs/architecture/security_audit.md로 출력.
심각도: CRITICAL / HIGH / MED / LOW / INFO.
```

---

## 작업 17: FMP/Gemini 장애 대응 감사 + fallback 설계

| 필드 | 내용 |
|------|------|
| **작업명** | 외부 API 의존성 장애 영향 분석 + fallback 유무 감사 |
| **실행 방식** | 서브에이전트 (`@infra`) |
| **대상 파일** | `*/services/*fmp*`, `*/services/*client*`, `*/tasks.py`, `config/celery.py` (읽기), `docs/architecture/api_dependency_audit.md` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** (읽기 전용 분석) |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 40K |
| **검증 방법** | 감사 문서에 의존성 매트릭스 + fallback 유무 테이블 존재 |

**현황:**
- FMP fallback/retry 패턴: **0건** (에러만 잡고 빈 값 반환)
- Gemini fallback: **1건만**
- Circuit breaker: **미구현**
- 타임아웃: 10~30초로 설정됨

**프롬프트 초안:**

```
외부 API 장애 대응 감사. 코드 수정 없이 분석만.

(1) FMP API 장애 시 영향:
   - FMP를 호출하는 모든 서비스/태스크 목록화
   - 각각의 에러 핸들링 패턴 (재시도? 캐시 fallback? 빈 응답?)
   - FMP 다운 시 사용자에게 보이는 영향 (빈 차트? 500 에러? 캐시된 데이터?)
   - FMP 402 (프리미엄) 에러 처리 일관성

(2) Gemini API 장애 시 영향:
   - Gemini를 호출하는 모든 서비스/태스크 목록화
   - RPM/RPD 초과 시 처리 (429 에러 핸들링)
   - LLM 없이 동작 가능한 기능 vs 완전 불가 기능 분류

(3) FRED API 장애 시 영향:
   - 거시경제 지표 조회 실패 시 캐시 TTL + 빈 데이터 처리

(4) Neo4j 다운 시 영향:
   - neo4j_service.py의 fallback 패턴 (driver=None → 빈 데이터)
   - 동기화 태스크 실패 시 데이터 일관성

(5) 개선 제안:
   - Circuit breaker 도입 후보 (가장 빈번한 외부 호출)
   - 캐시 fallback 강화 후보 (stale-while-revalidate 패턴)
   - 사용자 알림 (서비스 상태 표시) 필요 지점

결과를 docs/architecture/api_dependency_audit.md로 출력.
```

---

## 작업 18: 모바일 UX 감사 (반응형 + 터치 타겟)

| 필드 | 내용 |
|------|------|
| **작업명** | FE 컴포넌트 모바일 반응형 + 터치 접근성 감사 |
| **실행 방식** | 서브에이전트 (`@UI-UX-designer`) |
| **대상 파일** | `frontend/components/`, `frontend/app/` (읽기), `docs/architecture/mobile_ux_audit.md` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** (읽기 전용 분석) |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 40K |
| **검증 방법** | 감사 문서에 페이지별 모바일 이슈 목록 + 스크린샷 기준 존재 |

**현황:**
- Tailwind 반응형 브레이크포인트: 173건 사용 (기본은 갖춤)
- 고정 폭 컴포넌트: 26건 (`w-[NNpx]`, `min-w-[NNpx]`)
- viewport meta: 설정됨 (viewportFit: cover)

**프롬프트 초안:**

```
모바일 UX 감사. 코드 수정 없이 분석만.

(1) 반응형 누락:
   - w-[NNpx], min-w-[NNpx] 등 고정 폭 사용하는 26개 컴포넌트 식별
   - 각각이 모바일(375px)에서 overflow 발생하는지 분석
   - 테이블/차트 컴포넌트의 가로 스크롤 처리 여부

(2) 터치 타겟:
   - Apple HIG 기준 44x44pt 미만 터치 영역 (버튼, 링크, 아이콘)
   - 특히: thesis 관제실 지표 카드, validation 프리셋 탭, chainsight 노드
   - text-[10px], text-[11px] 사용처에서 터치 가능 요소 여부

(3) 모바일 네비게이션:
   - 모바일에서 사이드바/헤더 접근성
   - Bottom navigation 또는 hamburger 메뉴 존재 여부
   - 스크롤 성능 (긴 목록에 virtualization 적용 여부)

(4) 차트/그래프:
   - Recharts 컴포넌트의 모바일 대응 (터치 줌, 스와이프)
   - 분기 스파크라인의 모바일 가독성

페이지별로 분류하여 docs/architecture/mobile_ux_audit.md로 출력.
심각도: BLOCKER / MAJOR / MINOR.
```

---

## 작업 19: 설계서 대비 구현 갭 분석 (앱별 분할)

> 59개 설계서 + 68개 완료보고서를 한 번에 분석하면 컨텍스트 부담이 큼.
> 앱별로 분할 실행하여 품질 확보.

### 작업 19-A: Chain Sight 설계서 갭 (가장 중요)

| 필드 | 내용 |
|------|------|
| **작업명** | Chain Sight 설계 26개 vs 코드 구현 갭 |
| **실행 방식** | 서브에이전트 (`@qa-architect`) |
| **대상 파일** | `docs/chain_sight/plan/` (26개), `chainsight/` (읽기), `docs/chain_sight/task_done/` (읽기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** |
| **권한 모드** | auto |
| **예상 소요** | ~15분, 토큰 < 30K |
| **검증 방법** | 감사 문서에 cs_00~cs_54 각각의 구현률 존재 |

**프롬프트 초안:**

```
docs/chain_sight/plan/ 의 설계 문서 26개를 읽고
chainsight/ 코드와 대조하여 구현 갭 분석. 코드 수정 없이 분석만.

분류: (A) 완전 구현 (B) 부분 구현 (C) 미구현 (D) 폐기/대체
특히: redesign_v1_260409/ 가 기존 cs_* 문서를 대체하는지 확인.
task_done/*.md 와 cross-reference.

결과를 docs/chain_sight/design_gap_audit.md로 출력.
```

### 작업 19-B: Thesis Control 설계서 갭

| 필드 | 내용 |
|------|------|
| **작업명** | Thesis Control 설계 vs 코드 갭 (Phase 3 중심) |
| **실행 방식** | 서브에이전트 (`@qa-architect`) |
| **대상 파일** | `docs/thesis_control/` (읽기), `thesis/`, `frontend/components/thesis/` (읽기) |
| **리스크 등급** | **LOW** |
| **예상 소요** | ~15분, 토큰 < 30K |

### 작업 19-C: SEC Pipeline + 나머지

| 필드 | 내용 |
|------|------|
| **작업명** | SEC Pipeline + validation + news 설계서 갭 |
| **실행 방식** | 서브에이전트 (`@qa-architect`) |
| **대상 파일** | `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/` (읽기) |
| **리스크 등급** | **LOW** |
| **예상 소요** | ~15분, 토큰 < 30K |

---

## 작업 20: API 문서 자동생성 감사 (drf-spectacular)

| 필드 | 내용 |
|------|------|
| **작업명** | DRF API 문서 자동생성 현황 감사 + 도입 제안 |
| **실행 방식** | 서브에이전트 (`@backend`) |
| **대상 파일** | `config/settings.py`, `config/urls.py`, `*/views.py`, `*/serializers.py` (읽기), `docs/architecture/api_docs_audit.md` (쓰기) |
| **선행 조건** | 없음 |
| **리스크 등급** | **LOW** (읽기 전용 분석) |
| **권한 모드** | auto |
| **예상 소요** | ~10분, 토큰 < 20K |
| **검증 방법** | 감사 문서에 엔드포인트 수 + 문서화율 + 도입 플랜 존재 |

**현황:** drf-spectacular/Swagger **미설정**. MVP 출시 시 API 문서 부재.

**프롬프트 초안:**

```
DRF API 문서 자동생성 현황 감사. 코드 수정 없이 분석만.

(1) 현재 상태:
   - drf-spectacular / drf-yasg / swagger 설치 여부
   - urls.py에 schema view 등록 여부
   - serializer에 help_text / @extend_schema 데코레이터 사용 여부

(2) 엔드포인트 목록화:
   - 모든 urls.py를 읽고 등록된 API 엔드포인트 전수 조사
   - 앱별 엔드포인트 수 테이블

(3) 도입 제안:
   - drf-spectacular 도입 시 필요한 작업 목록
   - 자동 생성 가능한 엔드포인트 vs 수동 @extend_schema 필요한 엔드포인트
   - 예상 작업량

결과를 docs/architecture/api_docs_audit.md로 출력.
```

---

## 추가 TOP 5 (읽기 전용 감사 작업)

| 순위 | 작업 | 관점 | 리스크 | 소요 |
|:---:|------|------|:---:|:---:|
| **1** | rag_analysis 최소 테스트 (#13) | rag_analysis | LOW | 25분 |
| **2** | API 성능 감사 (#15) | N+1 + 인덱스 | LOW | 20분 |
| **3** | 보안 감사 (#16) | OWASP | LOW | 20분 |
| **4** | FMP/Gemini 장애 대응 (#17) | 외부 의존성 | LOW | 15분 |
| **5** | 설계서 구현 갭 (#19) | 설계 vs 코드 | LOW | 30분 |

> 모두 읽기 전용 분석이므로 브랜치 없이 즉시 실행 가능.
> #13만 테스트 코드 작성이 포함되어 브랜치 필요.

---

---

# Part 3: 실행 계획

## 1회성 작업 (이번 주 수동 실행)

### Tier 1: 즉시 수정 (머지 가능)

| 작업 | 리스크 | 소요 | 실행 |
|------|:---:|:---:|------|
| TS 컴파일 에러 (#1) | LOW | 5분 | `git checkout -b fix/ts-compile-errors && claude -p` |
| 깨진 테스트 (#2) | LOW | 15분 | `git checkout -b fix/broken-tests && claude -p` |
| 타입 안전성 (#7) | LOW | 10분 | `git checkout -b fix/fe-type-safety && claude -p` |
| Dead code (#8) | MED | 15분 | `git checkout -b chore/dead-code-cleanup && claude -p` |

### Tier 2: 테스트 확보 (0 -> 90+개)

| 작업 | 리스크 | 소요 | 선행 조건 |
|------|:---:|:---:|------|
| **수동**: FE 테스트 인프라 설치 | - | 5분 | `cd frontend && npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom` |
| validation 테스트 (#3) | LOW | 30분 | 마이그레이션 완료 |
| rag_analysis 테스트 (#13) | LOW | 25분 | - |
| FE thesis 테스트 (#11) | LOW | 25분 | 위 수동 설치 완료 |
| FE validation+chainsight (#12) | LOW | 20분 | 위 수동 설치 완료 |

## 야간 시스템 매핑

```
매일 Phase 1~4 (자동):
  lint + 타입 체크 + 깨진 테스트 자동 수정
  → #1, #2, #7 유형 반복 처리

월 (UI/UX):
  → #18 모바일 반응형 감사

화 (데이터/API):
  → #17 FMP/Gemini 장애 대응 감사
  → #14 데이터 무결성 (FK orphan + Neo4j-PG 동기화)

수 (보안/성능):
  → #16 OWASP 보안 감사
  → #15 API 성능 (N+1 쿼리 + 인덱스)

목 (비즈니스 로직):
  → #19-A Chain Sight 설계서 갭
  → #19-B Thesis Control 설계서 갭
  → #10 카탈로그 동기화 검증

금 (아키텍처):
  → #9 API 응답 일관성 감사
  → #20 API 문서 자동생성 감사

토 (전략):
  → #6 Beat 스케줄 감사
  → #19-C SEC Pipeline + 나머지 설계서 갭
```

## 전체 작업 인덱스 (21개)

| # | 작업명 | 유형 | 관점 |
|---|------|------|------|
| 1 | TS 컴파일 에러 수정 | 코드 수정 | 타입 안전성 |
| 2 | 깨진 테스트 수정 | 코드 수정 | 테스트 |
| 3 | validation 테스트 작성 | 테스트 신규 | BE 커버리지 |
| 4 | sec_pipeline 테스트 작성 | 테스트 신규 | BE 커버리지 |
| 5 | users 테스트 작성 | 테스트 신규 | BE 커버리지 |
| 6 | Beat 스케줄 감사 | 감사 | 인프라 |
| 7 | FE 타입 안전성 | 코드 수정 | 타입 안전성 |
| 8 | Dead code 정리 | 코드 수정 | 코드 품질 |
| 9 | API 응답 일관성 감사 | 감사 | 아키텍처 |
| 10 | 카탈로그 동기화 검증 | 감사 | 비즈니스 로직 |
| 11 | FE thesis 컴포넌트 테스트 | 테스트 신규 | FE 커버리지 |
| 12 | FE validation+chainsight 테스트 | 테스트 신규 | FE 커버리지 |
| 13 | rag_analysis 최소 테스트 | 테스트 신규 | BE 커버리지 |
| 14 | 데이터 무결성 감사 | 감사 | 데이터 |
| 15 | API 성능 감사 | 감사 | 성능 |
| 16 | 보안 감사 | 감사 | 보안 |
| 17 | FMP/Gemini 장애 대응 감사 | 감사 | 외부 의존성 |
| 18 | 모바일 UX 감사 | 감사 | UX |
| 19-A | Chain Sight 설계서 갭 | 감사 | 설계 vs 구현 |
| 19-B | Thesis Control 설계서 갭 | 감사 | 설계 vs 구현 |
| 19-C | SEC Pipeline + 나머지 설계서 갭 | 감사 | 설계 vs 구현 |
| 20 | API 문서 자동생성 감사 | 감사 | 문서화 |
