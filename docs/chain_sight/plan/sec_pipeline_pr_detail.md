# SEC EDGAR 파이프라인 — PR별 세부 설계서

> **작성일**: 2026-04-03
> **기반 문서**: `docs/sec_pipeline/base_design.md`
> **위치**: `docs/sec_pipeline/pr_detail.md`

---

## PR 실행 규칙

```
1. PR은 순차 실행. 이전 PR 완료 후 다음 PR 착수.
2. 각 PR의 "참조 문서"를 반드시 읽은 뒤 작업.
3. 프롬프트에 명시된 파일만 생성/수정. 나머지 건드리지 않는다.
4. PR 완료 후 docs/sec_pipeline/task_done/sec_pr_{번호}_{설명}.md 기록.
5. 테스트가 명시된 PR은 테스트 통과 확인 후 완료.
6. ⚠️ 표시 규칙을 위반하면 해당 PR 전체 재작업.
```

---

# Phase 1 — SEC Filing Pipeline + Track A

---

## SEC-PR-1: Django 앱 + 모델 + migration

**목표**: `sec_pipeline/` 앱 생성, 8개 모델 정의, migration 완료.

**참조**: `docs/sec_pipeline/design_v2.2.md` 섹션 6, `base_design.md` 섹션 3

**생성 파일**:
```
sec_pipeline/__init__.py
sec_pipeline/apps.py
sec_pipeline/models.py
sec_pipeline/admin.py            ← 빈 파일 (PR-8에서 채움)
sec_pipeline/migrations/
config/settings.py               ← INSTALLED_APPS 추가
```

**모델 8개**: RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport

### Claude Code 프롬프트

```
docs/sec_pipeline/design_v2.2.md 섹션 6과 
docs/sec_pipeline/base_design.md 섹션 3을 읽어.

sec_pipeline Django 앱을 생성하고 8개 모델을 정의해줘.

작업:
1. python manage.py startapp sec_pipeline
2. sec_pipeline/models.py에 8개 모델 정의 (설계서 필드 정확히 따라)
3. config/settings.py INSTALLED_APPS에 'sec_pipeline' 추가
4. python manage.py makemigrations sec_pipeline && python manage.py migrate

⚠️ 절대 하면 안 되는 것:
- synced_to_neo4j 필드 생성 금지. neo4j_dirty(BooleanField, default=True)만.
- BusinessModelSnapshot.Meta.get_latest_by는 'as_of_date'여야 함. 'created_at' 아님.
- CompanyAlias.unique_together에 context_country 넣지 마. ['alias', 'context_sector']만.
- UnmatchedCompanyQueue에 source_sectors(JSONField, default=list) 반드시 포함.
- PipelineIntelligenceReport는 Phase 3에서 쓰지만 migration은 지금 함께 생성.

완료 확인:
- python manage.py showmigrations sec_pipeline → 전부 [X] 확인
- python manage.py shell → from sec_pipeline.models import * → import 에러 없음

완료 후 docs/sec_pipeline/task_done/sec_pr_1_models.md 작성:
- 생성된 테이블 목록
- FK 관계 요약 (어떤 모델이 어디를 참조하는지)
- 변경된 파일 목록
```

---

## SEC-PR-2: FMP 2-Step 수집기 + 섹션 추출 + 사후 검증

**목표**: FMP 메타데이터 → SEC HTML → 섹션 추출 → 사후 검증 파이프라인.

**참조**: `design_v2.2.md` 섹션 0, 3.1~3.3 + `design_v2.3_delta.md` 섹션 1

**선행**: SEC-PR-1

**생성 파일**:
```
sec_pipeline/collector.py
sec_pipeline/validators.py
```

### Claude Code 프롬프트

