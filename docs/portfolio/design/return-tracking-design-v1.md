# Stock-Vis Return Tracking Design

> **문서 버전**: v1.0 (2026-04-20)
> **작성 배경**: 세션 D 결정 사항 중 수익률 추적 영역
> **관련 문서**:
> - `wallet-portfolio-architecture-v1.md` (데이터 모델 — 이 문서의 전제)
> - `coach-llm-design-v1.md` (Coach LLM — 수익률 breakdown은 Tier 2.5에 포함)
> - `metric-dictionary-v1.2.md` (지표 사전 — return 관련 지표는 별도 목록)

---

## 1. 요구사항

### 1-1. 해석 1: 카테고리별 계층 분해

사용자는 포트폴리오 전체 수익률만이 아니라 **카테고리 단위로 분해된 수익률**을 보고 싶어한다.

**계층 구조** (상위 → 하위):
```
전체 (total)
  └─ 섹터 (sector)
       └─ 인더스트리 (industry)
            └─ 종목 (holding)
```

**예시**:
- 전체: +12%
  - Technology 섹터: +18% (전체 기여도 +10.8%p, Tech가 60% 비중)
    - Semiconductors 인더스트리: +22% (섹터 내 기여도 +13.2%p, 섹터 내 60% 비중)
      - NVDA: +45%
      - AMD: +5%
    - Software 인더스트리: +15%
      - MSFT: +18%
      - ADBE: +12%
  - Healthcare 섹터: +2% (전체 기여도 +0.4%p, Healthcare가 20% 비중)

**비중 가중 원칙**:
- 각 레벨의 수익률 = 하위 요소의 **비중 가중 평균**
- 각 레벨의 **전체 기여도** = 해당 레벨 비중 × 해당 레벨 수익률

### 1-2. 해석 2-c: 종목별 기여도 분해

사용자가 **현재 보유한 종목이 포트폴리오 전체 수익률에 얼마나 기여했는지** 파악.

**예시**:
- 포트폴리오 전체 수익률: +12%
  - NVDA가 +5%p 기여 (비중 15% × 종목 수익률 +33%)
  - MSFT가 +3%p 기여
  - INTC가 -1%p 기여 (손실 중)
  - 나머지 종목 합산: +5%p

**중요**:
- "매매 이력 기반 P&L" (해석 2-a)는 **Phase 2**로 이연 (Trade 모델 필요)
- "기회비용 분석" (해석 2-b)는 Phase 2+로 이연 (반사실 시뮬레이션 필요)
- MVP는 해석 2-c만 지원

---

## 2. 데이터 모델 (결정 R3)

### 2-1. 하이브리드 접근

**MVP 수단**:
- `WalletHolding.avg_cost` 기반 단순 수익률
- `WalletHolding.shares × current_price` 기반 현재 가치
- **Trade 모델 없이도** 해석 1, 2-c 충족 가능

**Phase 2 수단** (향후 대체):
- Trade 모델 도입으로 매매 이력 정밀 추적
- TWR/MWR 정확 계산
- 매매별 P&L (해석 2-a)

### 2-2. sector/industry 필드 위치 (결정 RV2-b)

**Stock 모델에 저장**.

```python
class Stock(models.Model):
    """
    종목 마스터 데이터 (기존 stocks 앱).
    세션 D 결정: sector, industry 필드 추가.
    """
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)

    # ★ 추가 필드 (RV2-b)
    sector = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="GICS Sector. FMP /profile 엔드포인트 기반.",
    )
    industry = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="GICS Industry. FMP /profile 엔드포인트 기반.",
    )

    # ...기타 기존 필드
```

**이유**:
- 종목의 섹터/인더스트리는 **절대적 사실** (NVDA는 항상 Technology > Semiconductors).
- 종목마다 단일 출처 — WalletHolding이 많아도 Stock은 하나.
- `metric-dictionary-v1.2.md`의 `comparison_group: industry` 설정이 Stock의 industry 정보를 전제.

