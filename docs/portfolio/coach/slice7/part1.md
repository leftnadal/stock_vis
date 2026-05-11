Slice 7 Part 1 작업 지시서 — E4 대화 Q&A 진입

슬라이스 목적: 6번째 글쓰기 외삽(차원 확장 — 종목 단위 → portfolio 단위 → 대화 multi-turn)으로 글쓰기 가설을 한 단계 더 견고화하고, Stock-Vis의 사용자 경험을 "정적 코멘트 생성" → "동적 대화" 차원으로 확장한다.
선행 결정 (Slice 7 진입 전 확정):

Step 0 = #25 rubric 표준화 (H3 noise 의심 → 측정 도구 선검증)
비용 임계 = $1.00 → $1.50 상향 (COST_POLICY.md 갱신)
Step 9 슬롯 = #19 LLMClient system 인자 (E4 본질 일관)

Part 1 범위: Step 0 (#25 rubric + H3 재측정) + COST_POLICY 갱신 + E4 schema 설계. LLM 호출 0 예상.
회귀 영향: 0 (docs + scripts only). 코드 변경은 Part 2(mock fixture)부터.

§0. 사전 체크 (5초)
bashgit status
git log --oneline -5
pytest -q # 395 passed 유지 (목표 KPI)

# 기준 자료 확인

cat docs/portfolio/coach/COST_POLICY.md # 현재 임계 확인
ls docs/portfolio/coach/slice6/step9_3_scored.json # H3 재측정 입력
ls docs/portfolio/coach/slice6/step9_2_eval_filled.md # rubric 적용 비교용

395 passed
COST_POLICY.md 현재 임계 = $1.00 확인
Slice 6 manual eval raw 자료 존재

§1. Step 0 — #25 manual eval rubric 표준화
1.1 rubric 신설 (docs only, LLM 호출 0)
docs/portfolio/coach/manual_eval_rubric.md 생성:
markdown# Manual Eval Rubric (Stock-Vis Portfolio Coach)

> **목적**: 모든 슬라이스 manual eval에서 평가자가 일관된 기준으로
> naturalness/insight를 평가하도록 표준화. Slice 6에서 발견한
> "큰 차이 없음" 관찰(좁은 분포 2~4 수렴) 대응.
>
> **적용 범위**: Slice 7 이후 모든 manual eval (Slice 1~6 raw 재평가 가능).

---

## A. Naturalness (자연스러움) — 1~5점

**평가 질문**: "한국 개인 투자자가 읽었을 때 어색함 없이 자연스럽게 흘러가는가?"

| 점수  | 기준      | 구체 신호                                                  |
| ----- | --------- | ---------------------------------------------------------- |
| **1** | 매우 부족 | 기계 번역체, 어색한 영문 직역, 한국어 어순 깨짐 (3건 이상) |
| **2** | 부족      | 일부 어색한 표현, 부자연스러운 조사/어미 (1~2건)           |
| **3** | 보통      | 무난하지만 정형적, 사람이 쓴 것 같진 않음                  |
| **4** | 좋음      | 자연스러운 흐름, 어색함 거의 없음                          |
| **5** | 매우 좋음 | 사람이 쓴 듯한 자연스러움, 문맥에 맞는 어휘 선택, 리듬감   |

**평가 가이드**:

- "정형적이지만 어색하지 않음" = 3점 (4점 아님 — 자연스러운 흐름이라면 4점)
- "기계 번역체 1건이라도 발견" = 2점 하한
- 분포 2~4에 수렴하는 안전 평가를 피하기 위해 **1점·5점도 적극 사용**

---

## B. Insight (통찰력) — 1~5점

**평가 질문**: "포트폴리오 지표(hhi/sector_hhi/top3_weight 등)를 의미 있게 해석하여 투자자에게 가치 있는 시사점을 제공하는가?"

| 점수  | 기준      | 구체 신호                                                          |
| ----- | --------- | ------------------------------------------------------------------ |
| **1** | 통찰 없음 | 숫자 나열만, 해석 0, 행동 시사점 0                                 |
| **2** | 약함      | 기본 해석만 있음 (예: "집중도가 높습니다"), preset 의도 반영 없음  |
| **3** | 보통      | 지표 1~2개 해석 + 일반적 시사점 (preset 의도 부분 반영)            |
| **4** | 좋음      | 지표 간 관계 + preset 의도 명확 반영 + 행동 시사점 1건             |
| **5** | 매우 좋음 | 지표 간 관계 + preset 의도 + 위험·기회 균형 + 행동 시사점 2건 이상 |

**평가 가이드**:

- "preset 의도 반영" 핵심 체크: e.g. concentrated_value(Buffett)에서는 "의도적 집중 vs 위험 집중" 구분이 필수
- "행동 시사점"은 구체성 요구 (예: "리밸런싱 검토" 권장 vs "분산이 부족합니다" 진술)
- 5점은 **드물게** 사용 (전체 5% 이하 권장) — 인플레이션 방지

---

## C. 안전 평가 회피 (분포 사용)

**Slice 6 관찰**: 평가자가 2~4점에 수렴하여 분포 좁음 → gap 측정 불안정.

**개선 규칙**:

1. **1점·5점 적극 사용**: 진짜 부족하면 1점, 진짜 뛰어나면 5점. "혹시 모르니 안전하게 2점" 회피.
2. **앵커링 회피**: 첫 entry에 3점 주고 나머지를 3점 근처에 두는 패턴 금지.
3. **블라인드 평가**: provider 라벨 가리고 평가 (Slice 6 패턴 유지).
4. **순서 무작위화**: seed 고정 random shuffle (Slice 6 seed=42 패턴 유지).

---

## D. 평가 양식 (예시)

Eval #1 (preset=V1)
[코멘트 본문]

naturalness: [ ? ] / 5 # 위 A 기준 참조
insight: [ ? ] / 5 # 위 B 기준 참조
note (선택): "어떤 표현이 어색했는지 / 어떤 통찰이 좋았는지"

---

## E. Rubric 사용 KPI

향후 모든 슬라이스 manual eval에서:

- [ ] 평점 분포: 1~5 전 범위 활용 (min 1, max 5 사용 시 +1점 KPI)
- [ ] 분포 폭(max - min): 평균 3.0 이상
- [ ] 5점 비율: 5% 이상 ~ 20% 이하 (양극단 균형)
- [ ] note 작성률: 30% 이상 (왜 그 점수인지 근거 확보)
      1.2 Slice 6 raw 데이터 H3 재측정
      scripts/slice7/remeasure_h3_with_rubric.py 생성:
      python"""
      Slice 7 Part 1 Step 0.2: Slice 6 manual eval raw 데이터에
      manual_eval_rubric.md 기준 재적용하여 H3 분기 진위 검증.

비교 대상:

- 기존: step9_2_eval_filled.md (rubric 없는 평가)
- 신규: step0_2_eval_filled_rubric.md (rubric 적용 평가)

분기 자동 결정:

- 재측정 결과 haiku insight gap ≤ 0.50 → H3 false alarm → #24 close, Slice 8 Step 0 변경
- 재측정 결과 haiku insight gap > 0.50 → H3 진짜 신호 → #24 Slice 8 Step 0 유지
  """

import json
import re
from pathlib import Path
from collections import defaultdict

ORIGINAL_PATH = Path("docs/portfolio/coach/slice6/step9_2_eval_filled.md")
RUBRIC_PATH = Path("docs/portfolio/coach/manual_eval_rubric.md")
KEY_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_key.json")
RUBRIC_EVAL_PATH = Path("docs/portfolio/coach/slice7/step0_2_eval_filled_rubric.md")
OUT_PATH = Path("docs/portfolio/coach/slice7/step0_2_h3_remeasure.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step0_2_h3_remeasure_report.md")

EVAL_BLOCK = re.compile(
r"##\s*Eval\s*#(\d+)._?naturalness:\s_\[?\s*(\d+(?:\.\d+)?)\s*\]?._?insight:\s_\[?\s*(\d+(?:\.\d+)?)\s*\]?",
re.DOTALL,
)

def parse_evals(text: str) -> dict:
results = {}
for match in EVAL_BLOCK.finditer(text):
eid = match.group(1)
nat = float(match.group(2))
ins = float(match.group(3))
results[eid] = {"naturalness": nat, "insight": ins}
return results

def stats(parsed: dict, key_map: dict, label: str) -> dict:
by_preset = defaultdict(list)
distribution = defaultdict(int)
for eid, scores in parsed.items():
meta = key_map[eid]
if meta["provider"] != "anthropic_haiku":
continue # H3는 haiku만 검증
by_preset[meta["preset_id"]].append(scores["insight"])
for v in (scores["naturalness"], scores["insight"]):
distribution[int(v)] += 1
insight_means = {p: sum(v) / len(v) for p, v in by_preset.items()}
if insight_means:
gap = round(max(insight_means.values()) - min(insight_means.values()), 4)
else:
gap = None
return {
"label": label,
"insight_means_by_preset": insight_means,
"insight_gap": gap,
"distribution_1_to_5": dict(sorted(distribution.items())),
"total_ratings": sum(distribution.values()),
}

def main():
key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))

    original = parse_evals(ORIGINAL_PATH.read_text(encoding="utf-8"))
    # rubric 재평가 파일은 사용자 작업 후 존재
    if not RUBRIC_EVAL_PATH.exists():
        print(f"⚠ {RUBRIC_EVAL_PATH} not found — rubric 재평가 미실행")
        print("  → docs/portfolio/coach/slice7/step0_2_eval_filled_rubric.md 작성 후 재실행")
        return
    rubric = parse_evals(RUBRIC_EVAL_PATH.read_text(encoding="utf-8"))

    s_orig = stats(original, key_map, "original")
    s_rub = stats(rubric, key_map, "rubric")

    # 분기 판정
    BASELINE = 0.50
    orig_gap = s_orig["insight_gap"]
    rub_gap = s_rub["insight_gap"]

    if rub_gap is None:
        verdict = "indeterminate"
        action = "rubric 재평가 누락 — 재실행 필요"
        h3_status = "unresolved"
    elif rub_gap <= BASELINE:
        verdict = "h3_false_alarm"
        action = (
            f"rubric 재측정 gap {rub_gap} ≤ {BASELINE} → H3는 측정 도구 noise."
            f" #24(preset 외삽 일반화 PS 2.5) close. Slice 8 Step 0 변경 필요."
        )
        h3_status = "closed_false_alarm"
    else:
        verdict = "h3_confirmed"
        action = (
            f"rubric 재측정 gap {rub_gap} > {BASELINE} → H3 진짜 신호."
            f" #24(preset 외삽 일반화 PS 2.5) Slice 8 Step 0 유지."
        )
        h3_status = "confirmed_keep"

    # 분포 폭 비교 (rubric 효과 확인)
    def dist_width(d):
        keys = [int(k) for k, v in d.items() if v > 0]
        return max(keys) - min(keys) if keys else 0

    orig_width = dist_width(s_orig["distribution_1_to_5"])
    rub_width = dist_width(s_rub["distribution_1_to_5"])
    rubric_effect = rub_width > orig_width  # rubric 적용 후 분포 넓어졌는가

    result = {
        "original": s_orig,
        "rubric": s_rub,
        "baseline": BASELINE,
        "verdict": verdict,
        "action": action,
        "h3_status": h3_status,
        "distribution_width_original": orig_width,
        "distribution_width_rubric": rub_width,
        "rubric_widened_distribution": rubric_effect,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 1 Step 0.2 — H3 재측정 보고\n",
        "## 비교\n",
        "| 항목 | 기존 (rubric 없음) | 신규 (rubric 적용) |",
        "|---|---|---|",
        f"| haiku insight gap | {orig_gap} | {rub_gap} |",
        f"| 분포 폭 (max-min) | {orig_width} | {rub_width} |",
        f"| 총 평점 수 | {s_orig['total_ratings']} | {s_rub['total_ratings']} |",
        "",
        f"## 판정: **{verdict}**",
        f"- action: {action}",
        f"- H3 상태: {h3_status}",
        f"- rubric 효과 (분포 넓어짐): {rubric_effect}",
    ]
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ result: {OUT_PATH}")
    print(f"✓ report: {REPORT_PATH}")
    print(f"  verdict: {verdict}")
    print(f"  gap: orig={orig_gap} → rubric={rub_gap}")
    print(f"  width: orig={orig_width} → rubric={rub_width}")

