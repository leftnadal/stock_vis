# Slice 2 — Part 1 작업 지시서 v2 (Step 0~5)

> 작성일: 2026-04-29 (v1 재검증 결과 반영)
> 대상: Stock-Vis Portfolio Coach 슬라이스 2 전반부
> 진입점: **E5 (조정 파싱, 자연어 → override JSON, D-6 정의)**
> 전제: Slice 1 (E1+GARP) 완료, 회귀 37/37, primary provider=haiku 확정
> 브랜치: portfolio
> 누적 LLM 호출: 10 / 50 (Slice 1 종료 시점)

---

## v1 → v2 변경 요지

본 v2는 v1 재검증 보고서의 권고를 **모두 적용**한 통합본이다. 변경 사항:

| 항목   | v1 → v2                                                                                                   |
| ------ | --------------------------------------------------------------------------------------------------------- |
| **C1** | Step 0 진단 #4 sleep 1초 → 0.5초 (한도 30분 충족)                                                         |
| **C2** | Step 4 `test_e5_view_timeout_first_fallback` 본문 작성 (pass 제거)                                        |
| **C3** | COMMANDS dict에 `"large_multi"` 키 추가 (ALL_FIXTURES와 일치)                                             |
| **I1** | `ambiguous` fixture 의미 단순화 — `no_actionable_intent=True`로 변경 + `unclear_amount` 보조 fixture 신설 |
| **I2** | AdjustmentItem `@model_validator` 추가 (action ↔ delta_weight 일관성)                                     |
| **I3** | E5Response `@model_validator` 추가 (no_actionable_intent ↔ adjustments 일관성)                            |
| **I4** | analysis_context 포함 유지 + Step 7 토큰 모니터링 계획 명시                                               |
| **I5** | services 모듈 module-level import + 패치 타겟 변경 (Slice 1 E1 함께 정리)                                 |
| **M2** | `portfolio/llm/mocks.py` 존재 검증 단계 추가 (Step 4 진입 전)                                             |
| **M3** | `parsed_obj` 미사용 변수 제거 (Step 0.5)                                                                  |

테스트 카운트 재계산: 37 baseline + (Step 1 +6 / Step 2 +5 / Step 3 +3 / Step 4 +4 / Step 5 +13) + (I5 Slice 1 E1 패치 정리 시 추가 회귀 0) = **68 passed**.

추가 작업 시간: 약 **52분** (Step 0의 30분 한도와는 별도).

---

## 정정 사항 (반드시 인지)

**E5는 Watchlist가 아닌 조정 파싱 진입점**이다. 이전 메모에서 일부 혼선이 있었으나 정확한 정의는 다음과 같다:

| 진입점 | 작업                                 | 산출물             |
| ------ | ------------------------------------ | ------------------ |
| E1     | 한 줄 진단 (자연어 글쓰기)           | D-2 — Slice 1 완료 |
| E2     | 진단 카드 4요소                      | D-3                |
| E3     | 지표 코멘트                          | D-4                |
| E4     | 대화 Q&A (Tier 1~3 전체)             | D-5, 최복잡        |
| **E5** | **조정 파싱 (자연어 → 구조화 JSON)** | **D-6**            |
| E6     | 조정 후 비교 해설                    | D-7                |
| (E11)  | Watchlist 제안                       | Phase 2 신설       |

E5의 본질은 사용자 자연어 명령(예: "TSLA 비중 좀 줄이고 NVDA 늘려줘")을 받아 구조화된 override JSON으로 변환하는 **추출 작업**이다. 이는 E1과 LLM 사용 패턴이 다르다 — E1은 글쓰기, E5는 정확한 추출. 이 차이가 평가 산식과 fixture 구조에 반영된다.

---

## 0. 사전 검증

### 0.1 Slice 1 완료 확인

```bash
git rev-parse --abbrev-ref HEAD
# 예상: portfolio

pytest portfolio/tests/ -q
# 예상: 37 passed (Slice 1 종료 baseline)

ls docs/portfolio/coach/
# 예상 (5건): step6_smoke_output.json, step8_3way_raw.json,
#            step8_3way_scored.json, validation_report_slice1.md, refactor_backlog_slice1.md
```

위 셋이 모두 통과하지 않으면 Slice 1로 되돌아가 회귀 원인 해결 후 진입.

### 0.2 결정 사항 (Slice 1 회고 + 본 슬라이스 신규)

| Q                              | 결정                                                             | 근거                                                                     |
| ------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Slice 2 범위                   | E5 단독 (Slice 1 패턴 mirror)                                    | 진입점 패턴 일반화 검증 + 변수 최소화                                    |
| LLM primary                    | **haiku** (Slice 1 winner, label_means 33.68)                    | sonnet 13.89 / gemini 13.38. 효율 점수 분모 효과 우세하나 절대 품질 충분 |
| 잔존 부채 처리                 | Step 0 (Gemini 진단 30분) + Step 0.5 (step6 reparse 5분)         | 다음 슬라이스로 무한 누적 방지                                           |
| 평가 차원                      | schema(binary) + 의도매칭(1~5) + 추가변경없음(1~5) + 비용 + 지연 | E5는 추출 작업, 자연스러움/통찰성 부적합                                 |
| 평가 산식                      | Lexicographic + 효율 + B fallback (Slice 1 산식 라벨만 변경)     | Slice 1 검증 패턴 보존                                                   |
| docs 경로                      | `docs/portfolio/coach/` (사용자 정책)                            | Slice 1 Part 2부터 적용 정책 유지                                        |
| **schema 검증 깊이 (v2 신규)** | **명확한 모순만 거름 (action↔delta, intent↔adjustments)**        | LLM 자유도와 schema 의미 균형                                            |
| **mock 패치 패턴 (v2 신규)**   | **module-level import + 패치 타겟을 services 모듈로**            | pytest best practice. 미래 자기 보호                                     |

### 0.3 비용 가드 예산 분배 (총 50회 한도)

| Step                        | 호출 수       | 누적  | 안전 마진 |
| --------------------------- | ------------- | ----- | --------- |
| Slice 1 종료                | —             | 10    | 40        |
| Step 0 (Gemini 진단)        | 1~3           | 11~13 | 37~39     |
| Step 0.5 (reparse)          | 0             | 11~13 | 37~39     |
| Step 1~5 (Mock fixture까지) | 0             | 11~13 | 37~39     |
| Step 6 (실제 1회)           | 1             | 12~14 | 36~38     |
| Step 8 (3-way 회고)         | 9 + 재시도 ~3 | 21~26 | 24~29     |
| 회귀/디버깅 예비            | 0~5           | 21~31 | 19~29     |

최대 31/50 (62%) 점유 예상. **Slice 3 진입 시 비용 가드 reset 검토 필요** (env 분리 또는 카운터 초기화 — 현 시점은 결정 보류, Slice 2 종료 회고 시 결정).

### 0.4 환경 사전 검증

```bash
# .env 키 활성 (gemini 진단 대상 포함)
python -c "from django.conf import settings; \
  print('GEMINI:', bool(settings.GEMINI_API_KEY)); \
  print('ANTHROPIC:', bool(settings.ANTHROPIC_API_KEY))"
# 예상: 둘 다 True

# Slice 1 산출물 무결성
python -c "import json; \
  d=json.load(open('docs/portfolio/coach/step8_3way_scored.json')); \
  print('winner:', d.get('winner')); \
  print('use_fallback:', d.get('use_fallback'))"
# 예상: winner=haiku, use_fallback=False

# v2 신규: portfolio/llm/mocks.py 존재 검증 (M2 대응)
ls portfolio/llm/mocks.py && echo "OK" || echo "MISSING — Step 4 진입 전 신설 필요"
```

`portfolio/llm/mocks.py`가 없으면 Step 4 진입 전 신설. 신설 가이드는 Step 4의 사전 조건 섹션 참고.

---

# Step 0 — Gemini API 진단 (30분 한도, 엄격, v2 갱신)

## 0.1 목표

Slice 1에서 9/9 폴백된 Gemini API 호출 실패 원인을 30분 한도 안에서 진단한다. **30분 초과 시 진단 중단, sonnet+haiku 2-way로 Slice 2 진행 + 진단 사항을 Slice 3 Step 0 백로그로 이관**. 무한루프 절대 금지.

## 0.2 진단 절차 (퀀트 공학 우선순위, v2 시간 재배분)

가능한 원인을 발생 빈도(prior probability) × 진단 비용 역수 순으로 정렬. 우선순위 높은 것부터 5분씩 진단:

| #   | 원인 가설                                                            | 사전 확률 (휴리스틱) | 진단 시간    | 우선순위 점수   |
| --- | -------------------------------------------------------------------- | -------------------- | ------------ | --------------- |
| 1   | 모델 ID 잘못됨 (gemini-2.0-flash-exp가 deprecate 되었거나 권한 없음) | 0.40                 | 5분          | 0.40 / 5 = 0.08 |
| 2   | API key 권한 부족 또는 만료                                          | 0.25                 | 5분          | 0.05            |
| 3   | SDK 버전 mismatch                                                    | 0.15                 | 5분          | 0.03            |
| 4   | rate limit 또는 quota 초과                                           | 0.10                 | **5분 (v2)** | 0.02            |
| 5   | 프롬프트 자체 거부 (safety filter)                                   | 0.05                 | 5분          | 0.01            |
| 6   | 네트워크/방화벽                                                      | 0.05                 | 5분          | 0.01            |

**v2 변경**: 진단 #4 sleep을 1초→0.5초로 단축, 5분 한도 안에서 처리. 합계 5×6=30분 한도 정확히 충족.

## 0.3 작업 단계

### 0.3.1 진단 스크립트 신설 (5분)

`scripts/validation/diagnose_gemini.py` 신설:

```python
"""
Gemini API 진단. 30분 한도 안에서 우선순위 6개 원인을 순차 검증.

각 검증 5분 한도. 결과를 docs/portfolio/coach/gemini_diagnosis.md에 기록.

Usage:
    python -m scripts.validation.diagnose_gemini
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockvis.settings")
django.setup()

from django.conf import settings


def diagnostic_1_model_id() -> dict:
    """모델 ID gemini-2.0-flash-exp가 활성인지 검증."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    try:
        models = list(genai.list_models())
        flash_exp = [m for m in models if "flash-exp" in m.name or "flash" in m.name]
        return {
            "diagnostic": "model_id",
            "result": "PASS" if flash_exp else "FAIL",
            "available_flash_models": [m.name for m in flash_exp[:5]],
            "total_models": len(models),
            "note": "현재 사용 중 gemini-2.0-flash-exp가 위 목록에 있는지 확인.",
        }
    except Exception as e:
        return {"diagnostic": "model_id", "result": "ERROR", "error": str(e)}


def diagnostic_2_api_key() -> dict:
    """API key 권한 (간단한 generateContent 호출)."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        t0 = time.monotonic()
        resp = model.generate_content("Say OK in one word.")
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "diagnostic": "api_key",
            "result": "PASS",
            "response_text": resp.text[:50] if resp and resp.text else None,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return {
            "diagnostic": "api_key",
            "result": "FAIL",
            "error_type": type(e).__name__,
            "error": str(e)[:300],
        }


def diagnostic_3_sdk_version() -> dict:
    """SDK 버전 확인."""
    import google.generativeai as genai

    return {
        "diagnostic": "sdk_version",
        "result": "INFO",
        "google_generativeai_version": getattr(genai, "__version__", "unknown"),
        "expected_min": "0.8.0",
        "note": "버전이 0.8.0 미만이면 model 호환성 의심.",
    }


def diagnostic_4_rate_limit() -> dict:
    """초당 0.5초 간격 5번 호출. rate limit 거부율 측정. (v2: sleep 1.0 → 0.5)"""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    failures = 0
    for i in range(5):
        try:
            model.generate_content("Say OK.")
        except Exception as e:
            if "rate" in str(e).lower() or "quota" in str(e).lower():
                failures += 1
        time.sleep(0.5)  # v2 변경: 1.0 → 0.5
    return {
        "diagnostic": "rate_limit",
        "result": "PASS" if failures == 0 else "WARN",
        "rate_limit_failures": f"{failures}/5",
    }


def diagnostic_5_prompt_safety() -> dict:
    """Slice 1에서 사용된 실제 프롬프트로 호출 — safety filter 확인."""
    import google.generativeai as genai

    from portfolio.services.e1_garp import build_e1_garp_prompt
    from portfolio.tests.fixtures.sample_analysis_context import (
        get_context_garp_tech,
    )

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    prompt = build_e1_garp_prompt(get_context_garp_tech())
    try:
        resp = model.generate_content(prompt)
        return {
            "diagnostic": "prompt_safety",
            "result": "PASS",
            "response_length": len(resp.text) if resp.text else 0,
            "finish_reason": str(resp.candidates[0].finish_reason)
            if resp.candidates
            else None,
        }
    except Exception as e:
        return {
            "diagnostic": "prompt_safety",
            "result": "FAIL",
            "error_type": type(e).__name__,
            "error": str(e)[:300],
        }


def diagnostic_6_network() -> dict:
    """네트워크 진단 (curl + python requests)."""
    import socket

    try:
        socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=5)
        return {"diagnostic": "network", "result": "PASS"}
    except Exception as e:
        return {
            "diagnostic": "network",
            "result": "FAIL",
            "error": str(e),
        }


DIAGNOSTICS = [
    diagnostic_1_model_id,
    diagnostic_2_api_key,
    diagnostic_3_sdk_version,
    diagnostic_4_rate_limit,
    diagnostic_5_prompt_safety,
    diagnostic_6_network,
]


def main() -> int:
    print("=" * 60)
    print("Gemini API Diagnosis — Slice 2 Step 0 (v2)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("Time budget: 30 min hard limit (6 × 5min)")
    print("=" * 60)

    t_start = time.monotonic()
    results = []
    for fn in DIAGNOSTICS:
        elapsed_min = (time.monotonic() - t_start) / 60
        if elapsed_min > 30:
            print(f"\n[BUDGET EXCEEDED] {elapsed_min:.1f} min. 진단 중단.")
            results.append({"diagnostic": fn.__name__, "result": "SKIPPED_BUDGET"})
            break
        print(f"\n[{fn.__name__}] (elapsed {elapsed_min:.1f}min)")
        try:
            r = fn()
        except Exception as e:
            r = {"diagnostic": fn.__name__, "result": "EXCEPTION", "error": str(e)}
        results.append(r)
        for k, v in r.items():
            print(f"  {k}: {v}")

    output_path = Path("docs/portfolio/coach/gemini_diagnosis.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Gemini API Diagnosis — Slice 2 Step 0 (v2)",
        "",
        f"- 실행 시점: {datetime.now(timezone.utc).isoformat()}",
        f"- 총 소요: {(time.monotonic() - t_start) / 60:.1f}분 / 30분 한도",
        "",
        "## Results",
        "",
    ]
    for r in results:
        lines.append(f"### {r.get('diagnostic')}")
        for k, v in r.items():
            if k == "diagnostic":
                continue
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines += [
        "## Conclusion (수동 작성)",
        "",
        "- 식별된 원인: ...",
        "- 적용한 수정: ...",
        "- 미해결 원인 (Slice 3 이관 시): ...",
        "- 결정: PASS (Gemini 정상화) / WAIT (sonnet+haiku 2-way로 Slice 2 진행) / ESCALATE",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[Saved] {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 0.3.2 진단 실행 (15~30분)

```bash
python -m scripts.validation.diagnose_gemini
```

### 0.3.3 수동 결론 (5분)

`docs/portfolio/coach/gemini_diagnosis.md`의 "Conclusion" 섹션을 직접 작성:

- 식별된 원인 (예: "diagnostic_1에서 gemini-2.0-flash-exp가 list에 없음 — 모델 deprecate 가능성")
- 적용한 수정 (예: "client.py의 GEMINI_MODEL을 'gemini-2.0-flash'로 변경")
- 결정:
  - **PASS**: Gemini 정상화. Slice 2 Step 8을 3-way로 진행.
  - **WAIT**: 30분 안에 미해결. Slice 2를 sonnet+haiku 2-way로 진행 + Slice 3 Step 0으로 이관.
  - **ESCALATE**: 30분 초과인데 패턴 식별이 됐고 추가 30분으로 해결 가능 — 본인 판단.

## 0.4 검증 판정

| #   | 판정                                   | 임계                                   | 자동/수동 |
| --- | -------------------------------------- | -------------------------------------- | --------- |
| 1   | 진단 스크립트 6개 모두 실행            | 6/6 또는 BUDGET_EXCEEDED 명시          | 자동      |
| 2   | 30분 시간 한도 준수                    | 실제 ≤ 32분 (2분 tolerance, v2 재조정) | 수동      |
| 3   | gemini_diagnosis.md Conclusion 작성    | 식별 원인 + 결정 PASS/WAIT/ESCALATE    | 수동      |
| 4   | LLMClient 코드 변경 (있다면) 회귀 통과 | 37 passed 유지                         | 자동      |

## 0.5 롤백 / 실패 시 처리

(v1과 동일 — 케이스 A~E)

## 0.6 산출물

- `scripts/validation/diagnose_gemini.py` (신규, ~150줄)
- `docs/portfolio/coach/gemini_diagnosis.md` (실행 산출물 + 수동 결론)
- `portfolio/llm/client.py` (필요 시 수정 — 모델 ID, SDK 호출 방식 등)

## 0.7 비용 가드

- LLM 호출: 1~3회 (진단 2/4/5에서 발생)
- 누적: 11~13 / 50

---

# Step 0.5 — step6_smoke_output.json reparse (5분, 호출 0, v2 정리)

## 0.5.1 목표

Slice 1 Step 6의 산출물 `step6_smoke_output.json`이 raw 시점 상태(schema_pass=False, cost_pass=False, naturalness=null)로 보존되어 외관상 FAIL이 잔존하는 부채를 해결한다. **신규 LLM 호출 없이** 기존 raw_content를 새 parser(parsers.py)와 새 임계($0.020)로 재처리.

## 0.5.2 작업 단계

### 0.5.2.1 reparse 스크립트 신설 (v2: 미사용 변수 제거 — M3)

`scripts/validation/reparse_step6.py` 신설:

```python
"""
Step 6 산출물 재처리 (LLM 호출 없음).

Slice 1 종결 commit에서 도입된 parsers.py와 갱신 임계($0.020)를 적용해
docs/portfolio/coach/step6_smoke_output.json의 judgments를 갱신.

Naturalness는 사용자 수동 평가 결과를 별도 입력 받음.

Usage:
    python -m scripts.validation.reparse_step6 [--naturalness 4]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockvis.settings")
django.setup()

NEW_THRESHOLDS = {
    "cost_usd_max": 0.020,  # Slice 1 회고에서 갱신
    "latency_ms_max": 5000,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--naturalness", type=int, default=None,
                        help="사용자 수동 평가 (1~5). 미입력 시 기존 값 보존.")
    args = parser.parse_args()

    target = Path("docs/portfolio/coach/step6_smoke_output.json")
    if not target.exists():
        print(f"[ERROR] {target} 없음.")
        return 1

    data = json.loads(target.read_text(encoding="utf-8"))

    # parsers.py로 재파싱 (v2 정리: 미사용 parsed_obj 제거)
    raw_content = data.get("raw_content", "")
    try:
        from portfolio.services.e1_garp import parse_e1_response
        parsed = parse_e1_response(raw_content)  # 내부에서 parse_json_response 호출
        schema_pass = True
        schema_error = None
    except Exception as e:
        parsed = None
        schema_pass = False
        schema_error = f"{type(e).__name__}: {str(e)[:200]}"

    # 새 임계 적용
    cost_usd = data["metadata"]["cost_usd"]
    latency_ms = data["metadata"]["latency_ms"]
    cost_pass = cost_usd <= NEW_THRESHOLDS["cost_usd_max"]
    latency_pass = latency_ms <= NEW_THRESHOLDS["latency_ms_max"]

    # naturalness 처리
    if args.naturalness is not None:
        naturalness = args.naturalness
    else:
        naturalness = data["judgments"].get("naturalness")

    data["judgments"] = {
        "schema_pass": schema_pass,
        "schema_error": schema_error,
        "cost_pass": cost_pass,
        "latency_pass": latency_pass,
        "naturalness": naturalness,
    }
    data["thresholds"] = NEW_THRESHOLDS
    data["reparse_metadata"] = {
        "reparsed_at": datetime.now(timezone.utc).isoformat(),
        "previous_thresholds_cost": 0.001,
        "current_thresholds_cost": NEW_THRESHOLDS["cost_usd_max"],
        "parser_version": "parsers.py (Slice 1 종결 commit)",
        "note": "raw_content는 변경되지 않음. judgments만 갱신.",
    }
    if parsed:
        data["parsed"] = parsed.model_dump()

    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {target} 재처리 완료")
    print(f"  schema_pass: {schema_pass}")
    print(f"  cost_pass:   {cost_pass} (${cost_usd:.5f} / ${NEW_THRESHOLDS['cost_usd_max']:.4f})")
    print(f"  latency_pass: {latency_pass}")
    print(f"  naturalness: {naturalness}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 0.5.2.2 실행

```bash
# Slice 1 시점에 평가한 naturalness 점수가 기억나면 그 값으로:
python -m scripts.validation.reparse_step6 --naturalness 4

# 기억 안 나면 인자 없이 실행 (기존 null 값 보존, 별도 평가):
python -m scripts.validation.reparse_step6
```

평가 안 된 상태라면 `raw_content` 또는 `parsed`를 보고 1~5 평가 후 인자 추가 재실행.

## 0.5.3 검증 판정

| #   | 판정                                | 임계                 | 자동 |
| --- | ----------------------------------- | -------------------- | ---- |
| 1   | step6_smoke_output.json schema_pass | true                 | 자동 |
| 2   | cost_pass                           | true (임계 $0.020)   | 자동 |
| 3   | naturalness                         | 정수 1~5 (null 아님) | 수동 |
| 4   | reparse_metadata 필드 추가          | 존재                 | 자동 |

## 0.5.4 비용 가드

- LLM 호출: 0회
- 누적: 11~13 / 50 (Step 0 누적 그대로)

---

# Step 1 — E5 Pydantic 스키마 (D-0b 재사용 + I2/I3 validator)

## 1.1 목표

E5 진입점의 입력/출력 Pydantic 스키마를 신설한다. **v2 변경**: I2 (AdjustmentItem 교차 필드 검증) + I3 (E5Response 일관성 검증) 적용.

## 1.2 사전 조건

D-0b 산출물 `portfolio/schemas/` 폴더 검토:

```bash
ls portfolio/schemas/
grep -nE "(Adjustment|Override|Parse)" portfolio/schemas/*.py | head -20
```

**케이스 A**: D-0b에 E5 관련 스키마가 이미 있음 → import해서 재사용. validator는 본 Step에서 추가.
**케이스 B**: D-0b가 E1만 정의됐고 E5는 미정의 → 본 Step에서 신설 + validator 함께.

본 지시서는 **케이스 B 가정**.

## 1.3 작업 단계

### 1.3.1 Pydantic 스키마 정의 (v2: model_validator 추가)

`portfolio/schemas/llm.py`에 추가 (또는 `portfolio/schemas/adjustment.py` 신설):

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class AdjustmentItem(BaseModel):
    """단일 종목 조정. delta_weight는 음수(축소) / 양수(확대) / 0(정보용)."""
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=10)
    action: Literal["increase", "decrease", "remove", "add", "info_only"]
    delta_weight: Optional[float] = Field(
        None, ge=-1.0, le=1.0,
        description="포트폴리오 비중 변화량 (-1.0 ~ +1.0). action=info_only 시 None.",
    )
    target_weight: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="명시적 목표 비중. delta_weight과 동시 지정 가능.",
    )
    reason_quote: str = Field(
        ..., max_length=300,
        description="사용자 자연어 명령에서 이 조정을 추출한 근거 부분 인용. 추측 금지.",
    )

    @model_validator(mode="after")
    def check_action_consistency(self):
        """v2 신규 (I2): action ↔ delta_weight 명확한 모순 거름.

        룰:
        - decrease: delta_weight is None or <= 0
        - increase: delta_weight is None or >= 0
        - remove: target_weight is None or 0
        - info_only: delta_weight in (None, 0) and target_weight in (None,)
        """
        if self.action == "decrease" and self.delta_weight is not None and self.delta_weight > 0:
            raise ValueError("decrease action requires delta_weight <= 0")
        if self.action == "increase" and self.delta_weight is not None and self.delta_weight < 0:
            raise ValueError("increase action requires delta_weight >= 0")
        if self.action == "remove" and self.target_weight not in (None, 0.0):
            raise ValueError("remove action requires target_weight None or 0")
        if self.action == "info_only":
            if self.delta_weight not in (None, 0.0):
                raise ValueError("info_only action requires no delta_weight change")
            if self.target_weight is not None:
                raise ValueError("info_only action requires no target_weight")
        return self


class E5Response(BaseModel):
    """조정 파싱 응답. LLM이 사용자 자연어 → 구조화 override로 변환."""
    model_config = ConfigDict(extra="forbid")

    adjustments: list[AdjustmentItem] = Field(default_factory=list)
    confidence: int = Field(..., ge=1, le=5,
                             description="LLM이 자연어 의도를 얼마나 확실히 파악했는지.")
    ambiguity_notes: Optional[str] = Field(
        None, max_length=500,
        description="명령이 모호한 경우 다중 해석 메모. 명령이 명확하면 None.",
    )
    no_actionable_intent: bool = Field(
        False,
        description="자연어 명령이 조정 의도가 아닌 경우(질문/잡담) True.",
    )

    @model_validator(mode="after")
    def check_intent_consistency(self):
        """v2 신규 (I3): no_actionable_intent ↔ adjustments 일관성.

        명확한 모순만 거름:
        - no_actionable_intent=True인데 adjustments 비어있지 않음 → 거절
        confidence ↔ ambiguity_notes 관계는 LLM 자율 판단에 맡김
        (부분 명확/부분 모호 가능).
        """
        if self.no_actionable_intent and self.adjustments:
            raise ValueError(
                "no_actionable_intent=True but adjustments non-empty"
            )
        return self


class E5Request(BaseModel):
    """조정 파싱 요청 컨텍스트."""
    model_config = ConfigDict(extra="forbid")

    analysis_context: dict  # AnalysisContext (Tier 0~3)
    user_command: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
```

### 1.3.2 import 경로 통합

`portfolio/schemas/__init__.py`에 export 추가:

```python
from portfolio.schemas.llm import (
    LLMResponse,  # Slice 1
    E5Request,
    E5Response,
    AdjustmentItem,
)
```

### 1.3.3 단위 테스트 추가 (v2: validator 테스트 +2개)

`portfolio/tests/test_schemas.py`에 추가:

```python
import pytest
from pydantic import ValidationError
from portfolio.schemas.llm import AdjustmentItem, E5Response


def test_adjustment_item_valid():
    item = AdjustmentItem(
        ticker="TSLA",
        action="decrease",
        delta_weight=-0.05,
        reason_quote="TSLA 비중 좀 줄여줘",
    )
    assert item.delta_weight == -0.05


def test_adjustment_item_extra_field_rejected():
    with pytest.raises(ValidationError):
        AdjustmentItem(
            ticker="TSLA",
            action="decrease",
            reason_quote="...",
            extra_field="should_be_rejected",  # extra=forbid
        )


def test_adjustment_item_delta_out_of_range():
    with pytest.raises(ValidationError):
        AdjustmentItem(
            ticker="TSLA",
            action="decrease",
            delta_weight=-1.5,  # < -1.0
            reason_quote="...",
        )


# v2 신규 (I2 검증)
def test_adjustment_item_decrease_with_positive_delta_rejected():
    """decrease + 양수 delta_weight는 의미 모순 → 거절."""
    with pytest.raises(ValidationError, match="decrease action requires delta_weight <= 0"):
        AdjustmentItem(
            ticker="TSLA",
            action="decrease",
            delta_weight=0.05,  # decrease인데 양수
            reason_quote="줄여",
        )


def test_adjustment_item_info_only_with_delta_rejected():
    """info_only + non-zero delta_weight 거절."""
    with pytest.raises(ValidationError, match="info_only action"):
        AdjustmentItem(
            ticker="TSLA",
            action="info_only",
            delta_weight=-0.05,
            reason_quote="TSLA 정보만",
        )


def test_e5_response_no_actionable_intent():
    resp = E5Response(
        adjustments=[],
        confidence=5,
        no_actionable_intent=True,
        ambiguity_notes=None,
    )
    assert len(resp.adjustments) == 0
    assert resp.no_actionable_intent is True


# v2 신규 (I3 검증)
def test_e5_response_no_intent_with_adjustments_rejected():
    """no_actionable_intent=True인데 adjustments가 있으면 거절."""
    with pytest.raises(ValidationError, match="no_actionable_intent=True but adjustments non-empty"):
        E5Response(
            adjustments=[
                AdjustmentItem(
                    ticker="TSLA", action="decrease",
                    delta_weight=-0.05, reason_quote="..."
                )
            ],
            confidence=3,
            no_actionable_intent=True,  # 모순
        )


def test_e5_response_multiple_adjustments():
    resp = E5Response(
        adjustments=[
            AdjustmentItem(ticker="TSLA", action="decrease", delta_weight=-0.05,
                           reason_quote="TSLA 줄여"),
            AdjustmentItem(ticker="NVDA", action="increase", delta_weight=0.05,
                           reason_quote="NVDA 늘려"),
        ],
        confidence=4,
    )
    assert len(resp.adjustments) == 2
```

## 1.4 검증 판정 (v2: 테스트 6개로 갱신)

| #   | 판정                                              | 임계               | 자동 |
| --- | ------------------------------------------------- | ------------------ | ---- |
| 1   | E5Request, E5Response, AdjustmentItem import 가능 | python -c 통과     | 자동 |
| 2   | extra=forbid 동작                                 | 단위 테스트 통과   | 자동 |
| 3   | I2 model_validator 동작 (action↔delta)            | 2 추가 테스트 통과 | 자동 |
| 4   | I3 model_validator 동작 (intent↔adjustments)      | 1 추가 테스트 통과 | 자동 |
| 5   | 회귀 (Slice 1 baseline)                           | 37 + 6 = 43 passed | 자동 |

```bash
pytest portfolio/tests/test_schemas.py -v
pytest portfolio/tests/ -q
```

## 1.5 산출물

- `portfolio/schemas/llm.py` (확장) 또는 `portfolio/schemas/adjustment.py` (신설, ~70줄)
- `portfolio/schemas/__init__.py` (export 추가)
- `portfolio/tests/test_schemas.py` (확장, ~80줄)

## 1.6 비용 가드

- LLM 호출: 0회
- 누적: 11~13 / 50

---

# Step 2 — services/e5_adjustment_parser.py 신설 (v2: module-level import)

## 2.1 목표

E5 비즈니스 로직을 view에서 분리한 service 레이어로 작성한다. **v2 변경 (I5)**: LLMClient를 module-level import로 변경하여 Mock 패치 타겟을 services 모듈로 정렬.

## 2.2 사전 조건

- Step 1 완료 (E5Request, E5Response 사용 가능)
- LLMClient 재사용 (Slice 1 검증됨)
- parsers.py의 `parse_json_response` 재사용

## 2.3 작업 단계

### 2.3.1 service 모듈 신설 (v2: module-level import)

`portfolio/services/e5_adjustment_parser.py`:

```python
"""E5 진입점 비즈니스 로직: 자연어 → 구조화 override JSON."""
from __future__ import annotations

from typing import Any

# v2 변경 (I5): module-level import.
# Mock 패치 타겟은 portfolio.services.e5_adjustment_parser.LLMClient.
from portfolio.llm.client import LLMClient
from portfolio.parsers import parse_json_response
from portfolio.schemas.llm import E5Request, E5Response


def build_e5_prompt(request: E5Request) -> str:
    """E5 프롬프트 조립.

    프롬프트 설계 원칙:
    - schema 강제: JSON 형식만, 마크다운 펜스 금지, extra 키 금지
    - 의도 매칭 강조: 사용자 명령에 없는 종목 임의 추가 금지
    - reason_quote 강제: 모든 adjustment에 자연어 근거 인용 필수
    - confidence 가이드: 1=불확실, 5=확실
    - no_actionable_intent: 잡담/질문은 빈 adjustments + 플래그
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", [])
    holdings_summary = ", ".join(
        f"{h['ticker']}({h['weight']:.0%})" for h in holdings
    )

    return f"""당신은 한국 개인 투자자의 포트폴리오 조정 명령을 파싱하는 전문가입니다.

## 현재 포트폴리오
{holdings_summary}

## 분석 결과 요약
{_format_analysis_summary(ctx)}

## 사용자 명령
"{request.user_command}"

## 작업
사용자 명령을 다음 JSON schema로 변환하세요. JSON 객체만 반환하며, 마크다운 코드 펜스나 추가 설명을 절대 포함하지 마세요.

{{
  "adjustments": [
    {{
      "ticker": "...",
      "action": "increase|decrease|remove|add|info_only",
      "delta_weight": -1.0 ~ 1.0 (또는 null),
      "target_weight": 0.0 ~ 1.0 (또는 null),
      "reason_quote": "사용자 명령에서 이 조정을 추출한 근거 인용 (한국어 그대로)"
    }}
  ],
  "confidence": 1~5,
  "ambiguity_notes": "명령이 모호한 경우 메모 (또는 null)",
  "no_actionable_intent": false
}}

## 규칙
1. 사용자 명령에 명시되지 않은 종목을 임의로 추가하지 마세요.
2. 비중 수치가 명시되지 않은 경우 delta_weight를 null로 두고 action만 채우세요.
3. 명령이 질문/잡담이면 adjustments=[], no_actionable_intent=true.
4. reason_quote는 사용자 원문에서 인용. 의역 금지.
5. confidence는 명령 명확성 기준 (5=명확, 1=모호).
6. action 일관성 — decrease는 delta_weight ≤ 0, increase는 ≥ 0, remove는 target_weight=0 또는 null.
"""