```
docs/sec_pipeline/design_v2.2.md 섹션 3.1~3.3과
docs/sec_pipeline/design_v2.3_delta.md 섹션 1을 읽어.

SEC filing 수집기와 사후 검증을 구현해줘.

1. sec_pipeline/collector.py — SECFilingCollector 클래스:
   - get_filing_metadata(symbol): FMP API → 메타데이터
   - fetch_filing_html(final_link): SEC EDGAR HTML (sleep 0.12초)
   - extract_sections(html): 3단계 (ToC제거 + 다중후보 + longest scoring)
   - extract_sections_fallback(symbol): edgartools (ImportError → None)
   - collect(symbol): 통합 (수집 → 추출 → 검증 → fallback)

2. sec_pipeline/validators.py — validate_extracted_sections(sections, full_text):
   - Check 1: Item 순서 검증 (1 < 1A < 7 < 8). 위반 → 전체 폐기 + fallback.
   - Check 2: heading 재확인 (첫 500자에 heading 없음 → 해당 섹션 제거).
   - Check 3: 비정상 길이 플래그 (WARN만, 제거 안 함).
   - 반환: (validated_sections, warnings)

3. collect() 안에서 검증 통합:
   - extract → validate → 실패 시 fallback
   - 로그 기록: FAIL: prefix → status='failed', WARN: prefix → status='success'

⚠️ 필수:
- section_patterns에 금융 변형: 'Description of Business', 'General Development of Business'
- SEC_HEADERS User-Agent: 'Stock-Vis stockvis@example.com'
- FMP API key: settings.FMP_API_KEY
- lxml parser 사용
- edgartools는 try/except ImportError. requirements.txt에 넣지 마.

테스트: AAPL, JPM, XOM 3종목 collect() 수동 실행.
- 섹션별 추출 성공 여부, 길이, 경고 여부 확인
- fallback 사용 여부 확인

docs/sec_pipeline/task_done/sec_pr_2_collector.md에 3종목 결과 기록.
```

---

## SEC-PR-3: Pass 1 키워드 필터 + Pass 2 Gemini Flash (Track A)

**목표**: 수집된 섹션에서 supply chain 관계 추출.

**참조**: `design_v2.2.md` 섹션 5 (v1 레이어 C), 섹션 6.1

**선행**: SEC-PR-2

**생성 파일**:
```
sec_pipeline/normalizer.py
sec_pipeline/prompts.py
sec_pipeline/extractor.py
sec_pipeline/validator_track_a.py
```

### Claude Code 프롬프트

```
docs/sec_pipeline/design_v2.2.md 섹션 5와 6.1을 읽어.

Track A supply chain 추출 파이프라인을 구현해줘.

1. sec_pipeline/normalizer.py
   - normalize_section_all(sections: dict) → str: HTML 잔여물/공백 정리
   - filter_paragraphs(text, track='supply_chain', max_paragraphs=15) → list[str]
     - 키워드: supplier, customer, supply chain, partnership, contract,
       manufacture, distribute, compete, vendor, procurement,
       outsource, subcontract, license, OEM, foundry 등
     - keyword_hits 수 기준 상위 max_paragraphs개

2. sec_pipeline/prompts.py
   - PROMPT_VERSION = 'v1'
   - SUPPLY_CHAIN_EXTRACTION_PROMPT: 프롬프트 템플릿
     - 입력: {symbol}, {company_name}, {paragraphs}
     - 출력 JSON: relationships 배열
       - target_company_name, relationship_type, evidence_text, confidence, direction

3. sec_pipeline/extractor.py
   - GeminiExtractor 클래스
     - gemini-2.5-flash, response_mime_type='application/json', temperature=0.1
     - extract_supply_chain(symbol, company_name, filtered_paragraphs) → dict
     - API key: settings.GEMINI_API_KEY

4. sec_pipeline/validator_track_a.py
   - validate_supply_chain_result(result, source_symbol) → list[dict]
     - 자기 참조 제거, confidence < 0.3 제거, target 2자 미만 제거
     - relationship_type 허용 목록 외 → 'DEPENDS_ON' 폴백
   - calculate_confidence_grade(confidence) → str: >= 0.8 high, >= 0.6 medium, else low
   - save_supply_chain_evidences(validated, document)
     - SupplyChainEvidence 벌크 생성
     - prompt_version = prompts.PROMPT_VERSION

⚠️ confidence는 내부 전용 숫자. grade는 save 시 자동 계산.

테스트: AAPL collect() 결과로 extract_supply_chain 실행.
추출 관계 수, 타입 분포, confidence 분포 확인.

docs/sec_pipeline/task_done/sec_pr_3_track_a_extractor.md 기록.
```

---

## SEC-PR-4: Celery tasks + 에러 핸들링

**목표**: 전체 파이프라인을 Celery task로 조립. 에러 유형별 재시도 정책.

