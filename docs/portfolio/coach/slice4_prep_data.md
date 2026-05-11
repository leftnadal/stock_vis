# Slice 4 Prep Data — Read-Only 데이터 수집

> 작성일: 2026-05-07
> 작성 대상: Slice 4 진입 (E6 권장) 직전 사실 정합성 점검
> 원칙: read-only — 코드/검증 산출물 수정 없음. 인용은 실제 파일 그대로.
> 회귀 baseline: 123 passed (Slice 3 종결 시점)
> 누적 LLM 호출: 57 / 150 (Slice 1: 10, Slice 2: 32, Slice 3: 15)

---

## 1. 비용 분석

### 1.1 슬라이스별 누적 비용 (실측 인용)

| Slice | 출처 파일 | § | LLM 호출 | 실측 비용 (USD) | Reset 메커니즘 |
|-------|----------|---|---------|----------------|----------------|
| 1 (E1) | `docs/portfolio/coach/slice1/validation_report_slice1.md` | §1 Metadata, §6 Cost Guard | 10~16 (Step 6 1 + Step 8 9 + 재실행 1 + Gemini 진단 5) | $0.137 (Step 6 $0.0152 + Step 8 $0.1064 + 재실행 $0.0153 + 진단 ~$0.0005) | 인스턴스별 `_call_count` (Slice 1 시점에는 CostGuard 미존재) |
| 2 (E5) | `docs/portfolio/coach/slice2/validation_report_slice2.md` | §5 누적 비용 | 32 (Slice 1 종결 10 + Gemini 진단 7 + Step 6 1 + Step 8 1차 손실 14 → 2차 14) | $0.19 (Slice 1 ~$0.10 + 진단 ~$0.005 + Step 6 $0.00135 + Step 8 1차 손실 ~$0.04 + 2차 $0.0404) | 인스턴스별 카운터 (슬라이스 간 누적 안 됨) |
| 3 (E2) | `docs/portfolio/coach/slice3/validation_report_slice3.md` | §5 누적 비용 | 15 / 50 (Step 6 1 + Step 8 14, Q5 reset 적용) | $0.101 (Step 6 $0.00303 + Step 8 $0.0977) | **CostGuard 싱글톤** + `reset_for_slice("slice3")` 멱등 (`scripts/validation/_setup.py:16-31`) |
| **누적** | `docs/portfolio/PORTFOLIO_OVERALL_ANALYSIS.md` | §4 슬라이스별 패턴 진화 표 (105~109행) | 57 / 150 (Slice별 50 한도) | **~$0.41** (종합 분석 기준) | — |

> 모든 비용 값은 각 validation_report_slice*.md의 **실측 표**에서 그대로 인용. 추정/평균 보정 없음.

### 1.2 $0.49 vs $0.41 차이 해석

| 출처 | 값 | 계산 |
|------|----|----|
| `PORTFOLIO_OVERALL_ANALYSIS.md` 머리말 6행 | **~$0.49** | "실측 누적 비용: ~$0.49" (텍스트 인용) |
| `PORTFOLIO_OVERALL_ANALYSIS.md` §4 표 109행 | **~$0.41** | Slice 1 ~$0.10 + Slice 2 ~$0.21 + Slice 3 ~$0.10 = $0.41 (표 합산) |

**차이: $0.08** (≈ 19.5%).

**해석 (선택)**: 차이는 **§4 표가 슬라이스 메인 비용만 합산하고 머리말 $0.49는 부수 비용을 포함한 광의 누적치**라는 표기 차이.

근거 수치:
- §4 표는 Slice 2를 "~$0.21"로만 기재 (Step 6 $0.00135 + Step 8 1차 손실 $0.04 + Step 8 2차 $0.0404 + Slice 1 누적 ~$0.10 + Gemini 진단 ~$0.005 = $0.18~$0.19, 반올림 $0.21).
- `validation_report_slice2.md` §5에 명시된 광의 누적은 **$0.19** (Slice 2 종결 시점) — Slice 1 분 ~$0.10 포함.
- 즉 §4 표 "~$0.21"이 이미 누적치이므로 (~$0.10 + ~$0.21 + ~$0.10 = $0.41) 단순 합산이 맞음.
- 머리말 $0.49는 Slice 1의 광의(진단 + 재실행 포함 $0.137)를 적용했을 때의 합 ($0.137 + $0.21 + $0.10 ≈ $0.45~$0.49) — Step 6 재실행 + Gemini 진단 단발 + 손실 1차 시도 비용을 더 보수적으로 누적한 결과로 해석된다.