def _format_analysis_summary(ctx: dict[str, Any]) -> str:
    """AnalysisContext에서 요약 추출. Tier 1 위주, 간결하게.

    v2 (I4): 200자 truncate 유지. Step 7 토큰 측정 결과에 따라 추후 100자로 압축 검토.
    """
    summary = ctx.get("analysis_summary", {})
    one_line = summary.get("one_line_diagnosis", "분석 결과 없음")
    return one_line[:200]


def parse_e5_response(raw_content: str) -> E5Response:
    """LLM raw 응답 → E5Response Pydantic 객체."""
    data = parse_json_response(raw_content)
    return E5Response.model_validate(data)


def run_e5(request: E5Request, *, provider: str = "haiku") -> dict[str, Any]:
    """E5 진입점 entry function. view가 호출.

    Returns:
        {
            "response": E5Response (model_dump),
            "metadata": LLMResponse metadata (provider/model/cost/latency/...),
        }

    v2 (I5): LLMClient는 module-level import. 테스트에서 Mock 패치 타겟은
    portfolio.services.e5_adjustment_parser.LLMClient.
    """
    prompt = build_e5_prompt(request)
    client = LLMClient(provider=provider)
    raw = client.invoke(prompt=prompt)
    parsed = parse_e5_response(raw.content)
    return {
        "response": parsed.model_dump(),
        "metadata": {
            "provider": raw.provider,
            "model": raw.model,
            "input_tokens": raw.input_tokens,
            "output_tokens": raw.output_tokens,
            "latency_ms": raw.latency_ms,
            "cost_usd": raw.cost_usd,
            "fallback_from": raw.fallback_from,
        },
    }
