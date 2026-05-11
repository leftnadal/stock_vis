# FMP Premium-Only Symbols

FMP Starter Plan에서 지원하지 않는 S&P 500 심볼 목록.
해당 심볼은 재무제표 동기화(`sync_sp500_financials`, `bulk_sync_sp500_financials`)에서 자동 제외됩니다.

## 제외 기준

- FMP `/stable/*` 엔드포인트에서 **HTTP 402 (Payment Required)** 반환
- 공통 특징: 심볼에 `.` 포함 (Share Class 구분자)
- Alpha Vantage fallback도 동일하게 데이터 없음

## Premium-Only 심볼 목록

| Symbol | Company | Sector | 비고 |
|--------|---------|--------|------|
| BRK.B | Berkshire Hathaway | Financials | Class B 주식. BRK-B로도 조회 불가 |
| BF.B | Brown-Forman | Consumer Staples | Class B 주식. BF-B로도 조회 불가 |

## 필터링 로직

`stocks/tasks.py`에서 `.` 포함 심볼을 자동 제외:

```python
sp500_symbols = [s for s in all_symbols if '.' not in s]
```

`api_request/providers/fmp/client.py`에서 402 응답 시 재시도 없이 즉시 실패:

```python
elif response.status_code == 402:
    raise FMPPremiumError(f"Premium-only symbol/endpoint (402): {endpoint}")
```

## 영향

- 503개 S&P 500 중 2개 제외 → 501개 동기화
- 제외된 2개 종목의 재무제표는 프론트엔드 Fallback 체인(yfinance)으로 조회 가능
- EOD Dashboard, 주가 동기화 등 다른 파이프라인에는 영향 없음

## 업데이트 이력

- 2026-03-04: 최초 작성. BRK.B, BF.B 확인 및 필터링 적용