**Stock 모델 접근 권한 확인 필요**:
- 만약 `stocks` 앱이 외부 앱이거나 수정 불가능하면 폴백: WalletHolding에 sector/industry 캐시 필드 추가 (결정 RV2-a)
- 데이터 동기화 로직 필요 (Stock 데이터 갱신 배치 시 WalletHolding 캐시도 업데이트)

### 2-3. WalletHolding의 수익률 관련 필드

```python
class WalletHolding(models.Model):
    # ...기존 필드...

    # ---- 수익률 계산용 ----
    shares = models.DecimalField(max_digits=14, decimal_places=4)
    avg_cost = models.DecimalField(max_digits=12, decimal_places=4)
    first_bought_at = models.DateField()

    # sector, industry는 self.stock.sector, self.stock.industry로 접근
```

**동적 계산 필드**:
- `cost_basis` = `shares × avg_cost`
- `current_value` = `shares × current_price` (price feed 필요)
- `unrealized_return` = `(current_value - cost_basis) / cost_basis`

이 필드들은 DB에 저장하지 않고 `ReturnCalculator` 호출 시 실시간 계산.

### 2-4. WalletSnapshot의 수익률 데이터

```python
class WalletSnapshot(models.Model):
    # ...기존 필드...

    aggregate_metrics = models.JSONField()
    # 구조 예시:
    # {
    #   "total_value": 150000.00,
    #   "total_cost_basis": 135000.00,
    #   "total_return": 0.1111,
    #   "sector_distribution": {"Tech": 0.60, "Healthcare": 0.20, ...},
    #   "industry_distribution": {...},
    #   "holding_count": 10
    # }

    holdings_json = models.JSONField()
    # 구조 예시:
    # [
    #   {
    #     "stock_id": "...", "symbol": "NVDA",
    #     "sector": "Technology", "industry": "Semiconductors",
    #     "shares": 10, "avg_cost": 400.00,
    #     "price_at_snapshot": 550.00,  # 스냅샷 시점 가격
    #     "market_value_at_snapshot": 5500.00
    #   },
    #   ...
    # ]
```

스냅샷은 **시점의 모든 정보 자체완결** — 이후 가격 변동에 영향받지 않음.

---

## 3. ReturnCalculator 인터페이스 (결정 RV3-a)

### 3-1. 단일 메소드 원칙

```python
from pydantic import BaseModel
from decimal import Decimal
from typing import Union

class ContributionItem(BaseModel):
    name: str           # 섹터/인더스트리/종목명
    weight: Decimal     # 상위 레벨 내 비중
    return_rate: Decimal        # 이 항목의 수익률
    contribution_pp: Decimal    # 상위 레벨 기여도 (%p)

class CategoryBreakdown(BaseModel):
    name: str                          # 카테고리명 (예: "Technology")
    weight: Decimal                    # 전체 대비 비중
    return_rate: Decimal               # 이 카테고리 수익률
    contribution_pp: Decimal           # 전체 기여도 (%p)
    children: list["CategoryBreakdown"] = []  # 재귀 구조
    holdings: list[ContributionItem] = []     # 리프 레벨은 종목

class ReturnBreakdown(BaseModel):
    scope_type: str                    # "portfolio" | "wallet"
    scope_id: str                      # Portfolio UUID 또는 Wallet UUID
    calculated_at: str                 # ISO 8601 timestamp
    total_return: Decimal              # 전체 수익률
    total_value: Decimal               # 현재 총 평가금액
    total_cost_basis: Decimal          # 총 매수 원가
    by_sector: list[CategoryBreakdown] # 섹터 계층
    top_contributors: list[ContributionItem]  # 상위 기여 종목 (top 5)
    bottom_contributors: list[ContributionItem]  # 하위 기여 종목 (bottom 5)


class ReturnCalculator:
    """
    MVP 구현. Phase 2에 Trade 모델 도입 시 내부 구현 교체.
    인터페이스는 안정 유지.
    """

    def __init__(self, price_feed: PriceFeedInterface):
        self.price_feed = price_feed

    def calculate(
        self,
        scope: Union[Portfolio, Wallet, WalletSnapshot],
    ) -> ReturnBreakdown:
        """
        주어진 스코프의 수익률 breakdown을 전체 계산.

        MVP 구현:
        - Portfolio: effective_holdings() → 각 WalletHolding의 현재 가치 vs 원가
        - Wallet: 모든 WalletHolding 대상
        - WalletSnapshot: 스냅샷 시점 가격 기준 재계산 (이미 저장된 값 활용)

        Phase 2 확장:
        - Trade 모델이 있으면 avg_cost 대신 정밀한 원가 계산
        - TWR (Time-Weighted Return) / MWR (Money-Weighted Return) 제공
        """
        ...
```