```

### 2.3.2 Slice 1 E1 정리 (v2 신규, I5 횡단 적용)

`portfolio/services/e1_garp.py`도 동일 패턴으로 정리. 만약 E1이 함수 내 import를 사용 중이면 module-level로 이동:

```python
# portfolio/services/e1_garp.py 상단
from portfolio.llm.client import LLMClient  # 함수 내에서 빼기
```

기존 `test_e1_garp_view.py`의 patch target을 `portfolio.services.e1_garp.LLMClient`로 통일. 회귀 37 passed 재확인.

### 2.3.3 단위 테스트 추가

`portfolio/tests/test_e5_service.py` 신설:

````python
import pytest
from portfolio.schemas.llm import E5Request, E5Response
from portfolio.services.e5_adjustment_parser import (
    build_e5_prompt,
    parse_e5_response,
)


def _sample_request(command: str) -> E5Request:
    return E5Request(
        analysis_context={
            "holdings": [
                {"ticker": "MSFT", "weight": 0.3},
                {"ticker": "TSLA", "weight": 0.2},
                {"ticker": "NVDA", "weight": 0.5},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 적합도 양호. TSLA 비중 과다.",
            },
        },
        user_command=command,
    )


def test_build_prompt_contains_holdings():
    req = _sample_request("TSLA 좀 줄여줘")
    prompt = build_e5_prompt(req)
    assert "MSFT" in prompt
    assert "TSLA" in prompt
    assert "TSLA 좀 줄여줘" in prompt


def test_build_prompt_contains_schema_directive():
    req = _sample_request("아무거나")
    prompt = build_e5_prompt(req)
    assert "JSON" in prompt
    assert "마크다운" in prompt
    assert "no_actionable_intent" in prompt


def test_parse_e5_response_valid_json():
    raw = """{"adjustments":[{"ticker":"TSLA","action":"decrease","delta_weight":-0.05,"reason_quote":"TSLA 줄여"}],"confidence":4,"ambiguity_notes":null,"no_actionable_intent":false}"""
    parsed = parse_e5_response(raw)
    assert isinstance(parsed, E5Response)
    assert len(parsed.adjustments) == 1
    assert parsed.adjustments[0].ticker == "TSLA"


def test_parse_e5_response_with_markdown_fence():
    raw = """```json
{"adjustments":[],"confidence":3,"ambiguity_notes":null,"no_actionable_intent":true}
```"""
    parsed = parse_e5_response(raw)
    assert parsed.no_actionable_intent is True


def test_parse_e5_response_invalid_schema():
    raw = """{"adjustments":[{"ticker":"X","action":"INVALID_ACTION","reason_quote":"..."}],"confidence":3}"""
    with pytest.raises(Exception):  # pydantic ValidationError
        parse_e5_response(raw)
````

## 2.4 검증 판정

| #   | 판정                                        | 임계               | 자동 |
| --- | ------------------------------------------- | ------------------ | ---- |
| 1   | build_e5_prompt 단위 테스트 통과            | 2/2                | 자동 |
| 2   | parse_e5_response 단위 테스트 통과          | 3/3                | 자동 |
| 3   | 마크다운 펜스 자동 제거 (parsers.py 재사용) | OK                 | 자동 |
| 4   | E1 patch target 정리 후 회귀 통과           | Slice 1 37 유지    | 자동 |
| 5   | 회귀                                        | 43 + 5 = 48 passed | 자동 |

## 2.5 산출물

- `portfolio/services/e5_adjustment_parser.py` (신규, ~120줄)
- `portfolio/services/e1_garp.py` (정리, module-level import)
- `portfolio/tests/test_e1_garp_view.py` (정리, patch target 변경)
- `portfolio/tests/test_e5_service.py` (신규, ~80줄)

## 2.6 비용 가드

- LLM 호출: 0회
- 누적: 11~13 / 50

---

# Step 3 — Django view + URL 라우팅

## 3.1 목표

E5 진입점을 HTTP endpoint로 노출. Slice 1의 E1 view 패턴 mirror.

## 3.2 작업 단계

### 3.2.1 view 추가

`portfolio/views.py`에 추가:

```python
import json
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["POST"])
def e5_adjustment_parser_view(request: HttpRequest) -> JsonResponse:
    """E5: 자연어 조정 명령 → 구조화 override JSON.

    Request body (JSON):
        {
            "analysis_context": {...},
            "user_command": "TSLA 비중 줄여",
            "session_id": "..." (optional)
        }
    Query params:
        provider: haiku (default) | sonnet | gemini
    """
    from portfolio.schemas.llm import E5Request
    from portfolio.services.e5_adjustment_parser import run_e5
    from portfolio.llm.exceptions import LLMBudgetExceededError

    try:
        body = json.loads(request.body)
        e5_req = E5Request.model_validate(body)
    except (json.JSONDecodeError, Exception) as e:
        return JsonResponse(
            {"error": "invalid_request", "detail": str(e)[:300]}, status=400,
        )

    provider = request.GET.get("provider", "haiku")
    if provider not in {"haiku", "sonnet", "gemini"}:
        return JsonResponse(
            {"error": "invalid_provider", "allowed": ["haiku", "sonnet", "gemini"]},
            status=400,
        )

    try:
        result = run_e5(e5_req, provider=provider)
    except LLMBudgetExceededError as e:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(e)}, status=429,
        )
    except Exception as e:
        return JsonResponse(
            {"error": "llm_invocation_failed", "detail": str(e)[:300]}, status=500,
        )

    return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})