if **name** == "**main**":
main()
1.3 실행 절차
bash# 1) rubric 작성 (Claude Code가 1.1의 마크다운 생성)

# 2) Slice 6 eval form 복사하여 rubric 재평가용 양식 준비

cp docs/portfolio/coach/slice6/step9_1_eval_form.md \
 docs/portfolio/coach/slice7/step0_2_eval_form_rubric.md

# 3) 병진이 rubric 기준으로 재평가 (~15분, LLM 호출 0)

# 결과를 step0_2_eval_filled_rubric.md로 저장

# 4) 자동 분기 처리

python scripts/slice7/remeasure_h3_with_rubric.py
1.4 검증 체크리스트

manual_eval_rubric.md 생성 (5개 섹션 A~E)
step0_2_eval_form_rubric.md 작성
병진 rubric 재평가 수행 (~15분)
step0_2_h3_remeasure.json + report.md 생성
verdict ∈ {h3_false_alarm, h3_confirmed, indeterminate}
action 항목에 #24 처리 방향 명시

§2. COST_POLICY.md 갱신 ($1.00 → $1.50)
2.1 갱신 내용
docs/portfolio/coach/COST_POLICY.md 수정:
markdown## Cost Threshold Policy (Slice 7 갱신, 2026-05-11)

### 누적 광의 비용 임계: **$1.50** (이전 $1.00)