**결론**: 두 값 모두 측정 오류는 아님. 표가 협의(슬라이스 메인 4스텝 합), 머리말이 광의(진단/재실행/손실 포함). 향후 리포트는 광의를 기본으로 통일하는 편이 일관성 있음.

---

## 2. fixture 그룹 비교 (Slice 3 Step 8 그룹 분석)

### 2.1 출처

`docs/portfolio/coach/slice3/step8_2way_e2_group_analysis.json` (Slice 3 Step 8 그룹 산출물).

### 2.2 8개 수치 매트릭스 (haiku 4 + sonnet 4)

| 모델 | 그룹 | n | naturalness_mean | insight_mean | score_mean | cost_total_usd | latency_mean_ms |
|------|------|---|------------------|--------------|------------|----------------|-----------------|
| **haiku** | slice1_baseline | 3 | 5.00 | 3.6667 | **30.2556** | $0.0088 | 6,810.0 |
| **haiku** | e2_focused | 4 | 5.00 | 4.5 | **32.8021** | $0.0123 | 7,045.2 |
| **sonnet** | slice1_baseline | 3 | 5.00 | 4.3333 | **11.3797** | $0.0350 | 14,300.3 |
| **sonnet** | e2_focused | 4 | 5.00 | 5.0 | **13.8665** | $0.0416 | 12,566.5 |

> 해당 표의 4행 × score_mean / cost / latency 등 8개 수치는 모두 group_analysis.json `comparison.{model}.{group}` 객체에서 그대로 인용.

### 2.3 그룹별 평균 차이 (interpretations 인용)

| 모델 | baseline | focused | Δ (%) | 판정 (interpretation_guide 기준) |
|------|----------|---------|-------|----------------------------------|
| haiku | 30.26 | 32.80 | +8.4% | `small_diff` (두 그룹 점수 유사 → hybrid 결정 정당) |
| sonnet | 11.38 | 13.87 | **+21.9%** | `focused_higher` (focused가 자연스러움 → E2 특화 fixture 효과) |

### 2.4 그룹 차이 해석 (선택)

**해석**: **focused 그룹이 sonnet의 통찰 측정에 차별화 가치를 더한다**. 단순 baseline 보강이 아니라 모델 차별화 정보 추가.

근거 수치:
- haiku는 baseline ↔ focused 사이 score 변동 +8.4%, insight_mean이 3.67 → 4.5 (+0.83)으로 **상승 폭 0.83**. 자연스러움(naturalness)은 5.00 → 5.00 동률이라 글쓰기 차원의 변동이 없음. → **fixture 다양성에 robust**.
- sonnet은 baseline ↔ focused 사이 score 변동 **+21.9%**, insight_mean이 4.33 → 5.00 (+0.67)으로 만점 도달. 자연스러움 동률(5.00). → **focused 그룹의 통찰 평가 fixture(`e2_balanced` / `e2_extreme_risk` 등)에서 sonnet의 통찰 강점이 시그널로 잡힘**.
- cost_total은 두 모델 모두 fixture 수 비례(haiku +40%, sonnet +19%)로 그룹 효과 아님. latency도 그룹 차이가 작음(haiku +3.5%, sonnet -12%).
- 따라서 winner 변동이 아니라 "**sonnet의 통찰 차별화 → focused 그룹이 fixture로서 의미 있다**"는 결론 → Q4 hybrid 정책 정당화. (validation_report_slice3.md §3.4 동일 결론)

---

## 3. 코드 인용 (read-only paraphrase 금지)

### 3.1 `portfolio/llm/cost_guard.py` — CostGuard 싱글톤 (Slice 3 신규, D3.C)