### 3-2. 계산 알고리즘 (MVP)

**입력**: Portfolio (또는 Wallet, WalletSnapshot)
**출력**: ReturnBreakdown

**단계**:

1. **종목 단위 계산**
   ```
   for holding in scope.effective_holdings():
       current_price = price_feed.get(holding.stock.symbol)
       market_value = holding.shares × current_price
       cost_basis = holding.shares × holding.avg_cost
       return_rate = (market_value - cost_basis) / cost_basis
       sector = holding.stock.sector
       industry = holding.stock.industry
   ```

2. **전체 집계**
   ```
   total_value = sum(market_value for holding)
   total_cost_basis = sum(cost_basis for holding)
   total_return = (total_value - total_cost_basis) / total_cost_basis
   ```

3. **종목 비중 계산**
   ```
   for holding:
       weight = holding.market_value / total_value
   ```

4. **인더스트리 레벨 집계**
   ```
   for industry in set(all industries):
       industry_value = sum(market_value for holdings in this industry)
       industry_cost_basis = sum(cost_basis for holdings in this industry)
       industry_return = (industry_value - industry_cost_basis) / industry_cost_basis
       industry_weight = industry_value / total_value
       industry_contribution = industry_weight × industry_return
       # holdings 리스트는 기여도 내림차순 정렬
   ```

5. **섹터 레벨 집계** (인더스트리와 동일 로직, 한 단계 상위)

6. **Top/Bottom Contributors**
   ```
   all_holdings_sorted_by_contribution = sorted(
       holdings_with_contribution_pp, 
       key=lambda h: h.contribution_pp, reverse=True
   )
   top_contributors = all_holdings_sorted_by_contribution[:5]
   bottom_contributors = all_holdings_sorted_by_contribution[-5:]
   ```

### 3-3. WalletSnapshot 기반 계산 (시간 이동)

Saved Analysis 조회 시 "저장 시점 수익률"을 재현하려면 WalletSnapshot의 저장된 데이터 사용.

```python
def calculate_from_snapshot(
    self,
    snapshot: WalletSnapshot,
) -> ReturnBreakdown:
    """
    스냅샷 시점의 수익률을 그대로 재계산.
    현재 가격이 아닌 snapshot.holdings_json의 price_at_snapshot 사용.
    """
    holdings_data = snapshot.holdings_json
    # 각 holding에 대해 price_at_snapshot 기준 계산
    # aggregate_metrics에 이미 집계된 값이 있으면 활용
    ...
```

### 3-4. 캐싱 전략

MVP에서는 **요청 시마다 재계산**.

**Phase 2 캐싱**:
- Wallet/Portfolio 단위로 Redis 캐시
- TTL: 15분 (가격 변동 주기)
- Invalidation: WalletHolding 변경 시 즉시 무효화

---

## 4. 수익률 스코프 (결정 RV1-b)

### 4-1. 두 개의 독립 스코프

Tier 2.5 LLM 입력 JSON에 **두 개의 독립된 필드**로 포함:

```json
{
  "analysis_target_portfolio": {
    "holdings": [...],
    "metric_results": {...},
    "return_breakdown": {
      "scope_type": "portfolio",
      "total_return": 0.15,
      "by_sector": [...],
      "top_contributors": [...],
      "bottom_contributors": [...]
    }
  },
  "wallet_background": {
    "total_holdings_count": 12,
    "return_breakdown": {
      "scope_type": "wallet",
      "total_return": 0.08,
      "by_sector": [...],
      "top_contributors": [...],
      "bottom_contributors": [...]
    }
  }
}
```

### 4-2. 의미

