# Rubric §B Sample 코멘트 5건 (manual_eval_rubric.md §B 보강)

> **목적**: 평가자(병진)가 1~5점 척도의 구체 기준을 학습할 수 있도록 견본 코멘트 제공.
> **적용**: Slice 7 Part 4부터 영구 적용. 이후 모든 슬라이스 manual eval에 참조.
> **포맷**: 각 sample은 동일 portfolio context에 대한 다양한 품질의 답변 5건.

---

## 공통 Context (모든 sample에 공통)

**Portfolio 정보**:

- preset: GARP (합리적 가격 성장)
- 보유: Tech 50%, Healthcare 25%, Financials 25% (5종목)
- 지표: hhi_concentration=0.45, sector_hhi=0.50, top3_weight=0.65, holding_count=5, portfolio_beta=1.10, max_position_weight=0.30, avg_correlation=0.40

**User Question**: "내 포트폴리오의 집중도가 높은 편인가요?"

---

## Sample 1 — naturalness=1, insight=2 (어색 + 기본만)

```
{
  "answer": "당신의 포트폴리오 집중도 0.45 보입니다. 이것은 높은 것 같습니다.
  주식 5개 가지고 있고 top3 65% 입니다. 분산이 충분히 안 되었다고 생각할 수
  있습니다. 권장 사항은 더 많은 주식을 사는 것입니다.",
  "referenced_metrics": ["hhi_concentration", "top3_weight"],
  "confidence": "low"
}
```

**평가**: naturalness=1, insight=2

**Naturalness 1점 사유**:

- "0.45 보입니다", "당신의 포트폴리오" 등 어색한 한국어 어순
- "이것은 높은 것 같습니다" 같은 기계 번역체
- "주식 5개 가지고 있고" 부자연스러운 구어
- 3건 이상 어색한 표현 → §A 기준 1점

**Insight 2점 사유**:

- 지표 인용은 있으나 "높다"는 판단만 (사용자 질문에 대한 답)
- preset(GARP) 의도 반영 없음
- 행동 시사점이 "더 많은 주식 사기"로 막연 (구체 종목/섹터/비중 없음)
- §B 2점 (기본 해석만, preset 의도 반영 X)

---

## Sample 2 — naturalness=3, insight=1 (무난 + 통찰 없음)

```
{
  "answer": "포트폴리오 집중도는 hhi 0.45, top3 비중 65%입니다. 5종목으로
  구성되어 있으며 portfolio_beta는 1.10입니다. 평균 상관관계는 0.40으로
  나타납니다. sector_hhi는 0.50이며 max_position_weight는 0.30입니다.",
  "referenced_metrics": ["hhi_concentration", "top3_weight", "holding_count",
    "portfolio_beta", "avg_correlation", "sector_hhi", "max_position_weight"],
  "confidence": "medium"
}
```

**평가**: naturalness=3, insight=1

**Naturalness 3점 사유**:

- 한국어 자체는 어색하지 않음 (정상 문장)
- 그러나 정형적 — 단순 숫자 나열
- 사람이 쓴 느낌은 없음 → §A 3점 (보통, 정형적)

**Insight 1점 사유**:

- 지표 7개 모두 인용했지만 **해석이 0건**
- 사용자 질문 "집중도가 높은가?"에 대한 답이 없음
- preset(GARP) 반영 0, 행동 시사점 0
- 숫자 나열만 → §B 1점

---

## Sample 3 — naturalness=4, insight=3 (자연 + 보통 통찰)

```
{
  "answer": "현재 포트폴리오는 중간 수준의 집중도를 보입니다. hhi 0.45와
  top3 비중 65%는 5종목 포트폴리오 기준 다소 집중된 편이며, 특히 Tech 섹터
  50% 비중이 sector_hhi 0.50을 끌어올리고 있습니다. GARP 전략은 균형 잡힌
  성장을 추구하므로, 섹터 분산을 고려해볼 수 있습니다.",
  "referenced_metrics": ["hhi_concentration", "top3_weight", "sector_hhi"],
  "follow_up_suggestions": ["어떤 섹터를 추가하면 좋을까요?"],
  "confidence": "medium"
}
```