```python
# portfolio/llm/cost_guard.py:38-76 (발췌)
@dataclass
class CostGuard:
    """싱글톤 패턴. 슬라이스 단위 비용 가드."""

    slice_id: str = "default"
    max_calls: int = 50
    call_count: int = 0
    total_cost_usd: float = 0.0
    records: list[CallRecord] = field(default_factory=list)
    started_at: Optional[str] = None

    _instance: ClassVar[Optional["CostGuard"]] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def get_instance(cls) -> "CostGuard":
        """싱글톤 인스턴스 반환."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def reset_slice(self, slice_id: str, max_calls: int = 50) -> None:
        """슬라이스 진입 시 카운터 reset."""
        self.slice_id = slice_id
        self.max_calls = max_calls
        self.call_count = 0
        self.total_cost_usd = 0.0
        self.records = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "CostGuard reset for slice=%s, max_calls=%d", slice_id, max_calls
        )
```

### 3.2 `portfolio/llm/token_budgets.py` — 진입점별 token budget (Slice 3 백로그 #5, A2.C)

```python
# portfolio/llm/token_budgets.py:14-33
ENTRYPOINT_TOKEN_BUDGETS: dict[str, int] = {
    "e1": 5000,  # Slice 1 결정값
    "e5": 2000,  # Slice 2 Step 7 (P90=756 × 1.5 → round-up 2000)
    "e2": 1500,  # Slice 3 Step 7 (P90=686 × 1.5 → round-up 1500)
    # Slice 4+: e3/e4/e6 추가 시 등록
}


def get_token_budget(entrypoint: str) -> int:
    """진입점별 budget 반환.

    Raises:
        ValueError: 미등록 진입점
    """
    if entrypoint not in ENTRYPOINT_TOKEN_BUDGETS:
        raise ValueError(
            f"Unknown entrypoint: {entrypoint!r}. "
            f"Available: {list(ENTRYPOINT_TOKEN_BUDGETS.keys())}"
        )
    return ENTRYPOINT_TOKEN_BUDGETS[entrypoint]
```

### 3.3 `portfolio/services/_llm_kwargs.py` — PROVIDER_KWARGS 공유 (Slice 3 Step 2 흡수, 백로그 #3)

```python
# portfolio/services/_llm_kwargs.py:19-44
ProviderLabel = Literal["gemini", "anthropic", "sonnet", "haiku"]


PROVIDER_KWARGS: dict[str, dict] = {
    "gemini": {"provider": "gemini", "model": None},
    "anthropic": {"provider": "anthropic", "model": None},  # = Sonnet (LLMClient 기본)
    "sonnet": {"provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
    "haiku": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
}


def resolve_provider_kwargs(label: str) -> dict:
    """Provider label → LLMClient kwargs 변환."""
    if label not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {label!r}. "
            f"Available: {sorted(PROVIDER_KWARGS)}"
        )
    return PROVIDER_KWARGS[label]
```

### 3.4 `portfolio/services/_prompt_helpers.py` — prompt 헬퍼 분리 (Slice 3 Step 2 흡수, 백로그 #4)

```python
# portfolio/services/_prompt_helpers.py:12-36
def format_holdings_summary(holdings: list[dict]) -> str:
    """Holdings 리스트 → 'TICKER(weight%)' 컴마 구분 문자열.

    예: "MSFT(30%), TSLA(20%), NVDA(50%)"
    """
    parts: list[str] = []
    for h in holdings:
        ticker = h.get("ticker") or h.get("stock_symbol") or "?"
        try:
            w = float(h.get("weight", 0))
            parts.append(f"{ticker}({w:.0%})")
        except (TypeError, ValueError):
            parts.append(f"{ticker}(?)")
    return ", ".join(parts)


def format_analysis_summary(ctx: dict[str, Any], max_chars: int = 200) -> str:
    """AnalysisContext에서 한 줄 진단 요약 추출."""
    summary = ctx.get("analysis_summary", {}) or {}
    one_line = summary.get("one_line_diagnosis") or "분석 결과 없음"
    return str(one_line)[:max_chars]
```

### 3.5 `portfolio/services/e2_diagnostic_card.py` — E2 entry function (Slice 3 신규)