- **Portfolio breakdown**: "분석 중인 종목 묶음의 수익률 구조"
- **Wallet breakdown**: "전체 자산의 수익률 구조 (배경 맥락)"

Coach는 두 breakdown을 대조해 유의미한 해석 제공:

> "당신의 포트폴리오(Tech 성장주)는 +15%로 견조합니다. 다만 자산 전체 수익률은 +8%이므로, Tech 성장주를 제외한 나머지가 저조한 편입니다. 배당 포트폴리오 또는 Defensive 포트폴리오를 따로 분석해보시면 도움될 것 같습니다."

### 4-3. Coach 사용 규칙

시스템 프롬프트에 명시:
```
- Portfolio return_breakdown은 "분석 대상"의 수익률입니다. 기본 언급 대상.
- Wallet return_breakdown은 "배경 맥락"입니다. 사용자가 묻거나 대조가 유의미할 때만 언급.
- 무엇이든 수치 언급 시 scope를 명시하세요: "당신의 분석 포트폴리오는..." 또는 "당신의 자산 지갑 전체는...".
```

---

## 5. 시간 차원 (결정 RV4-b)

### 5-1. 저장 시점 vs 현재 시점

Saved Analysis 열람 시 **두 시점 모두** 제공.

```json
{
  "analysis_target_portfolio": {
    "return_breakdown": {
      "at_save_time": {
        "calculated_at": "2026-01-15T10:30:00Z",
        "total_return": 0.12,
        "by_sector": [...],
        "top_contributors": [...]
      },
      "current": {
        "calculated_at": "2026-04-20T14:05:00Z",
        "total_return": 0.15,
        "by_sector": [...],
        "top_contributors": [...]
      },
      "delta_since_save": {
        "total_return_change_pp": 0.03,
        "period_days": 95
      }
    }
  }
}
```

### 5-2. 두 시점 계산 방법

**at_save_time**:
- Saved Analysis 저장 시 WalletSnapshot + ReturnBreakdown이 함께 저장됨 (영속화)
- 재조회 시 DB에서 직접 로드 (재계산 없음)

**current**:
- 요청 시점에 `ReturnCalculator.calculate(portfolio.refresh_from_db())` 호출
- Wallet과 WalletHolding의 현재 상태 기준
- Portfolio가 저장된 wallet_holding_ids를 가지고 있지만, `effective_holdings()`를 통해 현재 Wallet에 존재하는 것만 반영

**delta_since_save**:
- `current.total_return - at_save_time.total_return`
- 기간: `current.calculated_at - at_save_time.calculated_at`

### 5-3. Coach 사용 규칙

시스템 프롬프트에 명시:
```
- 기본적으로 current 수치를 사용해 설명하세요.
- "저장 후 얼마나 변했나?", "이전 분석과 비교" 등 변화에 관한 질문에는
  at_save_time과 delta_since_save를 함께 참조.
- 저장 시점 이후 Wallet 구성이 바뀌었다면(예: 종목 매도) 이를 명시.
```

### 5-4. 비용 분석 (RV4-a 대비)

| 항목 | RV4-a (저장 시점만) | RV4-b (저장+현재) |
|---|---|---|
| 계산 횟수 | 0회 (저장된 값 로드) | 1회 추가 (current 계산) |
| 스토리지 | 1건 저장 | 동일 1건 (current는 미저장) |
| Coach 혼동 위험 | 없음 | 있음 (PV3 규칙으로 완화) |
| 사용자 정보 가치 | 낮음 | 높음 (변화 가시화) |

**판단**: 추가 비용이 1회 재계산 수준이라 RV4-b가 실용적.

---

## 6. Saved Analysis 수익률 불변성 (결정 RV4-b 상세)

### 6-1. 저장 시 자동 영속화

사용자가 "이 분석 저장" 클릭 시:

```python
def save_analysis(analysis_run: AnalysisRun) -> StoredAnalysis:
    """
    Saved Analysis로 승격.
    """
    # 1. WalletSnapshot 생성 (Wallet 현재 상태)
    wallet_snapshot = WalletSnapshot.objects.create(
        wallet=analysis_run.portfolio.wallet,
        triggered_by="saved_analysis",
        holdings_json=serialize_wallet(analysis_run.portfolio.wallet),
        aggregate_metrics=compute_wallet_metrics(analysis_run.portfolio.wallet),
    )

    # 2. AnalysisRun에 스냅샷 연결
    analysis_run.wallet_snapshot_at_execution = wallet_snapshot
    analysis_run.save()

    # 3. Portfolio return breakdown 계산 및 영속화
    portfolio_breakdown = ReturnCalculator().calculate(analysis_run.portfolio)
    wallet_breakdown = ReturnCalculator().calculate(analysis_run.portfolio.wallet)

    # 4. StoredAnalysis 생성
    stored = StoredAnalysis.objects.create(
        analysis_run=analysis_run,
        save_type="explicit",
        user_notes="",
        # 수익률 영속화
        portfolio_return_breakdown=portfolio_breakdown.model_dump(),
        wallet_return_breakdown=wallet_breakdown.model_dump(),
        saved_at=timezone.now(),
    )
    return stored
```

### 6-2. StoredAnalysis 모델 확장

```python
class StoredAnalysis(models.Model):
    analysis_run = models.OneToOneField(AnalysisRun, on_delete=models.CASCADE)
    save_type = models.CharField(
        max_length=20,
        choices=[("explicit", "Explicit"), ("auto_temp", "Auto Temporary")],
    )
    user_notes = models.TextField(blank=True)

    # ★ 수익률 영속화 (RV4-b)
    portfolio_return_breakdown = models.JSONField(
        null=True, blank=True,
        help_text="저장 시점 Portfolio 수익률 breakdown. 불변.",
    )
    wallet_return_breakdown = models.JSONField(
        null=True, blank=True,
        help_text="저장 시점 Wallet 수익률 breakdown. 불변.",
    )

    saved_at = models.DateTimeField(auto_now_add=True)
```

### 6-3. 재조회 시 동작

```python
def get_stored_analysis_with_current(stored: StoredAnalysis) -> dict:
    """
    저장 시점 + 현재 시점 수익률 조합.
    """
    # 저장 시점 (DB에서 로드)
    at_save_time_portfolio = stored.portfolio_return_breakdown
    at_save_time_wallet = stored.wallet_return_breakdown

    # 현재 시점 (재계산)
    portfolio = stored.analysis_run.portfolio
    current_portfolio = ReturnCalculator().calculate(portfolio).model_dump()
    current_wallet = ReturnCalculator().calculate(portfolio.wallet).model_dump()

    # 델타 계산
    delta_portfolio = compute_delta(at_save_time_portfolio, current_portfolio)
    delta_wallet = compute_delta(at_save_time_wallet, current_wallet)

    return {
        "portfolio_return_breakdown": {
            "at_save_time": at_save_time_portfolio,
            "current": current_portfolio,
            "delta_since_save": delta_portfolio,
        },
        "wallet_return_breakdown": {
            "at_save_time": at_save_time_wallet,
            "current": current_wallet,
            "delta_since_save": delta_wallet,
        },
    }
```

---

## 7. 수익률 관련 지표와 Metric Dictionary

### 7-1. 지표 사전과의 관계

`metric-dictionary-v1.2.md`의 기존 지표들은 **프리셋 분석**을 위한 것. 수익률 추적은 별도 레이어.

| 영역 | 구성 요소 | 담당 |
|---|---|---|
| 프리셋 분석 지표 | ROIC, PER, Volatility 등 57개 | Metric Dictionary |
| 수익률 추적 | 비중 가중 수익률, 섹터/인더스트리/종목 분해 | ReturnCalculator |

### 7-2. LLM 입력에서의 분리

Tier 2.5 JSON은 두 레이어를 구분:
- `analysis_target_portfolio.metric_results` — 프리셋 지표 분석
- `analysis_target_portfolio.return_breakdown` — 수익률 분해

Coach 프롬프트는 둘을 구분해 사용:
- 프리셋 관점 응답: "이 포트폴리오는 Buffett 기준 ROIC 상위 12%입니다."
- 수익률 관점 응답: "이 포트폴리오는 전체 +15% 중 NVDA가 +5%p 기여했습니다."

