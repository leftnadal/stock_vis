# SEC EDGAR 파이프라인 — 기본 설계서

> **작성일**: 2026-04-03
> **기반 문서**: `docs/sec_pipeline/design_v2.2.md`, `docs/sec_pipeline/design_v2.3_delta.md`
> **위치**: `docs/sec_pipeline/`
> **상태**: Phase 1 착수 전

---

## 1. 제작 원칙

SEC EDGAR 파이프라인 개발에 참여하는 모든 에이전트(Claude Code 포함)는 아래 원칙을 준수한다.

### 원칙 1 — 문서 기반 개발

모든 작업은 `docs/sec_pipeline/` 디렉토리의 문서를 기반으로 한다.
문서에 정의되지 않은 기능은 구현하지 않는다.
문서와 코드가 불일치하면 문서를 먼저 수정한 뒤 코드를 맞춘다.

```
docs/sec_pipeline/
├── design_v2.2.md                   ← 전체 설계서 (v2.2)
├── design_v2.3_delta.md             ← v2.3 수정안 (delta)
├── base_design.md                   ← 이 문서 (골자 설계)
├── pr_detail.md                     ← PR별 세부 설계 + 프롬프트
├── task_done/                       ← 완료된 작업 기록
│   ├── sec_pr_1_models.md
│   ├── sec_pr_2_collector.md
│   └── ...
└── decisions/                       ← 주요 의사결정 기록
    ├── 001_fmp_vs_edgartools.md
    ├── 002_neo4j_dynamic_type.md
    └── ...
```

### 원칙 2 — 작업 완료 기록

모든 완료된 작업은 `docs/sec_pipeline/task_done/`에 기록한다.
파일명 규칙: `sec_pr_{번호}_{간단설명}.md`

각 기록에 포함할 내용:
- 작업 번호 및 제목
- 변경된 파일 목록
- 생성/수정된 테이블 또는 스키마 변경사항
- 테스트 결과 (실행한 명령, 출력 요약)
- 발견된 이슈 및 해결 방법
- 다음 PR과의 연결점

### 원칙 3 — 개발 매니저가 파악 가능한 문서

개발 문서는 개발 매니저(병진)가 코드를 열어보지 않아도 전체 구조를 파악할 수 있어야 한다.

필수 포함 사항:
- 데이터 흐름도 (어디서 → 어디로)
- 테이블/모델 스키마 (필드명, 타입, 용도)
- Neo4j 노드/관계 속성 전체 목록
- API 요청/응답 예시 (해당 시)
- Celery task 스케줄 및 의존 관계

### 원칙 4 — 1인 개발 원칙

1인 개발자가 유지보수할 수 있는 단순한 구조를 유지한다.

- 추상화 레이어는 최소화 (필요할 때만 추가)
- 한 파일에서 한 가지 역할
- 외부 의존성은 검증된 것만 (beautifulsoup4, lxml, rapidfuzz, google-generativeai)
- Django 모놀리스 내 앱 분리로 해결. 마이크로서비스 금지.
- "나중에 필요할 수도 있는" 기능은 만들지 않는다
- edgartools는 선택적 의존성 (fallback 전용, 필수 설치 아님)

### 원칙 5 — 확장 가능한 연계 구조

`sec_pipeline/`은 독립 앱이지만, Stock-Vis 내 다른 서비스와 양방향으로 연계된다.
다른 앱이 `sec_pipeline.models`를 직접 import하지 않고, `metrics/services/` 서비스 레이어를 통해 접근한다.

```
sec_pipeline/models.py
    ↓ (직접 참조 금지)
metrics/services/business_model_service.py   ← 간접 참조 레이어
    ↓
validation/, thesis_control/, portfolio/     ← 소비자
```

### 원칙 6 — 숫자 점수 노출 경계 준수

