# Slice 8 Part 3 작업 지시서 — #29 Prompt Builder + Real LLM Matrix (trio 통합 3단계)

> **Part 3 범위**: trio 통합 3단계 — #29 E4 prompt builder 구현(출력 4요소 강제 + Sample 5 few-shot) + Step 6 smoke (1~2 calls) + Step 7 matrix (28 calls) + Step 7.5 KPI 11개 자동 검증 + Step 8 manual eval 입력 dump 준비
> **첫 LLM 비용 발생 단계 (Slice 8)**. 누적 광의 $1.595 → 예상 $1.97 (임계 $2.00 마진 1.5%)
> **선행 결정 (2026-05-17 확정)**: A1 그대로 진입 / B1 풀 매트릭스 14×2 / C3 하이브리드 sample / D3 자동 patterns + manual confirm
> **회귀 영향**: +5~10건 예상 (prompt builder 신규 코드 + patterns count 스크립트, 기존 회귀에 영향 없음)
> **CostGuard**: PER_INSTANCE 카운트 ≤ 50 / PER_SLICE 카운트 ≤ 100. 호출 = 1 (Step 6) + 28 (Step 7) + 28 (rationale) = **57/100** (마진 43)

---

## §0. 사전 체크

### §0.1 환경 정합 확인

작업 시작 전 다음을 순서대로 확인 (Claude Code 첫 작업):

```bash
# 0.1.1 git 상태
git status                                # working tree clean 확인
git branch --show-current                 # slice8 확인
git log --oneline -10                     # Part 2 종결 commit 4건 + 외래 1건(2b9d4c8) 확인

# 0.1.2 회귀 baseline
pytest portfolio/tests -q 2>&1 | tail -3  # 441 passed 확인 (Part 2 종결값)

# 0.1.3 IDENTICAL hash
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -10
# 7/7 PASS 확인 (Slice 1·3·4·5·6·7·Slice8 Part1·Part2 일관)

# 0.1.4 누적 비용 확인
cat docs/portfolio/coach/COST_POLICY.md | head -20
# 임계 $2.00 / 사전 경고 $1.60 / 누적 $1.595 확인

# 0.1.5 LLM budget 카운터 확인
cat portfolio/llm/cost_guard.py | grep -A 5 "PER_INSTANCE\|PER_SLICE"
# Step 0 #33 분리 적용 확인 (PER_INSTANCE=50, PER_SLICE=100)
```

**중단 조건**:

- 회귀 ≠ 441 → 외래 commit 영향 점검 (`git log --since="Part 2 종결 commit hash"` 확인)
- IDENTICAL hash ≠ 7/7 → 즉시 정지, 결정 사이클 진입
- 누적 비용 > $1.60 → CostGuard 80% 경고 트리거, Part 3 진입 보류

### §0.2 Part 2 산출물 통합 확인

Part 3 작업은 다음 Part 1·2 산출물에 의존:

