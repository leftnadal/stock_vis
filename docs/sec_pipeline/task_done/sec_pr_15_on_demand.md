# SEC-PR-15: On-demand 수집 + 신규 filing 감지

> **완료일**: 2026-04-04

## 생성/수정된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/on_demand.py` | get_or_collect_filing (1년 이내 체크, 1시간 중복 방지) |
| `sec_pipeline/views.py` (수정) | FilingDataView (GET → 200/202) |
| `sec_pipeline/urls.py` (수정) | filing/<symbol>/ 엔드포인트 |
| `sec_pipeline/tasks.py` (수정) | check_new_filings (S&P 500 신규 filing 감지) |

## API

```
GET /api/v1/sec-pipeline/filing/AAPL/
  → 200 {"symbol": "AAPL", "status": "available", "filing_date": "2025-10-31", ...}

GET /api/v1/sec-pipeline/filing/COST/
  → 202 {"symbol": "COST", "status": "collecting", "message": "..."}
```

## 다음 PR

→ SEC-PR-16: Pipeline Intelligence
