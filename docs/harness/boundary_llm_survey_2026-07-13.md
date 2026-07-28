# BOUNDARY-LLM 방향 결정 입력 — 전수 조사 (2026-07-13)

> 지시서 ⑪. **read-only** — 코드 이동·리팩터·경계 변경·KNOWN_VIOLATIONS 편집·테스트 변경 0.
> 브랜치 `monorepo/sess-boundary-llm-survey`, base origin/main `3f105cb`.
> STEP 0 원칙 "박힌 값 신뢰 금지" 적용 — TASKQUEUE/메모리의 상태값을 코드로 재검증.

---

## 🔴 요약 (한 줄)

**BOUNDARY-LLM은 이미 실행 완료(origin/main)**. `packages/shared/llm/` 코어가 존재하고, LLM 직접호출 **burn-down 23→0** 이 병합됐으며(merge `8be3f65`), 아키텍처 가드 2종이 **KNOWN_VIOLATIONS=0 / FROZEN_COUNT=0 으로 7 passed**. TASKQUEUE의 "DORMANT·미착수"와 메모리의 "미머지 worktree"는 **stale**. 남은 것은 실행이 아니라 ⑴ stale 하네스 항목 정리 ⑵ 잔여 테스트 부채(`DEBT-TEST-BOUNDARY-LLM`) ⑶ 하류 언블록(CS-P2-LLM 등)뿐이다.

---

## Part A — 범위 복원 (무엇이 문제였고 왜 열쇠였나)

### A-1. BOUNDARY-LLM이 겨냥한 위반 (repo 근거)
- **정의**(TASKQUEUE 434, DECISIONS [2026-06-18] "통합 래퍼 형식 = 옵션 C"): 27파일/9 surface에 흩어진 외부 LLM SDK **직접 호출**(`genai.Client`·`GenerativeModel`·`Anthropic`·`AsyncAnthropic`)을 `packages/shared/llm`의 단일 진입점(`complete()`)으로 모으고, escape/CB/재시도/cost 정책을 공통화. provider 분포 Gemini 24 : Anthropic 3 : OpenAI 0.
- **라벨 주의**(중요): 이 트랙은 shared→apps 경계 청소 `BOUNDARY-1/2/3`(2026-06-04 종결)과 **별개**다. 전자=LLM 래퍼 정합, 후자=shared 역방향 import 청소.

### A-2. BOUNDARY-1/2/3에서 청소된 것 vs 남은 것
| 트랙 | 대상 | 상태 |
|------|------|------|
| BOUNDARY-1 | shared→`apps.market_pulse.utils.circuit_breaker` 2건 | ✅ done (`d30915e`, circuit_breaker 승격) |
| BOUNDARY-2 | shared→`apps.chain_sight.models` 1건 | ✅ done (`80b9280`, `apps.get_model` 동적 lookup) |
| BOUNDARY-3 | shared→`macro.models` 2건 | ✅ done (`a9bb229`, VIXProvider 포트+등록) |
| **경계 burn-down** | 5→0 | ✅ **트랙 전체 종결 2026-06-04** |
| **BOUNDARY-LLM** | LLM 직접호출 23→0 | ✅ **완료 (아래 Part B 실측)** — TASKQUEUE는 stale |

### A-3. A3·A4⑴이 왜 "열쇠"였나 (하류 블록 → 지금은 언블록)
- repo의 **구체 블록 지점**: `CS-P2-LLM`(chain_sight Phase 2 — LLM 레이어 통합/10-K 관계추출/FRED 해석)의 `Depends On` = **"BOUNDARY-LLM 슬라이스① land"** (TASKQUEUE 92). 슬라이스①(`packages/shared/llm` 코어)이 land되어야 착수 가능하다는 게이트.
- **슬라이스① = landed** (Part B-1 확인) → **CS-P2-LLM 의존 충족, 언블록**. 같은 근거로 LLM 채움에 의존하는 하류 슬라이스(대시보드 캐러셀 LLM placeholder = `D-LLMFILL`/`a56804d`, 그리고 지시서가 지칭한 "A3·A4⑴")도 코어 의존이 해소돼 **더 이상 BOUNDARY-LLM에 막히지 않는다**.
- ⚠ "A3·A4⑴"의 정확한 로드맵 ID는 repo에서 단일 확정 불가(A3/A4 라벨이 dashboard EOD 시그널·audit·portfolio 등 다수 맥락에 중복). **블록 메커니즘(LLM 코어 의존)은 해소됐다**는 것이 확정 사실이며, 정확한 슬라이스 매핑은 발주자 로드맵 대조 필요.