```

### 3.2.2 URL 라우팅

`portfolio/urls.py`에 추가:

```python
from django.urls import path
from portfolio.views import (
    e1_garp_view,        # Slice 1
    e5_adjustment_parser_view,
)

app_name = "portfolio"

urlpatterns = [
    path("api/coach/e1/garp/", e1_garp_view, name="e1_garp"),
    path("api/coach/e5/adjustment/", e5_adjustment_parser_view, name="e5_adjustment"),
]
```

### 3.2.3 view 통합 테스트 (v2: patch target 갱신)

`portfolio/tests/test_e5_view.py` 신설:

```python
import json
import pytest
from django.test import Client
from unittest.mock import patch


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def valid_request_body():
    return {
        "analysis_context": {
            "holdings": [{"ticker": "TSLA", "weight": 0.5}],
            "analysis_summary": {"one_line_diagnosis": "test"},
        },
        "user_command": "TSLA 줄여줘",
    }


# v2 (I5): patch target은 services 모듈로 변경
@patch("portfolio.services.e5_adjustment_parser.run_e5")
def test_e5_view_normal(mock_run, client, valid_request_body):
    mock_run.return_value = {
        "response": {
            "adjustments": [{"ticker": "TSLA", "action": "decrease",
                             "delta_weight": -0.05, "target_weight": None,
                             "reason_quote": "TSLA 줄여줘"}],
            "confidence": 4,
            "ambiguity_notes": None,
            "no_actionable_intent": False,
        },
        "metadata": {"provider": "anthropic", "model": "haiku",
                     "cost_usd": 0.001, "latency_ms": 1200,
                     "input_tokens": 500, "output_tokens": 100,
                     "fallback_from": None},
    }
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/?provider=haiku",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "metadata" in data
    assert data["response"]["adjustments"][0]["ticker"] == "TSLA"