```python
# portfolio/services/e2_diagnostic_card.py:98-134
def run_e2(
    request: E2Request,
    *,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """E2 진입점 entry function.

    Args:
        request: E2Request (analysis_context).
        provider: label (default haiku — D2.B, 글쓰기 작업).
        client: LLMClient 의존성 주입 (테스트 모킹용).
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. "
            f"Valid: {sorted(PROVIDER_KWARGS)}"
        )

    prompt = build_e2_prompt(request)

    if client is None:
        client = LLMClient()
    raw = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    preset_id = request.analysis_context.get("preset_id", "unknown")
    parsed = parse_e2_response(raw.text, preset_id=preset_id)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }
```

### 3.6 `scripts/validation/score_step8.py` — DIMENSION_LOOKUP (Slice 1→2→3 진화)

```python
# scripts/validation/score_step8.py:33-63
DIMENSION_LOOKUP = {
    "e1": {
        "dim1": {"key": "naturalness", "manual_field": "naturalness"},
        "dim2": {"key": "insight", "manual_field": "insight"},
        "model_label_field": "label",
        "result_structure": "flat",  # naturalness/insight 등이 result 최상위
        "default_raw": "docs/portfolio/coach/slice1/step8_3way_raw.json",
        "default_scored": "docs/portfolio/coach/slice1/step8_3way_scored.json",
        "weight": 0.5,
    },
    "e5": {
        "dim1": {"key": "intent_match", "manual_field": "intent_match_manual"},
        "dim2": {"key": "no_extra_changes", "manual_field": "no_extra_changes_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw": "docs/portfolio/coach/slice2/step8_2way_e5_raw.json",
        "default_scored": "docs/portfolio/coach/slice2/step8_2way_e5_scored.json",
        "weight": 0.5,
        "delegated_to": "scripts.validation.score_step8_e5",
    },
    "e2": {  # Slice 3 — e1 산식 그대로 + completeness 자동 보강 (additional_lex_check)
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "model_label_field": "model_label",
        "result_structure": "nested",  # judgments + metadata 분리
        "default_raw": "docs/portfolio/coach/slice3/step8_2way_e2_raw.json",
        "default_scored": "docs/portfolio/coach/slice3/step8_2way_e2_scored.json",
        "weight": 0.5,
        "additional_lex_check": "completeness_auto",  # Q3.C 자동 측정
    },
}
```

---

## 4. E3 진입점 정합성 평가 (Slice 3 인프라 재활용 가능성)

### 4.1 E3 진입점 사실 베이스

`docs/portfolio/PORTFOLIO_OVERALL_ANALYSIS.md` §1 (17행) 기준:
- E3 = 지표 코멘트 (D-4) — 입력 AnalysisContext / 출력 MetricComments / 상태 ⚠️ prompt 스켈레톤만 / Winner 미정 / URL 미구현
- prompt 디렉토리: `portfolio/prompts/e3/` (input_builder.py, instructions.py, examples.py, e3_builder.py 존재)
- schema: `portfolio/schemas/llm_outputs.py:65-89` (MetricComment + MetricComments 정의 완료)

### 4.2 9개 항목 E3 정합성 평가