---

## Part B — 경계 실측 + import 그래프 (양방향)

### B-1. LLM 코어 물리 위치·구조 (실측)
- **`packages/shared/llm/`** 존재. 12 파일: `core.py`·`types.py`·`__init__.py` + `providers/{base,gemini,anthropic}.py` + `policy/{escape,circuit,retry,cost}.py`.
- provider SDK: gemini.py=`google.genai`(신SDK), anthropic.py=`anthropic`(sync+async), 모두 함수 내 lazy import. base.py=인터페이스.
- 진입점 4종: `complete()` / `acomplete()` / `astream()`(정규화 델타 StreamDelta·StreamFinal) / `count_tokens()`.

### B-2. shared→apps 방향 위반 전수
- **아키텍처 가드 실행 = 7 passed**: `test_shared_boundary.py`(shared→apps/macro 0, `KNOWN_VIOLATIONS=set()`) + `test_llm_direct_call_boundary.py`(직접호출 0, `KNOWN_VIOLATIONS=set()`, `FROZEN_COUNT=0`).
- **outbound(코어가 무는 것)**: `packages.shared.llm.*`(policy/providers/types) + `packages.shared.api_request.circuit_breaker`. **apps/macro/services import 0건** → shared→apps 역방향 **0**.
- **외부 SDK 직접호출 잔존(코어 밖)**: `genai.Client(`·`GenerativeModel(`·`Anthropic(`·`AsyncAnthropic(` 전부 **0건**(주석·테스트 mock 제외). burn-down 완료 확증.

### B-3. LLM 코어 inbound (누가 소비하나) — 12파일/25 import
| 앱/레이어 | 소비처(발췌) |
|-----------|--------------|
| apps/portfolio (2) | `llm/client.py`(complete), `measure/estimator_v3.py`(count_tokens) |
| packages/shared (2) | `alerting/delivery/email.py`(with_circuit), `stocks/llm/fill_service.py`·`stocks/services/korean_overview_service.py`(complete) |
| services/news (4) | `keyword_extractor`·`news_deep_analyzer`·`api/views`·`stock_insights` (complete) |
| services/rag_analysis (4) | `adaptive_llm_service`(astream)·`context_compressor`·`entity_extractor`(acomplete)·`llm_service`(astream) |
| services/sec_pipeline (2) | `extractor`·`intelligence` (complete) |
| services/serverless (7) | `csv_url_resolver`·`keyword_generator{,_v2}`·`keyword_service`·`llm_relation_extractor`·`regulatory_service`·`relationship_keyword_enricher`·`thesis_builder` |
| services/validation (1) | `llm_peer_filter` (complete) |
- 소비 양식: complete() 18 · acomplete() 5 · astream()/델타 3 · count_tokens() 1. **전 소비처가 코어 단일 경유**(직접 SDK 0).

