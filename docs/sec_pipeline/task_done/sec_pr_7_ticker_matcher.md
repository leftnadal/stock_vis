# SEC-PR-7: TickerMatcher + CompanyAlias + 큐 적재

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/ticker_matcher.py` | TickerMatcher 클래스 (3단계 매칭 + 큐 적재) |

## 의존성 추가

- `rapidfuzz==3.14.3` (poetry add로 관리)

## 매칭 로직

```
1순위: CompanyAlias (context_sector 우선 → 범용 fallback)
2순위: Stock.stock_name exact 매칭 (_clean_name 접미사 제거 포함)
3순위: rapidfuzz token_sort_ratio ≥ 85%
실패: UnmatchedCompanyQueue 적재 (fuzzy_candidates top 5 포함)
```

## 15종목 배치 매칭 결과

| 지표 | 값 |
|------|-----|
| 전체 evidence | 66 |
| 매칭 성공 | 2 (3.0%) |
| 미매칭 → 큐 | 60 |
| 매칭 방법 | exact: 2 |

### 매칭 성공 건
- NVDA → MU (Micron Technology, Inc.) — exact
- PG → WMT (Walmart Inc.) — exact

### 매칭 실패 원인 분류

| 원인 | 건수 | 예시 |
|------|------|------|
| 비미국 주식 (Stock DB 미등록) | ~15 | TSMC, Samsung, SK Hynix, Hon Hai |
| LLM이 일반 명사 추출 | ~30 | "third parties", "OEMs", "suppliers", "resellers" |
| 비상장/자회사 | ~15 | "Wistron", "Fabrinet", "GSBE" |

## 개선 필요 사항

1. **프롬프트 개선**: 일반 명사 추출 방지 (SEC-PR-6에서 프롬프트 버전 업)
2. **비미국 주식**: Admin에서 CompanyAlias 수동 등록 (TSM→TSMC 등)
3. **confidence 필터 강화**: 일반 명사는 보통 confidence가 낮음

## 다음 PR

→ SEC-PR-8: Django Admin 큐 뷰 + post_save signal