def test_e5_view_invalid_provider(client, valid_request_body):
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/?provider=invalid",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_provider"


def test_e5_view_invalid_body(client):
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400
```

## 3.3 검증 판정

| #   | 판정             | 임계               | 자동 |
| --- | ---------------- | ------------------ | ---- |
| 1   | view 통합 테스트 | 3/3                | 자동 |
| 2   | URL routing      | reverse 가능       | 자동 |
| 3   | 회귀             | 48 + 3 = 51 passed | 자동 |

## 3.4 산출물

- `portfolio/views.py` (확장)
- `portfolio/urls.py` (확장)
- `portfolio/tests/test_e5_view.py` (신규, ~70줄)

## 3.5 비용 가드

- LLM 호출: 0회
- 누적: 11~13 / 50

---

# Step 4 — Mock LLM client 통합 테스트 (v2: 본문 완성 + 패치 타겟 갱신)

## 4.1 목표

LLMClient의 5개 통합 시나리오(normal / rate_limit_first / timeout_first / auth_error / budget_exceeded)를 E5 view 위에 mirror. **v2 변경**: C2 (timeout 본문 작성), I5 (패치 타겟 services 모듈), M2 (mocks.py 사전 검증).

## 4.2 사전 조건 (v2 신규: M2 대응)

```bash
ls portfolio/llm/mocks.py
```

존재하지 않으면 신설:

```python
"""Mock LLM client builder for testing.

Slice 1에서 도입된 헬퍼. Slice 2에서도 재사용.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def build_mock_llm_client(
    primary_responses: list,
    fallback_responses: list = None,
) -> MagicMock:
    """Mock LLMClient 인스턴스 생성.

    Args:
        primary_responses: primary provider 응답 리스트.
            예외 객체 또는 LLMResponse-like 객체.
        fallback_responses: fallback provider 응답 리스트.

    Returns:
        invoke()를 반복 호출 가능한 mock instance.
        primary가 예외 던지면 fallback으로 넘어감.
    """
    fallback_responses = fallback_responses or []
    mock = MagicMock()
    primary_iter = iter(primary_responses)
    fallback_iter = iter(fallback_responses)

    def _invoke(*args, **kwargs):
        try:
            r = next(primary_iter)
        except StopIteration:
            r = next(fallback_iter)
        if isinstance(r, Exception):
            # primary 예외면 fallback 시도
            try:
                r = next(fallback_iter)
            except StopIteration:
                raise r
            if isinstance(r, Exception):
                raise r
        return r

    mock.invoke = MagicMock(side_effect=_invoke)
    return mock
```

> **주의**: 위 헬퍼는 Slice 1 mocks.py가 존재하지 않을 경우의 보강용. Slice 1 mocks.py가 있다면 그 시그니처를 그대로 사용.

## 4.3 작업 단계 (v2: 본문 완성)

`portfolio/tests/test_e5_view.py`에 추가:

```python
from portfolio.llm.exceptions import (
    LLMRateLimitError, LLMTimeoutError, LLMAuthError, LLMBudgetExceededError,
)
from portfolio.llm.mocks import build_mock_llm_client


def _make_fallback_response(provider: str = "anthropic", model: str = "haiku"):
    """Fallback 시 사용할 가상 LLMResponse 객체."""
    return type("R", (), {
        "content": '{"adjustments":[],"confidence":3,"ambiguity_notes":null,"no_actionable_intent":true}',
        "provider": provider,
        "model": model,
        "input_tokens": 500,
        "output_tokens": 50,
        "latency_ms": 1000,
        "cost_usd": 0.001,
        "fallback_from": "gemini",
    })()


# v2 (I5): patch target은 services 모듈
@patch("portfolio.services.e5_adjustment_parser.LLMClient")
def test_e5_view_rate_limit_first_fallback(mock_client_cls, client, valid_request_body):
    """gemini가 RateLimit → anthropic으로 자동 폴백."""
    mock_instance = build_mock_llm_client(
        primary_responses=[LLMRateLimitError("rate")],
        fallback_responses=[_make_fallback_response()],
    )
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/?provider=gemini",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["metadata"]["fallback_from"] == "gemini"


# v2 (C2): 본문 완성
@patch("portfolio.services.e5_adjustment_parser.LLMClient")
def test_e5_view_timeout_first_fallback(mock_client_cls, client, valid_request_body):
    """primary가 Timeout → fallback 성공."""
    mock_instance = build_mock_llm_client(
        primary_responses=[LLMTimeoutError("timeout after 30s")],
        fallback_responses=[_make_fallback_response()],
    )
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/?provider=gemini",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["metadata"]["fallback_from"] == "gemini"


@patch("portfolio.services.e5_adjustment_parser.LLMClient")
def test_e5_view_auth_error_no_fallback(mock_client_cls, client, valid_request_body):
    """auth_error는 폴백 안 함 → 500 응답."""
    mock_instance = build_mock_llm_client(
        primary_responses=[LLMAuthError("invalid key")],
        fallback_responses=[],
    )
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/?provider=gemini",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 500


@patch("portfolio.services.e5_adjustment_parser.LLMClient")
def test_e5_view_budget_exceeded(mock_client_cls, client, valid_request_body):
    """budget exceeded → 429."""
    mock_instance = build_mock_llm_client(
        primary_responses=[LLMBudgetExceededError("limit reached")],
        fallback_responses=[],
    )
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e5/adjustment/",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 429
```

> **리팩토링 백로그 (Step 9 슬롯)**: rate_limit/timeout 두 테스트는 거의 동일한 구조. pytest.mark.parametrize로 통합 검토. 단, mock side_effect의 lazy 평가 주의(예외는 인스턴스화되어 있어야 함).

## 4.4 검증 판정

| #   | 판정                                              | 임계               | 자동 |
| --- | ------------------------------------------------- | ------------------ | ---- |
| 1   | mocks.py 존재 (또는 신설 완료)                    | 파일 존재          | 자동 |
| 2   | 5개 시나리오 통과 (normal은 Step 3, 4개는 Step 4) | 4/4                | 자동 |
| 3   | 회귀                                              | 51 + 4 = 55 passed | 자동 |

## 4.5 산출물

- `portfolio/llm/mocks.py` (필요 시 신설)
- `portfolio/tests/test_e5_view.py` (확장, +4 테스트)

## 4.6 비용 가드

- LLM 호출: 0회 (Mock만)
- 누적: 11~13 / 50

---

# Step 5 — Mock fixture (v2: COMMANDS 정리 + ambiguous 의미 단순화)

## 5.1 목표

E5 입력은 (분석 결과, 자연어 명령) 쌍. Slice 1 GARP 분석 결과를 재활용하고 자연어 명령 6종을 정의한 fixture loader를 신설.

**v2 변경**:

- C3 적용: COMMANDS dict에 `"large_multi"` 키 추가, `get_e5_fixture_large`가 참조
- I1 적용: `ambiguous` fixture를 `no_actionable_intent=True`로 의미 단순화 + `unclear_amount` 보조 fixture 신설

## 5.2 작업 단계

### 5.2.1 fixture 추가 (v2: COMMANDS 6+ 엔트리)

`portfolio/tests/fixtures/sample_adjustment_context.py` 신설:

```python
"""E5 진입점 fixture: 분석 결과 + 자연어 명령 쌍."""
from __future__ import annotations

from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_tech,
    get_context_garp_misfit,
    get_context_garp_large,
)


# v2 (C3): COMMANDS는 모든 fixture가 참조하는 단일 진실 출처(SSoT).
# v2 (I1): ambiguous → no_intent로 의미 통합. unclear_amount 보조 fixture 신설.
COMMANDS = {
    "clear_decrease": "TSLA 비중 좀 줄여줘. 너무 많은 것 같아.",
    "clear_multi": "TSLA는 줄이고 NVDA는 좀 늘려줘.",
    "unclear_amount": "TSLA 좀 줄여",  # v2 신규: 비중 수치 미명시 → delta_weight=null 기대
    "no_intent_question": "GARP 프리셋이 뭐야?",
    "no_intent_chitchat": "포트폴리오가 좀 불안한데 어떻게 할까?",  # v2 (I1): ambiguous → no_intent로 분류
    "remove": "PLTR은 빼버릴게.",
    "large_multi": "변동성 큰 종목들 비중 좀 줄여줘. TSLA, PLTR, SHOP.",  # v2 (C3): 인라인 → COMMANDS
}


def get_e5_fixture_clear_decrease() -> dict:
    """단일 종목 명확 축소 명령 (Tech fixture 기반)."""
    return {
        "analysis_context": _wrap_context(get_context_garp_tech()),
        "user_command": COMMANDS["clear_decrease"],
        "expected": {
            "adjustments_min_count": 1,
            "expected_tickers": {"TSLA"},
            "expected_actions": {"decrease"},
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_clear_multi() -> dict:
    """다중 종목 명확 명령."""
    return {
        "analysis_context": _wrap_context(get_context_garp_tech()),
        "user_command": COMMANDS["clear_multi"],
        "expected": {
            "adjustments_min_count": 2,
            "expected_tickers": {"TSLA", "NVDA"},
            "expected_actions": {"decrease", "increase"},
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_unclear_amount() -> dict:
    """v2 신규 (I1 보강): 비중 수치 미명시 명령. delta_weight=null 기대."""
    return {
        "analysis_context": _wrap_context(get_context_garp_tech()),
        "user_command": COMMANDS["unclear_amount"],
        "expected": {
            "adjustments_min_count": 1,
            "expected_tickers": {"TSLA"},
            "expected_actions": {"decrease"},
            "delta_weight_required_null": True,  # 수치 없으므로 null 기대
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_no_intent_question() -> dict:
    """질문 — no_actionable_intent=True 기대."""
    return {
        "analysis_context": _wrap_context(get_context_garp_tech()),
        "user_command": COMMANDS["no_intent_question"],
        "expected": {
            "adjustments_count": 0,
            "no_actionable_intent": True,
        },
    }


def get_e5_fixture_no_intent_chitchat() -> dict:
    """v2 (I1): "어떻게 할까?" 류 잡담/모호 명령 — no_actionable_intent=True 기대."""
    return {
        "analysis_context": _wrap_context(get_context_garp_misfit()),
        "user_command": COMMANDS["no_intent_chitchat"],
        "expected": {
            "adjustments_count": 0,
            "no_actionable_intent": True,
        },
    }


def get_e5_fixture_remove() -> dict:
    """종목 제거 명령 (action=remove)."""
    return {
        "analysis_context": _wrap_context(get_context_garp_large()),
        "user_command": COMMANDS["remove"],
        "expected": {
            "adjustments_min_count": 1,
            "expected_tickers": {"PLTR"},
            "expected_actions": {"remove"},
            "no_actionable_intent": False,
        },
    }


def get_e5_fixture_large() -> dict:
    """v2 (C3): COMMANDS 참조. large fixture (종목 15) — 토큰 예산 검증용."""
    return {
        "analysis_context": _wrap_context(get_context_garp_large()),
        "user_command": COMMANDS["large_multi"],
        "expected": {
            "adjustments_min_count": 3,
            "expected_tickers": {"TSLA", "PLTR", "SHOP"},
            "expected_actions": {"decrease"},
            "no_actionable_intent": False,
        },
    }


def _wrap_context(garp_ctx: dict) -> dict:
    """GARP 분석 결과를 E5 입력 형태로 래핑.

    Slice 1의 garp_ctx는 holdings + metrics 위주.
    E5는 거기에 analysis_summary 추가 (한 줄 진단 등) 필요.
    """
    return {
        "holdings": garp_ctx["holdings"],
        "metrics": garp_ctx.get("metrics", {}),
        "analysis_summary": {
            "one_line_diagnosis": "GARP 적합도는 보통. TSLA, PLTR 변동성 우려.",
            "preset_id": garp_ctx.get("preset_id", "garp"),
        },
        "preset_version": garp_ctx.get("preset_version", "v1.0"),
    }


# v2: 6개 → 6개 (clear_decrease, clear_multi, unclear_amount, no_intent_question, no_intent_chitchat, remove)
# + large = 7개
ALL_FIXTURES = {
    "clear_decrease": get_e5_fixture_clear_decrease,
    "clear_multi": get_e5_fixture_clear_multi,
    "unclear_amount": get_e5_fixture_unclear_amount,
    "no_intent_question": get_e5_fixture_no_intent_question,
    "no_intent_chitchat": get_e5_fixture_no_intent_chitchat,
    "remove": get_e5_fixture_remove,
    "large": get_e5_fixture_large,
}
```

### 5.2.2 fixture validation 테스트 (v2: 카운트 7로 갱신)

`portfolio/tests/test_e5_fixtures.py` 신설:

```python
import pytest

from portfolio.schemas.llm import E5Request
from portfolio.tests.fixtures.sample_adjustment_context import (
    ALL_FIXTURES, COMMANDS,
)


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e5_fixture_valid_request(fixture_name):
    """각 fixture가 E5Request로 검증 통과해야 함."""
    fixture = ALL_FIXTURES[fixture_name]()
    req = E5Request(
        analysis_context=fixture["analysis_context"],
        user_command=fixture["user_command"],
    )
    assert req.user_command
    assert "holdings" in req.analysis_context


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e5_fixture_has_expected_field(fixture_name):
    """각 fixture에 expected 필드 (회고 시 비교 기준) 존재."""
    fixture = ALL_FIXTURES[fixture_name]()
    assert "expected" in fixture


def test_e5_fixture_count():
    """v2: 7개 fixture (5종 표준 + unclear_amount + large)."""
    assert len(ALL_FIXTURES) == 7


def test_commands_match_fixtures():
    """v2 (C3): COMMANDS의 키와 fixture가 사용하는 명령 일치."""
    # large_multi는 large fixture가 사용. unclear_amount는 unclear_amount fixture가 사용.
    used_commands = set()
    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        # COMMANDS 안의 어느 키와 매칭되는지 검증
        cmd = fixture["user_command"]
        matched = [k for k, v in COMMANDS.items() if v == cmd]
        assert matched, f"fixture {name}이 COMMANDS에 없는 명령 사용: {cmd!r}"
        used_commands.update(matched)
    # 모든 COMMANDS 키가 최소 1번 이상 사용되어야 함
    unused = set(COMMANDS.keys()) - used_commands
    assert not unused, f"COMMANDS에 정의됐지만 미사용: {unused}"
```

## 5.3 검증 판정

| #   | 판정                                       | 임계                          | 자동 |
| --- | ------------------------------------------ | ----------------------------- | ---- |
| 1   | 7개 fixture loader 모두 Pydantic 검증 통과 | 7/7                           | 자동 |
| 2   | expected 필드 존재                         | 7/7                           | 자동 |
| 3   | 카운트 검증                                | len=7                         | 자동 |
| 4   | COMMANDS-fixture 일치 (v2 신규)            | 통과                          | 자동 |
| 5   | 회귀                                       | 55 + (7+7+1+1=16) = 71 passed | 자동 |

## 5.4 산출물

- `portfolio/tests/fixtures/sample_adjustment_context.py` (신규, ~180줄)
- `portfolio/tests/test_e5_fixtures.py` (신규, ~50줄)

## 5.5 비용 가드

- LLM 호출: 0회
- 누적: 11~13 / 50

---

# Part 1 종결 체크리스트 (v2)

Step 0 ~ Step 5 완료 직전 본인 확인:

- [ ] **C1**: Step 0 진단 #4 sleep 0.5초 적용. 6×5분=30분 한도 충족
- [ ] **C2**: Step 4 `test_e5_view_timeout_first_fallback` 본문 작성 완료
- [ ] **C3**: COMMANDS dict에 `large_multi`, `unclear_amount` 키 추가, fixture 모두 COMMANDS 참조
- [ ] **I1**: `ambiguous` fixture → `no_intent_chitchat`로 변경. `unclear_amount` 보조 fixture 추가
- [ ] **I2**: AdjustmentItem `model_validator` 동작 (action↔delta 모순 거름)
- [ ] **I3**: E5Response `model_validator` 동작 (intent↔adjustments 모순 거름)
- [ ] **I5**: services 모듈 module-level import. patch target = `portfolio.services.e5_adjustment_parser.LLMClient`
- [ ] **I5 횡단**: Slice 1 E1도 같은 패턴으로 정리. test_e1_garp_view.py patch target 갱신
- [ ] **M2**: `portfolio/llm/mocks.py` 존재 또는 신설 완료
- [ ] **M3**: reparse_step6.py 미사용 변수 `parsed_obj` 제거
- [ ] Step 0 Gemini 진단: gemini_diagnosis.md Conclusion PASS/WAIT/ESCALATE 결정
- [ ] Step 0.5 step6 reparse: schema_pass=true, cost_pass=true, naturalness 정수
- [ ] Step 1 E5 schemas: 6 단위 테스트 통과 (validator 포함)
- [ ] Step 2 services/e5: 5 단위 테스트 통과
- [ ] Step 3 view + URL: 3 통합 테스트 통과
- [ ] Step 4 Mock 5 시나리오: rate_limit/timeout/auth/budget 통과
- [ ] Step 5 fixture 7종: Pydantic 검증 + expected 필드 + COMMANDS 일치
- [ ] **누적 테스트: 37 + 6 + 5 + 3 + 4 + 16 = 71 passed**
- [ ] 누적 LLM 호출: 11~13 / 50 (Step 0 진단 호출만)
- [ ] 누적 비용: $0.122 (Slice 1) + 진단 ~$0.005 = ~$0.127

# Part 2 진입 조건

위 체크리스트 모두 통과 시 Part 2 (Step 6~9) 지시서로 진입.

> "Slice 2 Part 2 시작. Step 6 실제 haiku 호출 검증부터."

Part 2는 별도 답변에서 작성 예정 (예상 ~900줄):

- Step 6: 실제 haiku 호출 1회 (clear_decrease fixture, 4개 판정)
- Step 7: large fixture 토큰 측정 (E5는 input 더 작아 budget 갱신, **I4 모니터링 — analysis_summary 200자 압축 검토 신호 측정**)
- Step 8: 3-way 회고 (haiku + sonnet + gemini, gemini 정상화 시 / 2-way fallback)
- Step 9: 30분 리팩토링 슬롯 (Sharpe-like priority — Mock 시나리오 parametrize 통합 등)

---

# 부록 A — 결정 사항 단일 표 (v2 갱신)

| Q                              | 결정                                                      | 파일/위치                                          |
| ------------------------------ | --------------------------------------------------------- | -------------------------------------------------- |
| 진입점                         | E5 = 조정 파싱 (Watchlist 아님)                           | `portfolio/services/e5_adjustment_parser.py`       |
| primary provider               | haiku                                                     | `portfolio/llm/client.py` 기본값 또는 view default |
| 평가 차원                      | schema + 의도매칭 + 추가변경없음 + 비용 + 지연            | Part 2 Step 8에서 정의                             |
| fixture 구조                   | 분석결과 (Slice 1 재활용) + 자연어 6종 + large 1종 = 7개  | `sample_adjustment_context.py`                     |
| docs 경로                      | `docs/portfolio/coach/`                                   | 모든 산출물                                        |
| 비용 가드                      | 50회 한도 유지 (reset은 Slice 2 종료 회고 시 결정)        | `LLM_BUDGET_MAX_CALLS=50`                          |
| **schema validator (v2)**      | **명확 모순만 거름 — action↔delta, intent↔adjustments**   | `portfolio/schemas/llm.py`                         |
| **mock patch target (v2)**     | **services 모듈 (module-level import 후)**                | 모든 view/service 테스트                           |
| **ambiguous 의미 (v2)**        | **no_actionable_intent=True로 통합. unclear_amount 보조** | `sample_adjustment_context.py`                     |
| **analysis_context 길이 (v2)** | **200자 truncate 유지. Step 7 토큰 측정 후 재검토**       | `_format_analysis_summary`                         |

# 부록 B — Part 1 신규 파일 목록 (v2 갱신)

| 파일                                                      | 종류             | 줄 수 (추정) | v1 → v2 변경                |
| --------------------------------------------------------- | ---------------- | ------------ | --------------------------- |
| `scripts/validation/diagnose_gemini.py`                   | 진단 스크립트    | ~150         | sleep 0.5초                 |
| `scripts/validation/reparse_step6.py`                     | 재처리 스크립트  | ~80          | parsed_obj 제거             |
| `docs/portfolio/coach/gemini_diagnosis.md`                | 진단 보고서      | ~50          | —                           |
| `portfolio/schemas/llm.py` (확장 또는 신규 adjustment.py) | 스키마           | ~70          | model_validator +2          |
| `portfolio/tests/test_schemas.py` (확장)                  | 단위 테스트      | ~80          | validator 테스트 +2 (총 6)  |
| `portfolio/services/e5_adjustment_parser.py`              | 비즈니스 로직    | ~120         | module-level import         |
| `portfolio/services/e1_garp.py`                           | (정리)           | —            | module-level import         |
| `portfolio/tests/test_e1_garp_view.py`                    | (정리)           | —            | patch target 갱신           |
| `portfolio/tests/test_e5_service.py`                      | 단위 테스트      | ~80          | —                           |
| `portfolio/views.py` (확장)                               | view             | ~40          | —                           |
| `portfolio/urls.py` (확장)                                | URL              | ~5           | —                           |
| `portfolio/tests/test_e5_view.py`                         | view 통합 테스트 | ~170         | timeout 본문 + patch target |
| `portfolio/llm/mocks.py`                                  | mock 헬퍼        | ~50          | M2 — 필요 시 신설           |
| `portfolio/tests/fixtures/sample_adjustment_context.py`   | fixture          | ~180         | COMMANDS +2, fixture +1     |
| `portfolio/tests/test_e5_fixtures.py`                     | fixture 검증     | ~50          | COMMANDS-fixture 일치 +1    |

총 신규 코드: ~975줄 (v1 ~955 + v2 추가). 보고서/JSON 별도.

# 부록 C — v2 변경 적용 순서 (실행 가이드)

추가 작업 시간 ~52분을 다음 순서로 분배:

1. **즉시 (12분)** — Step 0/0.5 진입 전:
   - C1 (sleep 0.5초): `diagnose_gemini.py` ~5분
   - C3 (COMMANDS dict): `sample_adjustment_context.py` ~2분 (Step 5에서 작성하므로 그때 적용)
   - M3 (parsed_obj 제거): `reparse_step6.py` ~5분

2. **Step 1 진입 전 (25분)**:
   - I2 (AdjustmentItem validator): `schemas/llm.py` ~10분 + 테스트 ~5분
   - I3 (E5Response validator): `schemas/llm.py` ~5분 + 테스트 ~5분

3. **Step 2/3/4 진입 전 (10분)**:
   - I5 (module-level import): E5/E1 services + 테스트 patch target ~10분

4. **Step 4 진입 직전 (5분)**:
   - M2 검증: `ls portfolio/llm/mocks.py`. 없으면 부록 A 헬퍼 신설

5. **Step 5 작성 시 (자연 흡수)**:
   - C3: COMMANDS 7종으로 작성
   - I1: `ambiguous` 명칭 → `no_intent_chitchat`, `unclear_amount` 추가
   - C2: timeout fallback 본문 (Step 4 작성 시 자연 흡수)

# 부록 D — 회귀 카운트 진행 표 (v2)

| 단계                         | 추가 테스트                                       | 누적   |
| ---------------------------- | ------------------------------------------------- | ------ |
| Slice 1 baseline             | —                                                 | 37     |
| Step 1 (schemas + validator) | +6                                                | 43     |
| Step 2 (services + I5 정리)  | +5 (E1 회귀 0)                                    | 48     |
| Step 3 (view)                | +3                                                | 51     |
| Step 4 (Mock 4 시나리오)     | +4                                                | 55     |
| Step 5 (fixtures 7)          | +16 (Pydantic 7 + expected 7 + count 1 + match 1) | **71** |

> **주의**: Slice 1의 E1 patch target 정리(I5 횡단)는 회귀 0 — 기존 테스트 수정만 하고 신규 테스트 없음.