**참조**: `design_v2.2.md` 섹션 9

**선행**: SEC-PR-3

**생성 파일**:
```
sec_pipeline/exceptions.py
sec_pipeline/tasks.py
sec_pipeline/sp500.py
```

### Claude Code 프롬프트

```
docs/sec_pipeline/design_v2.2.md 섹션 9를 읽어.

Celery task 파이프라인과 에러 핸들링을 구현해줘.

1. sec_pipeline/exceptions.py
   - FilingCollectionError (base)
   - FMPApiError: retry 3회, 60초 exponential backoff
   - SECFetchError: retry 5회, 10초 exponential backoff
   - SectionExtractionError: retry 1회, fallback 시도
   - LLMExtractionError: retry 2회, 30초

2. sec_pipeline/tasks.py
   - collect_and_extract(symbol): 수집→저장→LLM 분리
     - Step 1: FMP 메타데이터 → FMPApiError 시 retry
     - Step 2: SEC HTML → SECFetchError 시 retry
     - Step 3: 섹션 추출+검증 → 실패 시 fallback → skip+로그
     - Step 4: RawDocumentStore 저장 (accession_no 중복 체크)
     - Step 5: extract_from_document.delay(doc.id, symbol)
   
   - extract_from_document(doc_id, symbol): max_retries=2
     - Track A: supply chain 추출+저장
     - Track B: pass (Phase 2에서 구현)
     - Track A 실패해도 Track B 시도
   
   - _retry_or_log(task, symbol, stage, error)

3. sec_pipeline/sp500.py
   - get_sp500_symbols() → list[str]

⚠️ collect_and_extract와 extract_from_document 분리 이유:
LLM 실패 시 문서는 보존. 재추출만 하면 됨.
⚠️ Celery Beat 설정은 settings.py에 주석으로만.
⚠️ S&P 500 배치는 아직 실행하지 않음 (PR-6에서).

테스트: collect_and_extract.delay('AAPL') 실행.
FilingProcessLog 각 단계 기록 확인.

docs/sec_pipeline/task_done/sec_pr_4_celery_tasks.md 기록.
```

---

## SEC-PR-5: Gold Set 라벨링 + 평가 스크립트

**목표**: 정답셋 정의 + 자동 평가 management command.

**참조**: `design_v2.3_delta.md` 섹션 6

**선행**: SEC-PR-4

**생성 파일**:
```
sec_pipeline/fixtures/gold_set.json
sec_pipeline/fixtures/gold_set_schema.py
sec_pipeline/management/__init__.py
sec_pipeline/management/commands/__init__.py
sec_pipeline/management/commands/evaluate_gold_set.py
```

### Claude Code 프롬프트

```
docs/sec_pipeline/design_v2.3_delta.md 섹션 6을 읽어.

Gold Set 평가 시스템을 구현해줘.

1. sec_pipeline/fixtures/gold_set_schema.py
   - GoldSetEntry dataclass
   - supply_chain_relations는 primary_type 사용 (relationship_type 아님)

2. sec_pipeline/fixtures/gold_set.json
   - 초기 10종목: AAPL, MSFT, NVDA, GOOGL, JPM, GS, JNJ, UNH, XOM, AMZN
   - 각 종목: section_presence, supply_chain_relations, business_model
   - 처음에는 AAPL만 완전 라벨. 나머지는 section_presence만 우선.
   - ⚠️ 라벨은 실제 10-K 확인 기반. LLM 자동 생성 금지.

3. sec_pipeline/management/commands/evaluate_gold_set.py
   - --prompt-version 옵션
   - Phase 1: (target_ticker, primary_type) 단일 매칭
   - 출력: Section / Track A Precision & Recall / Track B / Ticker Match
   - 목표: Section ≥ 90%, Precision ≥ 70%, Recall ≥ 50%

docs/sec_pipeline/task_done/sec_pr_5_gold_set.md에 라벨링 현황 기록.
```

---

## SEC-PR-6: S&P 500 배치 실행 + 결과 검증

**목표**: Phase 1 전체 배치 실행, Gold Set 평가, 수동 검증.

**선행**: SEC-PR-5

**⚠️ 코드 작성 아닌 실행+검증 PR.**