#### 갱신 근거 (정량)

- 6슬라이스 누적 비용 평균: $0.879 / 6 = **$0.147 per slice**
- E4 multi-turn 외삽 (Tier 1~3, turn 3개 평균): **$0.32~0.42**
- Slice 8/9 추정 비용 (E4 외 진입점): **$0.30~0.40**
- 안전 마진 (15%): **$0.20**
- **총 합산: $0.879 + $0.42 + $0.40 + $0.20 ≈ $1.90**
- 결론: $1.00은 부족, $1.50은 단기 안전(Slice 7~8), $2.00은 중기 안전(Slice 9~10)
- **Slice 7 진입 시 $1.50 채택** (Slice 9~10 진입 전 재검토)

#### 갱신 이력

- 2026-05-11 (Slice 7 Part 1): $1.00 → $1.50

#### 임계 도달 시 행동

- 누적 ≥ 80% ($1.20): 경고 + Slice 매트릭스 축소 검토
- 누적 ≥ 90% ($1.35): 즉시 매트릭스 축소 + 부채 처리 우선
- 누적 ≥ 100% ($1.50): Slice 진행 중단, 정책 재검토
  2.2 메모리 갱신
  기존 메모리 항목 중 비용 정책 언급 부분에 "임계 $1.50 (Slice 7 갱신)" 추가.