---

## 8. Phase 2 확장 경로

### 8-1. Trade 모델 도입

```python
class Trade(models.Model):
    """
    매매 이력. Phase 2 도입.
    """
    wallet = models.ForeignKey(Wallet, ...)
    stock = models.ForeignKey(Stock, ...)
    trade_type = models.CharField(choices=[("buy", "Buy"), ("sell", "Sell")])
    shares = models.DecimalField(...)
    price = models.DecimalField(...)
    trade_date = models.DateField()
    commission = models.DecimalField(default=0)
    note = models.TextField(blank=True)
```

**MVP 대비 추가되는 기능**:
- 해석 2-a: 개별 매매 P&L
- 정밀 원가 계산 (avg_cost 자동 유도)
- TWR/MWR 구분
- 세금 계산 (Phase 2+)

### 8-2. 일별 가치 추적 (PortfolioSnapshot)

```python
class PortfolioSnapshot(models.Model):
    """
    일별 Wallet 가치 기록. Phase 2 도입.
    Celery EOD 배치로 자동 생성.
    """
    wallet = models.ForeignKey(Wallet, ...)
    snapshot_date = models.DateField()
    total_value = models.DecimalField(...)
    holdings_value_json = models.JSONField()
```

**MVP 대비 추가되는 기능**:
- 시계열 그래프
- 정밀 CAGR
- 변동성 추적

### 8-3. 기회비용 분석 (해석 2-b)

시나리오 시뮬레이션:
- "3개월 전 INTC 축소 결정이 없었다면 수익률은 어땠을까?"
- 반사실 포트폴리오 재구성 + 가상 수익률 계산

Phase 2+ 영역. MVP는 범위 외.

### 8-4. ReturnCalculator 인터페이스 안정성

MVP의 `ReturnCalculator.calculate(scope) → ReturnBreakdown` 시그니처는 Phase 2에서도 유지.

**내부 구현만 교체**:
- MVP: avg_cost 기반 단순 계산
- Phase 2: Trade 기반 정밀 계산, PortfolioSnapshot 활용 시계열

외부 호출자(Coach 프롬프트 생성, UI 렌더링)는 영향 없음.

---

## 9. 확정 결정 목록

이 문서에 반영된 결정:

| # | 결정 | 내용 |
|---|---|---|
| R3 | 데이터 모델 방향 | 하이브리드 (MVP는 avg_cost 기반, Trade는 Phase 2) |
| 해석 1 | 카테고리별 계층 분해 | 섹터 > 인더스트리 > 종목, 비중 가중 |
| 해석 2-c | 종목별 기여도 분해 | 해석 2-a/b는 Phase 2 |
| RV1-b | 수익률 필드 위치 | Portfolio + Wallet 독립 필드 |
| RV2-b | sector/industry 필드 위치 | Stock 모델 (불가 시 WalletHolding 폴백) |
| RV3-a | ReturnCalculator 인터페이스 | 단일 메소드, ReturnBreakdown 전체 리턴 |
| RV4-b | Saved Analysis 수익률 표시 | 저장 시점 + 현재 시점 혼합 |

---

## 10. 남은 작업 / 의존 사항

### 10-1. Stock 모델 현황 확인 (최우선)

Stock 모델에 sector, industry 필드가 있는지 확인. 없으면:
- Stock 모델 수정 작업 (외부 앱이면 권한 확인)
- FMP `/profile` 엔드포인트 데이터 동기화 배치 설계

### 10-2. Price Feed 인터페이스

ReturnCalculator는 현재 가격을 얻기 위한 `PriceFeedInterface` 필요. 이는 기존 FMP 연동 코드 재사용 가능.

### 10-3. ReturnCalculator 구현

이 문서의 §3 알고리즘을 Python으로 구현. 단위 테스트 포함.

### 10-4. StoredAnalysis 모델 수정

`portfolio_return_breakdown`, `wallet_return_breakdown` JSONField 추가 마이그레이션.

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 — 세션 D 수익률 추적 결정 전체 문서화. RV1~RV4 확정 반영. |
