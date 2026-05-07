# Slice 4 Part 2 — E6 (조정 후 비교 해설) 진입점 검증 + 통합 지시서

> 작성일: 2026-05-07
> 진입점: **E6** (조정 후 비교 해설, E5 흐름 통합)
> 범위: **Part 2 = Step 6 ~ Step 9 + validation_report + refactor_backlog**
> Part 1 종결 baseline: **160 passed** (Slice 4 Part 1 commit 6개 완료 후 진입)
> 누적 비용 협의: ~$0.41 / 광의: ~$0.49 (Slice 4 Step 6/8 호출 후 갱신)

---

# §0. 참조 문서

본 지시서를 실행하기 전에 다음 참조 문서를 확인하세요. 코드/구조 정보는 모두 이 문서들의 **실측 인용**에서 가져왔습니다.

| 우선순위 | 참조 문서 | 사용 목적 |
|---|---|---|
| 1 | `docs/portfolio/coach/slice4_decisions.md` | Slice 4 결정 보존 (E6 진입점 + hybrid 7 + Step 9 #2) |
| 2 | `docs/portfolio/coach/slice4_part2_prep_data.md` | Part 2 사전 데이터 (환경 차이 5+6건 + 토큰 추정 + score 산식 사전 점검) |
| 3 | `docs/portfolio/coach/slice4_prep_data.md` | Part 1 진입 사전 데이터 (코드 인용 6건 + fixture 그룹 차이) |
| 4 | `docs/portfolio/PORTFOLIO_OVERALL_ANALYSIS.md` | 종합 재분석 (인프라 누적 + 가설 정착) |
| 5 | `docs/portfolio/instructions/slice_3_frontend_instruction_part2.md` | Slice 3 Part 2 패턴 (Step 6~9 mirror 대상) |
| 6 | `docs/portfolio/instructions/slice_4_frontend_instruction_part1.md` | Slice 4 Part 1 지시서 (분석 엔진 의존성 회피 결정 보존) |
| 7 | `docs/portfolio/coach/slice3/validation_report_slice3.md` | validation_report 6 섹션 패턴 mirror |
| 8 | `docs/portfolio/coach/slice3/refactor_backlog_slice3.md` | 백로그 형식 mirror |
| 9 | `scripts/validation/run_step6_e2_smoke.py` (라인 28~167) | Step 6 smoke 패턴 직접 인용 |
| 10 | `scripts/validation/score_step8.py` (라인 33~382) | Step 8/9 score 산식 통합 대상 |
| 11 | `portfolio/llm/cost_guard.py` (라인 84~88) | LLMBudgetExceededError raise 패턴 |
| 12 | `portfolio/llm/client.py` (라인 117~171) | LLMClient.complete 이중 가드 + 폴백 |

---

# §1. 목표

## 1.1 작업 단위 정의

E6 진입점의 실 LLM 호출 검증 + 회고 + 인프라 통합. Slice 1·2·3 Part 2 패턴을 직접 mirror하며, 동시에 Slice 4 슬라이스 종결 산출물(validation_report + refactor_backlog) 작성.

## 1.2 정량 목표

| 항목 | 목표 |
|---|---|
| 회귀 카운트 | 160 → **168~172 passed** (Slice 3 Part 2 +23 패턴 보수적 적용) |
| Step 6~9 신규 코드 | ~600~800줄 (smoke + measure + 회고 + 통합 score) |
| LLM 호출 (실 호출) | **~18 / 50** (Step 6 1 + Step 8 14 + 재시도 ~3) |
| 누적 비용 (Slice 4) | **~$0.10** 예상 (Step 6 ~$0.003 + Step 8 ~$0.10) |
| Step 9 통합 검증 | Slice 1 e1 산출물 IDENTICAL + Slice 3 e2 산출물 IDENTICAL |
| 작업 시간 추정 | Claude Code 75~90분 |
| validation_report 섹션 | 6개 (§1~§6, Slice 3 패턴 mirror) |
| refactor_backlog 항목 | ~5~8건 (Slice 3 9건 패턴 — Slice 4 신규 + 일부 이연) |

## 1.3 정성 목표

- **글쓰기 가설 4번째 외삽 검증**: Slice 1 E1 / Slice 3 E2에서 정착된 "글쓰기 → haiku" 가설을 E6에서 재검증. winner == haiku면 가설 4/4 정착, sonnet이면 외삽 신뢰도 재평가
- **score 산식 통합 완성**: 백로그 #2 (PS 3.0) 처리 — e1/e2/e6 `_main_unified()` 통합 + e5 delegation 유지. 새 글쓰기 진입점은 한 줄 추가만으로 합류 가능한 일반화 인프라 구축
- **#9 latency 임계 처리** (PS 2.0): `run_step6_e6_smoke.py` 신규에만 16,000ms 적용 — 기존 5 파일 보존 결정으로 회귀 위험 0
- **D4 가이드 적용**: 모든 Step 6~9 산출물에 `_json_default` + `_safe_write` round-trip 패턴 의무화 (Slice 3 손실 0건 검증 완료)
- **분석 엔진 의존성 회피 일관 유지**: Step 6/8에서 LLM이 자연어 비교 해설만 생성, 정량 재계산 없음 (Phase 2 위임)

---

# §2. 사전 조건

## 2.1 환경 점검 (Part 2 진입 직전 — Step 6 시작 전)

```bash
# git 상태
git branch --show-current
# 기대: portfolio

git status --short
# 기대: 빈 출력 또는 (.claude/scheduled_tasks.lock + slice_3_frontend_* 미tracking 정도)

git log --oneline -10
# 기대: Slice 4 Part 1 6개 commit이 최상단에 존재

# 회귀 baseline
pytest portfolio/tests/ --collect-only -q | tail -1
# 기대: 160 tests collected

# CostGuard 초기 상태
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from portfolio.llm.cost_guard import CostGuard; import json; print(json.dumps(CostGuard.get_instance().status(), ensure_ascii=False, indent=2))"
# 기대: slice_id="default", call_count=0, started_at=null

# .env 키 점검
grep -E "^(ANTHROPIC_API_KEY|GEMINI_API_KEY)=" .env | awk -F= '{print $1, "=set"}'
# 기대: ANTHROPIC_API_KEY=set, GEMINI_API_KEY=set
```

## 2.2 Slice 1·3 round-trip 사전 검증 (Step 9 회귀 KPI baseline)

Step 9 통합 작업 후 동일 명령으로 검증할 baseline을 *Part 2 진입 시점에* 사전 확보:

```bash
# Slice 1 e1 baseline 산출물 hash 저장
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json > /tmp/slice4_step9_baseline_e1.sha256

# Slice 3 e2 baseline 산출물 hash 저장
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json > /tmp/slice4_step9_baseline_e2.sha256

# 정상 동작 확인 (Step 9 작업 *전* 한 번 재실행하여 IDENTICAL 검증 — Slice 4 사전 데이터 §3.4 결과 확인)
python -m scripts.validation.score_step8 --entrypoint e1
python -m scripts.validation.score_step8 --entrypoint e2

# 위 두 명령 후 hash 동일성 즉시 확인
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | diff - /tmp/slice4_step9_baseline_e1.sha256
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | diff - /tmp/slice4_step9_baseline_e2.sha256
# 기대: 두 diff 모두 빈 출력 (hash 동일)
```

이 hash들은 Step 9 통합 후 동일 명령으로 다시 검증되어야 하며, 두 hash가 한 비트라도 변경되면 **Step 9 회귀 발생** → 즉시 git revert + 사용자 에스컬레이션.

## 2.3 디렉토리 사전 점검

```bash
# Slice 4 docs 경로 준비
mkdir -p docs/portfolio/coach/slice4

# 신규 작성 예정 파일 미존재 확인
ls scripts/validation/run_step6_e6_smoke.py 2>&1
ls scripts/validation/measure_e6_tokens.py 2>&1
ls scripts/validation/run_step8_e6_2way.py 2>&1
ls scripts/validation/analyze_e6_groups.py 2>&1
# 기대: 4건 모두 "No such file or directory" (Part 2에서 신규 작성)
```

## 2.4 작업 차단 조건 (Block conditions)

다음 중 하나라도 해당하면 작업 중단 + 사용자 에스컬레이션:

| 차단 조건 | 확인 방법 | 시점 |
|---|---|---|
| Slice 4 Part 1 6 commit 미수행 | `git log --oneline -10` | Part 2 진입 직전 |
| 회귀 baseline 불일치 (160 ≠ 실측) | `pytest --collect-only` | Part 2 진입 직전 |
| Slice 1 또는 Slice 3 e1/e2 round-trip baseline 깨짐 | §2.2 명령 | Part 2 진입 직전 |
| ANTHROPIC_API_KEY 미설정 | `grep ANTHROPIC_API_KEY .env` | Step 6 진입 직전 |
| CostGuard `slice_id != "default"` (이전 세션 잔재) | `CostGuard.get_instance().status()` | Step 6 진입 직전 (reset 호출 전) |
| Step 8 도중 호출 마진 < 5 (CostGuard remaining) | `CostGuard.status()["remaining"]` | Step 8 매 호출 후 |
| **Step 9 통합 후 Slice 1 또는 Slice 3 산출물 hash 불일치** | §2.2 hash diff | Step 9 종결 직전 — **즉시 revert** |

---

# §3. 스코프

## 3.1 IN scope (Part 2)

| Step | 작업 | 산출물 | 신규 코드 | LLM 호출 |
|---|---|---|---|---|
| Step 6 | smoke 1 call (haiku, e5_baseline_decrease) + #9 처리 (16,000ms 신규 적용) | `scripts/validation/run_step6_e6_smoke.py` 신규 + `docs/portfolio/coach/slice4/step6_smoke_e6_output.json` | ~150줄 + 산출물 | **1** |
| Step 7 | E6 token 측정 + e6 budget 확정 + `token_budgets.py` 갱신 + 단위 테스트 +3 | `scripts/validation/measure_e6_tokens.py` 신규 + `portfolio/llm/token_budgets.py` 1줄 추가 + `portfolio/tests/test_token_budgets.py` 확장 + `docs/portfolio/coach/slice4/step7_e6_tokens.json` | ~120줄 + 산출물 | **0** |
| Step 8 | 14 calls 회고 (haiku 7 + sonnet 7) + manual 평가 28건 + 그룹 분석 + `score_step8.py`에 e6 entry 추가 | `scripts/validation/run_step8_e6_2way.py` 신규 + `analyze_e6_groups.py` 신규 + `score_step8.py` e6 entry 추가 + 산출물 4종 (raw/scored/group/manual) | ~250줄 + 산출물 | **14** + 재시도 |
| Step 9 | #2 백로그 — `_main_unified()` 통합 (e1/e2/e6) + e5 delegation 유지 + Slice 1·3 IDENTICAL 검증 + 단위 테스트 +5~10 | `scripts/validation/score_step8.py` 리팩토링 + 단위 테스트 추가 | ~200줄 (대부분 리팩토링) | **0** |
| validation_report | 6 섹션 작성 | `docs/portfolio/coach/slice4/validation_report_slice4.md` | (산출물) | 0 |
| refactor_backlog | Slice 4 신규 + Slice 3 이연 진행 추적 | `docs/portfolio/coach/slice4/refactor_backlog_slice4.md` | (산출물) | 0 |

**총 신규 코드: ~720줄, 산출물 8건, LLM 호출 ~18 / 50**.

## 3.2 OUT of scope (Phase 2 또는 Slice 5+)

| 항목 | 위임 시점 |
|---|---|
| 분석 엔진 재계산 로직 (조정 후 AnalysisContext 산출) | Phase 2 (D-7 스켈레톤 패턴은 그 시점에 회귀 검토) |
| LLM-as-judge 평가 차원 | Phase 2 (Slice 5+) |
| `--input` / `--output` flag 추가 (score_step8.py CLI 확장) | Slice 5+ (Slice 4는 default 경로 유지) |
| Slice 3 백로그 #5 (TOKEN_BUDGET LLMClient 통합 잔여) | Slice 5 |
| Slice 3 백로그 #6 (Step 8 CSV 옵션) | Slice 5 |
| Slice 3 백로그 #7 (Mock mode dict 매핑) | Slice 5 |
| Slice 3 백로그 #8 (LLMClient entrypoint 인자) | Slice 5 |
| Slice 3 백로그 #10 (E2 keyword_match 룰 보완) | Slice 5 (E2 한정) |
| Slice 3 백로그 #11 (metrics_table 일반화) | Slice 5/6 (E3 진입 시) |
| E3 preset 외삽 검증 (insight 그룹차 0.67~0.83 위험) | Slice 5/6 |
| 기존 5 파일 latency 5,000ms 일괄 상향 | Slice 5+ (#9는 e6 한정 신규 적용으로 종결) |

## 3.3 명시적 비-스코프 (Negative scope)

다음 항목은 본 슬라이스에서 *의도적으로* 다루지 않습니다. Claude Code가 임의로 추가하면 안 됨:

- **기존 run_step6_*.py 5개 파일 latency 5,000ms 변경**: §6.2 영향 분석 — Slice 1/2/3 baseline 위험. e6 한정 신규 적용으로 종결
- **score_step8.py CLI 인자 확장 (`--input`/`--output`)**: Slice 4 OUT of scope. default 경로 패턴 유지
- **e5 산식 변경 (delegation 통합)**: 본질적 산식 차이 (efficiency 분모, normalize 패턴). Step 9에서 e5 delegation 유지
- **AnalysisContext / AdjustmentItem schema 변경**: Slice 1/2/3 회귀 위험
- **`LLMClient.complete` 시그니처 변경**: 모든 진입점 영향
- **Slice 4 Part 1 산출물 (schema/service/view/fixture) 변경**: Part 1 commit 후 IDENTICAL 유지

---

# §4. 단계별 작업

## Step 6 — 실 LLM smoke 1 call + #9 처리 (~10분, 1 call)

### 4.6.1 #9 처리 (latency 임계 16,000ms) — 5분

**범위**: `run_step6_e6_smoke.py` 신규 작성 시 `latency_ms_max: 16000` 적용. **기존 5 파일은 변경 금지** (§3.3 비-스코프).

**근거** (sliced4_part2_prep_data §6.2):
- 기존 5,000ms 파일 5종은 Slice 1/2/3 baseline 보존 — 변경 시 회귀 위험
- E6 출력 길이 ≈ E2 (Slice 3 latency 7,471ms 발생) → 16,000ms는 안전 마진 포함

### 4.6.2 신규 파일 — `scripts/validation/run_step6_e6_smoke.py`

`scripts/validation/run_step6_e2_smoke.py` 패턴 직접 mirror (slice4_part2_prep_data §4.3 인용 그대로):

```python
"""Slice 4 Step 6 — E6 (조정 후 비교 해설) smoke 실 호출.

목적:
  1. 실 LLM 호출(haiku) 1회 → E6Request 입력 → 자연어 비교 해설 출력
  2. schema_pass / completeness_auto / cost_pass / latency_pass 4개 판정
  3. raw + parsed + metadata + judgments JSON 저장 (D4 round-trip 의무)
  4. CostGuard 누적 1 call

차이 vs Slice 3 (run_step6_e2_smoke.py):
  - run_e2 → run_e6 (build_e6_prompt + parse_e6_response)
  - fixture: ALL_FIXTURES["garp_tech"] → ALL_FIXTURES["e5_baseline_decrease"]
  - latency 임계: 5,000ms → 16,000ms (Slice 4 #9 처리)
  - cost 임계: $0.020 (동일 유지)
  - reset_for_slice("slice3") → reset_for_slice("slice4")
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice


def _json_default(obj):
    """D4 가이드 — set/datetime/Decimal 직렬화 회피."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj).__name__} not JSON serializable")


def _safe_write(path: Path, data: dict) -> None:
    """Write + read-back round-trip 검증 (D4 가이드 의무)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)
    path.write_text(serialized, encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded is not None
    print(f"  [round-trip OK] {path}")


THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 16000,  # Slice 4 #9 — E6 한정 (e2 7,471ms + 안전 마진)
}

OUTPUT_PATH = Path("docs/portfolio/coach/slice4/step6_smoke_e6_output.json")


def main() -> int:
    init_django()
    guard = reset_for_slice("slice4", max_calls=50)
    print(f"[CostGuard] {guard.status()}")

    # 지연 import (init_django 후)
    from portfolio.llm.client import LLMClient
    from portfolio.llm.constants import ANTHROPIC_HAIKU_MODEL  # 또는 _llm_kwargs.PROVIDER_KWARGS["haiku"]
    from portfolio.llm.cost_guard import CostGuard
    from portfolio.schemas.llm import E6Request
    from portfolio.services.e6_comparison import (
        build_e6_prompt,
        parse_e6_response,
    )
    from portfolio.tests.fixtures.sample_comparison_context import ALL_FIXTURES

    fixture_fn = ALL_FIXTURES["e5_baseline_decrease"]
    fixture = fixture_fn()
    payload = {
        "analysis_context": fixture["analysis_context"],
        "adjustments": fixture["adjustments"],
    }
    if fixture.get("user_intent"):
        payload["user_intent"] = fixture["user_intent"]

    request = E6Request.model_validate(payload)
    prompt = build_e6_prompt(request)
    print(f"[Prompt] chars={len(prompt)}")

    client = LLMClient()
    resp = client.complete(
        prompt=prompt,
        provider="anthropic",
        model=ANTHROPIC_HAIKU_MODEL,
    )
    print(f"[LLM] provider={resp.provider} model={resp.model} latency={resp.latency_ms}ms cost=${resp.cost_usd:.6f}")

    # 1. schema_pass — parse_e6_response 성공 여부
    try:
        parsed = parse_e6_response(resp.text)
        schema_pass = True
        parsed_dump = parsed.model_dump()
    except Exception as exc:
        schema_pass = False
        parsed_dump = None
        print(f"[schema_pass=False] parse error: {exc}")

    # 2. completeness_auto — 6 필드 모두 schema minimum 통과 (parse 성공 시 자동 만족)
    completeness_auto = schema_pass

    # 3. cost_pass / latency_pass
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    output = {
        "step": "step6_e6_smoke",
        "fixture": "e5_baseline_decrease",
        "fixture_group": fixture["fixture_group"],
        "fixture_id": fixture["fixture_id"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "raw_content": resp.text,
        "parsed": parsed_dump,
        "metadata": resp.metadata_dict(),
        "judgments": {
            "schema_pass": schema_pass,
            "completeness_auto": completeness_auto,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "naturalness_manual": None,  # 사용자 수동 입력 자리
            "insight_manual": None,
        },
        "thresholds": THRESHOLDS,
        "cost_guard_status": CostGuard.get_instance().status(),
    }
    _safe_write(OUTPUT_PATH, output)

    all_pass = schema_pass and completeness_auto and cost_pass and latency_pass
    print(
        f"[Result] schema={schema_pass} completeness={completeness_auto} "
        f"cost={cost_pass} ({resp.cost_usd:.6f}/{THRESHOLDS['cost_usd_max']}) "
        f"latency={latency_pass} ({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
    )
    print(f"[Final] {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 4.6.3 Step 6 실행

```bash
python -m scripts.validation.run_step6_e6_smoke
```

**기대 결과**:
- `latency` ~7,000~10,000ms 범위 (E2 7,471ms 참조 + 안전)
- `cost_usd` ~$0.001~0.005 (haiku 가격 + 입력 1,000자 + 출력 ~500자)
- `schema_pass=True`, `completeness_auto=True`, `cost_pass=True`, `latency_pass=True`
- `[Final] PASS` 출력
- `step6_smoke_e6_output.json` 생성 + round-trip OK

### 4.6.4 Step 6 실패 처리

| 실패 케이스 | 처리 |
|---|---|
| `schema_pass=False` (parse 실패) | raw_content 보존 + 사용자 에스컬레이션. prompt 재설계 필요 가능성 |
| `latency > 16,000ms` | `[Final] FAIL` 종결 후 사용자 에스컬레이션. THRESHOLDS 재검토 (또는 sonnet 호출로 polling 재시도 1회) |
| `cost > $0.020` | 사용자 에스컬레이션. token_budgets 재검토 |
| LLMRateLimitError | LLMClient 폴백이 자동 처리 — `fallback_from=anthropic`이 metadata에 기록됨. 이는 PASS 처리 (Slice 1 패턴) |
| LLMBudgetExceededError | `[Final] FAIL` + CostGuard 재설정 검토 (이전 세션 잔재 의심) |
| ANTHROPIC_API_KEY 누락 | LLMAuthError → 즉시 종료. .env 점검 후 재실행 |

### 4.6.5 Step 6 완료 보고 형식

```
## Step 6 완료 보고

- 실행 명령: python -m scripts.validation.run_step6_e6_smoke
- fixture: e5_baseline_decrease (e5_baseline 그룹)
- prompt chars: <N>
- LLM 메타: provider=<>, model=<>, latency=<>ms, cost=$<>
- 4 판정:
  - schema_pass: <Y/N>
  - completeness_auto: <Y/N>
  - cost_pass: <Y/N> (<cost> / 0.020)
  - latency_pass: <Y/N> (<lat>ms / 16000ms) — #9 처리 적용
- fallback_from: <None | anthropic | gemini>
- CostGuard 누적: 1 / 50
- 산출물: docs/portfolio/coach/slice4/step6_smoke_e6_output.json (round-trip OK)
- [Final] PASS / FAIL
```

---

## Step 7 — E6 token 측정 + e6 budget 확정 + 단위 테스트 +3 (~15분, 0 calls)

### 4.7.1 신규 파일 — `scripts/validation/measure_e6_tokens.py`

E5 (`measure_e5_tokens.py`) 또는 E2 (`measure_e2_tokens.py`) 패턴 직접 mirror. anthropic count_tokens API로 7 fixture 모두 측정 → P90 산출 → budget 확정.

```python
"""Slice 4 Step 7 — E6 token 측정.

목적:
  1. 7 fixture 각각의 prompt를 anthropic count_tokens API로 실측
  2. P90 산출 → budget = ceil(P90 × 1.5 / 500) × 500 round-up
  3. token_budgets.py에 e6 entry 추가 결정값 산출
  4. Slice 4 Part 1 §2.4 1차 추정 (1,000 tokens) 검증
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from scripts.validation._setup import init_django


OUTPUT_PATH = Path("docs/portfolio/coach/slice4/step7_e6_tokens.json")


def main() -> int:
    init_django()

    from portfolio.schemas.llm import E6Request
    from portfolio.services.e6_comparison import build_e6_prompt
    from portfolio.tests.fixtures.sample_comparison_context import ALL_FIXTURES

    client = anthropic.Anthropic()

    measurements = []
    for fixture_name, fixture_fn in ALL_FIXTURES.items():
        fx = fixture_fn()
        payload = {"analysis_context": fx["analysis_context"], "adjustments": fx["adjustments"]}
        if fx.get("user_intent"):
            payload["user_intent"] = fx["user_intent"]
        req = E6Request.model_validate(payload)
        prompt = build_e6_prompt(req)

        # anthropic count_tokens API
        result = client.messages.count_tokens(
            model="claude-haiku-4-5",
            messages=[{"role": "user", "content": prompt}],
        )
        actual_tokens = result.input_tokens
        char_estimate = len(prompt) // 3  # 사전 데이터 §2.2 비교용

        measurements.append({
            "fixture_id": fx["fixture_id"],
            "fixture_group": fx["fixture_group"],
            "chars": len(prompt),
            "char_estimate_tokens": char_estimate,
            "actual_tokens": actual_tokens,
            "delta_pct": (actual_tokens - char_estimate) / char_estimate * 100 if char_estimate else 0,
        })

    # 통계
    actuals = sorted(m["actual_tokens"] for m in measurements)
    n = len(actuals)
    p90_idx = math.ceil(0.9 * n) - 1
    p90 = actuals[p90_idx]
    mean = sum(actuals) / n
    budget_proposed = math.ceil(p90 * 1.5 / 500) * 500

    output = {
        "step": "step7_e6_tokens",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "measurements": measurements,
        "statistics": {
            "n": n,
            "min": min(actuals),
            "max": max(actuals),
            "mean": round(mean, 1),
            "p90": p90,
            "p90_index": p90_idx,
        },
        "budget_decision": {
            "p90": p90,
            "p90_x1.5": round(p90 * 1.5, 1),
            "round_up_500": budget_proposed,
            "previous_estimate_chars_div_3": 1000,  # Part 1 §2.4
            "delta_from_estimate_pct": (budget_proposed - 1000) / 1000 * 100,
        },
        "compared_to_existing": {
            "e1": 5000,
            "e5": 2000,
            "e2": 1500,
            "e6_proposed": budget_proposed,
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[Tokens] n={n}, min={min(actuals)}, max={max(actuals)}, mean={mean:.1f}, P90={p90}")
    print(f"[Budget] P90 × 1.5 = {p90 * 1.5:.1f} → round-up 500 = {budget_proposed}")
    print(f"[Saved] {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 4.7.2 `token_budgets.py` 갱신

`portfolio/llm/token_budgets.py` 라인 14~19 ENTRYPOINT_TOKEN_BUDGETS dict에 1줄 추가:

```python
ENTRYPOINT_TOKEN_BUDGETS: dict[str, int] = {
    "e1": 5000,  # Slice 1 결정값
    "e5": 2000,  # Slice 2 Step 7 (P90=756 × 1.5 → round-up 2000)
    "e2": 1500,  # Slice 3 Step 7 (P90=686 × 1.5 → round-up 1500)
    "e6": <Step 7 측정값>,  # Slice 4 Step 7 (P90=<P90> × 1.5 → round-up <budget>)
    # Slice 5+: e3/e4 추가 시 등록
}
```

> **권장 budget**: 1차 추정 1,000 tokens. 실측 P90이 다르면 그 값으로 반영. 단 1차 추정에서 ±20% 이내 차이면 1,000 유지 권장 (round-up 500 단위 안정성).

### 4.7.3 단위 테스트 +3

`portfolio/tests/test_token_budgets.py` 확장 (Slice 3 패턴 mirror):

```python
def test_e6_budget_registered():
    """Slice 4에서 e6 budget이 token_budgets에 등록되어야 함."""
    from portfolio.llm.token_budgets import ENTRYPOINT_TOKEN_BUDGETS, get_token_budget
    assert "e6" in ENTRYPOINT_TOKEN_BUDGETS
    budget = get_token_budget("e6")
    assert budget > 0
    assert budget >= 500  # round-up 단위 최소
    assert budget <= 5000  # e1보다 크진 않을 것 (e6는 분석 엔진 의존성 회피로 가벼움)


def test_e6_budget_smaller_than_e1():
    """E6는 분석 엔진 의존 없어 e1보다 작아야 함 (입력 평탄화 가벼움)."""
    from portfolio.llm.token_budgets import get_token_budget
    assert get_token_budget("e6") < get_token_budget("e1")


def test_token_budgets_full_dict():
    """ENTRYPOINT_TOKEN_BUDGETS dict가 4 진입점 (e1/e5/e2/e6)을 등록."""
    from portfolio.llm.token_budgets import ENTRYPOINT_TOKEN_BUDGETS
    assert set(ENTRYPOINT_TOKEN_BUDGETS.keys()) >= {"e1", "e5", "e2", "e6"}
```

### 4.7.4 Step 7 검증

```bash
python -m scripts.validation.measure_e6_tokens
# 기대: P90 출력 + budget 결정 + step7_e6_tokens.json 저장

# token_budgets.py 갱신 후 회귀
pytest portfolio/tests/test_token_budgets.py -v
# 기대: 기존 + 추가 3 = N+3 passed

pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 기대: 160 → 163 passed (+3)
```

### 4.7.5 Step 7 완료 보고 형식

```
## Step 7 완료 보고

- 측정 명령: python -m scripts.validation.measure_e6_tokens
- 7 fixture 실측 결과:
  - min: <N> tokens
  - max: <N> tokens
  - mean: <N> tokens
  - P90: <N> tokens (사전 추정 372 대비 차이: <±N>%)
- budget 결정: <P90> × 1.5 = <X> → round-up 500 = **<budget>** tokens
- token_budgets.py 갱신: e6=<budget> 추가
- 단위 테스트 +3: test_e6_budget_registered / test_e6_budget_smaller_than_e1 / test_token_budgets_full_dict
- 회귀: 160 → 163 passed (+3)
- 산출물: docs/portfolio/coach/slice4/step7_e6_tokens.json (round-trip 미적용 — 단순 실측 결과)
- 1차 추정값 (1,000) 정확도: <±N>% — 적정 / 재조정 필요
```

---

## Step 8 — 14 calls 회고 + manual 평가 + 그룹 분석 + score_step8 e6 entry (~30~40분, 14+ calls)

### 4.8.1 `score_step8.py`에 e6 entry 추가 (Step 8 작업 전)

`scripts/validation/score_step8.py` 라인 33~63 DIMENSION_LOOKUP dict에 e6 entry 추가:

```python
DIMENSION_LOOKUP = {
    "e1": {...},  # 기존
    "e5": {...},  # 기존 (delegated_to)
    "e2": {...},  # 기존 (additional_lex_check: completeness_auto)
    "e6": {  # Slice 4 신규 — e2 패턴 mirror (글쓰기 + completeness 자동)
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw":   "docs/portfolio/coach/slice4/step8_2way_e6_raw.json",
        "default_scored":"docs/portfolio/coach/slice4/step8_2way_e6_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # E2 mirror
    },
}
```

main() 함수 분기에 e6 추가 (라인 124~127 패턴 mirror):

```python
if args.entrypoint == "e6":
    return _main_e6()
```

`_main_e6()` 함수 신규 작성 — `_main_e2()` (라인 231~378) 직접 mirror, `default_raw`/`default_scored` 경로만 e6용으로 변경. **본 작업은 Step 9의 통합 작업 *전* 임시 분기 형태**로 작성. Step 9에서 `_main_unified()`로 흡수 예정.

### 4.8.2 신규 파일 — `scripts/validation/run_step8_e6_2way.py`

`run_step8_e2_2way.py` 패턴 직접 mirror. 14 calls (haiku 7 + sonnet 7). 각 호출 결과를 nested 구조(`{model_label, fixture, fixture_group, judgments, metadata}`)로 raw에 저장.

핵심 차이 vs Slice 3:
- `ALL_FIXTURES`: `sample_diagnostic_context` → `sample_comparison_context`
- `run_e2` → `run_e6`
- E6Request 입력 (analysis_context + adjustments + user_intent) — Slice 3 E2Request (analysis_context만)와 다름
- `cost_usd_max: 0.020` 동일
- `latency_ms_max: 16000` (Slice 4 #9 — Step 8도 Step 6과 동일 임계 적용)
- output: `docs/portfolio/coach/slice4/step8_2way_e6_raw.json`

```python
"""Slice 4 Step 8 — E6 (조정 후 비교 해설) 2-way 회고.

매트릭스: 7 fixture × 2 model (haiku + sonnet) = 14 calls.
Gemini 제외 (Slice 1 9/9 폴백 교훈 + Slice 4 결정 보존).
"""

# (run_step8_e2_2way.py 직접 mirror, fixture/service/path만 e6용으로 변경)
```

### 4.8.3 신규 파일 — `scripts/validation/analyze_e6_groups.py`

`analyze_e2_groups.py` 패턴 직접 mirror. baseline (e5_baseline 3) vs focused (e6_focused 4) 그룹 비교.

산출물: `docs/portfolio/coach/slice4/step8_2way_e6_group_analysis.json`

### 4.8.4 manual 평가 28건 (사용자 수동 입력)

Step 8 raw 산출 후 사용자가 28건(14 호출 × 2 차원 = naturalness + insight) 수동 평가. 각 호출에 대해:
- `naturalness_manual`: 1~5 (자연스러움 — 한국어 어조, 문법, 가독성)
- `insight_manual`: 1~5 (통찰력 — 비교 해설의 깊이, 변경 사항 분석 적절성)

평가 가이드 산출물: `docs/portfolio/coach/slice4/step8_e6_manual_eval_guide.md` (Slice 1·3 패턴 mirror).

### 4.8.5 score 산출

manual 평가 28건 입력 후:

```bash
python -m scripts.validation.score_step8 --entrypoint e6
```

산출물: `docs/portfolio/coach/slice4/step8_2way_e6_scored.json`. winner 결정 + label_means + lex_pass_rate.

### 4.8.6 그룹 분석

```bash
python -m scripts.validation.analyze_e6_groups
```

산출물: 그룹별 (baseline vs focused) × 모델별 (haiku vs sonnet) score 평균 4매트릭스 + interpretation_guide 적용.

### 4.8.7 Winner 판정

다음 기준으로 winner 결정 (Slice 1·3 패턴 mirror):

1. **lex_pass_rate**: 두 모델 모두 lex 필터(naturalness>=4 + insight>=4 + completeness_auto)를 일정 비율 이상 통과해야 함. 한 모델만 통과 → 그 모델이 winner
2. **label_means efficiency**: lex 통과 시 efficiency = sqrt(naturalness × insight) / sqrt(cost_usd × latency_ms / 1000) 산식. label_means가 높은 모델이 winner
3. **그룹 차이**: focused 그룹에서 sonnet이 차별화되면 hybrid 정당화 (Slice 3 패턴)

### 4.8.8 글쓰기 가설 4번째 외삽 검증

| 시나리오 | winner | 가설 정착 상태 |
|---|---|---|
| haiku winner | haiku | **글쓰기→haiku 가설 4/4 정착** — Slice 5+에서 글쓰기 진입점은 default haiku 안전 |
| sonnet winner | sonnet | 가설 3/4 — 외삽 신뢰도 재평가 필요. Slice 5에서 추가 글쓰기 진입점으로 5번째 검증 권장 |
| 그룹별 winner 다름 | mixed | 추가 분석 필요 — fixture 다양성 vs 모델 강점 매핑 |

### 4.8.9 Step 8 완료 보고 형식

```
## Step 8 완료 보고

- 실행 명령:
  - python -m scripts.validation.run_step8_e6_2way → 14 calls
  - python -m scripts.validation.score_step8 --entrypoint e6 → score 산출
  - python -m scripts.validation.analyze_e6_groups → 그룹 분석
- LLM 호출: 14 + 재시도 <N> = <total> / 50
- 비용: $<X> (haiku <Y> + sonnet <Z>)
- lex_pass_rate: haiku <X>/7, sonnet <Y>/7
- label_means: haiku=<X>, sonnet=<Y>
- **Winner: <haiku | sonnet | mixed>**
- 그룹 분석:
  - baseline (e5_baseline, 3 fixture):
    - haiku: naturalness=<X>, insight=<Y>, score=<Z>
    - sonnet: naturalness=<X>, insight=<Y>, score=<Z>
  - focused (e6_focused, 4 fixture):
    - haiku: naturalness=<X>, insight=<Y>, score=<Z>
    - sonnet: naturalness=<X>, insight=<Y>, score=<Z>
- 글쓰기 가설 외삽 검증: **<4/4 정착 | 3/4 재평가 필요>**
- 산출물:
  - step8_2way_e6_raw.json (round-trip OK)
  - step8_2way_e6_scored.json (round-trip OK)
  - step8_2way_e6_group_analysis.json (round-trip OK)
  - step8_e6_manual_eval_guide.md
- 회귀: 163 (Step 7 종결 동일, Step 8은 산출물만 — 단위 테스트 추가 없음)
```

---

## Step 9 — #2 백로그 score 산식 통합 (~30분, 0 calls)

### 4.9.1 작업 범위 명시

**IN scope (Step 9)**:
- `score_step8.py`의 e1/e2/e6 처리를 `_main_unified()` 한 함수로 통합
- DIMENSION_LOOKUP 메타로 분기 (`result_structure: flat/nested`, `additional_lex_check: None/completeness_auto`)
- e5는 delegation 유지 (산식 본질 차이)
- Slice 1·3 산출물 hash IDENTICAL 검증
- 단위 테스트 +5~10 (통합 함수 + dispatch 검증)

**OUT scope (Step 9)**:
- score_step8.py CLI 인자 변경 (`--input`/`--output` 추가 등)
- e5 산식 변경
- DIMENSION_LOOKUP 메타 키 추가 (현재 키만 사용)

### 4.9.2 통합 전 사전 검증 (5분)

§2.2 명령으로 baseline hash 재확인:

```bash
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | diff - /tmp/slice4_step9_baseline_e1.sha256
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | diff - /tmp/slice4_step9_baseline_e2.sha256
# 두 diff 모두 빈 출력이어야 함
```

차이 발견 시: Step 9 작업 보류. 사용자 에스컬레이션. (Step 8 도중 score_step8.py 임시 분기 작성으로 인해 baseline이 변경됐을 가능성 — Step 8 e6 entry 추가는 e1/e2 산출물에 영향 없어야 함)

### 4.9.3 통합 함수 작성 (15분)

`scripts/validation/score_step8.py`의 main() 함수 + `_main_e2()` + e1 인라인 부분을 다음 구조로 통합:

```python
def _normalize_results(results: list[dict], structure: str) -> list[dict]:
    """Result structure에 따라 normalize.

    flat (e1): 그대로 반환
    nested (e2/e6): judgments + metadata → flat dict
    """
    if structure == "flat":
        return results
    if structure == "nested":
        flat = []
        for r in results:
            j = r.get("judgments", {})
            m = r.get("metadata", {}) or {}
            flat.append({
                "label": r.get("model_label") or r.get("label"),  # nested의 model_label → label
                "fixture": r["fixture"],
                "fixture_group": r.get("fixture_group"),
                "schema_pass": j.get("schema_pass"),
                "completeness_auto": j.get("completeness_auto"),
                "naturalness": j.get("naturalness_manual") or j.get("naturalness"),
                "insight": j.get("insight_manual") or j.get("insight"),
                "cost_usd": m.get("cost_usd"),
                "latency_ms": m.get("latency_ms"),
                "fallback_from": m.get("fallback_from"),
            })
        return flat
    raise ValueError(f"Unknown result_structure: {structure!r}")


def _build_lex_filter(additional_check: str | None):
    """e1 base lex + optional additional_lex_check (e2/e6용 completeness_auto)."""
    def _filter(r: dict) -> bool:
        if not lexicographic_filter(r):  # e1 헬퍼 재사용
            return False
        if additional_check and not r.get(additional_check):
            return False
        return True
    return _filter


def _main_unified(entrypoint: str) -> int:
    """e1/e2/e6 통합 처리 (Slice 4 Step 9 #2 통합).

    e5는 delegation 유지 (산식 본질 차이로 별도 모듈).
    """
    config = DIMENSION_LOOKUP[entrypoint]
    raw_path = Path(config["default_raw"])
    scored_path = Path(config["default_scored"])

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    results = _normalize_results(raw["results"], config["result_structure"])

    lex_filter = _build_lex_filter(config.get("additional_lex_check"))
    passed = [r for r in results if lex_filter(r)]
    failed = [r for r in results if not lex_filter(r)]

    # efficiency / fallback / label_means — e1 기존 헬퍼 그대로 재사용
    scored = []
    for r in passed:
        r_with_score = dict(r)
        r_with_score["efficiency"] = efficiency_score(r)  # 기존 헬퍼
        scored.append(r_with_score)
    for r in failed:
        r_with_score = dict(r)
        r_with_score["efficiency"] = None
        r_with_score["fallback_score"] = fallback_score(r)  # 기존 헬퍼
        scored.append(r_with_score)

    # label_means
    label_field = config.get("model_label_field", "label")
    by_label: dict[str, list[float]] = {}
    for r in scored:
        label = r.get(label_field) or r.get("label")
        if label and r["efficiency"] is not None:
            by_label.setdefault(label, []).append(r["efficiency"])
    label_means = {l: sum(vs) / len(vs) if vs else 0 for l, vs in by_label.items()}
    winner = max(label_means, key=label_means.get) if label_means else None

    output = {
        "entrypoint": entrypoint,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "results": scored,
        "label_means": label_means,
        "winner": winner,
        "lex_pass_rate": {
            l: sum(1 for r in scored if (r.get(label_field) or r.get("label")) == l and r["efficiency"] is not None)
                / sum(1 for r in scored if (r.get(label_field) or r.get("label")) == l)
            for l in by_label
        },
    }
    _safe_write(scored_path, output)  # D4 round-trip 의무
    print(f"[Saved] {scored_path}")
    print(f"  winner={winner}, label_means={label_means}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrypoint",
        choices=list(DIMENSION_LOOKUP),
        default="e1",
    )
    args = parser.parse_args()

    if args.entrypoint == "e5":
        from scripts.validation import score_step8_e5
        return score_step8_e5.main()  # delegation 유지

    return _main_unified(args.entrypoint)  # e1/e2/e6 통합
```

### 4.9.4 통합 후 회귀 KPI 검증 (5분)

```bash
# Slice 1 e1 — IDENTICAL 검증
python -m scripts.validation.score_step8 --entrypoint e1
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | diff - /tmp/slice4_step9_baseline_e1.sha256
# 기대: 빈 출력 (hash 동일)

# Slice 3 e2 — IDENTICAL 검증
python -m scripts.validation.score_step8 --entrypoint e2
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | diff - /tmp/slice4_step9_baseline_e2.sha256
# 기대: 빈 출력 (hash 동일)

# Slice 4 e6 — Step 8 산출물 재실행
python -m scripts.validation.score_step8 --entrypoint e6
# 기대: Step 8 종결 시점 결과와 동일 (e6는 임시 _main_e6 → _main_unified로 흡수되어도 산식 동일)

# Slice 2 e5 — delegation 유지 확인
python -m scripts.validation.score_step8 --entrypoint e5
# 기대: 정상 동작 (score_step8_e5.main() 호출)
```

**핵심 KPI**: Slice 1 e1 hash + Slice 3 e2 hash 모두 IDENTICAL. **한 비트라도 변경 시 즉시 git revert + 사용자 에스컬레이션**.

### 4.9.5 단위 테스트 +5~10

`portfolio/tests/test_score_unified.py` 신규 (또는 기존 score 테스트에 추가):

```python
def test_normalize_flat_passthrough():
    """flat 구조는 그대로 반환."""
    from scripts.validation.score_step8 import _normalize_results
    results = [{"label": "haiku", "naturalness": 5, "insight": 4}]
    assert _normalize_results(results, "flat") == results


def test_normalize_nested_to_flat():
    """nested → flat normalize."""
    from scripts.validation.score_step8 import _normalize_results
    nested = [{
        "model_label": "haiku",
        "fixture": "f1",
        "judgments": {"naturalness_manual": 5, "insight_manual": 4, "completeness_auto": True, "schema_pass": True},
        "metadata": {"cost_usd": 0.001, "latency_ms": 5000},
    }]
    flat = _normalize_results(nested, "nested")
    assert flat[0]["label"] == "haiku"
    assert flat[0]["naturalness"] == 5
    assert flat[0]["completeness_auto"] is True


def test_build_lex_filter_no_additional():
    """additional_check 없으면 e1 베이스만 적용."""
    from scripts.validation.score_step8 import _build_lex_filter
    f = _build_lex_filter(None)
    assert f({"naturalness": 5, "insight": 4}) is True
    assert f({"naturalness": 3, "insight": 4}) is False  # e1 베이스 미달


def test_build_lex_filter_with_additional():
    """additional_check가 있으면 추가 검증."""
    from scripts.validation.score_step8 import _build_lex_filter
    f = _build_lex_filter("completeness_auto")
    assert f({"naturalness": 5, "insight": 4, "completeness_auto": True}) is True
    assert f({"naturalness": 5, "insight": 4, "completeness_auto": False}) is False


def test_e5_delegation_preserved():
    """e5는 delegation 유지 (산식 본질 차이)."""
    import subprocess
    # CLI 호출이 score_step8_e5.main()으로 dispatch되는지 검증
    result = subprocess.run(
        ["python", "-m", "scripts.validation.score_step8", "--entrypoint", "e5"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    # delegation은 score_step8_e5의 출력 패턴 포함
    assert "step8_2way_e5_scored" in result.stdout or "Saved" in result.stdout


def test_dimension_lookup_e6_registered():
    """Slice 4 e6 entry 등록 확인."""
    from scripts.validation.score_step8 import DIMENSION_LOOKUP
    assert "e6" in DIMENSION_LOOKUP
    e6 = DIMENSION_LOOKUP["e6"]
    assert e6["dim1"]["key"] == "naturalness"
    assert e6["dim2"]["key"] == "insight"
    assert e6.get("additional_lex_check") == "completeness_auto"
    assert e6["result_structure"] == "nested"
```

### 4.9.6 Step 9 회귀 검증

```bash
pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 기대: 163 → 168~173 passed (+5~10)
```

### 4.9.7 Step 9 완료 보고 형식

```
## Step 9 완료 보고

- 작업: #2 백로그 score 산식 통합 (PS 3.0)
- 통합 범위:
  - e1/e2/e6 → _main_unified() 한 함수
  - e5 → delegation 유지
  - DIMENSION_LOOKUP 메타로 분기 (result_structure / additional_lex_check)
- 회귀 KPI 검증:
  - Slice 1 e1 산출물 hash: <IDENTICAL | 차이 발견 → revert>
  - Slice 3 e2 산출물 hash: <IDENTICAL | 차이 발견 → revert>
  - Slice 4 e6 산출물 동일성: <확인 | 차이 발견>
  - Slice 2 e5 delegation 정상 동작: <확인>
- 단위 테스트 +<5~10>: <목록>
- 회귀: 163 → <168~173> passed
- 코드 변경:
  - score_step8.py 라인 수: 383 → <N> (-<M>줄 또는 +<M>줄)
  - 신규 헬퍼: _normalize_results / _build_lex_filter / _main_unified
- 작업 시간: <분> / 30분 한도 (초과/안전)
```

**시간 한도 초과 시 처리**:
- 30분 안에 통합 미완료 → git stash + 진행분 보존
- Slice 5 백로그에 #2 잔여로 이연
- 부분 완료된 통합 함수는 _main_unified_e1 / _main_unified_e2_e6 식으로 분리 가능

---

## validation_report 작성 (~15분, 0 calls)

### 4.R.1 산출물 — `docs/portfolio/coach/slice4/validation_report_slice4.md`

Slice 3 패턴 mirror — 6 섹션:

```markdown
# Slice 4 (E6 조정 후 비교 해설) Validation Report

> 작성일: 2026-05-07
> 진입점: E6 (조정 후 비교 해설)
> Part 1 종결: 160 passed
> Part 2 종결: <168~172> passed (+<8~12>)
> 누적 LLM 호출 (Slice 4): <18+재시도> / 50
> 누적 비용 (Slice 4): $<X>

## §1 메타데이터
- 진입점 / Default provider / fixture 전략 / 평가 차원 / Step 9 슬롯 / 실행 환경

## §2 Step 6 — Smoke Test
- 결과 / 임계 / 산출물 / fallback 발생 여부

## §3 Step 7 — Token 측정 + Budget 결정
- 7 fixture 실측 / P90 / budget / 사전 추정 정확도

## §4 Step 8 — 2-way 회고
- 14 calls 결과 / lex_pass_rate / label_means / **winner**
- §3.4 그룹 분석 (baseline vs focused × haiku vs sonnet)
- 글쓰기 가설 외삽 검증 (4/4 정착 또는 3/4 재평가)

## §5 누적 비용
- 슬라이스별: Slice 1 $0.137 + Slice 2 $0.19 + Slice 3 $0.10 + **Slice 4 $<X>** = 광의 $<누적>
- 협의 누계: <Slice 4 메인 4스텝 합>
- CostGuard 동작: reset_for_slice("slice4") + record_call 누적 + 한도 초과 발생 여부

## §6 Step 9 — Score 산식 통합 (백로그 #2)
- 통합 범위 / 회귀 KPI (Slice 1·3 IDENTICAL) / 단위 테스트 / 시간 한도 준수

## §7 회귀 카운트 진행
- 160 → <168~172> (+8~12)
- 진입점별 분포: e1=5, e2=31, e5=28, e6=<37+증가>, 기타=<59+증가>

## §8 케이스 발생 여부 (Slice 4 신규 또는 이연)
- Slice 3 9건 백로그 처리 결과
- Slice 4 신규 백로그 항목

## §9 Slice 5+ 진입 결정 자료
- 다음 슬라이스 진입점 후보 (E3 preset 외삽 검증 / E4 대화 Q&A)
- 의존성 / 인프라 준비도 / 예상 매트릭스
```

### 4.R.2 §3.4 그룹 분석 표 (Slice 3 패턴 mirror — 4매트릭스)

| 모델 | 그룹 | n | naturalness_mean | insight_mean | score_mean | cost_total_usd | latency_mean_ms |
|------|------|---|------------------|--------------|------------|----------------|-----------------|
| haiku | e5_baseline | 3 | <X> | <Y> | <Z> | $<C> | <L> |
| haiku | e6_focused | 4 | <X> | <Y> | <Z> | $<C> | <L> |
| sonnet | e5_baseline | 3 | <X> | <Y> | <Z> | $<C> | <L> |
| sonnet | e6_focused | 4 | <X> | <Y> | <Z> | $<C> | <L> |

Δ% 산출 + interpretation (`small_diff` / `focused_higher` / `baseline_higher`).

---

## refactor_backlog 작성 (~10분, 0 calls)

### 4.B.1 산출물 — `docs/portfolio/coach/slice4/refactor_backlog_slice4.md`

Slice 3 패턴 mirror:

```markdown
# Slice 4 Refactor Backlog

> 작성일: 2026-05-07
> 누적 처리율: <Slice 1·2·3·4 합산 완료/이연>

## §1 Slice 4 처리 결과 (Slice 3 9건 + Slice 4 신규)

| # | 항목 | PS | Slice 3 등록 | Slice 4 처리 |
|---|------|-----|-------------|-------------|
| 2 | score 산식 통합 (e1+e2+e6) | 3.0 | 신규 | **Slice 4 Step 9 완료** |
| 5 | TOKEN_BUDGET LLMClient 통합 (잔여) | 2.0 | 부분 | Slice 5 이연 |
| 6 | Step 8 CSV 옵션 | 1.0 | 이연 | Slice 5 이연 |
| 7 | Mock mode dict 매핑 | 1.0 | 이연 | Slice 5 이연 |
| 8 | LLMClient entrypoint 인자 | 2.5 | 이연 | Slice 5 이연 |
| 9 | latency 임계 16,000ms 상향 | 2.0 | 이연 | **Slice 4 Step 6 완료 (e6 한정)** |
| 10 | E2 keyword_match 룰 보완 | 1.5 | 이연 | Slice 5 이연 (E2 한정) |
| 11 | metrics_table 일반화 | 1.5 | 이연 | Slice 5 이연 |

## §2 Slice 4 신규 백로그

| # | 항목 | PS | 트리거 |
|---|------|-----|--------|
| 12 | E6 분석 엔진 재계산 (Phase 2) | 5.0 | D-7 스켈레톤 패턴 회귀 |
| 13 | run_step6_*.py 5종 latency 일괄 16,000ms 상향 | 1.0 | Slice 4 Step 6 e6 한정 적용 후 일관성 |
| 14 | score_step8.py CLI 인자 확장 (--input/--output) | 1.5 | Slice 5+ 진입점 추가 시 |
| <기타> | (Step 6/7/8/9 진행 중 발견 항목) | <PS> | <트리거> |

## §3 Slice 5 진입점 후보 (사전 등록)

| 후보 | 근거 | 의존성 |
|------|------|--------|
| E3 (지표 코멘트 — preset 외삽 검증) | Slice 3 insight 그룹차 0.67~0.83 위험 — Buffett/Defensive preset fixture 추가 검증 | 단독 (낮음) |
| E4 (대화 Q&A Tier 1~3) | Coach 핵심 가치 / Phase 2 product 시연 | Tier 다층 (높음) |

## §4 Slice 5 결정 사항 (Slice 4 종결 시 사전 등록)

(Slice 4 Part 2 종결 후 사용자 결정 추가)
```

---

# §5. 검증 지점

## 5.1 단계별 회귀 카운트 진행 표 (예상)

| 단계 | 추가 테스트 | 누적 | 비고 |
|---|---|---|---|
| Part 1 종결 baseline | — | 160 | |
| Step 6 (smoke 산출물) | 0 | 160 | 산출물만, 단위 테스트 추가 없음 |
| Step 7 (token 측정 + 단위 +3) | +3 | 163 | test_token_budgets 확장 |
| Step 8 (회고 산출물 + e6 entry 임시) | 0 | 163 | 산출물만 |
| Step 9 (#2 통합 + 단위 +5~10) | +5~10 | **168~173** | _main_unified + dispatch 검증 |
| validation_report | 0 | 168~173 | 산출물만 |
| refactor_backlog | 0 | 168~173 | 산출물만 |

**Part 2 종결 예상 회귀: 168~173 passed** (Slice 3 Part 2 +23 보수적 적용 시 +8~12).

## 5.2 검증 판정 표

| # | 검증 항목 | 임계 | 자동/수동 |
|---|---|---|---|
| 1 | Step 6 4 판정 모두 PASS | schema/completeness/cost/latency 모두 True | 자동 |
| 2 | Step 7 budget 1차 추정 정확도 | ±20% 이내 | 자동 |
| 3 | Step 8 lex_pass_rate | 두 모델 중 하나라도 ≥ 50% | 자동 + manual |
| 4 | Step 8 winner 결정 | label_means 차이 ≥ 5% (둘 동률 방지) | 자동 |
| 5 | Step 8 그룹 분석 | 4매트릭스 모두 산출 + interpretation 적용 | 자동 |
| 6 | **Step 9 Slice 1 e1 IDENTICAL** | sha256 hash 동일 | 자동 (KPI) |
| 7 | **Step 9 Slice 3 e2 IDENTICAL** | sha256 hash 동일 | 자동 (KPI) |
| 8 | Step 9 Slice 2 e5 delegation 정상 | exit code 0 | 자동 |
| 9 | Step 9 시간 한도 | ≤ 30분 | 수동 |
| 10 | CostGuard 한도 준수 | call_count ≤ 50 | 자동 |
| 11 | 누적 비용 임계 | Slice 4 총 ≤ $0.20 | 자동 |
| 12 | 모든 산출물 round-trip | _safe_write로 검증 | 자동 |
| 13 | validation_report 6 섹션 작성 | 섹션 수 ≥ 6 | 수동 |
| 14 | refactor_backlog Slice 4 처리 결과 | Slice 3 9건 + Slice 4 신규 처리 추적 | 수동 |

## 5.3 롤백 / 실패 시 처리

**케이스 A. Step 6 schema_pass=False (parse 실패)**:
- raw_content 보존
- 사용자 에스컬레이션 — prompt 재설계 또는 schema 조정 결정 필요
- Step 7+ 진입 보류

**케이스 B. Step 6 latency > 16,000ms**:
- THRESHOLDS 재검토 (또는 sonnet 1회 호출로 재시도)
- 실패 지속 시 사용자 에스컬레이션 — fixture 변경 또는 prompt 단축

**케이스 C. Step 8 도중 호출 마진 부족 (CostGuard remaining < 5)**:
- 남은 호출 단계적 진행 (실패한 호출만 재시도)
- 마진 0 도달 시 Step 8 부분 종결 + 부분 manual 평가 + 부분 winner 판정

**케이스 D. Step 9 Slice 1 또는 Slice 3 IDENTICAL 깨짐**:
- **즉시 git revert** (Step 9 commit 취소)
- 사용자 에스컬레이션 (긴급)
- _main_unified 통합 재설계 또는 Slice 5 백로그로 이연 결정

**케이스 E. Step 9 30분 한도 초과**:
- 진행분 git stash
- 부분 완료된 함수 분리 (_main_unified_e1 / _main_unified_e2_e6)
- Slice 5 백로그 #2 잔여 등록

**케이스 F. Step 8 winner sonnet (글쓰기 가설 3/4 재평가)**:
- 가설 재평가 분석 추가 (validation_report §4에 명시)
- Slice 5에서 추가 글쓰기 진입점으로 5번째 검증 권장
- 이는 작업 차단 조건 아님 — 결과 반영하여 진행

---

# §6. 판단 허용 / 금지 범위 (Claude Code 자율성 경계)

## 6.1 허용 (Claude Code 판단 권한 행사 가능)

| 영역 | 권한 | 사용 시 보고 |
|---|---|---|
| Step 6 prompt 자연어 어조 미세 조정 (build_e6_prompt 사용 — Part 1 산출물 변경 금지) | ❌ | Part 1 commit 후 변경 금지 |
| Step 7 budget 결정 (P90 × 1.5 round-up이 round-up 단위 경계 근처일 때) | ✅ | 결정 근거 명시 |
| Step 8 fixture 호출 순서 (어떤 fixture부터 호출할지) | ✅ | 보고 불요 |
| Step 8 manual 평가 가이드 자연어 표현 | ✅ | 보고 불요 |
| Step 8 fallback 발생 시 결과 처리 (fallback_from 기록만) | ✅ | 보고 불요 |
| Step 9 _main_unified 헬퍼 함수 분리 (`_normalize_results`, `_build_lex_filter` 등) | ✅ | 보고 불요 |
| 단위 테스트 케이스 수 추가 (5~10 범위 내) | ✅ | 보고 불요 |
| validation_report / refactor_backlog 자연어 어조 | ✅ | 보고 불요 |
| 케이스 C·F 발생 시 진행 결정 | ✅ | 보고 필수 |

## 6.2 금지 (사용자 에스컬레이션 필수)

| 영역 | 사유 |
|---|---|
| **Slice 1 또는 Slice 3 step8_*_scored.json 변경 (Step 9 통합 후)** | KPI 위반 — 즉시 revert |
| Slice 2 score_step8_e5.py 변경 | e5 delegation 유지 정책 |
| AnalysisContext / AdjustmentItem schema 변경 | Slice 1/2/3 회귀 위험 |
| LLMClient.complete 시그니처 변경 | 모든 진입점 영향 |
| 기존 5 파일 latency 5,000ms 일괄 변경 | §3.3 비-스코프 |
| score_step8.py CLI 인자 추가 (`--input`/`--output`) | §3.3 비-스코프 |
| Slice 4 Part 1 산출물 (schema/service/view/fixture) 변경 | Part 1 commit 후 IDENTICAL 유지 |
| 회귀 카운트 감소를 일으키는 모든 변경 | baseline 보존 |
| 분석 엔진 재계산 로직 추가 | Phase 2 스코프 |
| `requirements.txt` / `.env` 변경 | 환경 변경 |

## 6.3 균형 모드 명시

본 지시서는 **균형 모드** (Slice 1·2·3·4 Part 1 동일):
- 구조 (디렉토리, 모듈 분리, CLI 인자, 함수 시그니처) = **처방**
- 구현 세부 (변수명, prompt 어조, manual eval guide 자연어, logger 위치) = **위임**

특히 Step 9는 *기존 코드 리팩토링*이므로 처방 비중 ↑ — _main_unified 시그니처 + DIMENSION_LOOKUP 메타 키 + dispatch 패턴 모두 처방.

---

# §7. 산출물

## 7.1 신규 / 수정 파일 목록

| 파일 | 종류 | 줄 수 | Step |
|---|---|---|---|
| `scripts/validation/run_step6_e6_smoke.py` | 신규 | ~150 | Step 6 |
| `docs/portfolio/coach/slice4/step6_smoke_e6_output.json` | 신규 (산출물) | — | Step 6 |
| `scripts/validation/measure_e6_tokens.py` | 신규 | ~120 | Step 7 |
| `portfolio/llm/token_budgets.py` | 수정 (e6 1줄 추가) | +1 | Step 7 |
| `portfolio/tests/test_token_budgets.py` | 수정 (3 테스트 추가) | +30 | Step 7 |
| `docs/portfolio/coach/slice4/step7_e6_tokens.json` | 신규 (산출물) | — | Step 7 |
| `scripts/validation/run_step8_e6_2way.py` | 신규 | ~180 | Step 8 |
| `scripts/validation/analyze_e6_groups.py` | 신규 | ~80 | Step 8 |
| `scripts/validation/score_step8.py` | 수정 (e6 entry + Step 9 통합) | +60 / -100 | Step 8/9 |
| `docs/portfolio/coach/slice4/step8_2way_e6_raw.json` | 신규 (산출물) | — | Step 8 |
| `docs/portfolio/coach/slice4/step8_2way_e6_scored.json` | 신규 (산출물) | — | Step 8 |
| `docs/portfolio/coach/slice4/step8_2way_e6_group_analysis.json` | 신규 (산출물) | — | Step 8 |
| `docs/portfolio/coach/slice4/step8_e6_manual_eval_guide.md` | 신규 | ~50 | Step 8 |
| `portfolio/tests/test_score_unified.py` | 신규 | ~120 | Step 9 |
| `docs/portfolio/coach/slice4/validation_report_slice4.md` | 신규 | ~250 | report |
| `docs/portfolio/coach/slice4/refactor_backlog_slice4.md` | 신규 | ~80 | backlog |

**총 신규 코드: ~720줄, 신규 파일 14개, 수정 파일 3개**.

## 7.2 산출물 검증 명령

Part 2 종결 시점:

```bash
# 1. 회귀 카운트
pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 기대: 168~173 passed

# 2. Slice 4 단독 회귀
pytest portfolio/tests/test_e6_*.py portfolio/tests/test_token_budgets.py portfolio/tests/test_score_unified.py -v
# 기대: 모두 통과

# 3. Slice 1·2·3 회귀 보존
pytest portfolio/tests/test_e1_*.py portfolio/tests/test_e2_*.py portfolio/tests/test_e5_*.py -v
# 기대: 64 passed (5 + 31 + 28)

# 4. Slice 1 IDENTICAL
sha256sum docs/portfolio/coach/slice1/step8_3way_scored.json | diff - /tmp/slice4_step9_baseline_e1.sha256
# 기대: 빈 출력

# 5. Slice 3 IDENTICAL
sha256sum docs/portfolio/coach/slice3/step8_2way_e2_scored.json | diff - /tmp/slice4_step9_baseline_e2.sha256
# 기대: 빈 출력

# 6. e6 entry 정상 동작
python -m scripts.validation.score_step8 --entrypoint e6
# 기대: winner + label_means 출력 + scored.json 갱신

# 7. e5 delegation 정상 동작
python -m scripts.validation.score_step8 --entrypoint e5
# 기대: 정상 동작 (score_step8_e5.main() 호출)

# 8. CostGuard 누적
python -c "from portfolio.llm.cost_guard import CostGuard; import json; print(json.dumps(CostGuard.get_instance().status(), ensure_ascii=False, indent=2))"
# 기대: slice_id="slice4", call_count=<18+>, total_cost_usd=<X>
```

## 7.3 git commit 권장 단위

Part 2 진입 후 6 commit 권장 (Slice 3 Part 2 패턴 mirror):

```
1. feat(portfolio): Slice 4 Part 2 Step 6 — E6 실 haiku 1회 smoke + #9 처리 (e6 한정 16,000ms)
2. feat(portfolio): Slice 4 Part 2 Step 7 — E6 토큰 측정 + budget <X> 결정 + 단위 테스트 +3
3. feat(portfolio): Slice 4 Part 2 Step 8 — E6 2-way 회고 14 calls + 그룹 분석 (winner: <haiku|sonnet>)
4. feat(portfolio): Slice 4 Part 2 Step 9 — score 산식 통합 (#2 PS 3.0, e1/e2/e6 _main_unified)
5. docs(portfolio): Slice 4 종결 — validation_report + refactor_backlog
6. (선택) docs(portfolio): Slice 4 Part 2 — progress 갱신
```

각 commit 메시지에 회귀 before/after 명시.

---

# §8. 완료 보고 포맷

Part 2 종결 시점 사용자에게 다음 형식으로 보고:

```
# Slice 4 Part 2 완료 보고 (Slice 4 종결)

## §A. 환경 정합성
- git branch / status / log
- 회귀: 160 → <168~173> passed (+<8~13>)
- CostGuard 종결 상태: slice_id="slice4", call_count=<X>, total_cost_usd=$<Y>

## §B. Step별 진척
| Step | 산출물 | LLM 호출 | 회귀 변화 | 시간 |
|---|---|---|---|---|
| 6 | smoke + #9 | 1 | 0 | <분> |
| 7 | token + budget + 단위 +3 | 0 | +3 | <분> |
| 8 | 회고 + 그룹 + e6 entry | 14+재시도 | 0 | <분> |
| 9 | #2 통합 + 단위 +<5~10> | 0 | +<5~10> | <분> |
| report + backlog | 산출물 | 0 | 0 | <분> |

## §C. 신규 / 수정 파일
- <14 신규 + 3 수정>

## §D. Step별 핵심 결과

### Step 6
- LLM: latency=<>ms, cost=$<>
- 4 판정: 모두 PASS (또는 실패 항목 명시)
- fallback_from: <None | 명시>

### Step 7
- 7 fixture 실측: P90=<>, mean=<>
- budget 결정: e6=<X> tokens
- 사전 추정 1,000 정확도: ±<N>%

### Step 8
- 14 calls 비용: $<X> (haiku $<Y> + sonnet $<Z>)
- lex_pass_rate: haiku <X>/7, sonnet <Y>/7
- label_means: haiku=<X>, sonnet=<Y>
- **Winner: <haiku | sonnet>**
- 그룹 분석 4매트릭스: <간략 명시>
- 글쓰기 가설 외삽 검증: **<4/4 정착 | 3/4 재평가>**

### Step 9
- 통합 함수: _main_unified (e1/e2/e6) + e5 delegation 유지
- Slice 1 IDENTICAL: <확인 | revert 발생>
- Slice 3 IDENTICAL: <확인 | revert 발생>
- 시간: <분> / 30분 한도

## §E. 케이스 A~F 발생 여부
- A (Step 6 schema 실패): 발생 / 미발생
- B (Step 6 latency 초과): 발생 / 미발생
- C (Step 8 호출 마진 부족): 발생 / 미발생
- D (Step 9 IDENTICAL 깨짐): **반드시 미발생** (발생 시 즉시 revert 했어야 함)
- E (Step 9 30분 한도 초과): 발생 / 미발생
- F (winner sonnet, 가설 재평가): 발생 / 미발생

## §F. 누적 비용
- Slice 1: $0.137 / Slice 2: $0.19 / Slice 3: $0.10 / **Slice 4: $<X>**
- 광의 누적: $<누적합>
- 협의 누적 (메인 4스텝만): $<누적>

## §G. Slice 4 KPI
- [ ] 회귀: <168~173> passed (목표 ±5)
- [ ] LLM 호출 마진: <X>/50 (안전 ≥ 5)
- [ ] Step 9 IDENTICAL 검증: Slice 1 + Slice 3 모두 통과
- [ ] D4 round-trip 위반: 0건
- [ ] 글쓰기 가설 외삽 검증: 4/4 정착 또는 3/4 재평가 명시
- [ ] validation_report 6 섹션 작성
- [ ] refactor_backlog Slice 3 9건 처리 결과 추적
- [ ] CostGuard 누적: slice_id="slice4" + call_count 정상

## §H. Slice 5 진입 결정 자료
- 다음 슬라이스 진입점 후보:
  - E3 (지표 코멘트, preset 외삽 검증) — 사전 등록 (Slice 4 결정 시)
  - E4 (대화 Q&A) — 가장 복잡, Phase 2 product 시연 가치
- 의존성 / 인프라 준비도 / 예상 매트릭스
- 권장: <E3 우선 (insight 차원 외삽 위험 해소) | E4 우선 (product 가치)>

## §I. Slice 5 사전 결정 보존 권장 (slice5_decisions.md)
- Slice 4 종결 시 사용자 결정 항목:
  1. Slice 5 진입점 (E3 / E4 / 기타)
  2. fixture 전략 (E3 채택 시 preset 매트릭스 / E4 채택 시 Tier별 fixture)
  3. Step 9 슬롯 작업 (백로그 #5/#8/#11 중 선택)
```

---

# §9. 변경 이력

## 9.1 본 지시서 변경 이력

| 일자 | 버전 | 변경 사항 |
|---|---|---|
| 2026-05-07 | v1.0 | 초안 작성. Slice 4 Part 2 Step 6~9 + validation_report + refactor_backlog 통합 |

## 9.2 Slice 4 결정 변경 이력 (Part 1 + Part 2 통합)

| 일자 | 결정 | 근거 |
|---|---|---|
| 2026-05-07 (사전) | Slice 4 진입점 = E3 → **E6** (재검토) | 사용자 결정 — E5 흐름 통합 가치 |
| 2026-05-07 | Q1 = 옵션 A' (hybrid 7) | 진입점 변경 자동 변환 |
| 2026-05-07 | Q2 = 옵션 β (#2 score 산식 통합) | 글쓰기 진입점 동일 PS 자동 적용 |
| 2026-05-07 | Slice 5/6 사전 등록 = E3 preset 외삽 검증 | E3 보존 + insight 그룹차 위험 해소 |
| 2026-05-07 (Part 2) | Step 9 통합 범위 = e1/e2/e6 한 _main_unified() + e5 delegation 유지 | sliced4_part2_prep_data §3 e5 산식 본질 차이 |
| 2026-05-07 (Part 2) | #9 latency 처리 = e6 한정 신규 적용 | sliced4_part2_prep_data §6 — 기존 5 파일 baseline 보존 |
| 2026-05-07 (Part 2) | Step 6 fixture = e5_baseline_decrease (1차 smoke) | 가장 단순 baseline (adjustments=1, 333 tokens) |
| 2026-05-07 (Part 2) | e6 budget 1차 후보 = 1,000 tokens | P90=372 × 1.5 = 558 → round-up 500 단위 |

---

# 부록 A — Slice 4 종결 결정 표

| 항목 | 값 (Part 1 시점) | 값 (Part 2 종결 시 갱신) |
|---|---|---|
| 진입점 | E6 (조정 후 비교 해설) | (동일) |
| Default provider | haiku | (Step 8 winner로 검증/갱신) |
| Fixture 전략 | hybrid 7 (e5_baseline 3 + e6_focused 4) | (동일) |
| 평가 차원 | naturalness / insight (manual) + completeness (자동) | (동일) |
| Step 8 매트릭스 | 7×2=14 (haiku 7 + sonnet 7) | (동일) |
| Step 9 슬롯 작업 | #2 score 산식 통합 (e1/e2/e6 _main_unified) | (Part 2 종결 시 완료/이연 명시) |
| Step 8 winner | (Part 2 종결 시 기재) | <haiku | sonnet> |
| fixture 그룹 비교 결과 | (Part 2 종결 시 기재) | <4매트릭스> |
| 글쓰기 가설 외삽 검증 | (Part 2 종결 시 기재) | <4/4 정착 | 3/4 재평가> |
| 누적 호출 (Slice 4) | (Part 2 종결 시 기재) | <X> / 50 |
| 누적 비용 (Slice 4) | (Part 2 종결 시 기재) | $<Y> |
| Slice 5 진입 결정 | Slice 4 종결 회고 시 | (사용자 결정) |

---

# 부록 B — Slice 4 백로그 처리 통합 표

## B.1 Slice 3 9건의 Slice 4 처리 결과

| # | 항목 | PS | Slice 3 등록 | Slice 4 처리 결과 |
|---|------|-----|-------------|---------------------|
| 2 | score 산식 통합 (e1/e2/e6) | 3.0 | 신규 | **Slice 4 Step 9 완료** (e1/e2/e6 _main_unified, e5 delegation 유지) |
| 5 | TOKEN_BUDGET LLMClient 통합 (잔여) | 2.0 | 부분 | Slice 5 이연 |
| 6 | Step 8 CSV 옵션 | 1.0 | 이연 | Slice 5 이연 |
| 7 | Mock mode dict 매핑 | 1.0 | 이연 | Slice 5 이연 |
| 8 | LLMClient entrypoint 인자 | 2.5 | 이연 | Slice 5 이연 |
| 9 | latency 임계 16,000ms 상향 | 2.0 | 이연 | **Slice 4 Step 6 완료 (e6 한정)** + Slice 5 이연 (기존 5 파일) |
| 10 | E2 keyword_match 룰 보완 | 1.5 | 이연 | Slice 5 이연 (E2 한정) |
| 11 | metrics_table 일반화 | 1.5 | 이연 | Slice 5 이연 (E3 진입 시) |

**누적 처리율**:
- Slice 3 신규 9건 중 Slice 4 완료: **2건** (#2, #9 e6 한정)
- Slice 5 이연: 7건

## B.2 Slice 4 신규 백로그

| # | 항목 | PS | 트리거 |
|---|------|-----|--------|
| 12 | E6 분석 엔진 재계산 (Phase 2) | 5.0 | D-7 스켈레톤 패턴 회귀 — 정량 재계산 추가 시 |
| 13 | run_step6_*.py 5종 latency 일괄 16,000ms 상향 | 1.0 | Slice 4 Step 6 e6 한정 적용 후 일관성 |
| 14 | score_step8.py CLI 인자 확장 (`--input`/`--output`) | 1.5 | Slice 5+ 진입점 추가 시 |

---

# 부록 C — 회귀 카운트 진행 표 (Part 1 + Part 2 통합)

| 단계 | 추가 테스트 | 누적 | 비고 |
|---|---|---|---|
| Slice 3 종결 | — | 123 | baseline |
| Slice 4 Part 1 Step 0 | 0 | 123 | reset만 |
| Part 1 Step 1 | +5 | 128 | E6 schema |
| Part 1 Step 2 | 0 | 128 | service |
| Part 1 Step 3 | 0 | 128 | view + url |
| Part 1 Step 4 | +17 | 145 | Mock tests (service 8 + view 9) |
| Part 1 Step 5 | +15 | 160 | hybrid 7 + 단위 +12 |
| **Part 1 종결** | — | **160** | |
| Part 2 Step 6 | 0 | 160 | smoke 산출물 |
| Part 2 Step 7 | +3 | 163 | token_budgets 단위 +3 |
| Part 2 Step 8 | 0 | 163 | 회고 산출물 + e6 entry |
| Part 2 Step 9 | +5~10 | **168~173** | _main_unified + dispatch 단위 |
| **Slice 4 종결 예상** | — | **168~173** | (Slice 1·2·3·4 누적 +45~50) |

---

# 부록 D — 분석 엔진 의존성 회피 일관 적용 (Part 1 → Part 2)

Slice 4 핵심 설계 결정인 분석 엔진 의존성 회피는 Part 1·Part 2 모두 일관 적용:

| 항목 | Part 1 | Part 2 |
|---|---|---|
| E6 schema (Request/Response) | analysis_context + adjustments + user_intent (정량 재계산 입력 없음) | (동일 유지) |
| build_e6_prompt | 원본 holdings + adjustments → LLM 자연어 추론 위임 | (동일 유지) |
| Mock 응답 (`_mock_text_e6`) | 자연어 비교 해설만 | Step 6/8에서 그대로 활용 |
| fixture (`sample_comparison_context.py`) | 7개 모두 원본 + adjustments 형태 (조정 후 상태 미산출) | Step 8에서 그대로 활용 |
| Step 6/8 LLM 호출 | (Part 1에는 없음) | LLM이 자연어 비교만 — 수치 검증 없음 |
| score_step8.py e6 entry | (Part 1에는 없음) | naturalness + insight + completeness 만 평가 (정량 차원 미사용) |
| validation_report | (Part 1에는 없음) | §4 회고에서도 정량 비교 분석 없음, 자연어 평가만 |

Phase 2 분석 엔진 슬라이스 추가 시:
- E6Request에 `adjusted_context: dict` 필드 추가 (선택)
- D-7 스켈레톤 (`build_e6_input(original, adjusted, overrides)`) 패턴 회귀 검토
- score 차원에 정량 변화 측정 추가 (예: risk_score_delta, return_score_delta)

---

# 부록 E — Slice 1·2·3·4 패턴 mirror 비율 (Part 1 + Part 2 종합)

| 항목 | mirror 대상 | 비율 |
|---|---|---|
| Schema 추가 위치 | Slice 1·2·3 동일 | 100% |
| Service 인터페이스 (run_*, build_*_prompt, parse_*) | Slice 3 E2 | 100% |
| View 인터페이스 (csrf_exempt + POST + JSON 응답 + 429 매핑) | Slice 1·2·3 동일 | 100% |
| Hybrid fixture (baseline + focused) | Slice 3 E2 | 100% (3 + 4 비율) |
| Step 6 smoke 패턴 (`_json_default` + `_safe_write`) | Slice 3 E2 | 100% |
| Step 7 token 측정 (count_tokens API + P90 × 1.5) | Slice 3 E2 | 100% |
| Step 8 회고 매트릭스 (7×2 = 14 calls + Gemini 제외) | Slice 3 E2 | 100% |
| Step 8 그룹 분석 (4매트릭스 + interpretation_guide) | Slice 3 E2 | 100% |
| Step 9 score 산식 통합 (#2 백로그) | Slice 2 Step 9 패턴 | 100% (e5 delegation 유지) |
| validation_report 6 섹션 | Slice 3 | 100% |
| refactor_backlog 형식 | Slice 3 | 100% |

전체 mirror 비율: **~100%** (구조 모든 영역). 자연어 / 결정 근거 / Step 6/8 LLM 응답만 위임 영역.

---

# 부록 F — Slice 5 진입 결정 사전 안내 (Slice 4 종결 시 입력)

Slice 4 종결 시 사용자 결정 자료로 사용:

## F.1 Slice 5 진입점 후보 비교

| 후보 | 사전 등록 근거 | 의존성 | 인지부하 |
|---|---|---|---|
| **E3 (지표 코멘트, preset 외삽 검증)** | Slice 3 insight 차원 그룹차 0.67~0.83 위험 — Buffett/Defensive preset fixture 추가 검증 필요. Slice 4 결정 시 사전 등록 | 단독 (낮음) | 낮음 (글쓰기 가설 5번째 검증) |
| **E4 (대화 Q&A Tier 1~3)** | Coach 핵심 가치 — Phase 2 product 시연. 대화 컨텍스트 처리 신규 인프라 필요 | Tier 다층 (높음) | 매우 높음 |

## F.2 Slice 5 진입점 결정 시 고려 사항

- **글쓰기 가설 4번째 외삽 검증 결과** (Step 8 winner)에 따라 E3 진입 가치 변동
- 4/4 정착 → E3 진입 안전 (preset 외삽만 검증)
- 3/4 재평가 → E3가 5번째 검증 + preset 외삽 동시 (스코프 ↑)
- E4 진입 시 Tier별 fixture 신규 인프라 필요 — 한 슬라이스에서 처리 가능한지 검토 필요

## F.3 Slice 5 Step 9 슬롯 후보

Slice 4에서 이연된 7건 중 PS 순:
- #5 TOKEN_BUDGET LLMClient 통합 (PS 2.0)
- #8 LLMClient entrypoint 인자 (PS 2.5)
- #11 metrics_table 일반화 (PS 1.5) — E3 진입 시 자연 흡수 가능
- #14 score_step8.py CLI 인자 확장 (PS 1.5)
- #13 latency 일괄 상향 (PS 1.0)
- #6 Step 8 CSV 옵션 (PS 1.0)
- #7 Mock mode dict 매핑 (PS 1.0)

## F.4 권장 사전 결정 (Slice 4 종결 시 보존)

```markdown
# slice5_decisions.md
> 작성일: (Slice 4 종결 시점)

## 진입점 결정
- 1순위 후보: <E3 | E4>
- 근거: <Slice 4 winner / Phase 2 가치 / 인지부하>

## 진입점별 사전 결정
- E3 채택 시:
  - 매트릭스: 다른 11 preset (Buffett / Defensive 등) × Core/Supporting/Context 일부
  - fixture 전략: preset별 baseline 1 + focused 1 = 2 × N preset
  - Step 9 슬롯: #11 metrics_table 일반화 자연 흡수
- E4 채택 시:
  - Tier 1~3 fixture 신규 인프라
  - default provider: Tier별 다름 (Tier 1 추출=sonnet, Tier 2~3 글쓰기=haiku)
  - Step 9 슬롯: #5 또는 #8

## 누적 결정 (Slice 1~4 보존)
- (Slice 1~4 결정 표 통합 — slice4_decisions.md 누적 결정 표 그대로)
```