### B-4. KNOWN_VIOLATIONS 중 LLM 관련 동결 = **0건**
- `test_llm_direct_call_boundary.py:KNOWN_VIOLATIONS = set()`, `FROZEN_COUNT = 0`.
- `scripts/health_check.py:_LLM_KNOWN_VIOLATIONS = set()`, `_BOUNDARY_KNOWN_VIOLATIONS = set()` — **SSOT 양쪽 동기화 완료**.
- 동결 이력(테스트 주석): 23→...→6(keyword_generator #16)→5(#12 stream)→4(#19 multipart)=Gemini 군집 종결→3(#9 구SDK)→2(#2 portfolio anthropic)→1(#8 adaptive stream)→**0(#3 estimator count_tokens)** = burn-down 종결.

### B-5. ★ shared→chain_sight 역의존 재발 (HALT 체크)
- **재발 0 — HALT 미해당.** `packages/shared/metrics/services/daily_report.py:298`이 `CompanyChainProfile`을 쓰나 **`django_apps.get_model("chainsight",...)` 동적 lookup**(BOUNDARY-2 승인 패턴)이라 static import 아님. 그 외 shared 내 chain_sight 참조는 주석/문자열/로컬 계산(eod_json_baker `chain_sight_sectors`)뿐. static import 0.

---

## Part C — 방향 후보 + 영향면 (스코어카드 재료, 판단 보류)

> 실측 구조상 BOUNDARY-LLM **실행은 완료**. 따라서 "청소 방향"은 실행이 아니라 **정합·잔여·언블록** 3축.

| # | 방향 | touch 범위 | 행위보존 리스크 | 회귀 표면 |
|---|------|-----------|-----------------|-----------|
| **C1** | **종결 정합**: TASKQUEUE DORMANT 항목(434~452)·CS-P2-LLM blocker 노트·메모리 `project_boundary_llm_track`을 "완료" 반영, DECISIONS "코어 베이스 #2 정정" fold-in | docs 3~4개(TASKQUEUE·DECISIONS·메모리), 코드 0 | 0 (문서) | 없음 |
| **C2** | **DEBT-TEST-BOUNDARY-LLM 청소**: `test_news_deep_analyzer`(≈10e, `mock_genai` 17곳 `.models.generate_content` 직접참조) + `test_csv_url_resolver`(4f, `_llm_client=MagicMock`) mock을 **shared 래퍼 seam**(`patch('...shared.llm.complete')`)으로 재작성 | 테스트 2파일(프로덕션 코드 0) | 낮음(테스트 전용, 프로덕션 정상) | 뉴스/serverless 테스트 스위트(선존 red 상환) |
| **C3** | **하류 언블록 착수**: CS-P2-LLM(10-K 관계추출/FRED 해석)·A3/A4⑴ LLM-fill — 코어 의존 해소됨, 별개 트랙 착수 | 신규 기능(별 트랙) | 신규 개발 | 해당 앱 |
| **C4** | **동결 유지(무행동)**: 이미 0 위반이라 방치해도 회귀 없음(가드가 신규 위반만 차단) | 0 | 0 | 없음 |

- **회귀 표면 주의(C2)**: `test_news_deep_analyzer` genai-mock 실패는 지시서⑩ 회귀에서도 관측된 **선존 baseline**(코드는 shared 이관 완료·정상, 테스트 mock만 stale). C2가 이 baseline을 상환하면 뉴스 스위트 green 회복.
- **DEBT-TEST-CHAINSIGHT vs BOUNDARY-LLM 구분**: 전자는 stale 워크트리/공유 test DB 오염 오탐 가능(pristine 체크아웃 판정 필요), 후자(C2)는 시그니처 명확(genai attr 부재)해 즉시 착수 가능.

---

## Part D — B1 EVENTGROUP-WINDOW 시한 부채 실측

### D-1. 부채 정의 (코드 실측)
- `apps/chain_sight/services/event_group_pipeline.py::_build_base`가 `ChainNewsEvent.objects.filter(is_duplicate=False)` — **무윈도우 전량 소비**(시간 필터 없음, 라인 52-54). `as_of = max(published_at)`(라인 61).
- **핵심 모순**: `_build_base(half_life)`가 half_life를 **시그니처로 수용**하고 `EventGroup.window_days=21`(help_text "co-mention half-life 윈도우(일)")로 **저장**하나, **쿼리는 이를 무시**. Jaccard 결합강도도 raw co_count(시간 가중 0). → 선언한 21일 윈도우가 **형식만 존재**.
- 설계 의도: `docs/chain_sight/plan/relation_confidence_design_v1.md` "decay(half-life)는 MVP에서 미구현" → **의도적 MVP 유예 = 부채로 명시적**.

### D-2. 현재 희석 정량 (DB 실측, as_of=파이프라인 기준 2026-07-11)
- ChainNewsEvent(is_duplicate=False) 총 **7,162** (span 155일, 2026-02-06~07-11). 월별: Feb 4·Mar 258·Apr 366·May **0(갭)**·Jun 3,450·Jul 3,084 (누적 급증).

| 기준 윈도우 | within | **aged(밖=희석분)** |
|-------------|-------:|--------------------:|
| **선언 21일** (≥06-20) | 5,013 (70.0%) | **2,149 (30.0%)** |
| 30일 (≥06-11) | 6,534 (91.2%) | 628 (8.8%) |

- **판독**: 시스템이 **자기 선언(21일)** 을 지켰다면 클러스터링 입력의 **30%(2,149건)가 배제**됐어야 하나, 무윈도우라 전부 섞임 = **선언 대비 30% 희석**. EventGroup 산출 35건(as_of=07-09, 단일).

### D-3. 시한성 (언제까지·놓치면 비용)
- **하드 데드라인 없음 — soft·단조 증가**. 매월 ~3,000건 누적(Jun+Jul=6,534)되므로 21일 밖 비율은 corpus 성장에 따라 **계속 상승**(현재 30% → 방치 시 신규 월분이 21일 밖으로 밀리며 증대). 비용 = 하류 leadership(22:30)/attention(22:40) 점수가 30%+ 희석된 EventGroup 위에서 계산 → **보드 신선도·신뢰도 저하가 시간에 비례해 누적**.

### D-4. ② 실행 구간 편입 후보 위치
- 부채는 **단일 파일·단일 쿼리**(`_build_base` 라인 52 필터에 `published_at__gte=as_of - window` 추가) → 소형 슬라이스. window 컷오프 도입(하드 윈도우) 또는 지수감쇠 가중(soft) 택1은 별도 결정.
- 편입 후보: chain_sight 하류 트랙(collect→extract→**load**(22:15) 체인의 load 단계) 정비 시, 또는 CS-P2-GRAPH(EventGroup 시각화) 착수 전 **입력 품질 선행 슬라이스**로. 행위보존: window 도입은 그룹 구성 변동(=행위 변경) → golden/스냅샷 회귀 필요(EventGroup 35건 델타 관측).

---

## Part E — 조사 결론 (방향 결정 재료)

1. **BOUNDARY-LLM 실행 = 완료** (origin/main `8be3f65` merge, burn-down 23→0, 가드 2종 0위반 7 passed, SSOT 동기). 남은 방향 = C1(종결 정합)·C2(테스트 부채)·C3(하류 언블록). C4(무행동)도 회귀 없음.
2. **하네스 stale 3곳**: TASKQUEUE DORMANT(434)·CS-P2-LLM blocker·메모리 `project_boundary_llm_track` → C1로 정정 권장.
3. **shared→apps/chain_sight 역의존 재발 0** (HALT 미해당).
4. **EVENTGROUP-WINDOW**: 선언 21일 대비 **30% 희석(2,149/7,162)**, soft·단조증가 부채, 단일-쿼리 소형 슬라이스로 load 체인/CS-P2-GRAPH 선행 편입 가능.

## 회계
- **read-only**: 코드/설정 정적 분석 + 아키텍처 테스트 실행(판정용, 무변경) + `chain_sight`/`django_celery_*` DB **SELECT**. **코드·테스트·경계·KNOWN_VIOLATIONS 변경 0**. 조사 산출 = 본 문서(docs)뿐.