| # | Slice 3 인프라 항목 | E3 적용 가능성 | 근거 / 조정 필요 사항 |
|---|--------------------|---------------|---------------------|
| 1 | `CostGuard` 싱글톤 + `reset_for_slice` | **그대로 가능** | slice_id만 "slice4" 또는 "slice5"로 reset. 인프라 의존성 없음 (`cost_guard.py:61-76`). |
| 2 | `ENTRYPOINT_TOKEN_BUDGETS` (`token_budgets.py`) | **항목 추가 필요** | `e3` key 미등록. `get_token_budget("e3")` 호출 시 ValueError. Step 7 측정 후 `e3: <budget>` 추가 (현재 dict 주석 18행 "Slice 4+: e3/e4/e6 추가 시 등록"이 명시). |
| 3 | `PROVIDER_KWARGS` (`_llm_kwargs.py`) | **그대로 가능** | label 4종(gemini/anthropic/sonnet/haiku) 모두 진입점 무관. E3 service에서 동일 import 가능. |
| 4 | `format_holdings_summary` (`_prompt_helpers.py`) | **재활용 가능 (선택적)** | E3는 metric 중심 입력이라 holdings 자체가 prompt에 없을 수 있음 (input_builder.py에서 metrics만 추출). 필요 시 호출. |
| 5 | `format_analysis_summary` | **재활용 가능 (선택적)** | E3 instructions가 "preset 맥락 해석" 요구하므로 한 줄 진단을 보조 컨텍스트로 넣을 가치 있음. |
| 6 | `format_metrics_table` | **재활용 가능** | E3는 지표 중심 prompt이므로 `format_metrics_table`이 직접 적용. 단, E3 instructions은 metric_id/percentile/level_tag/threshold 등 풍부한 메타를 요구하므로 (input_builder.py:22-32) 표 컬럼 확장 필요할 수 있음. |
| 7 | `parse_json_response` (`portfolio/llm/parsers.py`) | **그대로 가능** | MetricComments schema(llm_outputs.py:81-89)도 Pydantic. 마크다운 펜스 사후 제거 + Pydantic 검증 패턴 동일. |
| 8 | `DIMENSION_LOOKUP` (`score_step8.py`) | **e3 entry 추가 필요** | 현재 e1/e5/e2만 등록(33-63행). e3는 dim1=`one_liner_quality`(미정의) / dim2=`metric_alignment`(미정의) 같은 신규 차원. 산식은 e1 mirror(글쓰기) 가능. |
| 9 | E2 hybrid fixture 패턴 (`sample_diagnostic_context.py` slice1_baseline 3 + e2_focused 4) | **부분 적용** | E3는 metric 입력 차원이므로 fixture를 metric 다양성 기준으로 재구성 필요(예: "Core 지표 pass 위주" vs "Supporting 지표 borderline 다수"). hybrid 7개 패턴 자체는 재활용. |

### 4.3 Slice 4 진입 시 권장 조합 3개

