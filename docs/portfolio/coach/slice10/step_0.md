# Slice 10 Step 0 지시서 — Mini-slice (#48 estimator v3)

> **슬라이스 성격**: mini-slice 첫 사례 (Step 9 슬롯 비움, 단일 부채 격리)
> **진입점**: #48 estimator v3 — 한국어 systematic underestimate 60.83% 보정
> **예상 회귀**: 496 → 509~516 (+13~20) / **비용**: $0~$0.05 / **LLM**: 0~10/50
> **cap 정책**: $0.50 (mini-slice 정책 신설)

---

## 0. 사전 결정 (확정)

| 결정           | 채택                                         | 핵심                                  |
| -------------- | -------------------------------------------- | ------------------------------------- |
| D-1 구조       | A. Step 0 단독 mini-slice                    | Step 9 슬롯 비움, 도구류 부채 격리    |
| D-2 #48 접근법 | c. Anthropic count_tokens API 실측           | 무료, ±2% 실측 정밀도                 |
| D-3 cap 정책   | ii. cap $0.50 mini-slice                     | COST_POLICY.md에 mini-slice 정책 추가 |
| D-4 scope      | b. input만 보정 + output Slice 11+ 부채(#51) | mini-slice 정체성 보존                |
| D-5 dump       | i. Step 0 §1에 통합 dump 포함                | 200~250건 backtest 자산 영구화        |

**환경 확인**:

- ✅ `anthropic==0.48` → `client.messages.count_tokens()` 정식 지원 (beta 졸업)
- ✅ raw 데이터 200~250건 표준 위치 확인 (`docs/portfolio/coach/slice{1..9}/`)
- ❓ pre-commit hook slice10 화이트리스트 — §0 첫 단계에서 검증 + 미등록 시 추가

---

## §0 환경 점검 + 사전 준비

### 작업

1. **Slice 9 종결 상태 검증**

   ```bash
   git checkout slice9
   pytest portfolio/tests -q  # 회귀 496 confirm
   ```

2. **브랜치 분기**

   ```bash
   git checkout -b slice10
   ```

3. **pre-commit hook 화이트리스트 검증/추가**

   ```bash
   grep -E "slice10" .pre-commit-config.yaml  # 또는 hook 스크립트
   # 없으면 slice9 패턴 따라 추가
   ```

4. **SDK 버전 검증**

   ```bash
   pip show anthropic | grep Version  # 0.48 예상
   python -c "from anthropic import Anthropic; c = Anthropic(); print(hasattr(c.messages, 'count_tokens'))"  # True 예상
   ```

5. **환경 변수 확인**
   ```bash
   echo $ANTHROPIC_API_KEY | wc -c  # >0 확인 (값 노출 금지)
   ```

### 산출물

- 없음 (검증만)

### KPI

- SDK 0.25.0+ 확인 PASS
- count_tokens 메서드 존재 PASS
- 회귀 baseline 496 confirm

---

## §1 통합 dump 스크립트 구현

### 작업

1. **`scripts/coach/dump_all_llm_calls.py` 신규 작성**

   요구사항:
   - 입력 경로: `docs/portfolio/coach/slice{1..9}/**/*.json` (재귀)
   - 스키마 정규화: flat(Slice 1, 8 matrix, 9) vs nested(Slice 2~7 step8 `metadata.input_tokens`)
   - 출력: `docs/portfolio/coach/all_llm_calls.jsonl` (한 줄 = 한 호출)
   - 멱등성: 재실행 시 동일 결과
   - 신규 슬라이스 entry 1줄 추가만으로 자동 흡수

   정규화 함수 패턴:

   ```python
   def normalize_entry(entry: dict, slice_n: int, file_source: str) -> dict:
       """flat or nested → 통합 평탄 schema."""
       if "input_tokens" in entry:
           norm = dict(entry)
       else:
           meta = entry.get("metadata", {})
           norm = {**{k: v for k, v in entry.items() if k != "metadata"}, **meta}
       norm["slice"] = slice_n
       norm["source_file"] = file_source
       # Slice 9 part1 estimated_input_tokens 보존 (검증용)
       return norm
   ```

   슬라이스별 파일 매핑 (사용자 회신 기반):
   - Slice 1: `step6_smoke_output.json` (flat, n=1) + `step8_3way_raw.json` (flat, n=9)
   - Slice 2: `step8_2way_e5_raw.json` (nested, n=14)
   - Slice 3: `step8_2way_e2_raw.json` (nested, n=14)
   - Slice 4: `step8_2way_e6_raw.json` (nested, n=14)
   - Slice 5: `step8_2way_e3_raw.json` (nested, n=14)
   - Slice 6: `step7_matrix_raw.json` + `step8_2way_e3_portfolio_raw.json` (nested)
   - Slice 7: `step7_matrix_raw.json` + `step8_2way_e4_conversation_raw.json` (nested, n=28)
   - Slice 8: `part3/step6_smoke_result.json` + `part3/matrix/*.json` + `part3/matrix_summary.json` (flat, n=27)
   - Slice 9: `part1/rationale_records.json` (flat, n=26, **`estimated_input_tokens` 보존**)

   ⚠️ **주의**: `docs/portfolio/coach/slice7/step9_1_rationales.json`은 `rationale_cost_usd`만 있고 토큰 없음 → 제외

2. **단위 테스트 작성**: `tests/coach/test_dump_llm_calls.py`
   - flat schema 정규화 PASS
   - nested schema 정규화 PASS
   - 멱등성 (2회 실행 동일 결과)
   - 슬라이스별 파일 매핑 검증
   - N >= 200 (필수 entry 누락 시 FAIL)
   - 5~8건 (data-prep 카테고리)

### 산출물

- `scripts/coach/dump_all_llm_calls.py`
- `tests/coach/test_dump_llm_calls.py`
- `docs/portfolio/coach/all_llm_calls.jsonl` (read-only 자산)

### KPI

- 정규화 성공률 100% (N≥200)
- 필수 필드 (input_tokens, output_tokens, cost_usd, model) 누락 0건
- 멱등성 PASS (hash 일치)

---

## §2 estimator v3 구현

### 작업

1. **`portfolio/measure/estimator_v3.py` 신규** (또는 기존 `estimator.py` 갱신 + v3 인터페이스 추가)

   설계 원칙:
   - **인터페이스 분리**: `estimate_input_tokens()` / `estimate_output_tokens()`
   - **input**: count_tokens API 실측
   - **output**: v2 (char ratio) 유지 → Slice 11 #51로 이연
   - **backward-compat**: legacy `estimate_tokens()` → `input + output` 합산 wrapper

   핵심 구현:

   ```python
   from anthropic import Anthropic
   from functools import lru_cache
   import hashlib
   import logging

   _client = Anthropic()
   _logger = logging.getLogger(__name__)


   def estimate_input_tokens(
       messages: list[dict],
       system: str | None = None,
       model: str = "claude-haiku-4-5-20251001",
   ) -> int:
       """Anthropic count_tokens API로 input_tokens 실측.

       API 실패 시 v2 fallback (warn log).
       """
       cache_key = _hash_inputs(messages, system, model)
       cached = _cache_get(cache_key)
       if cached is not None:
           return cached

       try:
           response = _client.messages.count_tokens(
               model=model,
               system=system or "",
               messages=messages,
           )
           result = response.input_tokens
           _cache_set(cache_key, result)
           return result
       except Exception as e:
           _logger.warning(f"count_tokens API failed, fallback to v2: {e}")
           return _estimate_input_tokens_v2(messages, system)


   def estimate_output_tokens(
       expected_chars: int | None = None,
       model: str = "claude-haiku-4-5-20251001",
   ) -> int:
       """Output 추정 (v2 char ratio 유지).

       TODO(Slice 11 #51): 진입점별 fitting 모델로 교체.
       """
       return _estimate_output_tokens_v2(expected_chars)


   def estimate_tokens(
       messages: list[dict],
       system: str | None = None,
       expected_output_chars: int | None = None,
       model: str = "claude-haiku-4-5-20251001",
   ) -> dict:
       """Legacy wrapper — input + output 합산 반환."""
       return {
           "input_tokens": estimate_input_tokens(messages, system, model),
           "output_tokens": estimate_output_tokens(expected_output_chars, model),
       }
   ```

   캐시 정책:
   - In-memory dict + LRU (max 1000 entries)
   - Slice당 reset (Slice 8 CostGuard reset_for_slice 패턴 참조)
   - hash key: SHA256(json.dumps({messages, system, model}, sort_keys=True))

2. **단위 테스트**: `tests/coach/test_estimator_v3.py`
   - input_tokens 실측 PASS (mock client)
   - output_tokens v2 호환 PASS
   - cache hit/miss 동작
   - API 실패 시 v2 fallback 동작
   - backward-compat (legacy 호출자 영향 0)
   - 8~12건

### 산출물

- `portfolio/measure/estimator_v3.py`
- `tests/coach/test_estimator_v3.py`

### KPI

- backward-compat 100% (기존 estimator v2 호출자 테스트 PASS)
- cache hit ratio 검증
- API 실패 fallback 동작 PASS

---

## §3 backtest 검증 (KPI ±2%)

### 작업

1. **`scripts/coach/backtest_estimator_v3.py` 신규**

   요구사항:
   - 입력: `all_llm_calls.jsonl` (N=200~250)
   - 검증: `estimate_input_tokens(raw.messages)` vs `raw.input_tokens`
   - delta% = |estimated - actual| / actual × 100
   - 통계: mean / median / P90 / max / per-slice

   ⚠️ **중대 위험**: Slice 1~9 raw에 `messages` 원본이 보존되어 있는지 미확인
   - **있으면**: 전체 N=200~250 backtest 가능 (이상적)
   - **없으면**: Slice 9 part1 `rationale_records.json` N=26만 가능 (`estimated_input_tokens` vs `input_tokens` 직접 대조)

   **Fallback A** (raw.messages 부재 시):
   - N=26 (Slice 9 part1만)로 진행
   - KPI 1 임계 완화: ≤ 5% (통계 신뢰도 감소 인정)
   - 신규 부채 #52 등록 (Slice 11+에서 messages 보존 정책 수립)

2. **언어 분포 분석**
   - 한국어 char 비율 vs delta% 산점도
   - Slice별 delta% (외삽 안전성)
   - 60.83% systematic underestimate 해소 확인

3. **`docs/portfolio/coach/slice10/backtest_report.md` 작성**
   - delta% 통계 표
   - 한국어/영어 분포 분석
   - KPI 1 (≤2% or ≤5% fallback) 판정

### 산출물

- `scripts/coach/backtest_estimator_v3.py`
- `docs/portfolio/coach/slice10/backtest_report.md`

### KPI

- max_delta ≤ 2% (또는 fallback ≤ 5%)
- Slice 9 part1 estimated_input_tokens 대비 v3 개선폭 ≥ 50%p
- LLM 호출 0~10/50 (count_tokens는 무료 + cache 활용)

---

## §4 mini-slice 패턴 문서화

### 작업

1. **`docs/portfolio/coach/MINI_SLICE_PATTERN.md` 신규**

   포함 내용:
   - **정의**: Step 0 단독 슬라이스, Step 9 슬롯 비움, cap $0.50, 단일 부채 격리
   - **적용 기준**:
     - 도구류 부채 (estimator, classifier, measure, dump 등)
     - production endpoint 영향 0
     - 단일 책임 + 명확한 KPI
   - **회귀 격리 KPI**:
     - data-prep 카테고리 분리
     - cost 카테고리 ±30% / no-cost ±50%
   - **첫 사례**: Slice 10 (#48 estimator v3)
   - **차후 후보**: #50 classifier 룰 / #51 output_tokens estimator / #47 S13 service layer 일부

### 산출물

- `docs/portfolio/coach/MINI_SLICE_PATTERN.md`

### KPI

- 파일 존재 + 5개 섹션(정의/기준/KPI/첫사례/후보) 모두 포함

---

## §5 COST_POLICY.md 갱신

### 작업

1. **기존 `docs/portfolio/coach/COST_POLICY.md`에 mini-slice 정책 섹션 추가**

   추가 내용:
   - `# Slice별 cap` 섹션에 `mini-slice: $0.50` 한 줄 추가
   - "mini-slice는 Step 9 슬롯 없음, 단일 부채 격리 슬라이스" 명시
   - MINI_SLICE_PATTERN.md 참조 링크

### 산출물

- `docs/portfolio/coach/COST_POLICY.md` (갱신)

### KPI

- `grep "mini-slice.*\$0.50" COST_POLICY.md` PASS

---

## §6 회귀 분류 + KPI 검증

### 작업

1. **`portfolio/measure/regression_classifier.py` 갱신**
   - `data-prep` 카테고리 추가 (dump 스크립트, 정규화 함수 테스트)
   - 분류 룰:
     - `tests/coach/test_dump_llm_calls.py::*` → data-prep
     - `tests/coach/test_estimator_v3.py::*` → cost (estimator는 cost 추정 도구)
     - 그 외 → 기존 분류

2. **KPI 매트릭스 검증**
   - `pytest portfolio/tests -q` → 회귀 +13~20 확인
   - 회귀 분류기 통과
   - IDENTICAL hash 7/7 유지 (`test_static_integrity`)

### 산출물

- `portfolio/measure/regression_classifier.py` (갱신)
- 단위 테스트 1~2건 (classifier 룰 검증)

### KPI

- 회귀 분류 정확도 100%
- IDENTICAL hash 7/7 PASS
- 회귀 9a (cost ±30%) / 9b (no-cost ±50%) PASS

---

## §7 종결 보고

### 작업

1. **`docs/portfolio/coach/slice10/step0_closing.md` 작성**

   포함 내용:
   - 회귀 결과: 496 → 실제값 (예상 +13~20)
   - IDENTICAL hash 7/7
   - 비용: 단독 $0~$0.05, 누적 $2.38~$2.43
   - LLM 호출 0~10/50
   - **KPI 11건 매트릭스** (아래 §8 참조)
   - **#48 close**: max_delta 검증 결과
   - **#51 신규 부채 등록**: output_tokens estimator (PS 1.5, Slice 11 Step 9 슬롯 묶음 후보)
   - **#52 신규 부채** (Fallback A 발동 시): raw messages 보존 정책 (PS 1.0)
   - mini-slice 패턴 첫 사례 정착 보고

2. **`docs/portfolio/coach/slice10/kpi_step0.md` 작성** (KPI 매트릭스 단독 문서)

### 산출물

- `docs/portfolio/coach/slice10/step0_closing.md`
- `docs/portfolio/coach/slice10/kpi_step0.md`

---

## §8 KPI 매트릭스 (11건)

| #   | KPI                                   | 임계                               | 측정 방법             | PASS/FAIL 룰      |
| --- | ------------------------------------- | ---------------------------------- | --------------------- | ----------------- |
| 1   | estimator v3 max_delta                | ≤ 2% (또는 fallback ≤ 5%)          | backtest 결과         | max_delta 측정    |
| 2   | dump 정규화 성공률                    | 100% (N≥200)                       | dump 출력 entry count | N 확인            |
| 3   | count_tokens API rate limit 위반      | 0건                                | API 응답 status       | 4xx/5xx 없음      |
| 4   | IDENTICAL hash 유지                   | 7/7                                | test_static_integrity | hash 일치         |
| 5   | backward-compat (estimator v2 호출자) | 100% PASS                          | 기존 테스트           | 변경 0건          |
| 6   | 회귀 분류 정확도                      | predicted ±30%(cost)/±50%(no-cost) | regression_classifier | KPI 9a/9b         |
| 7   | COST_POLICY.md mini-slice cap         | $0.50 명시                         | grep                  | 매치              |
| 8   | MINI_SLICE_PATTERN.md 신설            | 파일 + 5섹션                       | ls + grep             | 존재              |
| 9   | 누적 비용                             | ≤ $2.45 (마진 18%+)                | CostGuard             | $2.43 예상        |
| 10  | LLM budget                            | ≤ 10/50                            | CostGuard             | count_tokens 무료 |
| 11  | #51 신규 부채 등록                    | Slice 11 Step 9 슬롯 명시          | DEBT.md               | 라인 존재         |

---

## §9 Fallback 룰

| 트리거                        | 조치                                                               |
| ----------------------------- | ------------------------------------------------------------------ |
| §1 dump 회귀 +8 초과          | 정규화 단위 테스트 축소 (5건 → 3건), Slice 11에 보완 등록          |
| §3 raw.messages 부재          | Fallback A: N=26 (Slice 9 part1만), KPI 1 임계 ≤ 5% 완화, #52 등록 |
| count_tokens 응답 > 30ms/call | cache 우선 적용, batch patterns 검토                               |
| 회귀 +20 초과                 | mini-slice 한계 위반 — 사용자 보고 후 Slice 10 Part 1 분리 검토    |
| 누적 비용 $2.45 초과          | LLM 호출 중단, CostGuard 알림 + 사용자 보고                        |

---

## §10 작업 순서 (recommend)

| §   | 작업                   | 예상 시간 | 누적 |
| --- | ---------------------- | --------- | ---- |
| §0  | 환경 점검              | 15분      | 0:15 |
| §1  | dump 스크립트 + 테스트 | 1.5h      | 1:45 |
| §2  | estimator v3 + 테스트  | 1.0h      | 2:45 |
| §3  | backtest + report      | 45분      | 3:30 |
| §4  | MINI_SLICE_PATTERN.md  | 30분      | 4:00 |
| §5  | COST_POLICY.md         | 15분      | 4:15 |
| §6  | 회귀 분류 + KPI 검증   | 30분      | 4:45 |
| §7  | 종결 보고              | 15분      | 5:00 |

**총 ~5시간** (1인 개발자 1세션 적정 부하)

---

## §11 산출물 체크리스트 (12건)

- [ ] `scripts/coach/dump_all_llm_calls.py`
- [ ] `tests/coach/test_dump_llm_calls.py`
- [ ] `docs/portfolio/coach/all_llm_calls.jsonl` (read-only)
- [ ] `portfolio/measure/estimator_v3.py`
- [ ] `tests/coach/test_estimator_v3.py`
- [ ] `scripts/coach/backtest_estimator_v3.py`
- [ ] `docs/portfolio/coach/slice10/backtest_report.md`
- [ ] `docs/portfolio/coach/MINI_SLICE_PATTERN.md`
- [ ] `docs/portfolio/coach/COST_POLICY.md` (갱신)
- [ ] `portfolio/measure/regression_classifier.py` (갱신)
- [ ] `docs/portfolio/coach/slice10/kpi_step0.md`
- [ ] `docs/portfolio/coach/slice10/step0_closing.md`

---

## §12 회신 형식 (Claude Code → 사용자)

작업 완료 시 다음 형식으로 보고:

```
Slice 10 Step 0 mini-slice 종결.
- 회귀: 496 → ___ (+___)
- IDENTICAL: ___/7
- 비용 단독: $___ / 누적: $___ (마진 ___%)
- LLM 호출: ___/50
- KPI 11/11: ___개 PASS, ___개 FAIL
- #48 close: max_delta ___% (목표 ≤2% / fallback ≤5%)
- 신규 부채: #51 (확정) / #52 (fallback A 발동 시)
- mini-slice 패턴 첫 사례 정착: ___

git log --oneline slice9..HEAD
[commit hashes]
```

manual 검증 필요 사항이 있으면 별도 섹션으로 명시.
