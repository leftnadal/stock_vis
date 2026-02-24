# AI 키워드 생성 시스템 (Phase 2.5)

## 개요

Market Movers 및 Screener 종목에 대해 LLM 기반 핵심 키워드를 생성하는 시스템.
Gemini 2.5 Flash 사용, Celery 비동기 파이프라인으로 처리.

## 아키텍처

```
프론트엔드 (AI 키워드 버튼)
        │
        ▼
REST API (trigger_keyword_generation)
        │
        ▼
Celery 파이프라인 (collect → generate → save)
        │
        ├─ KeywordDataCollector (뉴스 수집)
        │     ├─ Marketaux API (우선)
        │     └─ Finnhub API (폴백)
        │
        └─ KeywordGenerationService (LLM 호출)
              └─ Gemini 2.5 Flash (동기 API)
        │
        ▼
StockKeyword 모델 (PostgreSQL)
        │
        ▼
프론트엔드 (KeywordList 컴포넌트)
```

## StockKeyword 모델

```python
{
    symbol: CharField(max_length=10),
    date: DateField,
    company_name: CharField,
    keywords: JSONField,  # ["AI 수요 증가", "실적 호조", "목표가 상향"]
    status: CharField,    # 'pending', 'completed', 'failed'
    error_message: TextField,
    llm_model: CharField,  # 'gemini-2.5-flash'
    generation_time_ms: IntegerField,
    prompt_tokens: IntegerField,
    completion_tokens: IntegerField,
    expires_at: DateTimeField  # 7일 후 만료
}
```

## LLM 프롬프트

- 정확히 3개 키워드, 각 15자 이내
- JSON 배열 형식: `["AI 수요 증가", "실적 호조", "목표가 상향"]`

## 폴백 키워드

```python
FALLBACK_KEYWORDS = {
    'gainers': ["급등", "거래량 증가", "모멘텀"],
    'losers': ["급락", "매도 압력", "조정"],
    'actives': ["거래량 급증", "변동성", "투자자 관심"],
    'screener': ["분석 대상", "투자 검토", "모니터링"],
}
```

## Rate Limit 대응

| Provider | Rate Limit | 대응 |
|----------|------------|------|
| Marketaux | 100/일, 15분 간격 | 5초 이상 대기 시 Finnhub 폴백 |
| Finnhub | 60/분, 1초 간격 | 기본 폴백 provider |
| Gemini Free | 15 RPM, 1500 RPD | 지수 백오프 재시도 |

## 프론트엔드 컴포넌트

- **KeywordTag**: 개별 키워드 태그 (색상, 툴팁)
- **KeywordList**: 키워드 목록 (로딩, 에러, 빈 상태 처리)
- **normalizeKeywords()**: string[] → Keyword[] 변환

## 성능

- 종목당 키워드 생성: 약 6초
- 50개 종목 배치: 약 5분
- max_output_tokens: 1200 (한국어 지원)