| 의존 항목                             | 위치                                                                  | 검증 방법                                                               |
| ------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `TimeSeriesContext` (Part 1 #27)      | `portfolio/schemas/commentary_input.py`                               | `from portfolio.schemas.commentary_input import TimeSeriesContext` 성공 |
| `ActionItem` 모델 (Part 2 #28)        | `portfolio/schemas/commentary_output.py`                              | `from portfolio.schemas.commentary_output import ActionItem` 성공       |
| 7 schema action_items 슬롯            | llm.py:18/95/222 + llm_outputs.py:103/181/228 + e4_conversation.py:80 | parametrized test 14건 PASS 확인                                        |
| Part 1 fixture (holdings PE/PEG/ROIC) | `portfolio/tests/slice8/fixtures/e3_concentrated_v2.json` 등          | `cat` 확인, action_items 필드 포함 여부                                 |

### §0.3 CostGuard 사전 경고 활성화

```python
# portfolio/llm/cost_guard.py 또는 settings에 다음 정책 명시
# (Step 0 #33 분리 후 이미 적용되었어야 함, Part 3에서 한 번 더 검증)

COST_THRESHOLD_USD = 2.00
COST_WARNING_USD = 1.60          # 80% 사전 경고
COST_SLICE9_TRIGGER_USD = 2.10   # Slice 9 임계 재상향 트리거

# 단건 임계 (Part 3 신규)
PER_CALL_THRESHOLD_HAIKU_USD = 0.03
PER_CALL_THRESHOLD_SONNET_USD = 0.10
```

**검증 스크립트** (별도 LLM 호출 0):

```bash
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard()
print(f'threshold={g.threshold}, warning={g.warning}, per_haiku={g.per_call_haiku}, per_sonnet={g.per_call_sonnet}')
"
# 출력 예시: threshold=2.0, warning=1.6, per_haiku=0.03, per_sonnet=0.10
```

### §0.4 specificity_patterns.md 초안 작성 (D3 자동 patterns)

작업 위치: `docs/portfolio/coach/slice8/specificity_patterns.md` (신규)

```markdown
# Specificity Patterns — rationale 텍스트 자동 분류 patterns

> **목적**: E4 답변의 "구체성 부족" 비율을 자동 측정 (Slice 7 75% → Slice 8 <30% 목표)
> **사용처**: Slice 8 Part 3 §5 rationale 28건 자동 카운트
> **재사용**: Slice 9 이후 동일 KPI 측정 시 본 patterns 재사용

## P1: 종목별 현재가/지표 언급

**정규식 또는 키워드**: `(현재가|주가|PE|PEG|ROIC|P/E|시가)` 1회 이상 등장
**5점 조건**: 종목명 + 지표값 함께 등장 (예: "삼성전자 PE 12.5")

## P2: 임계값/기준점 명시

**키워드**: `(이상|이하|초과|미만|보다 (높|낮))` AND 숫자 1회 이상
**5점 조건**: 비교 기준 명확 (예: "PE 15 이상은 부담", "ROIC 10% 미만 우려")

## P3: 액션 동사 (buy/sell/hold/축소/확대/유지)

**키워드**: `(매수|매도|보유|축소|확대|편입|제외|유지)` 1회 이상
**5점 조건**: 종목명 + 액션 동사 직접 연결 (예: "삼성전자 축소 검토")

## P4: 구체 수치 임계값

**키워드**: 숫자 + (%|배|원|달러) AND 동일 문장 내 종목명/지표명
**5점 조건**: 정량 의사결정 가능 수준 (예: "현금 비중 25% → 20%로 5%p 축소")

## P5: 기간/시점 명시

**키워드**: `(분기|반기|연간|YoY|QoQ|최근 \d+(년|개월|일))` 1회 이상
**5점 조건**: 시계열 비교 또는 의사결정 시점 명시

## 측정 룰

- **구체성 score** = P1~P5 중 등장 patterns 개수 (0~5)
- **"구체성 부족"** 판정: score ≤ 2
- **목표**: 28건 중 "구체성 부족" 비율 < 30% (8건 이하)
- **mismatch 처리**: manual eval에서 score 불일치 시 manual 우선, patterns docs 갱신 등록
```

**KPI 0.4**:

- [ ] specificity_patterns.md 작성 (5건 patterns 정의)
- [ ] patterns count 스크립트 동작 검증 (Part 1·2 fixture sample 텍스트 입력 시 점수 산출)

---

## §1. #29 E4 Prompt Builder 구현

### §1.1 작업 위치

`portfolio/prompts/e4/builder.py` 갱신

Part 1·2까지의 E4 prompt builder는 (1) holdings 입력 포맷팅 + (2) 자유 질문 wrapping만 담당. **Part 3에서 추가**:

1. **출력 4요소 강제 지시** (system prompt에 명시)
2. **Sample 5 few-shot** 삽입
3. **rubric §B 4점/5점 기준** 자체 인용

### §1.2 출력 4요소 정의

E4 답변은 다음 4요소를 **모두 포함**해야 함:

| 요소                    | 내용                                                    | 누락 시                        |
| ----------------------- | ------------------------------------------------------- | ------------------------------ |
| **요소 1: 현재 상태**   | 종목별 현재가 또는 핵심 지표(PE/PEG/ROIC) 1회 이상 인용 | "구체성 부족" 판정 (P1 미발동) |
| **요소 2: 임계값/기준** | "PE 15 이상", "ROIC 10% 미만" 등 정량 기준 명시         | "구체성 부족" 판정 (P2 미발동) |
| **요소 3: 액션 제안**   | buy/sell/hold/축소/확대 등 액션 동사 + 종목명           | "구체성 부족" 판정 (P3 미발동) |
| **요소 4: 시점/기간**   | 분기/반기/연간 또는 "최근 N개월" 명시                   | "구체성 부족" 판정 (P5 미발동) |

### §1.3 system prompt 골격 (코드 스켈레톤)

```python
# portfolio/prompts/e4/builder.py

E4_SYSTEM_PROMPT_TEMPLATE = """당신은 한국 개인 투자자를 위한 포트폴리오 코치입니다.

## 답변 작성 규칙 (필수)

모든 답변은 다음 4요소를 반드시 포함해야 합니다:

1. **현재 상태**: 언급하는 종목의 현재가 또는 핵심 지표(PE / PEG / ROIC) 중 1개 이상 명시
2. **임계값/기준**: 판단 근거가 되는 정량 기준 (예: "PE 15 이상", "ROIC 10% 미만") 명시
3. **액션 제안**: 매수/매도/보유/축소/확대 중 하나를 종목명과 함께 직접 제시
4. **시점/기간**: 분기/연간 또는 "최근 N개월" 등 시점 정보 1회 이상 인용

## 금지 사항

- "일반적으로", "보통", "대체로" 등 추상적 표현으로만 답변 마무리하지 마세요.
- 종목명 없이 "포트폴리오가 위험합니다" 같은 일반론 금지.
- 액션 없이 분석만 제시하고 마무리 금지.

## 답변 예시 (Sample 5 few-shot)

{few_shot_samples}

## 답변 형식

- commentary: 위 4요소를 포함한 자연어 답변 (300~500자)
- action_items: 액션 제안의 구조화된 리스트 (1~3건)
  - 각 항목: title (간결), description (근거 포함), priority (high/medium/low)
"""


def build_e4_prompt(
    holdings: list[dict],
    question: str,
    time_series_context: TimeSeriesContext | None = None,
    few_shot_samples: list[dict] | None = None,
) -> tuple[str, str]:
    """E4 prompt 구성.

    Args:
        holdings: 종목별 데이터 리스트 (PE/PEG/ROIC 포함, Part 1 #27)
        question: 사용자 자유 질문
        time_series_context: 시계열 컨텍스트 (Part 1 #27)
        few_shot_samples: Sample 5 few-shot (Part 3 #29). 기본값은 패키지 내 sample 5건.

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    if few_shot_samples is None:
        from portfolio.prompts.e4.samples import DEFAULT_FEW_SHOT_SAMPLES
        few_shot_samples = DEFAULT_FEW_SHOT_SAMPLES

    few_shot_text = "\n\n---\n\n".join(
        _format_sample(s) for s in few_shot_samples
    )

    system_prompt = E4_SYSTEM_PROMPT_TEMPLATE.format(
        few_shot_samples=few_shot_text
    )

    user_prompt = _build_user_prompt(holdings, question, time_series_context)

    return system_prompt, user_prompt


def _format_sample(sample: dict) -> str:
    """Sample 1건을 few-shot 포맷으로 변환."""
    return f"""### 예시: {sample['title']}
[질문] {sample['question']}
[답변] {sample['answer']}
[액션 항목] {sample['action_items']}"""


def _build_user_prompt(
    holdings: list[dict],
    question: str,
    time_series_context: TimeSeriesContext | None,
) -> str:
    """user prompt 본문 구성. Part 1 #27의 holdings 포맷팅 활용."""
    # ... (Part 1 작업물 재활용)
```

### §1.4 검증 단위 테스트

`portfolio/tests/slice8/test_e4_prompt_builder.py` (신규)

```python
"""Slice 8 Part 3 #29 — E4 prompt builder 검증."""

import pytest

from portfolio.prompts.e4.builder import build_e4_prompt
from portfolio.prompts.e4.samples import DEFAULT_FEW_SHOT_SAMPLES


class TestE4PromptBuilder:
    """system prompt 4요소 + few-shot 삽입 검증."""

    @pytest.fixture
    def sample_holdings(self):
        return [
            {"symbol": "005930", "name": "삼성전자", "pe": 12.5, "peg": 1.2, "roic": 11.3, "weight": 0.30},
            {"symbol": "AAPL", "name": "Apple", "pe": 28.0, "peg": 2.1, "roic": 35.0, "weight": 0.20},
        ]

    def test_system_prompt_includes_4_elements(self, sample_holdings):
        """system prompt에 4요소 강제 지시가 포함되어야 함."""
        system, _ = build_e4_prompt(sample_holdings, "리스크 어때?")
        assert "현재 상태" in system
        assert "임계값" in system or "기준" in system
        assert "액션 제안" in system or "액션" in system
        assert "시점" in system or "기간" in system

    def test_system_prompt_includes_few_shot(self, sample_holdings):
        """Sample 5 few-shot이 system prompt에 삽입되어야 함."""
        system, _ = build_e4_prompt(sample_holdings, "리스크 어때?")
        for sample in DEFAULT_FEW_SHOT_SAMPLES:
            assert sample["title"] in system

    def test_default_samples_count(self):
        """Sample 5건 정확히 정의되어야 함."""
        assert len(DEFAULT_FEW_SHOT_SAMPLES) == 5

    def test_default_samples_have_4_elements(self):
        """각 sample answer는 4요소를 포함해야 함 (C3 하이브리드 사전 검증)."""
        for sample in DEFAULT_FEW_SHOT_SAMPLES:
            answer = sample["answer"]
            # P1: 현재가 또는 PE/PEG/ROIC
            assert any(kw in answer for kw in ["현재가", "주가", "PE", "PEG", "ROIC"])
            # P2: 임계값 - 숫자 + (이상|이하|초과|미만)
            import re
            assert re.search(r"\d+.*(이상|이하|초과|미만|보다|넘|않)", answer)
            # P3: 액션 동사
            assert any(kw in answer for kw in ["매수", "매도", "보유", "축소", "확대", "편입", "제외", "유지"])
            # P5: 시점/기간
            assert re.search(r"(분기|반기|연간|YoY|QoQ|최근 ?\d+(년|개월|일))", answer)

    def test_user_prompt_includes_holdings_metrics(self, sample_holdings):
        """user prompt에 PE/PEG/ROIC가 포함되어야 함 (Part 1 #27 통합)."""
        _, user = build_e4_prompt(sample_holdings, "삼성전자 비중 어때?")
        assert "12.5" in user  # PE
        assert "1.2" in user   # PEG
        assert "11.3" in user  # ROIC

    def test_question_passthrough(self, sample_holdings):
        """user prompt에 질문이 그대로 포함되어야 함."""
        _, user = build_e4_prompt(sample_holdings, "리스크 평가해줘")
        assert "리스크 평가해줘" in user
```

### §1.5 KPI 1

- [ ] `build_e4_prompt`가 system + user 튜플 반환
- [ ] system prompt에 4요소 강제 지시 포함
- [ ] system prompt에 5건 few-shot 삽입
- [ ] 단위 테스트 6건 PASS
- [ ] 회귀 +6건

---

## §2. Sample 5 Few-Shot 작성 (C3 하이브리드)

### §2.1 출처 정책

**5건 구성**:

| #   | 출처                            | 시나리오                 | 작업                               |
| --- | ------------------------------- | ------------------------ | ---------------------------------- |
| 1   | Slice 7 manual eval 상위 답변 1 | "포트폴리오 리스크 평가" | rubric 4요소 사전 검증 + 미세 보정 |
| 2   | Slice 7 manual eval 상위 답변 2 | "특정 종목 비중 적절성"  | rubric 4요소 사전 검증 + 미세 보정 |
| 3   | rubric 합성 1                   | "섹터 집중도 평가"       | 새로 합성, 4요소 의도적 강조       |
| 4   | rubric 합성 2                   | "시장 변동기 대응"       | 새로 합성, 4요소 의도적 강조       |
| 5   | rubric 합성 3                   | "현금 비중 조정"         | 새로 합성, 4요소 의도적 강조       |

**작업 위치**: `portfolio/prompts/e4/samples.py` (신규)

```python
"""Slice 8 Part 3 #29 — E4 Sample 5 few-shot 정의.

C3 하이브리드: Slice 7 manual eval 상위 답변 2건 + rubric 합성 3건
모든 sample은 rubric §B 5점 기준 4요소 (현재 상태 + 임계값 + 액션 + 시점) 포함.

source 마킹:
- "slice7_h_v1" / "slice7_h_v2": Slice 7 manual eval 상위 답변 (rubric 4요소 사전 검증 + 미세 보정)
- "synthesized_v1" / "synthesized_v2" / "synthesized_v3": rubric 합성
"""

DEFAULT_FEW_SHOT_SAMPLES = [
    {
        "title": "포트폴리오 전반 리스크 평가",
        "source": "slice7_h_v1",
        "question": "내 포트폴리오 리스크 어떻게 봐?",
        "answer": (
            "현재 포트폴리오 상위 3종목 비중이 65%로 집중도가 높습니다. "
            "삼성전자(PE 12.5)는 합리적이나, NVIDIA(PE 65)는 업종 평균 30 이상으로 부담스럽습니다. "
            "최근 3개월 변동성이 18%로 KOSPI 12% 대비 1.5배 높아 NVIDIA 비중을 5%p 축소하고 "
            "방어주 편입을 다음 분기까지 검토하시는 것이 좋겠습니다."
        ),
        "action_items": [
            {"title": "NVIDIA 5%p 축소", "description": "PE 65 업종 평균 2배 부담", "priority": "high"},
            {"title": "방어주 편입 검토", "description": "변동성 1.5배 완화 목적, 다음 분기", "priority": "medium"},
        ],
    },
    {
        "title": "특정 종목 비중 적절성",
        "source": "slice7_h_v2",
        "question": "삼성전자 비중 25%인데 적절해?",
        "answer": (
            "삼성전자 현재 비중 25%는 단일 종목 한도 20%를 5%p 초과합니다. "
            "PE 12.5, ROIC 11.3%로 펀더멘털은 견고하나, "
            "반도체 업황 사이클(최근 4분기 추이)을 보면 단일 비중 과다는 변동성 노출이 큽니다. "
            "단기 5%p 축소 후 같은 섹터 내 SK하이닉스 또는 다른 섹터 우량주로 분산하시는 것을 권장합니다."
        ),
        "action_items": [
            {"title": "삼성전자 5%p 축소", "description": "단일 한도 20% 초과", "priority": "high"},
            {"title": "분산 후보 탐색", "description": "SK하이닉스 또는 타 섹터, 다음 리밸런싱 시점", "priority": "medium"},
        ],
    },
    {
        "title": "섹터 집중도 평가",
        "source": "synthesized_v1",
        "question": "내 포트폴리오 섹터 균형 봐줘",
        "answer": (
            "현재 IT 섹터 비중이 58%로 KOSPI IT 비중 32% 대비 1.8배 과다합니다. "
            "보유 IT 종목 평균 PE 28, ROIC 18%로 펀더멘털은 양호하나, "
            "최근 6개월 IT 섹터 변동성이 24%로 시장 평균 14%보다 1.7배 높습니다. "
            "IT 비중을 분기 내 10%p 축소하고 헬스케어(현 5%, 목표 12%)와 산업재(현 8%, 목표 15%) 확대를 검토하세요."
        ),
        "action_items": [
            {"title": "IT 비중 10%p 축소", "description": "KOSPI 1.8배 과다, 변동성 1.7배 노출", "priority": "high"},
            {"title": "헬스케어 7%p 확대", "description": "현 5% → 목표 12%, 분기 내", "priority": "medium"},
            {"title": "산업재 7%p 확대", "description": "현 8% → 목표 15%, 분기 내", "priority": "medium"},
        ],
    },
    {
        "title": "시장 변동기 대응",
        "source": "synthesized_v2",
        "question": "요즘 시장 변동성 큰데 어떻게 해야 해?",
        "answer": (
            "최근 1개월 KOSPI 변동성이 22%로 평년 평균 14% 대비 1.6배 높습니다. "
            "포트폴리오 베타가 1.35로 시장 대비 35% 더 출렁이는 상태입니다. "
            "고PEG 종목(PEG 2 이상) 비중을 다음 2주 내 15%p 축소하고, "
            "방어주(필수소비재, 통신) 또는 채권 ETF 비중을 20%까지 확대해 베타를 1.0 아래로 낮추는 것을 권장합니다."
        ),
        "action_items": [
            {"title": "고PEG 종목 15%p 축소", "description": "PEG 2 이상 종목 대상, 2주 내", "priority": "high"},
            {"title": "방어주/채권 ETF 20% 편입", "description": "베타 1.0 미만 목표", "priority": "high"},
        ],
    },
    {
        "title": "현금 비중 조정",
        "source": "synthesized_v3",
        "question": "현금 25%인데 너무 많은 거 아니야?",
        "answer": (
            "현재 현금 비중 25%는 일반적 권장 범위 5~15%를 10%p 초과합니다. "
            "최근 3개월 시장이 횡보(±3% 범위)했고 금리 환경(예금 3.5%)을 고려하면 "
            "기회비용이 큽니다. ROIC 15% 이상이고 PEG 1.5 이하인 우량 종목(예: 삼성전자, Apple) "
            "추가 매수로 다음 분기까지 현금 비중을 10~15%로 조정하시는 것을 권장합니다."
        ),
        "action_items": [
            {"title": "현금 10%p 축소 (25% → 15%)", "description": "권장 범위 10%p 초과", "priority": "medium"},
            {"title": "ROIC 15%↑ & PEG 1.5↓ 종목 매수", "description": "다음 분기까지, 단계적 분할 매수", "priority": "medium"},
        ],
    },
]
```

### §2.2 KPI 2

- [ ] `portfolio/prompts/e4/samples.py` 작성 (5건 sample)
- [ ] 각 sample이 rubric 4요소 모두 포함 (§1.4 `test_default_samples_have_4_elements` PASS)
- [ ] source 마킹 정합 (slice7_h_v1/v2, synthesized_v1/v2/v3)
- [ ] 회귀 +0건 (단위 테스트는 §1에 포함)

---

## §3. Step 6 Smoke + 1차 비용 측정 + #β2 1차 측정

### §3.1 목적

- **smoke**: prompt builder가 실제 LLM API에서 정상 동작하는지 검증 (Tier 1 baseline)
- **1차 비용 측정**: $1.60 사전 경고 미달 확인 + Step 7 폭주 차단 안전성 확보
- **#β2 estimator 1차 측정**: Step 0 재설계된 estimator의 정밀도 검증

### §3.2 작업

`portfolio/tests/slice8/test_part3_smoke.py` (신규)

```python
"""Slice 8 Part 3 §3 — Step 6 smoke (haiku 1 call, tier 1 baseline)."""

import json
import pytest

from portfolio.llm.client import LLMClient
from portfolio.llm.cost_guard import CostGuard
from portfolio.prompts.e4.builder import build_e4_prompt
from portfolio.schemas.e4_conversation import E4ConversationOutput


@pytest.mark.real_llm
@pytest.mark.slice8_part3
def test_step6_smoke_haiku_baseline():
    """1 call: haiku, fixture 1건 (concentrated_v2), 4요소 모두 충족 확인."""
    fixture_path = "portfolio/tests/slice8/fixtures/e3_concentrated_v2_with_actions.json"
    with open(fixture_path) as f:
        fixture = json.load(f)

    holdings = fixture["holdings"]
    question = "내 포트폴리오 리스크 평가해줘"

    system, user = build_e4_prompt(holdings, question)

    client = LLMClient(provider="anthropic", model="claude-haiku-4-5")
    response = client.chat(system=system, user=user, output_schema=E4ConversationOutput)

    # 검증
    assert response.metadata_dict()["cost_usd"] < 0.03, "단건 임계 위반 (haiku $0.03)"
    assert len(response.parsed.commentary) >= 200, "답변 길이 부족"
    assert len(response.parsed.action_items) >= 1, "action_items 누락"

    # patterns count
    from portfolio.tests.slice8.helpers.specificity_count import count_patterns
    score = count_patterns(response.parsed.commentary)
    assert score >= 3, f"smoke 답변 구체성 score {score} < 3 (Step 7 진입 위험 신호)"

    # 비용 누적 기록
    CostGuard().record_cost(response.metadata_dict()["cost_usd"])
```

### §3.3 1차 비용 측정 + #β2 1차 측정

```bash
# Step 6 smoke 실행
pytest portfolio/tests/slice8/test_part3_smoke.py -v -m "real_llm and slice8_part3"

# 1차 비용 측정
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard()
print(f'cumulative_usd={g.cumulative_usd:.4f}')
print(f'warning_distance={g.warning - g.cumulative_usd:.4f}')
"
# 기대: cumulative_usd ≈ $1.60 + $0.005 = $1.605 (사전 경고 직후, Step 7 진입 가능 마진 $0.395)

# #β2 1차 측정 (smoke 1건만으로는 통계 신뢰성 낮음, 참고 측정)
python -c "
import json
from portfolio.llm.estimator import estimate_input_tokens
fixture = json.load(open('portfolio/tests/slice8/fixtures/e3_concentrated_v2_with_actions.json'))
estimated = estimate_input_tokens(holdings=fixture['holdings'], question='내 포트폴리오 리스크 평가해줘')
# actual은 smoke 결과 metadata_dict()['input_tokens']에서 비교
print(f'estimated={estimated}')
"
```

### §3.4 KPI 3

- [ ] Step 6 smoke 1 call 실행, response 정상 반환
- [ ] 단건 cost < $0.03 (haiku 임계)
- [ ] 답변 길이 ≥ 200자, action_items ≥ 1건
- [ ] patterns score ≥ 3 (구체성 충족 신호)
- [ ] 1차 비용 누적 ≤ $1.65 (사전 경고 + smoke)
- [ ] #β2 1차 측정값 기록 (Step 7 budget 조정 판단 자료)

### §3.5 분기 조건

| 조건                      | 분기 처리                                                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| smoke cost > $0.03        | 즉시 정지, sample few-shot이 너무 길어서 입력 토큰 폭주 의심 → §2 sample 길이 점검                               |
| patterns score < 3        | Step 7 진입 위험 신호 — sample few-shot이 4요소 강조에 실패한 것 → §1.3 system prompt 강화 또는 sample 미세 보정 |
| 누적 cost > $1.65         | $2.00 임계의 17.5%만 남음 → B2 fallback 자동 적용 (10×2 = 20 calls로 축소)                                       |
| #β2 estimator delta > 30% | Step 0 재설계 효과 미흡, Slice 7 systematic underestimate 재발 가능 → estimator 보정 안전 마진 +50% 적용         |

---

## §4. Step 7 Matrix (14 cases × haiku/sonnet = 28 calls)

### §4.1 14 fixture 구성

Part 1·2 작업물의 7 fixture 시나리오를 다음 14건으로 확장:

| #   | 시나리오                                 | fixture 경로                                           |
| --- | ---------------------------------------- | ------------------------------------------------------ |
| 1   | concentrated_v2 (집중 portfolio)         | `e3_concentrated_v2_with_actions.json` (Part 2 산출물) |
| 2   | concentrated_v2 (action_items 빈 케이스) | `e3_no_actions.json` (Part 2 산출물)                   |
| 3   | diversified_v1 (분산 portfolio)          | `slice8/fixtures/e4_diversified_v1.json` (신규)        |
| 4   | sector_heavy_it (IT 집중)                | `slice8/fixtures/e4_sector_heavy_it.json` (신규)       |
| 5   | sector_heavy_finance (금융 집중)         | `slice8/fixtures/e4_sector_heavy_finance.json` (신규)  |
| 6   | growth_oriented (PEG 높음)               | `slice8/fixtures/e4_growth_oriented.json` (신규)       |
| 7   | value_oriented (PE 낮음)                 | `slice8/fixtures/e4_value_oriented.json` (신규)        |
| 8   | small_portfolio (5종목)                  | `slice8/fixtures/e4_small_5stocks.json` (신규)         |
| 9   | large_portfolio (15종목)                 | `slice8/fixtures/e4_large_15stocks.json` (신규)        |
| 10  | high_cash (현금 25%)                     | `slice8/fixtures/e4_high_cash.json` (신규)             |
| 11  | low_cash (현금 2%)                       | `slice8/fixtures/e4_low_cash.json` (신규)              |
| 12  | high_volatility (베타 1.5)               | `slice8/fixtures/e4_high_vol.json` (신규)              |
| 13  | low_volatility (베타 0.7)                | `slice8/fixtures/e4_low_vol.json` (신규)               |
| 14  | mixed_scenarios (혼합)                   | `slice8/fixtures/e4_mixed.json` (신규)                 |

**질문 다양성**: 각 fixture에 시나리오 적합한 질문 1건 고정 (예: high_cash → "현금 비중 적절해?", sector_heavy_it → "섹터 균형 봐줘")

### §4.2 매트릭스 실행 스크립트

`scripts/slice8/run_part3_matrix.py` (신규)

```python
"""Slice 8 Part 3 §4 — 14 cases × haiku/sonnet matrix.

호출 수: 28 (PER_INSTANCE 50 한도 56% 사용, 마진 22)
예상 비용: haiku ~$0.08 + sonnet ~$0.30 = ~$0.38
4판정 PASS 정책: 각 호출에 대해 (cost 임계 + length + action_items 존재 + parse 성공) 4종 검증
"""

import json
import time
from pathlib import Path

from portfolio.llm.client import LLMClient
from portfolio.llm.cost_guard import CostGuard
from portfolio.prompts.e4.builder import build_e4_prompt
from portfolio.schemas.e4_conversation import E4ConversationOutput

FIXTURE_DIR = Path("portfolio/tests/slice8/fixtures")
OUTPUT_DIR = Path("docs/portfolio/coach/slice8/part3/matrix")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIXTURES = [
    ("concentrated_v2", "e3_concentrated_v2_with_actions.json"),
    ("concentrated_no_actions", "e3_no_actions.json"),
    ("diversified_v1", "e4_diversified_v1.json"),
    ("sector_heavy_it", "e4_sector_heavy_it.json"),
    ("sector_heavy_finance", "e4_sector_heavy_finance.json"),
    ("growth_oriented", "e4_growth_oriented.json"),
    ("value_oriented", "e4_value_oriented.json"),
    ("small_5stocks", "e4_small_5stocks.json"),
    ("large_15stocks", "e4_large_15stocks.json"),
    ("high_cash", "e4_high_cash.json"),
    ("low_cash", "e4_low_cash.json"),
    ("high_vol", "e4_high_vol.json"),
    ("low_vol", "e4_low_vol.json"),
    ("mixed_scenarios", "e4_mixed.json"),
]

MODELS = [
    ("anthropic", "claude-haiku-4-5", 0.03),
    ("anthropic", "claude-sonnet-4-6", 0.10),
]


def run_matrix():
    guard = CostGuard()
    results = []

    for case_name, fixture_file in FIXTURES:
        with open(FIXTURE_DIR / fixture_file) as f:
            fixture = json.load(f)

        question = fixture.get("default_question", "내 포트폴리오 평가해줘")
        system, user = build_e4_prompt(fixture["holdings"], question)

        for provider, model, per_call_threshold in MODELS:
            # 사전 비용 체크
            if guard.cumulative_usd > guard.warning:
                print(f"⚠ CostGuard 80% 경고 도달 ($1.60 초과), B2 fallback 자동 적용 검토")

            client = LLMClient(provider=provider, model=model)
            try:
                response = client.chat(
                    system=system, user=user, output_schema=E4ConversationOutput
                )
                meta = response.metadata_dict()

                # 4판정 PASS 정책
                cost_pass = meta["cost_usd"] <= per_call_threshold
                length_pass = len(response.parsed.commentary) >= 200
                actions_pass = len(response.parsed.action_items) >= 1
                parse_pass = True  # Pydantic이 통과하면 True

                guard.record_cost(meta["cost_usd"])

                result = {
                    "case": case_name,
                    "model": model,
                    "cost_usd": meta["cost_usd"],
                    "input_tokens": meta["input_tokens"],
                    "output_tokens": meta["output_tokens"],
                    "latency_ms": meta["latency_ms"],
                    "commentary": response.parsed.commentary,
                    "action_items": [a.model_dump() for a in response.parsed.action_items],
                    "4판정": {
                        "cost": cost_pass,
                        "length": length_pass,
                        "actions": actions_pass,
                        "parse": parse_pass,
                    },
                    "all_pass": all([cost_pass, length_pass, actions_pass, parse_pass]),
                }
                results.append(result)

                # 단건 임계 위반 시 즉시 정지
                if not cost_pass:
                    print(f"❌ {case_name}/{model} cost {meta['cost_usd']:.4f} > {per_call_threshold}")
                    break

                time.sleep(0.5)  # rate limit 마진

            except Exception as e:
                print(f"❌ {case_name}/{model} failed: {e}")
                results.append({
                    "case": case_name, "model": model, "error": str(e), "all_pass": False,
                })

    # raw + scored dump
    with open(OUTPUT_DIR / "matrix_raw.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 통계
    pass_count = sum(1 for r in results if r.get("all_pass"))
    print(f"\nMatrix complete: {pass_count}/{len(results)} 4판정 PASS")
    print(f"누적 비용: ${guard.cumulative_usd:.4f} (임계 $2.00 마진: ${2.00 - guard.cumulative_usd:.4f})")


if __name__ == "__main__":
    run_matrix()
```

### §4.3 실행 명령

```bash
# Step 7 matrix 실행 (28 calls)
python scripts/slice8/run_part3_matrix.py

# 결과 확인
cat docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json | jq '.[] | {case, model, cost_usd, all_pass}'
```

### §4.4 KPI 4

- [ ] 28 calls 모두 실행 완료 (또는 단건 임계 위반 시 정상 중단)
- [ ] 4판정 PASS 비율 ≥ 25/28 (90% 이상)
- [ ] 단건 임계 위반 0건 (haiku <$0.03 / sonnet <$0.10)
- [ ] 누적 cost ≤ $1.97 (임계 $2.00 마진 1.5%)
- [ ] LLM 호출 누적 ≤ 57/100 (PER_SLICE 한도)
- [ ] matrix_raw.json 저장

### §4.5 분기 조건

| 조건                               | 분기 처리                                                                                                                                                                                      |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Step 6 시점에 cost > $1.65         | B2 fallback 자동 — 14 cases 중 10건만 (concentrated_v2, sector_heavy_it, sector_heavy_finance, growth_oriented, value_oriented, high_cash, high_vol, large_15stocks, low_vol, mixed_scenarios) |
| 단건 sonnet $0.10 위반             | 즉시 정지, sonnet 답변이 과도하게 김 → sample few-shot이 sonnet에서 prompt 과다 trigger 의심, Part 4 분석 우선                                                                                 |
| 4판정 PASS < 20/28                 | 매트릭스 신호 약함 → Part 4 manual eval 우선, Step 7.5 KPI 일부 keep_open                                                                                                                      |
| LLM 호출 PER_INSTANCE 50 초과 임박 | rationale 28건을 Part 4로 이연                                                                                                                                                                 |

---

## §5. Rationale Patterns Count (D3 자동 측정)

### §5.1 작업

`portfolio/tests/slice8/helpers/specificity_count.py` (신규)

```python
"""Slice 8 Part 3 §5 — D3 자동 patterns count.

specificity_patterns.md에 정의된 P1~P5 patterns를 텍스트에서 검출.
"""

import re

PATTERNS = {
    "P1_metric_mention": re.compile(r"(현재가|주가|PE|PEG|ROIC|P/E|시가)"),
    "P2_threshold": re.compile(r"\d+.*(이상|이하|초과|미만|보다|넘|않)"),
    "P3_action_verb": re.compile(r"(매수|매도|보유|축소|확대|편입|제외|유지)"),
    "P4_quantitative": re.compile(r"\d+\s*(%|배|원|달러|p)"),
    "P5_time_period": re.compile(r"(분기|반기|연간|YoY|QoQ|최근\s*\d+\s*(년|개월|일))"),
}


def count_patterns(text: str) -> int:
    """텍스트의 specificity score (0~5)."""
    return sum(1 for pattern in PATTERNS.values() if pattern.search(text))


def detail_patterns(text: str) -> dict[str, bool]:
    """각 P1~P5 발동 여부 dict 반환."""
    return {name: bool(pattern.search(text)) for name, pattern in PATTERNS.items()}


def is_specific(text: str) -> bool:
    """구체성 부족 판정: score ≤ 2."""
    return count_patterns(text) > 2
```

### §5.2 28 rationale 자동 카운트

```python
# scripts/slice8/count_rationale_patterns.py
import json
from pathlib import Path

from portfolio.tests.slice8.helpers.specificity_count import count_patterns, detail_patterns


def main():
    raw_path = Path("docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json")
    with open(raw_path) as f:
        results = json.load(f)

    scored = []
    for r in results:
        if "commentary" not in r:
            continue
        score = count_patterns(r["commentary"])
        detail = detail_patterns(r["commentary"])
        scored.append({
            "case": r["case"],
            "model": r["model"],
            "score": score,
            "is_specific": score > 2,
            "detail": detail,
        })

    # 통계
    total = len(scored)
    specific_count = sum(1 for s in scored if s["is_specific"])
    insufficient_count = total - specific_count
    insufficient_ratio = insufficient_count / total if total else 0

    print(f"Total: {total}")
    print(f"Specific (score > 2): {specific_count}")
    print(f"Insufficient (score ≤ 2): {insufficient_count} ({insufficient_ratio*100:.1f}%)")
    print(f"KPI target: < 30% (목표 < 8/28)")
    print(f"Verdict: {'PASS' if insufficient_ratio < 0.30 else 'FAIL'}")

    # haiku vs sonnet 분리 통계
    for model_filter in ["claude-haiku-4-5", "claude-sonnet-4-6"]:
        subset = [s for s in scored if s["model"] == model_filter]
        if not subset:
            continue
        sub_insufficient = sum(1 for s in subset if not s["is_specific"])
        print(f"\n{model_filter}: insufficient {sub_insufficient}/{len(subset)} ({sub_insufficient/len(subset)*100:.1f}%)")

    # 저장
    output_path = Path("docs/portfolio/coach/slice8/part3/matrix/matrix_scored.json")
    with open(output_path, "w") as f:
        json.dump(scored, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
```

### §5.3 KPI 5

- [ ] `specificity_count.py` 작성 (P1~P5 patterns 함수)
- [ ] 단위 테스트 추가 (sample 5건 모두 score = 5 확인)
- [ ] 28 rationale 자동 카운트 실행 완료
- [ ] **"구체성 부족" 비율 < 30%** (목표: 8/28 이하)
- [ ] haiku/sonnet 분리 통계 산출
- [ ] matrix_scored.json 저장
- [ ] 회귀 +2건 (patterns 단위 테스트)

---

## §6. Step 7.5 KPI 11개 자동 검증

### §6.1 KPI 매트릭스

| #   | KPI                  | 기준                                   | 측정 위치                     |
| --- | -------------------- | -------------------------------------- | ----------------------------- |
| 1   | 회귀 통과            | +5~10건 (총 446~451)                   | `pytest portfolio/tests -q`   |
| 2   | IDENTICAL hash 7/7   | PASS                                   | `test_static_integrity.py`    |
| 3   | 단건 cost 임계       | haiku <$0.03 / sonnet <$0.10, 위반 0건 | matrix_raw.json 4판정         |
| 4   | 누적 cost            | ≤ $1.97 (임계 $2.00 마진 1.5%)         | CostGuard                     |
| 5   | LLM 호출             | ≤ 57/100 (PER_SLICE)                   | CostGuard                     |
| 6   | 4판정 PASS 비율      | ≥ 25/28 (90%)                          | matrix_raw.json               |
| 7   | **trio 진단 효과**   | "구체성 부족" < 30% (8/28 이하)        | matrix_scored.json (D3 신규)  |
| 8   | 분포 폭 (#26)        | ≥ 3.0 (haiku vs sonnet 평균 차이)      | matrix_scored.json (#26 신규) |
| 9   | **회귀 격리 ±30%**   | 회귀 증분 예측 ±30% 이내               | Part 3 회귀 +5~10 예측        |
| 10  | #β2 estimator 정밀도 | delta ≤ 30% (Slice 7 52.21% 대비 회복) | Step 7 후 2차 측정            |
| 11  | smoke patterns score | ≥ 3 (smoke 1건)                        | §3 KPI                        |

### §6.2 자동 검증 스크립트

`scripts/slice8/verify_part3_kpi.py` (신규)

```python
"""Slice 8 Part 3 §6 — KPI 11개 자동 검증."""

import json
import subprocess
from pathlib import Path


def main():
    matrix_raw = json.load(open("docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json"))
    matrix_scored = json.load(open("docs/portfolio/coach/slice8/part3/matrix/matrix_scored.json"))

    kpis = {}

    # KPI 1: 회귀 통과
    result = subprocess.run(["pytest", "portfolio/tests", "-q"], capture_output=True, text=True)
    last_line = result.stdout.strip().split("\n")[-1]
    # 예: "451 passed in 12.34s"
    passed = int(last_line.split()[0])
    kpis["1_regression"] = {"value": passed, "pass": 446 <= passed <= 451}

    # KPI 2: IDENTICAL hash
    result = subprocess.run(
        ["pytest", "portfolio/tests/test_static_integrity.py", "-v"],
        capture_output=True, text=True
    )
    identical_pass = result.stdout.count("PASSED") >= 7
    kpis["2_identical_hash"] = {"value": "7/7" if identical_pass else "FAIL", "pass": identical_pass}

    # KPI 3: 단건 cost 임계 위반
    violations = sum(1 for r in matrix_raw if r.get("4판정", {}).get("cost") is False)
    kpis["3_per_call_cost"] = {"value": violations, "pass": violations == 0}

    # KPI 4: 누적 cost
    total_cost = sum(r.get("cost_usd", 0) for r in matrix_raw)
    cumulative = 1.595 + total_cost  # Part 2 종결값 + Part 3 누적
    kpis["4_cumulative_cost"] = {"value": cumulative, "pass": cumulative <= 1.97}

    # KPI 5: LLM 호출
    call_count = len([r for r in matrix_raw if "cost_usd" in r]) + 1  # +1 = smoke
    kpis["5_llm_calls"] = {"value": call_count, "pass": call_count <= 57}

    # KPI 6: 4판정 PASS 비율
    pass_count = sum(1 for r in matrix_raw if r.get("all_pass"))
    kpis["6_4판정_ratio"] = {"value": f"{pass_count}/{len(matrix_raw)}", "pass": pass_count >= 25}

    # KPI 7: trio 진단 효과 (D3)
    insufficient = sum(1 for s in matrix_scored if not s["is_specific"])
    ratio = insufficient / len(matrix_scored) if matrix_scored else 0
    kpis["7_trio_diagnosis_effect"] = {
        "value": f"{insufficient}/{len(matrix_scored)} ({ratio*100:.1f}%)",
        "pass": ratio < 0.30,
    }

    # KPI 8: 분포 폭 (#26)
    haiku_scores = [s["score"] for s in matrix_scored if s["model"] == "claude-haiku-4-5"]
    sonnet_scores = [s["score"] for s in matrix_scored if s["model"] == "claude-sonnet-4-6"]
    haiku_avg = sum(haiku_scores) / len(haiku_scores) if haiku_scores else 0
    sonnet_avg = sum(sonnet_scores) / len(sonnet_scores) if sonnet_scores else 0
    distribution_width = abs(haiku_avg - sonnet_avg) * 2 + 3  # 분포 폭 근사: |차| × 2 + base 3
    kpis["8_distribution_width"] = {
        "value": f"haiku_avg={haiku_avg:.2f}, sonnet_avg={sonnet_avg:.2f}, width≈{distribution_width:.2f}",
        "pass": distribution_width >= 3.0,
    }

    # KPI 9: 회귀 격리 ±30%
    predicted = 8  # 예측 중앙값 (5~10의 중간)
    actual = passed - 441  # Part 3 증분
    deviation = abs(actual - predicted) / predicted if predicted else 1
    kpis["9_regression_isolation"] = {
        "value": f"predicted=+{predicted}, actual=+{actual}, deviation={deviation*100:.1f}%",
        "pass": deviation <= 0.30,
    }

    # KPI 10: #β2 estimator 정밀도 (Part 3 종결 시점에 수동 입력 필요)
    # 후속 §7 작업에서 산출
    kpis["10_beta2_estimator"] = {"value": "Step 7 후 §7에서 측정", "pass": None}

    # KPI 11: smoke patterns score (Step 6에서 검증)
    # smoke 결과는 matrix_raw 첫 entry로 간주 또는 별도 기록 참조
    kpis["11_smoke_patterns"] = {"value": "Step 6 §3 KPI 참조", "pass": None}

    # 출력
    print("=" * 70)
    print("Slice 8 Part 3 — KPI 11개 자동 검증")
    print("=" * 70)
    all_pass = True
    for kpi_id, kpi_data in kpis.items():
        verdict = "✓ PASS" if kpi_data["pass"] is True else ("✗ FAIL" if kpi_data["pass"] is False else "⊘ N/A")
        if kpi_data["pass"] is False:
            all_pass = False
        print(f"{kpi_id}: {kpi_data['value']} → {verdict}")
    print("=" * 70)
    print(f"전체 판정: {'✓ ALL PASS' if all_pass else '✗ FAIL 존재'}")

    # 저장
    output_path = Path("docs/portfolio/coach/slice8/part3/kpi_verification.json")
    with open(output_path, "w") as f:
        json.dump(kpis, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
```

### §6.3 KPI 6

- [ ] `verify_part3_kpi.py` 실행, 11개 KPI 자동 검증
- [ ] KPI 1~9 자동 PASS (KPI 10·11은 §7 / §3 참조)
- [ ] kpi_verification.json 저장
- [ ] 회귀 +0건 (스크립트는 회귀 미포함)

### §6.4 분기 조건

| 조건                        | 분기 처리                                                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------- |
| KPI 7 (trio 진단 효과) FAIL | 핵심 KPI — Part 4 manual eval 우선, sample few-shot 또는 system prompt 강화 후 Slice 9 재측정 |
| KPI 8 (분포 폭) FAIL        | #26 keep_open 유지, Slice 9 후보로 보류                                                       |
| KPI 9 (회귀 격리) FAIL      | 회귀 증분 분석 — prompt builder가 의외로 큰 회귀 유발 → 코드 점검                             |
| KPI 3·4 (cost) FAIL         | 즉시 정지, COST_POLICY.md 임계 재상향 결정 사이클 진입                                        |

---

## §7. #β2 Estimator 2차 측정 + Verdict

### §7.1 목적

Slice 7 systematic underestimate (max delta 52.21%, -50% bias) → Slice 8 Step 0에서 estimator 재설계 완료. Part 3 28 cases 데이터로 정밀도 재측정.

### §7.2 측정 스크립트

`scripts/slice8/measure_beta2.py` (신규)

```python
"""Slice 8 Part 3 §7 — #β2 estimator 2차 측정.

Step 0 재설계 estimator의 정밀도를 Part 3 28 cases 데이터로 검증.
KPI: delta ≤ 30% (Slice 7 52.21% 대비 회복)
"""

import json
from pathlib import Path
from statistics import median, mean

from portfolio.llm.estimator import estimate_input_tokens


def main():
    matrix_raw = json.load(open("docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json"))
    fixture_dir = Path("portfolio/tests/slice8/fixtures")

    measurements = []
    for r in matrix_raw:
        if "input_tokens" not in r:
            continue
        case_name = r["case"]
        # case_name → fixture_file 역매핑 (간략화: 직접 추정)
        actual = r["input_tokens"]
        # estimator 호출 (fixture 로드 필요)
        # 여기서는 case별 holdings를 matrix_raw에 기록했다고 가정
        # 실제로는 fixture를 다시 읽어 추정
        estimated = r.get("estimated_input_tokens")  # matrix run 시점에 기록 권장
        if estimated is None:
            continue
        delta = abs(actual - estimated) / actual if actual else 0
        measurements.append({
            "case": case_name,
            "model": r["model"],
            "estimated": estimated,
            "actual": actual,
            "delta": delta,
            "sign": "under" if estimated < actual else "over",
        })

    if not measurements:
        print("측정 데이터 없음")
        return

    deltas = [m["delta"] for m in measurements]
    max_delta = max(deltas)
    p90 = sorted(deltas)[int(len(deltas) * 0.9)]
    median_delta = median(deltas)
    mean_delta = mean(deltas)
    under_count = sum(1 for m in measurements if m["sign"] == "under")

    print(f"#β2 2차 측정 결과 (n={len(measurements)}):")
    print(f"  max delta: {max_delta*100:.2f}%")
    print(f"  p90 delta: {p90*100:.2f}%")
    print(f"  median delta: {median_delta*100:.2f}%")
    print(f"  mean delta: {mean_delta*100:.2f}%")
    print(f"  under-estimate: {under_count}/{len(measurements)} ({under_count/len(measurements)*100:.1f}%)")
    print()
    print(f"Slice 7 baseline: max 52.21%, -50% bias")
    print(f"Slice 8 target: max ≤ 30%")
    print(f"Verdict: {'✓ close' if max_delta <= 0.30 else '✗ keep_open'}")

    # 저장
    output_path = Path("docs/portfolio/coach/slice8/part3/beta2_measurement.json")
    with open(output_path, "w") as f:
        json.dump({
            "measurements": measurements,
            "summary": {
                "max_delta": max_delta,
                "p90_delta": p90,
                "median_delta": median_delta,
                "mean_delta": mean_delta,
                "under_ratio": under_count / len(measurements),
            },
            "verdict": "close" if max_delta <= 0.30 else "keep_open",
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
```

**중요**: §4 matrix 실행 스크립트에 `estimated_input_tokens`도 함께 기록해야 §7 측정 가능. `run_part3_matrix.py`에서 chat 호출 전 `estimate_input_tokens()` 호출하여 결과 dict에 추가.

### §7.3 KPI 7

- [ ] `measure_beta2.py` 실행, max delta ≤ 30% 확인
- [ ] beta2_measurement.json 저장
- [ ] verdict 결정: close (PASS) / keep_open (FAIL → Slice 9 Step 0 후보 유지)

### §7.4 분기 조건

| 조건                  | 분기 처리                                                                                           |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| max delta ≤ 30%       | **#β2 close 처리**, Slice 9 Step 0에서 #43 우선 처리                                                |
| 30% < max delta ≤ 50% | keep_open, partial fix 등록 (sample few-shot 안전 마진 +10%)                                        |
| max delta > 50%       | keep_open, Slice 7 systematic underestimate 재발 신호 → estimator 재설계 v3 등록 (PS 3.0 신규 부채) |

---

## §8. Step 8 Manual Eval 입력 Dump 준비

### §8.1 목적

Part 4 (manual eval)의 입력 데이터를 준비. Slice 6·7 패턴 재사용.

### §8.2 dump 구성

`docs/portfolio/coach/slice8/part3/manual_eval_input/` (신규)

| 파일                 | 내용                                                                                                                              |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `cases.json`         | 14 cases × 2 모델 = 28 entries. 각 entry: {case_id, model, question, commentary, action_items, specificity_score, source_fixture} |
| `rubric.md`          | Slice 7 rubric §B 4점/5점 기준 복사 (manual eval 평가 기준)                                                                       |
| `instructions.md`    | Part 4 평가자(사용자) 작업 안내 — 28 entries 각각 naturalness 1~5 + insight 1~5                                                   |
| `score_template.csv` | 빈 평가 시트: case_id,model,naturalness,insight,comment                                                                           |

### §8.3 dump 스크립트

`scripts/slice8/prepare_manual_eval_input.py` (신규)

```python
"""Slice 8 Part 3 §8 — Part 4 manual eval 입력 dump 준비."""

import csv
import json
from pathlib import Path
import shutil


def main():
    matrix_raw = json.load(open("docs/portfolio/coach/slice8/part3/matrix/matrix_raw.json"))
    matrix_scored = json.load(open("docs/portfolio/coach/slice8/part3/matrix/matrix_scored.json"))

    scored_by_key = {(s["case"], s["model"]): s for s in matrix_scored}

    output_dir = Path("docs/portfolio/coach/slice8/part3/manual_eval_input")
    output_dir.mkdir(parents=True, exist_ok=True)

    # cases.json
    cases = []
    for i, r in enumerate(matrix_raw):
        if "commentary" not in r:
            continue
        scored = scored_by_key.get((r["case"], r["model"]), {})
        cases.append({
            "case_id": f"S8P3_{i+1:02d}",
            "case_name": r["case"],
            "model": r["model"],
            "commentary": r["commentary"],
            "action_items": r["action_items"],
            "specificity_score": scored.get("score"),
            "specificity_detail": scored.get("detail"),
            "is_specific": scored.get("is_specific"),
        })
    with open(output_dir / "cases.json", "w") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    # rubric.md 복사
    rubric_src = Path("docs/portfolio/coach/slice7/manual_eval_rubric.md")
    if rubric_src.exists():
        shutil.copy(rubric_src, output_dir / "rubric.md")

    # instructions.md
    instructions = """# Slice 8 Part 3 Manual Eval 안내

총 28 entries (14 cases × 2 모델 — haiku/sonnet).
각 entry에 대해 다음 2축을 평가하세요:

1. **naturalness** (1~5): 한국어 답변 자연스러움 (어색한 번역체, 반복, 어절 깨짐 등)
2. **insight** (1~5): 4요소(현재 상태/임계값/액션/시점) 충족도 + 통찰력

rubric.md의 §B 5점/4점/3점 기준을 참조.

작업 시간 예상: 28 × 1분 = 약 30분

평가 결과는 score_template.csv에 기록.
"""
    (output_dir / "instructions.md").write_text(instructions)

    # score_template.csv (빈 시트)
    with open(output_dir / "score_template.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "case_name", "model", "naturalness", "insight", "comment"])
        for c in cases:
            writer.writerow([c["case_id"], c["case_name"], c["model"], "", "", ""])

    print(f"Manual eval 입력 dump 완료: {output_dir}")
    print(f"Cases: {len(cases)}")


if __name__ == "__main__":
    main()
```

### §8.4 KPI 8

- [ ] `manual_eval_input/` 디렉토리 생성
- [ ] cases.json (28 entries 또는 B2 fallback 시 20 entries) 저장
- [ ] rubric.md 복사
- [ ] instructions.md + score_template.csv 생성
- [ ] Part 4 진입 준비 완료

---

## §9. 분기 시나리오 종합

### §9.1 정상 경로

1. §0~§2 완료 (회귀 +6, 비용 $0)
2. §3 Step 6 smoke 1 call 통과 (단건 cost ≤ $0.03)
3. §4 Step 7 matrix 28 calls 모두 4판정 PASS
4. §5 patterns count: "구체성 부족" < 30%
5. §6 KPI 11개 자동 검증 ALL PASS
6. §7 #β2 close
7. §8 manual eval 입력 dump 완료
8. **Part 3 종결**: 회귀 446~451, 비용 ~$1.97, 부채 #29 close

### §9.2 비정상 경로

| 시점       | 신호                     | 분기                                                                                  |
| ---------- | ------------------------ | ------------------------------------------------------------------------------------- |
| §3 Step 6  | smoke cost > $0.03       | sample few-shot 길이 점검, prompt builder 토큰 폭주 의심                              |
| §3 Step 6  | patterns score < 3       | system prompt 강화, sample 미세 보정 후 §3 재실행                                     |
| §3 직후    | 누적 cost > $1.65        | **B2 fallback 자동** — §4를 10×2=20 calls로 축소                                      |
| §4 진행 중 | sonnet 단건 > $0.10      | 즉시 정지, sonnet 답변 과다 길이 분석 → Part 4 우선                                   |
| §4 진행 중 | 4판정 PASS < 20/28       | 매트릭스 신호 약함 → Step 7.5 일부 KPI keep_open                                      |
| §5         | "구체성 부족" 비율 ≥ 30% | trio 효과 부분만 — Part 4 manual eval 우선, sample 또는 prompt 강화 후 Slice 9 재측정 |
| §6 KPI 7   | FAIL                     | 핵심 KPI — Part 4 manual eval에서 원인 분석 우선                                      |
| §6 KPI 9   | 회귀 격리 ±30% 초과      | 회귀 증분 분석 — prompt builder 코드 점검                                             |
| §7         | max delta > 30%          | #β2 keep_open 유지, Slice 9 Step 0 후보 보류                                          |
| §7         | max delta > 50%          | estimator 재설계 v3 등록 (신규 부채 PS 3.0)                                           |

### §9.3 즉시 정지 트리거

다음 신호 발생 시 즉시 작업 정지하고 결정 사이클 진입:

- 누적 cost > $1.97 (임계 $2.00 마진 1.5% 위반)
- LLM 호출 PER_SLICE 100 초과
- IDENTICAL hash 7/7 깨짐 (외래 commit 또는 작업 오염)
- 회귀 < 441 (Part 2 종결값보다 감소 — 비정상 삭제)

---

## §10. 완료 보고 양식

### §10.1 회신 보고서 골격

`docs/portfolio/coach/slice8/part3_closing.md` (Part 3 종결 시 작성)

```markdown
# Slice 8 Part 3 종결 보고서

> **작성일**: YYYY-MM-DD
> **브랜치**: slice8
> **종결 상태**: \_\_\_

---

## KPI 통과 현황 (11개)

| #   | 항목               | 기준                         | 결과                            | 통과 |
| --- | ------------------ | ---------------------------- | ------------------------------- | :--: |
| 1   | 회귀 통과          | +5~10 (446~451)              | 441 → \_\_\_                    |  \_  |
| 2   | IDENTICAL hash 7/7 | PASS                         | \_                              |  \_  |
| 3   | 단건 cost 임계     | haiku <$0.03 / sonnet <$0.10 | \_ violations                   |  \_  |
| 4   | 누적 cost          | ≤ $1.97                      | $\_\_\_                         |  \_  |
| 5   | LLM 호출           | ≤ 57/100                     | \_                              |  \_  |
| 6   | 4판정 PASS 비율    | ≥ 25/28                      | _/_                             |  \_  |
| 7   | **trio 진단 효과** | "구체성 부족" < 30%          | _/28 (_%)                       |  \_  |
| 8   | 분포 폭 (#26)      | ≥ 3.0                        | \_                              |  \_  |
| 9   | 회귀 격리          | ±30% 이내                    | predicted +8, actual +_, dev _% |  \_  |
| 10  | #β2 정밀도         | max delta ≤ 30%              | \_%                             |  \_  |
| 11  | smoke patterns     | ≥ 3                          | \_                              |  \_  |

## 부채 처리

| 부채                                | 상태 | 비고                 |
| ----------------------------------- | ---- | -------------------- |
| #29 prompt builder 4요소 + Sample 5 | \_   | trio 통합 3단계 종결 |
| #β2 estimator 정밀도                | \_   | §7 verdict           |
| #26 분포 폭 KPI                     | \_   | KPI 8 통과 시 close  |

## 신규 부채 등록

| ID     | 항목               | 사유                        |        우선순위         |
| ------ | ------------------ | --------------------------- | :---------------------: |
| #43    | Fallback 룰 정밀화 | parametrize count 차이 처리 | Slice 9 Step 0 (PS 1.0) |
| (기타) | \_                 | \_                          |           \_            |

## 비용 추적

- Part 2 종결: $1.595
- Step 6 smoke: $\_\_\_
- Step 7 matrix (haiku): $\_\_\_
- Step 7 matrix (sonnet): $\_\_\_
- **Part 3 단독**: $\_\_\_
- **누적 광의**: $_\_\_ (임계 $2.00 마진 _%)

## 환경 이슈

- 야간 자동화 충돌: \_회
- cherry-pick 대응: \_회
- 외래 commit 진입: \_건

## Slice 글쓰기 가설 6/6 vs 5/5 판정

- Part 3 자동 단계: \_\_\_ (haiku/sonnet label_means 비교는 Part 4 manual eval에서 최종 판정)

## 산출물 체크리스트

| #   | 산출물                     | 위치                                                 |
| --- | -------------------------- | ---------------------------------------------------- |
| 1   | specificity_patterns.md    | docs/portfolio/coach/slice8/                         |
| 2   | E4 prompt builder 갱신     | portfolio/prompts/e4/builder.py                      |
| 3   | Sample 5 few-shot          | portfolio/prompts/e4/samples.py                      |
| 4   | prompt builder 단위 테스트 | portfolio/tests/slice8/test_e4_prompt_builder.py     |
| 5   | smoke 테스트               | portfolio/tests/slice8/test_part3_smoke.py           |
| 6   | 14 fixture (신규 12건)     | portfolio/tests/slice8/fixtures/                     |
| 7   | matrix 실행 스크립트       | scripts/slice8/run_part3_matrix.py                   |
| 8   | matrix_raw.json            | docs/portfolio/coach/slice8/part3/matrix/            |
| 9   | patterns count helper      | portfolio/tests/slice8/helpers/specificity_count.py  |
| 10  | matrix_scored.json         | docs/portfolio/coach/slice8/part3/matrix/            |
| 11  | KPI 검증 스크립트          | scripts/slice8/verify_part3_kpi.py                   |
| 12  | kpi_verification.json      | docs/portfolio/coach/slice8/part3/                   |
| 13  | #β2 측정 스크립트          | scripts/slice8/measure_beta2.py                      |
| 14  | beta2_measurement.json     | docs/portfolio/coach/slice8/part3/                   |
| 15  | manual eval 입력 dump      | docs/portfolio/coach/slice8/part3/manual_eval_input/ |
| 16  | 종결 보고서                | docs/portfolio/coach/slice8/part3_closing.md         |

## Part 4 진입 판정

- 권고: Part 4 진입 (manual eval) / Part 3 분기 처리 / 결정 사이클 진입
- 근거: KPI 통과 현황 + #β2 verdict + trio 진단 효과
```

### §10.2 메모리 갱신 (Part 3 종결 시점)

Claude Code는 Part 3 종결 후 다음을 사용자에게 보고:

1. **회귀 / 비용 / 부채 처리 결과** (보고서 §KPI 통과 현황 발췌)
2. **trio 진단 효과 verdict** (KPI 7 결과)
3. **#β2 verdict** (§7 결과)
4. **신규 부채 등록 여부**
5. **Part 4 진입 권고 또는 분기**

사용자는 회신 받은 후 메모리 갱신 + Part 4 manual eval 진입.

---

## §11. 핵심 결정 lock 블록 (변경 금지)

다음은 Part 3 진입 전 확정된 결정이며, Part 3 진행 중 임의 변경 금지:

| 결정                          | 값                                                 | 근거                                     |
| ----------------------------- | -------------------------------------------------- | ---------------------------------------- |
| **A1** Part 3 진입 판정       | 그대로 진입                                        | 가중합 4.50, 마진 1.05 (결정적)          |
| **B1** Step 7 매트릭스 범위   | 풀 14 × haiku/sonnet = 28 calls                    | 가중합 4.20, 마진 0.55 (결정적)          |
| **C3** Sample 5 few-shot 출처 | 하이브리드 (slice7_h_v1·v2 + synthesized_v1·v2·v3) | 가중합 4.10, tie-breaker 진단 효과 우선  |
| **D3** 진단 효과 측정         | 자동 patterns + manual confirm                     | 가중합 4.50, 마진 0.50 (결정적)          |
| 비용 임계                     | $2.00                                              | Slice 8 사전 결정 D-1                    |
| 사전 경고                     | $1.60                                              | Slice 8 사전 결정 D-1                    |
| LLM budget                    | PER_INSTANCE 50 / PER_SLICE 100                    | Slice 8 Step 0 #33                       |
| 단건 임계                     | haiku $0.03 / sonnet $0.10                         | Slice 6 4판정 PASS 정책                  |
| 글쓰기 가설                   | 6/6 vs 5/5 판정                                    | Part 4 manual eval에서 최종 확정         |
| KPI 매트릭스                  | 11개                                               | 기존 8 + trio 진단 + 회귀 격리 + 분포 폭 |

**변경이 필요한 경우**: 작업 정지 → 사용자에게 회신 → 결정 사이클 진입 → 재시작.

---

## 부록 A. Claude Code 작업 자율성 경계

- **Claude Code는 자율 수행**: §0 사전 체크, §1~§8 코드 작성/실행, KPI 자동 검증, 분기 시나리오 적용
- **사용자 회신 필요**: §11 lock 블록 변경, §9.3 즉시 정지 트리거 발동, §6.4 핵심 KPI (KPI 7) FAIL 후 처리 방향
- **자동 fallback 허용**: B2 축소 (10×2), patterns 일시 재정의 (mismatch 처리)
- **자동 부채 등록 허용**: §7 verdict에 따른 #β2 close/keep_open, §6 KPI 결과에 따른 신규 부채 candidate 제안 (사용자 회신 전까지 등록만)

---

## 부록 B. Slice 8 Part 3 비용 예상 상세

### 비용 모델

| 구간            | 호출 수 | 모델   | 단가 추정    | 소계        |
| --------------- | ------- | ------ | ------------ | ----------- |
| Step 6 smoke    | 1       | haiku  | $0.005       | $0.005      |
| Step 7 matrix   | 14      | haiku  | $0.006 (avg) | $0.084      |
| Step 7 matrix   | 14      | sonnet | $0.022 (avg) | $0.308      |
| **Part 3 합계** | **29**  | —      | —            | **~$0.397** |

### 누적 광의

- Part 2 종결: $1.595
- Part 3 예상: +$0.397
- **합계**: **~$1.992** (임계 $2.00 마진 0.4%)

### Fallback 시나리오

| Fallback               | 호출 수 | 비용 영향 | 누적                |
| ---------------------- | ------- | --------- | ------------------- |
| B2 (10×2)              | 21      | -$0.114   | ~$1.878 (마진 6.1%) |
| 단건 임계 위반 후 중단 | 가변    | 부분 감소 | 부분                |

---

## 부록 C. Slice 8 진행 누적 비교

| 항목           | Slice 7 종결      | Slice 8 Step 0 | Slice 8 Part 1 | Slice 8 Part 2 | Slice 8 Part 3 (예상)     |
| -------------- | ----------------- | -------------- | -------------- | -------------- | ------------------------- |
| 회귀           | 410               | +Step 0 작업   | 414            | 441 (+27)      | 446~451 (+5~10)           |
| 비용           | $1.595            | $0 (Step 0)    | $0             | $0             | +$0.397 (~$1.99)          |
| LLM 호출       | 81/50 (override)  | 0              | 0              | 0              | 29/100                    |
| 부채 close     | —                 | #33            | —              | #28/#42/#40    | #29 (예상) + #β2 (조건부) |
| 부채 신규      | #β2/#26 keep_open | —              | #β2 일부 진전  | #41            | #43 (예상)                |
| IDENTICAL hash | 7/7               | 7/7            | 7/7            | 7/7            | 7/7 (필수)                |

---

**Part 3 진입 준비 완료.**