confidence 계열 숫자(system_confidence, overall_confidence)는 내부 전용.
사용자 facing API에서는 confidence_grade(high/medium/low)만 노출.
DQS는 source_count/source_types 형태로만 노출.
Admin 대시보드와 Intelligence Report는 내부 도구이므로 숫자 허용.

### 원칙 7 — Neo4j 표현 통일

Neo4j edge는 `apoc.create.relationship()`으로 dynamic type 생성.
`RELATED_TO` 고정 type 사용 금지.
`MERGE` 사용 금지. `DELETE` + `apoc.create.relationship` idempotent 패턴만.
Phase당 graph writer는 하나만 활성화.

---

## 2. 시스템 개요

### 2.1 SEC Pipeline이 하는 일

```
SEC 10-K filing 텍스트에서 두 가지를 추출한다:

Track A — Supply Chain 관계
  10-K Item 1(Business) + Item 7(MD&A)에서
  "이 회사가 누구에게 의존하는가, 누구와 경쟁하는가"를 추출.
  → Neo4j 그래프에 edge로 저장
  → Chain Sight에서 관계 탐색에 사용

Track B — Business Model 분류
  10-K Item 1에서 사업 모델 특성 5개 필드를 분류.
  → PostgreSQL에 저장
  → 1차 검증, Thesis Control에서 컨텍스트로 사용
```

### 2.2 데이터 흐름

```
FMP API ──→ filing 메타데이터 (날짜, accession_no, finalLink)
              │
              ▼
SEC EDGAR ──→ 10-K HTML 원문 다운로드 (무료, 10req/sec)
              │
              ▼
섹션 추출 ──→ Item 1, 1A, 7 텍스트 분리
  │           │ (실패 시 edgartools fallback)
  │           ▼
  │      사후 검증 ──→ 순서/heading/길이 검증
  │           │
  │           ▼
  │      RawDocumentStore (PostgreSQL)
  │           │
  ├───────────┼──────────────┐
  │           │              │
  ▼           ▼              ▼
Pass 1     Pass 1          (저장만)
키워드     키워드
필터(A)    필터(B)
  │           │
  ▼           ▼
Pass 2     Pass 2
Gemini     Gemini
Flash(A)   Flash(B)
  │           │
  ▼           ▼
Supply     Business
Chain      Model
Evidence   Snapshot
(PG)       (PG)
  │           │
  ▼           ▼
Ticker     서비스
매칭       레이어
  │           │
  ▼           ▼
Neo4j      1차 검증
Graph      Thesis
           Control
```

### 2.3 FMP vs SEC 역할 분담

| 역할 | FMP (Starter $22/월) | SEC EDGAR (무료) |
|------|---------------------|-----------------|
| Filing 메타데이터 | ✅ accession_no, 날짜, 링크 | 가능하지만 FMP가 편함 |
| 재무제표 숫자 | ✅ 이미 구조화됨 | XBRL 파싱 필요 |
| 10-K 텍스트 원문 | ❌ 제공 안 함 | ✅ 무료, HTML |
| 신규 filing 감지 | ✅ RSS Feed API | submissions JSON polling |
| CIK ↔ Ticker 매핑 | ✅ CIK Search API | company_tickers.json |

---

## 3. 모델 스키마 요약

### 3.1 전체 모델 목록

| 모델 | 역할 | Phase |
|------|------|-------|
| `RawDocumentStore` | SEC filing 원문 저장 | 1 |
| `SupplyChainEvidence` | Track A 추출 결과 | 1 |
| `FilingProcessLog` | 파이프라인 실행 로그 | 1 |
| `CompanyAlias` | Ticker 별칭 테이블 | 1.5 |
| `UnmatchedCompanyQueue` | Ticker 미매칭 큐 | 1.5 |
| `BusinessModelSnapshot` | Track B 분류 결과 | 2 |
| `BusinessModelEvidence` | Track B 근거 문장 | 2 |
| `PipelineIntelligenceReport` | LLM 품질 리포트 | 3 |