§3. E4 Schema 설계 (Tier 1~3 Multi-turn)
3.1 E4 진입점 정의
E4 = 대화 Q&A — 사용자가 자기 포트폴리오에 대해 질문하면 LLM이 답변하는 multi-turn 대화 기능.
Tier 정의 (PRD 기반)
Tier정의turn 수예시Tier 1단일 turn Q&A1"내 포트폴리오 집중도가 높아?" → 답변 종료Tier 2후속 질문 (세션 단기 기억)2~3Tier 1 답변 후 "그럼 어떻게 분산해야 해?"Tier 3심층 분석 (세션 + 분석엔진 컨텍스트)3+추가로 "현재 보유 종목 중 어떤 걸 줄여야 해?"

Tier 2 세션 요약 정책: Phase 2 (사용자 메모리 정책). Slice 7 Part 1에서는 턴별 raw 컨텍스트 누적만 schema에 반영.

3.2 schema 구조 (Pydantic)
portfolio/coach/schemas/e4_conversation.py (Part 2에서 구현, Part 1은 docs only):
python"""
E4 대화 Q&A schema 설계 (Slice 7 Part 1, docs only).

Tier 1~3 multi-turn 지원. Tier 2 세션 요약은 Phase 2.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ===== Input =====

class E4ConversationTurn(BaseModel):
"""단일 turn (사용자 질문 또는 LLM 답변)."""
role: Literal["user", "assistant"]
content: str
timestamp: datetime
turn_idx: int = Field(ge=0)

class E4ConversationInput(BaseModel):
"""E4 대화 진입점 입력."""

    # 포트폴리오 컨텍스트 (E3 portfolio-level과 공통)
    portfolio_id: str
    preset_id: str
    portfolio_metrics: dict  # E3 portfolio Core 7 지표 재활용
    holdings_summary: str    # Top-N holdings 텍스트 요약

    # 대화 컨텍스트
    conversation_history: list[E4ConversationTurn]  # Tier 1: 0건 / Tier 2: 1~2건 / Tier 3: 3+건
    current_user_question: str
    tier: Literal[1, 2, 3]

    # 메타
    session_id: str
    max_history_turns: int = 5  # 토큰 절약: 마지막 N 턴만 prompt에 반영

# ===== Output =====

class E4ConversationOutput(BaseModel):
"""LLM 답변."""
answer: str = Field(min_length=20, max_length=2000)

    # tier별 추가 필드
    referenced_metrics: list[str] = Field(
        default_factory=list,
        description="이 답변에서 인용한 portfolio_metrics key들",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="후속 질문 추천 (Tier 2/3에서 활용)",
    )
    confidence: Literal["high", "medium", "low"] = "medium"

3.3 token budget 추정
token_budgets.py에 e4_conversation entry 추가 (Part 2에서 코드 반영, Part 1은 추정만):
Tierinput estimateoutput estimatebudget 권장Tier 1~3,500 (portfolio context + question)~6006,000 (안전 마진 70%)Tier 2~5,000 (Tier 1 + history 1~2턴)~6008,000Tier 3~7,500 (history 3+턴)~80012,000
근거: Slice 6 e3_portfolio P90/max input 4,030 → portfolio context 약 3,500 char. 대화 history는 turn당 ~700 char 추정 (질문 200 + 답변 500).
#β2 (estimator 외삽 정밀도) 재오픈 상태이므로, Part 2에서 실측 후 재조정.
3.4 분기 시나리오 (E4 특수)
기존 케이스 A~E (schema/completeness/cost/token/fallback) 외 E4 추가 케이스:
케이스조건처리I1history 턴 5개 초과 (max_history_turns 위반)가장 오래된 턴부터 제거, fallback flag setI2tier=2/3인데 history 비어있음Tier 1로 자동 다운그레이드, warning logI3answer가 history와 일관성 없음 (LLM 평가)manual eval 단계에서 분기I4referenced_metrics가 portfolio_metrics에 없는 key 인용hallucination 의심 — manual eval 분기

§4. Mock Fixture 설계 (Part 1에서는 시나리오 정의만)
4.1 시나리오 매트릭스 (15 cases)
시나리오presettierturn 수분기 케이스S1V1 (balanced)11baselineS2V122follow-upS3V133deepS4V2 (focused)11baselineS5V222follow-upS6V3 (factor)11baselineS7V322follow-upS8V4 (concentrated_value)11baseline (G6 관찰)S9V422follow-up (#23 영향 확인)S10V5 (aligned)11baselineS11V533deepS12V126 (I1 trigger)history overflowS13V120 (I2 trigger)empty history downgradeS14V234metrics inconsistent (I4 후보)S15V311confidence=low 분기
근거: Slice 6 매트릭스 10 cases 기반 확장 (+5 cases는 tier 2/3 multi-turn + 분기 트리거). preset 5종 cover, tier 3종 cover.
4.2 fixture 파일 구조 (Part 2에서 구현)
tests/fixtures/portfolio/e4_conversation/
├── S01_V1_tier1.json # input + expected_output
├── S02_V1_tier2.json
├── ...
└── S15_V3_tier1_low_conf.json

§5. 분기 시나리오 (Part 1 안에서)
시나리오트리거조치J1H3 verdict = h3_false_alarm#24 close 메모리 갱신 + Slice 8 Step 0 후보 재선정 (#23 또는 #β2)J2H3 verdict = h3_confirmed#24 Slice 8 Step 0 유지 + #24 PRD 작성 시작J3H3 verdict = indeterminaterubric 재평가 누락 → 병진에게 알림, Part 1 보류J4rubric 적용 후 분포 폭 변화 없음rubric 효과 약함 — rubric 보완 (사례 추가)J5E4 token budget 추정이 Slice 6 e3_portfolio 대비 50% 이상 큼#β2 재오픈 명시 + Part 2에서 실측 우선

§6. 회귀 영향 KPI
단계회귀 영향비용부채 변화§1 (rubric + H3 재측정)0 (docs + scripts only)$0-1 (J1) 또는 0 (J2)§2 (COST_POLICY 갱신)0 (docs only)$00§3 (E4 schema 설계)0 (docs only)$00§4 (mock fixture 시나리오)0 (docs only)$00
총 회귀 변화 예상: 0 (코드 변경 없음)

§7. 완료 보고 양식
[Slice 7 Part 1 완료 보고]

== Step 0.1 (rubric 표준화) ==

- manual_eval_rubric.md 생성: ✓
- 5개 섹션 (A. naturalness / B. insight / C. 회피 / D. 양식 / E. KPI): ✓

== Step 0.2 (H3 재측정) ==

- step0_2_eval_form_rubric.md 생성: ✓
- 병진 재평가 완료: ✓ (소요 ??분)
- step0_2_h3_remeasure.json + report.md 생성: ✓
- verdict: ??? (h3_false_alarm / h3_confirmed / indeterminate)
- gap: orig=??? → rubric=???
- 분포 폭: orig=??? → rubric=???

== Step 2 (COST_POLICY 갱신) ==

- 임계 $1.00 → $1.50 갱신: ✓
- 갱신 근거 명시: ✓
- 단계별 행동 정의: ✓

== Step 3 (E4 schema) ==

- E4ConversationInput/Output Pydantic 설계: ✓ (docs only)
- Tier 1~3 정의: ✓
- token budget 추정 표 (Tier별): ✓
- 분기 케이스 I1~I4 정의: ✓

== Step 4 (mock fixture 시나리오) ==

- 15 cases 매트릭스: ✓ (preset 5종 × tier 3종 cover)
- fixture 파일 구조 정의: ✓

== 종합 ==

- 회귀: 395 → 395 (변화 0)
- 비용: $0 (LLM 호출 0)
- 누적 광의: $0.879 (변화 없음, 임계 $1.50 갱신 후 마진 41%)
- 신규 부채: 0건
- 분기 시나리오 발동: J1 또는 J2 (verdict에 따라)

§I. 산출물 (8건 예상)
§II. H3 재측정 결과 (orig vs rubric)
§III. #24 처리 방향 (J1=close / J2=Slice 8 Step 0 유지)
§IV. Commit 메시지 권장
§V. 핵심 결과 (rubric 표준화 / 임계 상향 / E4 schema 확정)

§8. Commit 메시지 권장
docs(slice7/part1/step0.1): manual eval rubric 표준화 (#25 처리)
feat(slice7/part1/step0.2): H3 재측정 스크립트 + 자동 분기 판정
docs(slice7/part1/step0.2): rubric 재평가 결과 (verdict=???)
docs(slice7/part1/cost_policy): 비용 임계 $1.00 → $1.50 갱신
docs(slice7/part1/step3): E4 conversation schema 설계 (Tier 1~3)
docs(slice7/part1/step4): E4 mock fixture 시나리오 15 cases

§9. 완료 기준 (Part 1 종결 조건)

manual_eval_rubric.md 생성 (5개 섹션)
H3 재측정 완료 + verdict 확정
COST_POLICY.md 임계 $1.50 갱신
E4 schema 설계 docs 작성 (Pydantic 코드 + Tier 정의 + token budget 추정)
mock fixture 시나리오 15 cases 정의
회귀 395 유지
누적 광의 비용 $0.879 유지
분기 J1 또는 J2 처리 결정 (verdict 기반)
commit 5~6건 완료

§10. Part 2 진입 사전 등록
Part 1 종결 후 Part 2 작업 범위:

E4 Pydantic 코드 구현 (portfolio/coach/schemas/e4_conversation.py)
token_budgets.py에 e4_conversation 추가 (Tier별 6000/8000/12000)
mock fixture JSON 15 cases 구현
E4 estimator 정확도 검증 (#β2 재오픈 대상)
회귀 추가 ~10~15건 예상
비용: $0 (mock 단계, LLM 호출 0)