### Claude Code 프롬프트

```
SEC Pipeline Phase 1 배치를 실행하고 검증해줘.

1. 사전 확인
   - settings: FMP_API_KEY, GEMINI_API_KEY 존재 확인
   - Celery worker 실행 중 확인
   - Redis 실행 중 확인

2. 단계별 실행
   a) 5종목 테스트: AAPL, MSFT, JPM, XOM, JNJ
      → collect_and_extract 실행 → FilingProcessLog 확인
   b) 결과 양호하면 S&P 500 전체 배치

3. 검증
   a) python manage.py evaluate_gold_set → 목표 대비 확인
   b) SupplyChainEvidence 랜덤 10건 수동 확인
   c) 통계: 총 문서, 총 관계, 타입 분포, confidence 분포, 실패율

4. 미달 시
   → prompts.py 수정 → PROMPT_VERSION 올림 → 재추출 → 재평가

docs/sec_pipeline/task_done/sec_pr_6_phase1_batch.md에 전체 결과 기록:
- 배치 통계, Gold Set 결과, 섹터별 성공률, 이슈 및 조치
```

---

# Phase 1.5 — Ticker 매칭 + Neo4j 동기화

---

## SEC-PR-7: TickerMatcher + CompanyAlias + 큐 적재

**참조**: `design_v2.2.md` 섹션 7.1~7.3 + `design_v2.3_delta.md` 섹션 3

**선행**: SEC-PR-6

**생성 파일**:
```
sec_pipeline/ticker_matcher.py
```
**수정 파일**: `requirements.txt` (rapidfuzz 추가)

### Claude Code 프롬프트

```
docs/sec_pipeline/design_v2.2.md 섹션 7.1~7.3과
design_v2.3_delta.md 섹션 3을 읽어.

Ticker 매칭 엔진을 구현해줘.

1. sec_pipeline/ticker_matcher.py — TickerMatcher 클래스:
   - match(company_name) → (ticker | None, method)
     - 1순위: CompanyAlias (context_sector 포함, 없으면 범용 조회)
     - 2순위: exact_map 정확 매칭
     - 3순위: rapidfuzz token_sort_ratio ≥ 85%
   - match_with_queue(company_name, evidence, document, source_symbol)
     - 실패 시 UnmatchedCompanyQueue 적재
     - get_or_create(raw_company_name, status='pending')
     - 기존 건: occurrence_count += 1, source_sectors 축적
   - _get_fuzzy_candidates(name, top_k=5) → list[dict]

2. SEC-PR-4의 save_supply_chain_evidences 수정:
   - 저장 후 match_with_queue 호출
   - 매칭 성공 → evidence.target_company = Stock
   - 매칭 실패 → target_company = None, 큐 적재

⚠️ source_sectors는 set → sorted list. 중복 제거.
⚠️ rapidfuzz 설치: requirements.txt에 추가.

테스트: Phase 1 결과의 null target evidence에 매칭 돌려서 매칭률 확인.

docs/sec_pipeline/task_done/sec_pr_7_ticker_matcher.md 기록.
```

---

## SEC-PR-8: Django Admin 큐 뷰 + post_save signal

**참조**: `design_v2.2.md` 섹션 7.4~7.5 + `design_v2.3_delta.md` 섹션 3

**선행**: SEC-PR-7

**생성 파일**:
```
sec_pipeline/signals.py
```
**수정 파일**: `sec_pipeline/admin.py`, `sec_pipeline/apps.py`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 7.4~7.5와 v2.3 delta 섹션 3을 읽어.

Admin 미매칭 큐 뷰와 post_save signal을 구현해줘.

1. sec_pipeline/admin.py — UnmatchedCompanyQueueAdmin:
   - list_display: raw_company_name, source_symbol, occurrence_count,
     cross_sector_flag, status, fuzzy_top1, resolved_ticker
   - list_editable: status, resolved_ticker
   - actions: mark_not_public, mark_person, auto_resolve_top_candidate (≥ 0.90)
   - cross_sector_flag: source_sectors 2개+ → ⚠️ 배지