### 3.2 핵심 모델 필드 (축약)

**SupplyChainEvidence** — Track A의 핵심 저장소:
```
source_company       FK → Stock
target_company       FK → Stock (null 허용 — 미매칭 시)
target_company_name  CharField       LLM이 추출한 원문 회사명
relationship_type    CharField       SUPPLIES_TO / CUSTOMER_OF / PARTNER_WITH / DEPENDS_ON / COMPETES_WITH
evidence_text        TextField       근거 원문 발췌
system_confidence    FloatField      0.0~1.0 (내부 전용)
confidence_grade     CharField       high / medium / low (노출용)
neo4j_dirty          BooleanField    True=미동기화, False=동기화 완료
neo4j_synced_at      DateTimeField   null 허용
prompt_version       CharField       추출 프롬프트 버전
extracted_at         DateTimeField   auto_now_add
```

**CompanyAlias** — Ticker 매칭 별칭:
```
alias                CharField       "TSMC", "Taiwan Semiconductor" 등
ticker               CharField       "TSM"
context_sector       CharField       "" (범용) 또는 "Technology" 등
context_country      CharField       참고용 메타데이터 (unique key 아님)
source               CharField       admin_resolved / auto_90pct / manual_seed
unique_together = ['alias', 'context_sector']
```

**UnmatchedCompanyQueue** — 미매칭 관리:
```
raw_company_name     CharField       LLM이 추출한 원문 회사명
source_symbol        CharField       어떤 기업의 10-K에서 나왔는지
occurrence_count     IntegerField    같은 이름의 출현 횟수
source_sectors       JSONField       이 이름이 나온 sector 목록 (2개+면 동명이의 경고)
status               CharField       pending / matched / not_public / person / duplicate / skipped
fuzzy_candidates     JSONField       [{"ticker":"TSM","name":"...","score":0.82}, ...]
resolved_ticker      CharField       수동 매칭 결과
```

### 3.3 주의사항

```
⚠️ synced_to_neo4j 필드는 존재하지 않음. neo4j_dirty만 사용.
⚠️ BusinessModelSnapshot.Meta.get_latest_by = 'as_of_date' (created_at 아님)
⚠️ CompanyAlias의 context_country는 unique key에 포함하지 않음
⚠️ confidence 숫자는 프론트엔드 API에 노출 금지 (원칙 6)
```

---

## 4. Phase 개요

### Phase 1 — SEC Filing Pipeline + Track A (4~6일, PR 6개)

S&P 500 10-K에서 supply chain 관계를 추출하여 PostgreSQL에 저장.
Neo4j 동기화는 하지 않음 (Phase 1.5에서).

```
SEC-PR-1: Django 앱 + 모델 + migration
SEC-PR-2: FMP 2-Step 수집기 + 섹션 추출 + 사후 검증
SEC-PR-3: Pass 1 키워드 필터 + Pass 2 Gemini Flash (Track A)
SEC-PR-4: Celery tasks + 에러 핸들링
SEC-PR-5: Gold Set 라벨링 + 평가 스크립트
SEC-PR-6: S&P 500 배치 실행 + 결과 검증
```

### Phase 1.5 — Ticker 매칭 + Neo4j 동기화 (2~3일, PR 4개)

추출된 회사명을 Ticker로 매칭하고, Neo4j에 관계를 동기화.

```
SEC-PR-7: TickerMatcher + CompanyAlias + 큐 적재
SEC-PR-8: Django Admin 큐 뷰 + post_save signal
SEC-PR-9: sync_dirty_to_neo4j (동시성 방어 + dynamic type)
SEC-PR-10: 관계 병합 로직 + 미매칭 큐 처리
```

### Phase 2 — Track B + 서비스 레이어 (2~3일, PR 3개)

10-K에서 사업 모델 5개 필드를 분류하고, 서비스 레이어로 다른 앱에 제공.

