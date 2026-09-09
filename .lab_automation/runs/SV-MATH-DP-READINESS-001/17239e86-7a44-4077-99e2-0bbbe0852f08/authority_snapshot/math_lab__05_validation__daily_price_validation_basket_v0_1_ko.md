# DailyPrice Validation Basket v0.1

**Status:** Working / Selection Protocol Candidate  
**Date:** 2026-09-05

## 0. 한눈에 보는 요약

첫 DailyPrice validation은 편한 유명 종목 몇 개를 임의로 고르는 방식이 아니라, **적은 수의 자산으로 서로 다른 데이터 failure mode를 최대한 노출하는 것**을 목적으로 한다.

Basket은 두 층으로 분리한다.

1. **Representative Basket** — 서로 다른 sector/industry와 가격행동에서 정상 경로를 검증
2. **Adversarial Basket** — split, dividend, ticker/entity lifecycle, missing history 같은 경계조건을 의도적으로 공격

중요: 아래 ticker는 **selection candidate**다. GitHub code/document에서 StockVis universe와 sector mapping 존재는 확인했지만, 이 작업 환경에서는 production DB의 실제 `DailyPrice` row count/date range를 직접 조회하지 못했다. 따라서 실제 adapter 실행 전 DB readiness probe가 최종 selection gate다.

## 1. Selection Principles

### Representative Basket

가능한 한 다음 축을 다양화한다.

- sector / industry
- cyclicality
- liquidity / market behavior
- volatility
- dividend profile
- corporate-action complexity
- history length

동일 industry 종목을 여러 개 넣는 것은 특정 failure를 검증할 명시적 이유가 있을 때만 허용한다.

### Adversarial Basket

대표성을 목표로 하지 않는다. 다음 failure mode를 노출할 자산을 고른다.

- large/repeated stock split
- dividend / ex-dividend adjustment
- ticker change
- merger / acquisition
- spin-off
- IPO / short history
- delisting / terminal return
- long missing period / suspension

## 2. Representative Candidate Basket

| Candidate | Role | Sector/Industry diversity rationale | Primary validation |
|---|---|---|---|
| SPY | Market baseline | ETF / benchmark, company sector와 분리 | baseline time-series, market calendar |
| AAPL | Technology | long-lived mega-cap technology | split + dividend + long history |
| JPM | Financial Services | bank / rate-sensitive | sector diversity, financial behavior |
| XOM | Energy | commodity/cyclical | energy-specific price regime |
| WMT | Consumer Defensive | defensive retail | dividend/defensive behavior |
| UNH | Healthcare | managed healthcare | healthcare-specific behavior |

StockVis documentation의 Market Pulse mapping에서도 AAPL/NVDA는 Technology, JPM은 Financial Services, UNH는 Healthcare, XOM은 Energy, WMT는 Consumer Defensive로 서로 다른 sector group에 배치되어 있다.

## 3. Why NVDA Is Not in the First Representative Basket

NVDA는 중요한 validation asset이지만 AAPL과 같은 Technology 축에 있어 첫 representative basket에서는 sector 중복이 생긴다.

따라서 NVDA는 **Adversarial Corporate-Action candidate**로 이동하는 것을 기본안으로 한다.

목적:

- repeated/large split handling
- high-volatility price behavior
- ChainSight와의 향후 연결 가능성

즉 `대표성`과 `경계조건 공격` 역할을 분리한다.

## 4. Readiness Probe Before Final Selection

각 candidate에 대해 production read-only probe가 다음을 확인해야 한다.

```text
Stock row exists?
sector / industry present?
DailyPrice row count
min(date)
max(date)
missing-business-day profile
zero / negative OHLCV anomaly
StockSplit count and dates
currency
created_at range
```

가능하면 추가로:

```text
provider/source identity
adjusted vs raw semantics
dividend history availability
correction/revision lineage
```

을 확인한다.

## 5. Final Inclusion Rule

Representative asset은 기본적으로 다음을 만족해야 한다.

- Stock metadata 존재
- sector/industry 식별 가능
- 충분한 DailyPrice history
- 치명적 데이터 손상 없음
- 다른 representative asset과 sector/industry 역할이 과도하게 중복되지 않음

단, `충분한 history`의 정확한 기간/row threshold는 readiness distribution을 보기 전에 임의로 고정하지 않는다.

## 6. Adversarial Selection Rule

Adversarial basket은 ticker를 먼저 고정하지 않고 **failure mode → 실제 StockVis data candidate** 순서로 선정한다.

예:

```text
Repeated split failure mode
→ StockSplit table에서 event count 높은 종목 검색
→ DailyPrice coverage 확인
→ candidate 선정
```

이 방식은 유명 종목을 먼저 정하고 이유를 사후 부여하는 selection bias를 줄인다.

## 7. Current Data Opportunities

### Required

1. DailyPrice readiness probe command/query
2. split-adjusted research return contract
3. dividend/total-return data availability 확인
4. price source/provider provenance

### High Value

5. point-in-time entity/ticker lifecycle
6. delisting/terminal-return history
7. provider correction lineage

이 정보가 없으면 해당 failure mode는 `exploratory_only` 또는 별도 Data Gap으로 남긴다.

## 8. Next Implementation Step

다음 vertical slice는 production schema를 수정하지 않는 read-only adapter/probe다.

```text
candidate universe
→ readiness probe
→ diversified representative selection
→ adversarial selection
→ DataViewContract
→ Eligibility Gate
```

최종 basket은 이 probe 결과로 결정한다.