2. sec_pipeline/signals.py — on_unmatched_resolved:
   - status='matched' + resolved_ticker 있을 때만 동작
   - evidence.target_company 업데이트 + neo4j_dirty=True
   - 같은 이름 + 같은 sector의 다른 evidence만 선별 업데이트
   - CompanyAlias에 (alias, context_sector) 등록
   - ⚠️ 다른 sector evidence에 전파 금지
   - ⚠️ Neo4j 직접 동기화 금지. dirty flag만.

3. sec_pipeline/apps.py — ready()에서 signals import

테스트: Admin에서 1건 수동 매칭 → signal 동작 확인
→ evidence.target_company 업데이트, neo4j_dirty=True, CompanyAlias 생성 확인.

docs/sec_pipeline/task_done/sec_pr_8_admin_signal.md 기록.
```

---

## SEC-PR-9: sync_dirty_to_neo4j

**참조**: `design_v2.2.md` 섹션 7.5.1 + `design_v2.3_delta.md` 섹션 2

**선행**: SEC-PR-8

**수정 파일**: `sec_pipeline/tasks.py`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 7.5.1과 v2.3 delta 섹션 2를 읽어.

sync_dirty_to_neo4j Celery task를 구현해줘.

sec_pipeline/tasks.py에 추가:

sync_dirty_to_neo4j():
- 2-Phase + select_for_update(skip_locked=True)
  Phase A: transaction.atomic() 안에서 dirty row lock + dict 복사
    - select_related('source_company', 'target_company', 'source_document')
    - 최대 500건
  Phase B: neo4j_driver.session()으로 동기화
    - apoc.create.relationship() dynamic type
    - 기존 edge 삭제 (known_types) 후 재생성
  Phase C: 성공한 건 neo4j_dirty=False + neo4j_synced_at

_to_grade(confidence) → str

⚠️ RELATED_TO 고정 type 사용 금지. dynamic type만.
⚠️ MERGE 사용 금지. DELETE + CREATE 패턴만.
⚠️ known_types에 'RELATED_TO' 포함 (레거시 정리).
⚠️ Beat 1개 전제. 중복 실행 시에도 idempotent (데이터 오염 없음).
⚠️ Phase 1에서 이 함수가 Neo4j SOLE WRITER.

Celery Beat: crontab(minute='*/5') 주석으로 포함.

테스트: 매칭 완료 evidence 있는 상태에서 수동 호출
→ Neo4j edge 생성 → neo4j_dirty=False 확인.

docs/sec_pipeline/task_done/sec_pr_9_neo4j_sync.md 기록.
```

---

## SEC-PR-10: 관계 병합 + 미매칭 큐 처리

**참조**: `design_v2.2.md` 섹션 8 + `design_v2.3_delta.md` 섹션 4

**선행**: SEC-PR-9

**생성 파일**:
```
sec_pipeline/merger.py
sec_pipeline/management/commands/process_unmatched_queue.py
```

### Claude Code 프롬프트

```
design_v2.2.md 섹션 8과 v2.3 delta 섹션 4를 읽어.

관계 병합 로직과 미매칭 큐 일괄 처리를 구현해줘.

1. sec_pipeline/merger.py
   - RELATIONSHIP_SPECIFICITY: DEPENDS_ON(1) ~ SUPPLIES_TO(5)
   - SOURCE_RELIABILITY: sec_10k(0.95) ~ marketaux_news(0.60)
   - merge_relationship(existing, new) → dict
     - bounded boosting, relation_facets 보존, primary_type 선택
   - calculate_edge_dqs(source, target) → dict
     - 내부용: sufficiency, diversity, reliability, dqs_total
     - 사용자용: source_count, source_types

2. sec_pipeline/management/commands/process_unmatched_queue.py
   - fuzzy ≥ 0.90 자동 매칭 일괄 처리
   - 결과 요약 출력

⚠️ merge_relationship은 Phase 1에서 Neo4j에 직접 쓰지 않음.
   Phase 1은 dirty sync가 sole writer. 병합은 PostgreSQL에만.
⚠️ DQS 반환값에 내부용/사용자용 키 분리 필수 (원칙 6).

docs/sec_pipeline/task_done/sec_pr_10_merger.md 기록.
```

---

# Phase 2 — Track B + 서비스 레이어

---

## SEC-PR-11: Track B 키워드 사전

**선행**: SEC-PR-10

**생성 파일**: `sec_pipeline/keywords_track_b.py`

### Claude Code 프롬프트