```
SEC-PR-11: Track B 키워드 사전 정의
SEC-PR-12: Pass 1 + Pass 2 Gemini Flash (Track B)
SEC-PR-13: metrics/services/business_model_service.py
```

### Phase 3 — 모니터링 + On-demand + Intelligence (2~3일, PR 4개)

품질 대시보드, 자동 알림, LLM 통합 분석 리포트, 비-S&P 500 On-demand 수집.

```
SEC-PR-14: Admin 대시보드 + quality_checks
SEC-PR-15: On-demand 수집 + FMP RSS 증분 감지
SEC-PR-16: PipelineDataCollector + PipelineIntelligenceReporter
SEC-PR-17: Celery chord 통합 + E2E 테스트
```

---

## 5. PR 의존 관계

```
SEC-PR-1 ─→ SEC-PR-2 ─→ SEC-PR-3 ─→ SEC-PR-4 ─→ SEC-PR-5 ─→ SEC-PR-6
                                                                   │
                                                            Phase 1 완료
                                                                   │
SEC-PR-7 ─→ SEC-PR-8 ─→ SEC-PR-9 ─→ SEC-PR-10
                                          │
                                   Phase 1.5 완료
                                          │
SEC-PR-11 ─→ SEC-PR-12 ─→ SEC-PR-13
                              │
                       Phase 2 완료
                              │
SEC-PR-14 ─→ SEC-PR-15 ─→ SEC-PR-16 ─→ SEC-PR-17
                                            │
                                     Phase 3 완료
```

---

## 6. 안정성 규칙 빠른 참조

| # | 규칙 | 관련 PR |
|---|------|--------|
| 11 | confidence 숫자는 내부 전용, API에서는 grade만 | 3, 12, 13 |
| 12 | prompt_version을 evidence에 기록 | 3, 12 |
| 13 | 별칭 전파는 산업 문맥 내로 제한 | 8 |
| 14 | Neo4j 동기화는 배치로만 (dirty flag) | 9 |
| 15 | Neo4j edge는 dynamic type으로 통일 | 9, 10 |
| 16 | DQS는 source_count/source_types로만 노출 | 10 |
| 17 | Neo4j graph writer는 Phase당 하나만 | 9 |
| 18 | 알림은 최근 배치, 대시보드는 전체 누적 | 14 |
| 19 | 섹션 사후 검증 + detail prefix (FAIL:/WARN:) | 2 |
| 20 | prompt_version 변경 시 Gold Set 재평가 | 5, 6 |

---

## 7. 확정된 미결정 사항

| # | 항목 | 결정 | 근거 |
|---|------|------|------|
| 1 | 앱 위치 | 독립 앱 `sec_pipeline/` | Track A + Track B 양쪽 서빙 |
| 2 | 서비스 연결 | 서비스 레이어 간접 참조 | 순환참조 방지 |
| 3 | Earnings Transcript | 보류 | filing + profile만으로 운영 |
| 4 | 비-S&P 500 확장 | On-demand (사용자 조회 시) | Celery 트리거 |
| 5 | Ticker 별칭 초기화 | 사후 구축 | 배치 미매칭 → Admin → CompanyAlias |

---

## 8. 남은 미결정

| 항목 | 결정 시점 |
|------|----------|
| edgartools를 기본 의존성으로 설치할지 | Phase 1 배치 후 실패율 확인 |
| 배치 주기 (월 1회 vs 분기 1회) | Phase 1 운영 1분기 후 |
| Track B 필드 확장 (transcript 기반) | 수익화 이후 |
| LLM ticker hint 2차 호출 | Phase 1.5 미매칭 분석 후 |
| CompanyAlias unique key에 country 추가 | (alias, sector) 충돌 10건 이상 시 |
| Gold Set 30 → 50개 확장 | Phase 1 결과 후 |
| merge_and_sync_to_neo4j 상세 구현 | Phase 1.5 진입 시 |
