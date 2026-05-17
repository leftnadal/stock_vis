"""Slice 8 Part 3 #29 — E4 Sample 5 few-shot 정의.

C3 하이브리드: Slice 7 manual eval 상위 답변 2건 + rubric 합성 3건.
모든 sample은 rubric §B 5점 기준 4요소 (현재 상태 + 임계값 + 액션 + 시점) 포함.

source 마킹:
- "slice7_h_v1" / "slice7_h_v2": Slice 7 manual eval 상위 답변 (rubric 4요소 사전 검증 + 미세 보정)
- "synthesized_v1" / "synthesized_v2" / "synthesized_v3": rubric 합성
"""

from __future__ import annotations


DEFAULT_FEW_SHOT_SAMPLES: list[dict] = [
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
            {
                "title": "NVIDIA 5%p 축소",
                "description": "PE 65 업종 평균 2배 부담",
                "priority": "high",
            },
            {
                "title": "방어주 편입 검토",
                "description": "변동성 1.5배 완화 목적, 다음 분기",
                "priority": "medium",
            },
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
            {
                "title": "삼성전자 5%p 축소",
                "description": "단일 한도 20% 초과",
                "priority": "high",
            },
            {
                "title": "분산 후보 탐색",
                "description": "SK하이닉스 또는 타 섹터, 다음 리밸런싱 시점",
                "priority": "medium",
            },
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
            {
                "title": "IT 비중 10%p 축소",
                "description": "KOSPI 1.8배 과다, 변동성 1.7배 노출",
                "priority": "high",
            },
            {
                "title": "헬스케어 7%p 확대",
                "description": "현 5% → 목표 12%, 분기 내",
                "priority": "medium",
            },
            {
                "title": "산업재 7%p 확대",
                "description": "현 8% → 목표 15%, 분기 내",
                "priority": "medium",
            },
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
            {
                "title": "고PEG 종목 15%p 축소",
                "description": "PEG 2 이상 종목 대상, 2주 내",
                "priority": "high",
            },
            {
                "title": "방어주/채권 ETF 20% 편입",
                "description": "베타 1.0 미만 목표",
                "priority": "high",
            },
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
            {
                "title": "현금 10%p 축소 (25% → 15%)",
                "description": "권장 범위 10%p 초과",
                "priority": "medium",
            },
            {
                "title": "ROIC 15%↑ & PEG 1.5↓ 종목 매수",
                "description": "다음 분기까지, 단계적 분할 매수",
                "priority": "medium",
            },
        ],
    },
]