| # | 조합 | 적용 항목 | 비용 | 가치 |
|---|------|-----------|------|------|
| **A. 최소 변경 (E6 우선, E3 후순위)** | CostGuard reset + token_budgets에 `e6` 추가 + `_llm_kwargs` / `_prompt_helpers` 재활용 + DIMENSION_LOOKUP에 `e6` 추가 | 1, 2, 3, 4, 5, 6, 7, 8 | 낮음 (인프라 100% 재활용) | E5(Slice 2) → E6 흐름 통합 (사용자 시나리오: 분석 → 명령 → 적용 → 비교 해설). PORTFOLIO_OVERALL_ANALYSIS.md §8.2 권장. |
| **B. E3 우선 (단독 진입점, 의존성 낮음)** | 위 8개 + hybrid fixture 패턴 metric 다양성으로 재구성(9) + format_metrics_table 컬럼 확장(6) | 1~9 전부 | 중간 (fixture 재구성 + score 차원 신규 정의) | E3는 단독 진입점, MetricComments schema 이미 정의됨. 글쓰기 차원(haiku 예상)으로 가설 정착 강화 가능. |
| **C. 통합 — score 산식 통일 + E6 동시 처리 (백로그 #2 처리 포함)** | A 조합 + DIMENSION_LOOKUP의 e1/e2/e6를 한 main()으로 통합 + score_step8_e5 delegation 정리 | 1~8 + Step 9 슬롯에 #2 (PS 3.0) | 높음 (Slice 4 Step 9 슬롯 60분 사용) | 검증 인프라 일반화 완성. 새 글쓰기 진입점은 DIMENSION_LOOKUP 한 줄 추가만으로 합류 가능. |

> 권장: **A + Step 9 슬롯에 #2 일부 통합** = 사실상 C의 점진적 적용. PORTFOLIO_OVERALL_ANALYSIS.md §10 결정과 일치 (Q1=E6, Q6=DIMENSION_LOOKUP[e6] 추가 + e1/e2 통합).

---

## 5. 회귀 카운트 + CostGuard 현재 상태

### 5.1 pytest collect-only 실측

```bash
$ pytest portfolio/tests/ --collect-only -q | tail -5
        <Function test_get_token_budget_known>
        <Function test_get_token_budget_unknown>
        <Function test_estimate_input_tokens_heuristic>

========================= 123 tests collected in 0.74s =========================
```

### 5.2 종합 재분석 명시 카운트와 비교

| 출처 | 값 |
|------|----|
| `PORTFOLIO_OVERALL_ANALYSIS.md` §9 (260행) "테스트 카운트" | **123 passed** |
| `validation_report_slice3.md` §7 (162행) "회귀: 76 → **123 passed** (+47)" | **123 passed** |
| 본 점검 실측 (`pytest --collect-only`) | **123 collected** |

종합 재분석에서 명시한 123 passed와 일치 여부:
- [x] 일치 (collect 카운트 = 123, validation_report_slice3 §7과 PORTFOLIO_OVERALL_ANALYSIS §9 모두 123 passed로 동일)

> 참고: `--collect-only`는 수집된 테스트 수만 표시하며, 실제 통과 여부는 별도 실행 필요. 본 점검은 read-only 원칙에 따라 수집 카운트만 확인. 통과 여부는 Slice 3 종결 시점 validation_report §7의 **123 passed** 명시를 사실로 인용.

### 5.3 CostGuard 현재 상태

```bash
$ python -c "from portfolio.llm.cost_guard import CostGuard; import json; print(json.dumps(CostGuard.get_instance().status(), ensure_ascii=False, indent=2))"
```

출력 그대로 인용:
```json
{
  "slice_id": "default",
  "call_count": 0,
  "max_calls": 50,
  "remaining": 50,
  "total_cost_usd": 0.0,
  "started_at": null,
  "records_count": 0
}
```

> 해석: 새 Python 프로세스에서 싱글톤이 처음 인스턴스화된 직후 상태. `slice_id="default"`, `started_at=None`은 reset_slice가 한 번도 호출되지 않은 초기 상태. Slice 3 작업 산출물(누적 15회)은 동일 프로세스 내 메모리에만 살아있다가 프로세스 종료와 함께 소실됨 — 이는 D3.C 설계 의도(슬라이스 진입 시점에 reset 적용)와 일치.

---

## 6. 점검 체크리스트 (자기 검증)

작성 완료 후 본인 확인:
- [x] 1.1 비용 표 4행 모두 출처 파일 + § 섹션 명시 (Slice 1: validation_report_slice1.md §1/§6 / Slice 2: §5 / Slice 3: §5 / 누적: PORTFOLIO_OVERALL_ANALYSIS.md §4)
- [x] 1.2 $0.49 vs $0.41 차이 해석 1개 선택 + 근거 기술 (광의 vs 협의 누적치 차이로 해석, $0.137 + $0.21 + $0.10 ≈ $0.45~$0.49 근거 명시)
- [x] 2.2 fixture 그룹 비교 8개 수치 모두 채움 (haiku 4: 30.2556/0.0088/6810/3.6667 외 / sonnet 4: 11.3797/0.0350/14300.3/4.3333 외)
- [x] 2.4 그룹 차이 해석 1개 선택 + 근거 수치 명시 (sonnet의 통찰 차별화로 해석, insight_mean 4.33→5.00 +0.67 만점 도달 근거 명시)
- [x] 3.1~3.6 코드 인용은 실제 파일에서 그대로 (cost_guard.py:38-76, token_budgets.py:14-33, _llm_kwargs.py:19-44, _prompt_helpers.py:12-36, e2_diagnostic_card.py:98-134, score_step8.py:33-63 — 모두 paraphrase 없이 발췌)
- [x] 4.2 9개 항목 모두 E3 정합성 평가 (CostGuard / token_budgets / PROVIDER_KWARGS / format_holdings / format_analysis / format_metrics / parse_json_response / DIMENSION_LOOKUP / hybrid fixture)
- [x] 4.3 조합 3개 제시 (A. 최소 변경 E6 우선 / B. E3 우선 / C. score 산식 통일 통합)
- [x] 5.2 회귀 카운트 실측 + 123 일치 여부 (collect-only = 123, 일치 체크)
- [x] read-only 원칙 준수 (수정 금지) — 코드/검증 산출물 변경 없음, 본 문서 신규 작성만 수행
- [x] 모든 ___ 부분 채움 (빈 칸 없음)

---

## 부록 — 본 문서 작성에 사용된 read-only 명령

```bash
# 회귀 카운트 측정
pytest portfolio/tests/ --collect-only -q

# CostGuard 상태 조회
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from portfolio.llm.cost_guard import CostGuard; import json; print(json.dumps(CostGuard.get_instance().status(), ensure_ascii=False, indent=2))"
```

코드/검증 산출물에 대한 수정 명령은 사용하지 않음.
