# Peer Phase 7: LLM 대화형 Peer 조정

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `validation/services/llm_peer_filter.py` | parse_filter_with_llm + execute_peer_filter |
| `validation/api/views.py` (수정) | LLMPeerFilterView 추가 |
| `validation/api/urls.py` (수정) | llm-filter/ 엔드포인트 추가 |

## API

```
POST /api/v1/validation/{symbol}/llm-filter/
Body: {
  "query": "성숙기 기업 중 ROE 15% 이상만",
  "preset_key": "default"  // (선택) 기반 프리셋
}

Response: {
  "symbol": "NVDA",
  "query": "...",
  "parsed_filter": {"growth_stage": ["mature"], "metric_filters": [...]},
  "peers": ["AAPL", "MSFT", ...],
  "count": 42,
  "filters_applied": ["GrowthStage: ['mature']", "roe >= 15"]
}
```

## 지원 필터 항목

| 카테고리 | 필터 | 예시 |
|---------|------|------|
| Chain Sight | growth_stage | "성숙기", "성장기" |
| Chain Sight | capital_type | "균형형", "적극투자형" |
| Chain Sight | rate_sensitivity | "금리 민감도 낮은" |
| Chain Sight | forex_sensitivity | "환율 민감한" |
| Chain Sight | regulation_type | "금융 규제 안 받는" |
| Chain Sight | insider_signal | "내부자 매수 신호" |
| Sensitivity | foreign_revenue_pct | "해외 매출 50% 이상" |
| Metrics | 31개 재무 지표 | "ROE 15% 이상", "부채비율 30% 이하" |
| 제외 | exclude_sectors | "반도체 제외" |

## 테스트 결과

| 시나리오 | 파싱 | 결과 |
|---------|------|------|
| "성숙기 기업만" | growth_stage: mature | 364개 |
| "해외 매출 50%+, R&D 높은" | foreign_revenue_pct_min + rd_to_revenue | 0개 (metric 데이터 한계) |
| "금리 민감도 낮고 비금융" | rate_sensitivity: low + regulation: none | 183개 |

## 다음 작업

→ 전체 완료 (remaining_work_plan 소진)