**평가**: naturalness=4, insight=3

**Naturalness 4점 사유**:

- 자연스러운 흐름 ("다소 집중된 편이며", "끌어올리고 있습니다")
- 어색한 표현 없음
- 5점은 아님 — 약간 정형적 ("균형 잡힌 성장을 추구하므로" 다소 교과서적)
- §A 4점

**Insight 3점 사유**:

- 사용자 질문에 답함 ("중간 수준 집중도", "다소 집중된 편")
- 지표 간 관계 일부 ("Tech 50%가 sector_hhi 끌어올림")
- preset(GARP) 의도 1차 반영 ("균형 잡힌 성장 추구")
- 행동 시사점 막연 ("섹터 분산을 고려해볼 수 있다" — 어떤 섹터인지 X)
- §B 3점 (기본 해석 + preset 의도 부분 반영)

---

## Sample 4 — naturalness=5, insight=4 (매우 자연 + 좋은 통찰)

```
{
  "answer": "집중도는 중상위 수준입니다. hhi 0.45는 5종목 포트폴리오 평균
  (0.30~0.40)을 상회하고, top3 비중 65%는 특정 종목 의존도가 높음을 시사합니다.
  무엇보다 Tech 섹터 50% 편중이 GARP의 균형적 위험 통제 원칙과 어긋날 수
  있어 주의가 필요합니다. portfolio_beta 1.10도 시장보다 변동성이 큰 상태를
  반영합니다. Healthcare나 Consumer Staples 같은 방어 섹터 비중을 늘려
  sector_hhi를 0.35~0.40 수준으로 낮추는 리밸런싱을 검토해보세요.",
  "referenced_metrics": ["hhi_concentration", "top3_weight", "sector_hhi",
    "portfolio_beta"],
  "follow_up_suggestions": [
    "구체적으로 어떤 종목을 줄여야 할까요?",
    "방어 섹터 추천 종목이 있나요?"
  ],
  "confidence": "high"
}
```

**평가**: naturalness=5, insight=4

**Naturalness 5점 사유**:

- 사람이 쓴 듯한 자연스러움 ("무엇보다", "주의가 필요합니다")
- 문맥에 맞는 어휘 선택 ("편중", "어긋날 수 있어")
- 리듬감 있는 흐름
- §A 5점

**Insight 4점 사유**:

- 지표 간 관계 명확 (hhi vs 평균, top3 vs 종목 의존도, Tech vs sector_hhi, beta vs 변동성)
- preset(GARP) 의도 정확 반영 ("균형적 위험 통제 원칙과 어긋날 수 있어")
- **구체적 행동 시사점 2건** (1) "Healthcare/Staples 비중 늘리기" (2) "sector_hhi 0.35~0.40 목표"
- 5점이 아닌 이유: 위험과 기회의 양면 분석 부족 (집중의 장점도 있을 수 있음 — 언급 X)
- §B 4점

---

## Sample 5 — naturalness=5, insight=5 (매우 자연 + 매우 통찰)

