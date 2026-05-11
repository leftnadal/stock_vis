# CS-2-1c: InsiderSignal 계산

> **작업 번호**: CS-2-1c
> **목표**: Finnhub Insider Transactions API 기반 InsiderSignal 자동 계산
> **예상 소요**: 2~3시간
> **선행 조건**: CS-2-1b 완료 (SensitivityProfile), Finnhub Insider API 200 확인 (decisions/003)
> **산출물**: `chainsight/tasks/insider_tasks.py`, CompanyInsiderSignal ~500건 적재

---

## 데이터 원천

| 필드 | 원천 | API |
|------|------|-----|
| insider_buy_count_90d | Finnhub Insider Transactions | `transactionCode='P-Purchase'` 최근 90일 |
| insider_sell_count_90d | Finnhub Insider Transactions | `transactionCode='S-Sale'` 최근 90일 |
| insider_net_amount_90d | Finnhub | `sum(change * price)` 추정 |
| insider_signal | 계산 | buy/sell ratio 기반 |
| institutional_ownership_pct | FMP Institutional Holders | `/stable/institutional-holder?symbol=AAPL` |
| institutional_change_qoq | 계산 | 최근 2분기 비교 |
| top_holder_action | 계산 | 상위 기관 보유 변화 |
| short_interest_pct | Stock 모델 또는 FMP | 있으면 사용 |
| short_interest_change | 계산 | 전분기 대비 |
| days_to_cover | 계산 | short_interest / avg_volume |
| smart_money_signal | 종합 계산 | insider + institutional + short 종합 |

## 데이터 흐름

```
Finnhub Insider Transactions API
  ↓
90일 내 buy/sell 집계
  ↓
insider_signal 분류 (strong_buy ~ strong_sell)
  ↓
FMP Institutional Holders (보조)
  ↓
smart_money_signal 종합 판정
  ↓
CompanyInsiderSignal (PostgreSQL)
```

## Finnhub API

### Insider Transactions
```
GET https://finnhub.io/api/v1/stock/insider-transactions?symbol=AAPL&token={key}
```

응답 예시 (decisions/003에서 확인):
```json
{
  "data": [
    {
      "change": -60208,
      "filingDate": "2026-03-17",
      "name": "Newstead Jennifer",
      "share": 240832,
      "symbol": "AAPL",
      "transactionCode": "S-Sale",
      "transactionDate": "2026-03-14",
      "transactionPrice": 213.49
    }
  ],
  "symbol": "AAPL"
}
```

### Transaction Codes
| 코드 | 의미 | 분류 |
|------|------|------|
| P-Purchase | 공개시장 매수 | buy |
| S-Sale | 공개시장 매도 | sell |
| A-Grant | 스톡옵션 행사 | 제외 |
| M-Exempt | 면제 거래 | 제외 |
| F-Tax | 세금 납부용 매도 | 제외 |

⚠️ **A, M, F 코드는 insider signal에서 제외** — 자발적 매수/매도만 의미 있음.

## 신호 분류 규칙

### insider_signal
```python
ratio = buy_count / max(buy_count + sell_count, 1)

ratio >= 0.80 → 'strong_buy'    # 매수 80%+
ratio >= 0.60 → 'buy'           # 매수 60%+
ratio >= 0.40 → 'neutral'       # 혼재
ratio >= 0.20 → 'sell'          # 매도 60%+
ratio < 0.20  → 'strong_sell'   # 매도 80%+

# 거래 건수 3건 미만 → 'neutral' (통계적 의미 없음)
```

### smart_money_signal (종합)
```python
점수 = 0
if insider_signal in ('strong_buy', 'buy'): 점수 += 1
if institutional_ownership_pct > 70: 점수 += 1  # 기관 선호
if short_interest_pct and short_interest_pct < 3: 점수 += 1  # 공매도 적음

점수 >= 2 → 'bullish'
점수 == 1 → 'neutral'
점수 == 0 → 'bearish'
```

## Rate Limit

| API | 무료 한도 | S&P 500 | 전략 |
|-----|----------|---------|------|
| Finnhub Insider | 60 calls/min | 503 calls | 1.2초 딜레이 → ~10분 |

⚠️ **Finnhub 무료 60 RPM** — `time.sleep(1.2)` 필수.
⚠️ 403/429 응답 시 해당 종목 skip (전체 중단 금지).

## 구현

```python
# chainsight/tasks/insider_tasks.py

@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_insider_signals(self):
    """S&P 500 전체 InsiderSignal 계산."""
    # 1. Finnhub Insider Transactions API 호출 (1.2초 딜레이)
    # 2. 90일 내 P-Purchase / S-Sale 집계
    # 3. insider_signal 분류
    # 4. smart_money_signal 종합
    # 5. CompanyInsiderSignal update_or_create
```

## 완료 기준

```
□ CompanyInsiderSignal ~480건+ 적재
□ insider_signal 분포 확인 (strong_buy ~ strong_sell)
□ smart_money_signal 분포 확인 (bullish/neutral/bearish)
□ Finnhub API 에러율 < 10%
□ calculate_all_profiles 통합 task에 추가
□ task_done 기록 작성
```

→ **다음**: Celery Beat 일괄 등록 또는 DC-2 ETF Holdings

**END OF DOCUMENT**
