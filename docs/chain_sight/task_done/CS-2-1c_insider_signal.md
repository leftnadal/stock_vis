# CS-2-1c: InsiderSignal 계산

> **완료일**: 2026-04-04

## 생성/수정된 파일

| 파일 | 역할 |
|------|------|
| `chainsight/tasks/insider_tasks.py` | calculate_insider_signals (신규) |
| `chainsight/tasks/profile_tasks.py` | calculate_all_profiles에 insider 추가 |

## 결과

- **503건** 전체 적재 (성공 + skip)
- Finnhub Insider Transactions API 사용 (무료, 60 RPM)
- 소요 시간: ~10분 (503 × 1.2초 딜레이)

### insider_signal 분포

| Signal | 건수 | 비율 |
|--------|------|------|
| strong_sell | 253 | 50.3% |
| neutral | 205 | 40.8% |
| sell | 23 | 4.6% |
| strong_buy | 12 | 2.4% |
| buy | 10 | 2.0% |

> strong_sell이 과반인 이유: 대부분의 S&P 500 임원은 스톡옵션 행사 후 open market에서 매도(S코드)만 함. 자발적 매수(P코드)는 드묾.

### smart_money_signal 분포

| Signal | 건수 |
|--------|------|
| bearish | 276 |
| neutral | 227 |

> bullish 0건: institutional_ownership/short_interest 데이터 미확보 (별도 API 필요). 현재는 insider_signal만 반영.

### Buy signal 종목 (22건)

BX, CSGP, EXE, HBAN, IBM 등 — 내부자 자발적 매수가 90일 내 3건+ 있는 종목.

## 참고

- Transaction codes: P(Purchase)=buy, S(Sale)=sell만 집계
- M(Exercise), F(Tax), G(Gift), A(Grant) 등은 제외
- 90일 내 거래 3건 미만 → neutral (통계적 의미 없음)

## 다음 작업

→ Celery Beat 일괄 등록 또는 DC-2 ETF Holdings