```
Track B 키워드 사전을 정의해줘.

sec_pipeline/keywords_track_b.py:
- BM_KEYWORDS: 5개 필드별 키워드 dict
  - direct_customer_contact: direct sales, retail, consumer, B2C, end user, ...
  - contract_model: subscription, SaaS, recurring, license, one-time, hardware, ...
  - recurring_revenue_signal: ARR, MRR, recurring, retention, churn, renewal, ...
  - channel_dependency: distribution partner, reseller, OEM, direct, channel, ...
  - customer_concentration_hint:
    - 집중: accounted for X%, significant customer, major customer
    - 분산: no single customer, diversified customer base, no material concentration
- filter_paragraphs_track_b(text, max_paragraphs=15) → list[str]

⚠️ customer_concentration의 역방향 표현 필수 포함.
⚠️ 키워드는 Python dict. DB 아님. 변경 시 Git 커밋.

docs/sec_pipeline/task_done/sec_pr_11_keywords_track_b.md 기록.
```

---

## SEC-PR-12: Pass 1 + Pass 2 Gemini Flash (Track B)

**선행**: SEC-PR-11

**수정 파일**: `sec_pipeline/prompts.py`, `sec_pipeline/extractor.py`, `sec_pipeline/tasks.py`
**생성 파일**: `sec_pipeline/validator_track_b.py`

### Claude Code 프롬프트

```
Track B 추출 파이프라인을 구현해줘.

1. sec_pipeline/prompts.py에 추가:
   - PROMPT_VERSION_TRACK_B = 'v1'
   - BUSINESS_MODEL_EXTRACTION_PROMPT
     - 5개 필드 + evidence_text + confidence

2. sec_pipeline/extractor.py에 추가:
   - GeminiExtractor.extract_business_model(symbol, company_name, paragraphs)

3. sec_pipeline/validator_track_b.py (신규):
   - validate_business_model_result(result) → dict
   - save_business_model_snapshot(validated, document, symbol)
     - BusinessModelSnapshot + BusinessModelEvidence 생성
     - overall_confidence = 5개 confidence 평균
     - prompt_version 기록

4. sec_pipeline/tasks.py의 extract_from_document 수정:
   - Track B pass → 실제 구현 교체
   - Track A 실패해도 Track B 시도

⚠️ unknown은 판단 불가일 때만. 강제로 채우지 않음.

테스트: S&P 500 배치 재실행 (Track B). Gold Set Field Match 평가.

docs/sec_pipeline/task_done/sec_pr_12_track_b.md 기록.
```

---

## SEC-PR-13: 서비스 레이어

**선행**: SEC-PR-12

**생성 파일**: `metrics/services/business_model_service.py`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 10.2를 읽어.

metrics/services/business_model_service.py를 구현해줘.

- get_business_model(symbol, for_api=False) → dict | None
  - for_api=True: overall_confidence 제거, confidence_grade만 포함
  - for_api=False: 숫자 포함
  - latest('as_of_date') 사용
- get_business_model_evidence(symbol, field_name=None) → list[dict]
- is_recurring_business(symbol) → bool | None

⚠️ 다른 앱은 이 서비스만 호출. sec_pipeline.models 직접 import 금지.
⚠️ for_api가 점수 노출 경계의 유일한 게이트.

테스트: get_business_model('AAPL', for_api=True)에
overall_confidence가 없는지 확인.

docs/sec_pipeline/task_done/sec_pr_13_service_layer.md 기록.
```

---

# Phase 3 — 모니터링 + On-demand + Intelligence

---

## SEC-PR-14: Admin 대시보드 + quality_checks

**참조**: `design_v2.2.md` 섹션 11.1~11.3 + `design_v2.3_delta.md` 섹션 5

**선행**: SEC-PR-13

**수정 파일**: `sec_pipeline/admin.py`
**생성 파일**: `sec_pipeline/quality_checks.py`, `sec_pipeline/urls.py`, `templates/admin/sec_pipeline/dashboard.html`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 11.1~11.3과 v2.3 delta 섹션 5를 읽어.

품질 대시보드와 알림 시스템을 구현해줘.

1. sec_pipeline/admin.py — SECPipelineAdminView:
   - dashboard_view: 수집/추출/매칭/BM/에러 통계
   - Neo4j 동기화: neo4j_dirty=False(완료), neo4j_dirty=True(대기)
   - ⚠️ synced_to_neo4j 참조 금지

2. sec_pipeline/quality_checks.py:
   - run_post_batch_quality_checks(hours_back=24) → list[str]
   - 시간 기준: 대시보드=누적, 알림=최근 배치(hours_back)
   - 7개 체크 (실패율, unknown, 매칭률, confidence, 큐 적체, dirty 적체, 섹션검증)
   - 섹션 검증: detail__startswith='FAIL:' 필터

3. templates/admin/sec_pipeline/dashboard.html:
   - design_v2.2.md 11.2 ASCII 목업 참고

docs/sec_pipeline/task_done/sec_pr_14_dashboard.md 기록.
```