```
{
  "answer": "결론부터 말하면 현재 집중도는 중상위 수준이며, GARP 전략 기준
  주의가 필요한 영역입니다. 정량적으로 hhi 0.45는 5종목 평균(0.30~0.40)을
  넘어서고, sector_hhi 0.50은 Tech 50% 편중에 기인합니다. 다만 이런 집중이
  GARP에서 일반적으로 권장되는 5~7종목 분산 범위 안에서 일어났다는 점은
  의도적 선택일 가능성도 시사합니다.

  위험 측면에서는 portfolio_beta 1.10 + avg_correlation 0.40이 결합되어
  단일 섹터 사이클 충격에 portfolio 전체가 흔들릴 수 있습니다. 반면 기회
  측면에서는 Tech 강세 국면에서 집중도가 알파 원천이 될 수 있습니다.

  GARP의 원칙은 '균형'이므로, Tech 비중을 30~35%로 축소하면서 Healthcare나
  Industrials를 15%씩 추가해 sector_hhi 0.35 수준 + portfolio_beta 1.00
  근처를 목표로 단계적 리밸런싱을 권장합니다. 단번에 비중을 바꾸기보다
  분기별 5%씩 조정하는 방식이 변동성을 줄입니다.",
  "referenced_metrics": ["hhi_concentration", "top3_weight", "sector_hhi",
    "portfolio_beta", "avg_correlation"],
  "follow_up_suggestions": [
    "Healthcare/Industrials 구체 종목 추천이 가능한가요?",
    "분기별 5% 조정의 실제 거래 비용은 어느 정도인가요?",
    "현재 GARP 기준을 벗어난 종목이 있나요?"
  ],
  "confidence": "high"
}
```

**평가**: naturalness=5, insight=5

**Naturalness 5점 사유**:

- 사람이 쓴 듯한 흐름 + 논리 전개 ("결론부터", "정량적으로", "위험 측면" / "기회 측면")
- 어휘 선택 정교 ("알파 원천", "단계적 리밸런싱", "변동성을 줄입니다")
- 문단 구조 자연스러움
- §A 5점

**Insight 5점 사유**:

- 지표 간 관계 정교 (hhi vs 평균, beta+correlation 결합 위험)
- preset(GARP) 의도 다층 반영 ("균형 원칙", "5~7종목 분산 범위")
- **위험과 기회 양면 분석** (위험: 사이클 충격, 기회: 알파 원천 — Sample 4의 5점 미달 원인 해소)
- **구체 행동 시사점 3건 이상** (1) Tech 30~35% (2) Healthcare/Industrials 15%씩 (3) sector_hhi 0.35 목표 + beta 1.00 (4) 분기별 5%씩 조정
- "단번에 바꾸기보다" 등 실행 전술까지 제시
- §B 5점

---

## 사용 가이드

### 평가자에게 (병진)

1. 평가하는 entry를 읽기 전에 위 sample 5건을 먼저 검토 (~3분)
2. 각 sample의 (naturalness, insight) 점수 + 사유를 마음에 고정
3. 평가 entry를 sample과 비교하며 점수 매기기
4. 어느 sample에 가까운지 + 위/아래 어느 쪽인지로 판단
5. 분포 폭이 좁아지면 "이 entry는 정말 모든 sample 중간(3점) 수준인가? 1점 sample 같진 않나? 5점 sample 같진 않나?" 자문

### 작성자에게 (LLM)

다음 슬라이스 prompt builder에서 system prompt에 sample 인용 가능:

- "당신의 답변은 Sample 5 수준을 목표로 하세요"
- "Sample 1처럼 어색한 한국어와 기본 해석만 있는 답변은 피하세요"

이렇게 prompt-rubric 정렬을 통해 generator-evaluator gap을 줄임.

---

## 회귀 테스트 (Part 4 §2에서 추가)

```python
# portfolio/tests/test_rubric_samples.py
"""Rubric §B sample 5건 정합성 회귀."""

import json
from pathlib import Path

RUBRIC_PATH = Path("docs/portfolio/coach/manual_eval_rubric.md")


def test_rubric_has_5_samples():
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert content.count("## Sample") >= 5


def test_rubric_sample_score_spectrum():
    """Sample 1~5가 1~5점 spectrum 다양성 cover."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    for n in [1, 2, 3, 4, 5]:
        assert f"naturalness=" in content
        assert f"insight=" in content
    # 1점 + 5점 양극단 사용 확인
    assert "naturalness=1" in content
    assert "naturalness=5" in content
    assert "insight=1" in content
    assert "insight=5" in content


def test_rubric_sample_rationale_present():
    """각 sample에 점수 사유 명시."""
    content = RUBRIC_PATH.read_text(encoding="utf-8")
    assert "Naturalness 1점 사유" in content
    assert "Insight 5점 사유" in content
```
