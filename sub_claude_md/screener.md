# Screener 시스템

## Enhanced Screener Service (Phase 2.4)

### 문제

FMP `/stable/company-screener`가 PE/ROE/EPS Growth 필터 미지원

### 해결: 2단계 필터링

1. FMP 스크리너로 1차 필터링 (market_cap, volume 등)
2. FMP `/stable/key-metrics-ttm`으로 펀더멘탈 데이터 조회
3. 클라이언트 사이드 2차 필터링

### 프리셋 타입

| 타입 | 설명 | 필터 예시 |
|------|------|----------|
| **instant** | FMP 직접 지원 | market_cap, volume, sector, dividend |
| **enhanced** | 추가 API 필요 | PE, ROE, EPS Growth, D/E Ratio |

### FMP Key Metrics TTM 필드 매핑 (주의!)

```python
FMP_METRICS_FIELD_MAP = {
    'pe_ratio': 'earningsYieldTTM',      # 역수 계산 필요!
    'roe': 'returnOnEquityTTM',          # * 100 변환 필요
    'roa': 'returnOnAssetsTTM',          # * 100 변환 필요
    'current_ratio': 'currentRatioTTM',
    'debt_equity': 'debtToEquityTTM',
    'profit_margin': 'netProfitMarginTTM',  # * 100 변환 필요
}

# PE Ratio: 1 / earningsYield
earnings_yield = m.get('earningsYieldTTM')
pe_ratio = round(1 / earnings_yield, 2) if earnings_yield > 0 else None

# ROE: decimal → percentage
roe_decimal = m.get('returnOnEquityTTM')
roe_percent = round(roe_decimal * 100, 2) if roe_decimal else None
```

### 테스트: `tests/serverless/test_enhanced_screener_service.py` (14개, 100%)

---

## Investment Thesis Builder (Phase 2.3)

### 개요

스크리너 결과를 바탕으로 LLM이 투자 테제를 자동 생성. Gemini 2.5 Flash 동기 API 호출.

### InvestmentThesis 모델

```python
{
    user: FK(User),  # nullable
    title: CharField(200),
    summary: TextField,
    filters_snapshot: JSONField,
    preset_ids: JSONField,
    key_metrics: JSONField,   # ["PER < 15", "ROE > 20%"]
    top_picks: JSONField,     # ["AAPL", "MSFT", ...]
    risks: JSONField,
    rationale: TextField,
    llm_model: CharField(50),
    generation_time_ms: IntegerField,
    is_public: BooleanField,
    share_code: CharField(20, unique=True),  # 8자 UUID
    view_count: IntegerField,
    save_count: IntegerField,
}
```

### API

```bash
POST /api/v1/serverless/thesis/generate       # 테제 생성
GET  /api/v1/serverless/thesis/{id}           # 조회 (view_count +1)
GET  /api/v1/serverless/thesis?limit=10       # 내 목록
GET  /api/v1/serverless/thesis/shared/{code}  # 공유 조회
```

### 특징

- 동기 API: `client.models.generate_content()` (Celery 호환)
- share_code 자동 생성 (8자 UUID)
- 폴백 전략: LLM 실패 시 `create_fallback_thesis()` 사용
- 비용: ~$0.005 USD/테제

---

## Screener Upgrade 전체 (Phase 2)

- **Phase 2.1**: 프리셋 공유 시스템 (share_code URL, 트렌딩, 복사)
- **Phase 2.2**: Chain Sight DNA (연관 종목 발견)
- **Phase 2.3**: 투자 테제 빌더 (LLM 자동 생성)
- **Phase 2.4**: 프리셋-필터 동기화 (2단계 필터링, Enhanced 프리셋)