---

## SEC-PR-15: On-demand 수집 + FMP RSS

**참조**: `design_v2.2.md` 섹션 3.2, 12

**선행**: SEC-PR-14

**생성 파일**: `sec_pipeline/on_demand.py`, `sec_pipeline/views.py`
**수정 파일**: `sec_pipeline/urls.py`, `sec_pipeline/tasks.py`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 3.2와 12를 읽어.

1. sec_pipeline/on_demand.py
   - get_or_collect_filing(symbol) → dict | None
   - 1년 이내 문서 있으면 반환, 없으면 collect.delay 트리거
   - 중복 방지: 1시간 이내 로그 확인

2. sec_pipeline/views.py
   - FilingDataView(APIView).get → 200 또는 202

3. sec_pipeline/tasks.py에 추가:
   - check_new_filings_via_fmp(): RSS Feed API로 신규 10-K 감지

docs/sec_pipeline/task_done/sec_pr_15_on_demand.md 기록.
```

---

## SEC-PR-16: Pipeline Intelligence

**참조**: `design_v2.2.md` 섹션 11.4~11.10

**선행**: SEC-PR-15

**생성 파일**: `sec_pipeline/intelligence.py`
**수정 파일**: `sec_pipeline/admin.py`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 11.4~11.10을 읽어.

1. sec_pipeline/intelligence.py
   - PipelineDataCollector: 5차원 데이터 수집
   - PIPELINE_INTELLIGENCE_PROMPT: v2.2 11.6 프롬프트 그대로
   - PipelineIntelligenceReporter: Gemini Flash → DB 저장

2. sec_pipeline/admin.py에 추가:
   - PipelineIntelligenceReportAdmin
     - severity_badge, health_score_bar, worst_dim
     - fieldsets: 5차원 + cross insights + actions + trend
     - regenerate_report 액션

⚠️ 리포트 숫자는 전부 내부 운영용 (원칙 6 Admin 허용).

docs/sec_pipeline/task_done/sec_pr_16_intelligence.md 기록.
```

---

## SEC-PR-17: Celery chord 통합 + E2E 테스트

**참조**: `design_v2.2.md` 섹션 11.9 + `design_v2.3_delta.md` Celery chord 수정

**선행**: SEC-PR-16

**수정 파일**: `sec_pipeline/tasks.py`, `config/settings.py`

### Claude Code 프롬프트

```
design_v2.2.md 섹션 11.9와 v2.3 delta Celery chord 부분을 읽어.

1. sec_pipeline/tasks.py에 추가:
   - run_batch_and_report(symbols=None)
     - chord(collection_tasks)(post_batch)
     - post_batch = chain(
         sync_dirty_to_neo4j.si(),
         run_post_batch_quality_checks.si(hours_back=24),
         generate_intelligence_report.si(hours_back=24),
       )
   - generate_intelligence_report(hours_back=24)

2. config/settings.py Celery Beat 설정:
   - sync-dirty-neo4j: */5분
   - check-new-filings: 매월 1일
   - 주석 상태로 시작

3. E2E 테스트:
   - 5종목 run_batch_and_report(['AAPL','MSFT','JPM','XOM','JNJ'])
   - 전체 흐름: 수집 → 추출 → 매칭 → sync → quality → 리포트
   - PipelineIntelligenceReport 생성 확인

docs/sec_pipeline/task_done/sec_pr_17_e2e.md에 전체 파이프라인 결과 기록.
SEC Pipeline 전체 완료.
```
