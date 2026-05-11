# Stock-Vis Wallet / Portfolio Architecture

> **문서 버전**: v1.0 (2026-04-20)
> **작성 배경**: 세션 D 결정 사항 중 데이터 아키텍처 영역
> **관련 문서**:
> - `preset-design-v3.1.md` (프리셋 시스템 철학 — 기존 유지)
> - `return-tracking-design-v1.md` (수익률 추적 — 이 문서의 데이터 모델 위에 구축)
> - `coach-llm-design-v1.md` (Coach LLM — 이 문서의 개념 구분 위에 구축)

---

## 1. 배경과 요구사항

### 1-1. 문제의 출발점

초기 설계에서는 `Portfolio` 모델 하나가 **"사용자의 보유 전체"**와 **"분석 대상"**이라는 두 역할을 겸했다. 이 단순화는 다음 요구를 수용하지 못한다.

- 사용자는 자산 지갑에 있는 **모든 종목을 항상 같이 분석하고 싶지는 않다**.
- 일부 종목은 **다른 이유**로 보유 중일 수 있다 (장기 선물, 증여, 전략 외 보유).
- 사용자는 **관점별로 다른 묶음**을 보고 싶다 — "Tech 성장주 묶음은 GARP으로", "배당 묶음은 Dividend Growth로", "퀄리티 장기 보유는 Buffett으로".

### 1-2. 컨설턴트 비유

실제 투자 컨설팅에서 이런 구조는 다음과 같이 정리된다.

> **"컨설턴트는 고객이 제시한 종목만 본다. 제시하지 않은 것까지 분석하지 않는다."**

즉 **"사용자가 이번에 분석해달라고 제시한 묶음"** 이 자연스러운 Portfolio의 정의다. 보유 전체를 부르는 것이 아니라, **선택된 분석 대상**을 부르는 이름이다.

### 1-3. 개념 분리 원칙

| 개념 | 의미 | 모델 |
|---|---|---|
| **Wallet** (자산 지갑) | 사용자가 실제로 소유한 종목 전체. 사실 기록. | `Wallet`, `WalletHolding` |
| **Portfolio** (분석 대상) | Wallet의 부분집합. 사용자가 이번에 분석하려고 선택한 묶음. | `Portfolio` (의미 재정의) |

**핵심**: 한 Wallet에서 **여러 Portfolio**가 존재할 수 있다. Wallet에 없는 종목은 Portfolio에 들어갈 수 없다 (Wallet = 보유의 진실).

---

## 2. 핵심 개념 분리

### 2-1. Wallet

사용자의 **실제 보유 상태**. 다음 기능의 단일 출처.

- 종목 추가/제거/수량 변경
- 수익률 추적 (전체 자산 기준)
- 자산 변화 이력 (Phase 2 Trade 모델 도입 시 정밀화)
- 세금 계산 (Phase 2+)
- 포트폴리오 변천 시계열 (WalletSnapshot 기반)

**핵심 속성**: **변경의 진실 원천**. Wallet이 변하면 관련된 모든 Portfolio도 영향받는다 (§5 정책 참조).

### 2-2. Portfolio (의미 재정의)

**분석을 위해 선택된 Wallet 종목의 부분집합**.

- 사용자가 자산 지갑에서 체크박스로 종목을 선택해 생성
- 이름을 붙여 저장하거나 (명명 그룹), 일회성으로 분석 후 버릴 수 있음 (임시)
- 각 Portfolio는 독립적으로 프리셋 적용 가능
- AnalysisRun은 Portfolio를 기준으로 실행 (Wallet 전체가 아님)

**중요**: Portfolio는 **Wallet의 "뷰"** 성격이 강하다. Wallet에서 종목이 매도되면 Portfolio에서도 자동 제외된다 (§5).

### 2-3. 왜 "Portfolio"라는 이름을 재활용하는가

- **컨설턴트 비유와 일치**: 고객이 "이 종목들 봐주세요"라고 제시한 묶음을 컨설턴트는 자연스럽게 "포트폴리오"로 부른다.
- **업계 관용 내 용례 있음**: "Model Portfolio", "Sector Portfolio", "Tactical Portfolio" 등 특정 목적으로 구성된 종목 묶음을 Portfolio로 부르는 관습은 실제로 존재.
- **UI 일관성**: 사용자 UI에서 "포트폴리오 전략", "내 포트폴리오"라는 한국어 표현이 자연스럽게 쓰임.
- **별도 신규 용어(AnalysisGroup 등) 회피**: 용어 수를 줄여 학습 부담 최소화.

단 **LLM 프롬프트에서는 혼동 방지**를 위해 별도 규약을 사용한다 (`coach-llm-design-v1.md` PV3 참조).

---

## 3. 데이터 모델 설계

### 3-1. 모델 구조 개요

```
User
 └─ Wallet (1:1 또는 1:N, 현재 MVP는 1:1)
     ├─ WalletHolding (N개, 현재 보유 종목)
     └─ WalletSnapshot (N개, 시점별 상태 기록)

Wallet
 └─ Portfolio (N개, 분석 대상 묶음)
     ├─ wallet_holding_ids (선택된 WalletHolding ID 리스트)
     └─ AnalysisRun (N개, 프리셋별 분석 실행)
         └─ ... 기존 MetricResult, DiagnosticCard 등
```

### 3-2. Wallet 모델 (신규)

```python
class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="wallets",
    )
    name = models.CharField(
        max_length=100,
        default="My Wallet",
        help_text="자산 지갑 이름. MVP는 사용자당 1개.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user"])]
```

**MVP 단순화**: 사용자당 Wallet 1개. Phase 2에서 다중 Wallet(예: "장기 투자용", "단기 트레이딩용") 지원 가능.

### 3-3. WalletHolding 모델 (신규)

`Holding`의 개념을 이어받되 Wallet 하위로 재배치.

```python
class WalletHolding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        related_name="wallet_holdings",
    )

    # ---- 매수 정보 ----
    shares = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="보유 수량",
    )
    avg_cost = models.DecimalField(
        max_digits=12, decimal_places=4,
        help_text="평균 매수 단가 (USD). Phase 2 Trade 모델 도입 시 자동 계산.",
    )
    first_bought_at = models.DateField()

    # ---- 투자 근거 (Thesis Y1) ----
    investment_thesis = models.TextField(
        blank=True,
        help_text="매수 시 투자 근거. Coach가 대화 맥락으로 활용.",
    )

    # ---- 시뮬레이션 스냅샷 ----
    buy_snapshot = models.JSONField(
        null=True, blank=True,
        help_text="매수 확정 시점의 Wallet 구성 스냅샷.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["wallet"]),
            models.Index(fields=["wallet", "stock"]),
        ]
        unique_together = [("wallet", "stock")]
```

**주의**:
- `sector`, `industry` 필드는 `Stock` 모델에 위치 (결정 RV2-b). `WalletHolding`은 Stock FK로 참조.
- Stock 모델에 해당 필드가 없다면 추가 작업 필요 (§9 마이그레이션 플랜).

### 3-4. Portfolio 모델 (의미 재정의)

기존 `Portfolio`의 의미를 "분석 대상 슬라이스"로 전환. 이름 유지.

```python
class Portfolio(models.Model):
    """
    분석을 위해 선택된 WalletHolding의 부분집합.

    - Wallet의 "뷰" 성격
    - 이름을 붙여 저장 (명명 그룹) 또는 일회성 (임시)
    - AnalysisRun은 Portfolio를 기준으로 실행
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    name = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="분석 그룹 이름. null이면 임시 그룹 (일회성).",
    )
    description = models.TextField(
        blank=True,
        help_text="이 분석 묶음의 목적/근거.",
    )
    wallet_holding_ids = models.JSONField(
        help_text="선택된 WalletHolding UUID 리스트. "
                  "매도된 종목은 실행 시점에 자동 필터링 (H3 정책).",
    )
    save_type = models.CharField(
        max_length=20,
        choices=[("named", "Named"), ("temporary", "Temporary")],
        default="temporary",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["wallet", "save_type"]),
            models.Index(fields=["wallet", "name"]),
        ]

    def effective_holdings(self):
        """
        실행 시점에 유효한 WalletHolding만 필터링 (H3 참조 링크 정책).
        매도된 종목은 자동 제외.
        """
        return WalletHolding.objects.filter(
            id__in=self.wallet_holding_ids,
            wallet=self.wallet,
        )
```

**핵심 필드 설명**:
- `wallet_holding_ids`: 선택된 WalletHolding의 UUID 리스트를 JSONField로 저장. 외래키 배열을 쓰지 않는 이유는 실행 시점에 자동 필터링(H3)을 단순하게 하기 위함.
- `save_type`:
  - `"named"`: 사용자가 이름 붙여 저장한 그룹 (예: "Tech 성장주")
  - `"temporary"`: 일회성 분석용. 세션 종료 시 정리 배치로 삭제 가능.
- `effective_holdings()`: 실행 시점에 Wallet에 여전히 존재하는 것만 반환. 매도된 종목 자동 제외.

### 3-5. WalletSnapshot 모델 (신규, 결정 A1)

Wallet의 시점별 상태를 기록. Coach가 Wallet 시계열 변화를 분석할 때 사용 (결정 W2.5, 시나리오 A).

```python
class WalletSnapshot(models.Model):
    """
    Wallet의 특정 시점 상태 기록.

    트리거:
    - Saved Analysis 저장 시 자동 생성
    - Wallet 첫 설정 시 초기 스냅샷 자동 생성
    - (Phase 2) 주기 배치로 추가 생성 가능

    용도:
    - Coach가 Wallet 변화 추이 분석 (Case 1, 2)
    - Phase 2 사후 비교의 시계열 데이터
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    triggered_by = models.CharField(
        max_length=30,
        choices=[
            ("initial_setup", "Initial Setup"),
            ("saved_analysis", "Saved Analysis"),
            ("periodic_batch", "Periodic Batch (Phase 2)"),
            ("manual", "Manual"),
        ],
    )
    triggered_by_ref = models.UUIDField(
        null=True, blank=True,
        help_text="트리거한 StoredAnalysis ID 등.",
    )
    holdings_json = models.JSONField(
        help_text=(
            "스냅샷 시점의 WalletHolding 구조화 복사. "
            "[{stock_id, shares, avg_cost, sector, industry, market_value}, ...]"
        ),
    )
    aggregate_metrics = models.JSONField(
        help_text=(
            "집계 지표. "
            "{total_value, sector_distribution, industry_distribution, holding_count}"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
            models.Index(fields=["triggered_by"]),
        ]
```

**저장 데이터 크기 추정**: 종목 10~20개 기준 스냅샷 1건당 20~50KB. 사용자당 연간 20~30건 저장 가정 시 총 1~2MB. 관리 가능 수준.

**오래된 스냅샷 정리 정책**: MVP에서는 무제한 보관. Phase 2에서 "1년 이상은 월 1건만 유지" 등 정책 도입 검토.

### 3-6. AnalysisRun 수정

기존 `portfolio` FK의 의미가 자연스러워짐 (Portfolio = 분석 대상 슬라이스이므로).

```python
class AnalysisRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="analysis_runs",
    )
    preset_id = models.CharField(max_length=50)

    # ---- 버전 번들 (결정 M-4) ----
    preset_version = models.CharField(max_length=10)
    metric_version = models.CharField(max_length=10)
    scoring_version = models.CharField(max_length=10)
    prompt_version = models.CharField(max_length=10)
    universe_version = models.CharField(max_length=20)

    # ---- 실행 메타 ----
    executed_at = models.DateTimeField(auto_now_add=True)
    execution_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )

    # ---- Wallet 스냅샷 연결 (RV4-b) ----
    wallet_snapshot_at_execution = models.ForeignKey(
        WalletSnapshot,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="analyses_at_time",
        help_text="실행 시점 Wallet 스냅샷 (Saved로 승격 시 자동 생성).",
    )

    class Meta:
        indexes = [
            models.Index(fields=["portfolio", "-executed_at"]),
            models.Index(fields=["preset_id", "-executed_at"]),
        ]
```

**변경점**:
- `wallet_snapshot_at_execution` FK 신규 추가. Saved Analysis로 승격 시 WalletSnapshot과 연결. Temporary 상태에서는 null 가능.

### 3-7. 프리셋별 적용 가능 스코프 (결정 G3)

프리셋 정의에 스코프 호환성 정보 추가. `presets.py` 수정 필요.

```python
PRESETS = {
    "buffett_quality_value": {
        ...existing fields...,
        "applicable_scope": ["individual", "portfolio"],
    },
    "concentrated_portfolio": {
        ...existing fields...,
        "applicable_scope": ["portfolio"],  # 개별 종목 분석 의미 없음
    },
    "low_volatility": {
        ...existing fields...,
        "applicable_scope": ["portfolio"],  # portfolio_volatility 등이 Core
    },
    "multi_factor": {
        ...existing fields...,
        "applicable_scope": ["portfolio"],  # 합성 지표는 복수 종목 필요
    },
    # ...기타 프리셋은 "individual" + "portfolio" 조합
}
```

**UI 로직**: 사용자가 종목을 1개 선택 → `applicable_scope`에 `"individual"` 포함된 프리셋만 표시. 2개 이상 → `"portfolio"` 포함된 프리셋 표시.

**MVP 프리셋별 스코프 배정 (권장)**:

| 프리셋 | individual | portfolio |
|---|---|---|
| buffett_quality_value | ✅ | ✅ |
| piotroski_f_score | ✅ | ✅ |
| garp | ✅ | ✅ |
| quality_growth | ✅ | ✅ |
| dividend_growth | ✅ | ✅ |
| shareholder_yield | ✅ | ✅ |
| quality_factor | ✅ | ✅ |
| low_volatility | ❌ | ✅ |
| price_momentum | ✅ | ✅ |
| multi_factor | ❌ | ✅ |
| contrarian | ✅ | ✅ |
| concentrated_portfolio | ❌ | ✅ |

---

## 4. UX 구조

### 4-1. 탭 네비게이터 구조

포트폴리오 페이지는 **두 개의 탭**으로 구성. 동시 노출 없음.

```
Portfolio Page
├─ Tab 1: 자산 지갑
│   └─ Wallet CRUD, 수익률 추적, 변화 이력
│
└─ Tab 2: 자산 전략실
    ├─ 개별 전략 (단일 종목 분석)
    └─ 포트폴리오 전략 (묶음 분석)
```

### 4-2. 자산 지갑 탭

**구성**:
- 현재 보유 종목 리스트 (종목, 수량, 평가금액, 수익률)
- 수익률 추적 (섹터/인더스트리/종목별 분해 — `return-tracking-design-v1.md`)
- 포트폴리오 변화 이력 (WalletSnapshot 기반 간이 타임라인)
- 세금 계산 (Phase 2+)

**사용자 액션**:
- 종목 추가/제거/수량 변경
- 특정 시점 스냅샷 수동 생성 (선택 사항)

### 4-3. 자산 전략실 탭

**진입 시 기본 동작** (결정 A + 이전 결정):
- 이전 분석 결과 표시 (마지막 Saved Analysis 또는 마지막 Temp Analysis)
- 상단 소프트 알림: "포트폴리오가 변경되었습니다" (자산 지갑 수정 후 첫 진입 시)
- "재분석" 버튼 또는 "이전 결과 유지" 선택
- 이전 분석 없으면 → "새 전략 시작하기" 화면

**하위 구조**:

#### 개별 전략
- 자산 지갑에서 **종목 1개 선택** → 프리셋 선택 → 분석 실행
- 프리셋 목록은 `applicable_scope`에 `"individual"` 포함된 것만 표시

#### 포트폴리오 전략
- 자산 지갑 체크박스 UI → **2개 이상 종목 선택** → 이름(선택) → 프리셋 선택 → 분석 실행
- 또는 저장된 Portfolio(명명 그룹) 선택 → 프리셋 선택 → 실행
- 프리셋 목록은 `applicable_scope`에 `"portfolio"` 포함된 것만 표시

#### Coach 대화 영역
- 현재 분석 결과를 맥락으로 Q&A
- 레벨 1 조정 요청 가능 ("이번만 ROIC 기준 20%로")
- 조정 요청 시 확인 카드 → 실행

### 4-4. 자산 지갑 ↔ 전략실 흐름

```
[자산 지갑 탭]
사용자가 Wallet 수정 (NVDA 비중 변경, ABC 종목 추가)
  ↓
저장 (WalletHolding 업데이트)
  ↓
사용자가 [자산 전략실] 탭으로 이동
  ↓
[자산 전략실 진입 화면]
- 이전 분석 결과 표시
- 상단 배너: "🔄 포트폴리오가 변경되었습니다"
- [재분석 버튼] | [이전 결과 유지]
  ↓
사용자가 "재분석" 클릭
  ↓
- Wallet의 현재 상태로 Portfolio 구성 (기본값: 이전 Portfolio와 동일 wallet_holding_ids)
- 선택: 새 Portfolio 구성 (체크박스 UI)
- 프리셋 선택 (이전 프리셋 기본)
- 실행
```

**핵심 원칙**:
- "재분석 필요 배지"는 각 모듈에 개별 표시하지 않음 (병진 결정)
- 진입 자체가 재분석 의도 → 소프트 알림만 제공

---

## 5. 전략 저장 정책 (결정 F3)

### 5-1. 두 가지 저장 수준

Portfolio(분석 슬라이스)는 **일회성** 또는 **명명 그룹** 두 형태로 존재 가능.

| 형태 | save_type | 생성 방식 | 수명 |
|---|---|---|---|
| 일회성 | `"temporary"` | 체크박스 선택 → 즉시 분석 | 세션 종료 시 정리 배치로 삭제 |
| 명명 그룹 | `"named"` | 체크박스 선택 → 이름 입력 → 저장 | 사용자가 삭제할 때까지 영속 |

### 5-2. 일회성 → 명명 승격

사용자 워크플로우:
1. 체크박스로 종목 선택 → Temporary Portfolio 생성
2. 분석 실행 → 결과 확인
3. "맘에 들어. 이 구성 저장할래" 버튼 클릭
4. 이름 입력 → `save_type`이 `"named"`로 변경

**DB 수준**: 동일 Portfolio 레코드의 `save_type`만 변경. 새 레코드 생성 아님.

### 5-3. Temporary Portfolio 정리

**배치 정책** (Phase 2에 도입, MVP는 수동 삭제):
- 생성 후 30일 경과 + 연결된 Saved Analysis 없음 → 자동 삭제
- Saved Analysis에 연결된 Temporary는 삭제하지 않음 (사후 비교 가능성)

---

## 6. 개별 전략 vs 포트폴리오 전략 (결정 G3)

### 6-1. 개념 구분

| 전략 유형 | 대상 | Portfolio.wallet_holding_ids | 의미 |
|---|---|---|---|
| 개별 전략 | 단일 종목 | 1개 ID | "이 종목 하나를 Buffett 관점으로 보기" |
| 포트폴리오 전략 | 종목 묶음 | 2개 이상 ID | "이 묶음 전체를 GARP 관점으로 보기" |

### 6-2. 프리셋 호환성 필터링

`applicable_scope` 기반 (§3-7). UI는 선택된 종목 수에 따라 프리셋 목록을 자동 필터링.

```python
# 프리셋 필터링 로직 (pseudo-code)
def get_applicable_presets(selected_holdings_count: int) -> list[Preset]:
    scope = "individual" if selected_holdings_count == 1 else "portfolio"
    return [
        preset for preset in PRESETS.values()
        if scope in preset["applicable_scope"]
    ]
```

### 6-3. 분석 엔진 차이

- **개별 전략**: 프리셋의 Type 1 (stock_level) 지표만 계산. Type 2 (portfolio_level), Type 3 (composite) 지표는 N/A.
- **포트폴리오 전략**: Type 1~3 모두 계산. 퍼센타일은 분석 대상 내에서 비중 가중 집계.

### 6-4. Coach 대화 톤 차이

- **개별 전략**: "이 종목은 ROIC 기준으로 상위 12%에 있습니다."
- **포트폴리오 전략**: "당신의 포트폴리오는 전반적으로 ROIC 상위 24%에 있고, 그 중 INTC가 하위에 위치합니다."

시스템 프롬프트에서 `scope` 파라미터로 톤 전환 (`coach-llm-design-v1.md` 참조).

---

## 7. 자산 변경 시 그룹 처리 (결정 H3)

### 7-1. 정책: 참조 링크 + 자동 필터링

Portfolio는 `wallet_holding_ids` (UUID 리스트)로 **참조만** 보관. 실제 분석 실행 시 Wallet에 현재 존재하는 WalletHolding만 필터링.

### 7-2. 시나리오별 동작

**시나리오 1: WalletHolding 매도 (삭제)**

```
기존 상태:
  Wallet: [NVDA, MSFT, INTC, AAPL, GOOGL]
  Portfolio "Tech 성장주": [NVDA, MSFT, INTC]

사용자가 INTC 매도
  ↓
Wallet: [NVDA, MSFT, AAPL, GOOGL]  (INTC 제거)
Portfolio "Tech 성장주" wallet_holding_ids: [NVDA_id, MSFT_id, INTC_id]
  (Portfolio 정의는 안 바뀜)

다음 분석 실행 시:
  Portfolio.effective_holdings() → [NVDA, MSFT]
  (INTC는 Wallet에 없어 자동 제외)
```

**시나리오 2: 동일 종목 재매수**

```
이후 사용자가 INTC 재매수
  ↓
Wallet: [NVDA, MSFT, AAPL, GOOGL, INTC]  (INTC 복귀, 새 WalletHolding ID)
Portfolio "Tech 성장주" wallet_holding_ids: [NVDA_id, MSFT_id, OLD_INTC_id]
  (OLD_INTC_id는 이미 삭제된 ID)

다음 분석 실행 시:
  Portfolio.effective_holdings() → [NVDA, MSFT]
  (새 INTC는 ID가 다르므로 자동 포함 안 됨)
```

**결과**: 종목 재매수는 수동 추가 필요. 이는 의도적 — 재매수는 새로운 투자 결정이므로 Portfolio 재검토가 자연스러움.

### 7-3. UI 알림

Portfolio를 열었을 때:
- 원래 정의 종목 3개 중 1개가 매도됨 → "이 그룹의 원래 3개 종목 중 1개(INTC)가 매도되었습니다. 현재 2개 종목으로 분석됩니다."
- 사용자 선택:
  - "현재 2개로 계속" (기본)
  - "INTC 빼고 정의 업데이트" (wallet_holding_ids에서 INTC 제거)
  - "INTC 다시 추가" (재매수 후 Wallet에 다시 있을 때만 활성)

---

## 8. Saved Analysis와의 관계 (결정 ③)

### 8-1. Saved vs Temporary 분석

기존 결정 ③ 유지:
- **Saved Analysis**: 명시적 저장. Portfolio 스냅샷 + WalletSnapshot 포함하여 **시점 고정**.
- **Temporary Analysis**: 자동 저장 (세션 중). Portfolio 참조는 라이브.

### 8-2. 저장 시 자동 동작

사용자가 "이 분석 저장" 클릭 시:
1. 현재 AnalysisRun이 `save_type = "saved"`로 승격
2. **Wallet 현재 상태로 WalletSnapshot 자동 생성**
3. `AnalysisRun.wallet_snapshot_at_execution` 에 연결
4. Portfolio는 `save_type`이 `"named"`였으면 그대로, `"temporary"`였으면 사용자에게 "Portfolio도 저장할까요?" 질문

### 8-3. Saved Analysis 재방문 시 (결정 RV4-b)

사용자가 이전 Saved Analysis를 열 때 두 시점 정보 모두 제공:
- **저장 시점**: AnalysisRun + WalletSnapshot에 저장된 값 (불변)
- **현재 시점**: 현재 Wallet/Portfolio 기준 재계산 (ReturnCalculator)

UI 예시:
```
분석: Tech 성장주 (Buffett)
저장 시점: 2026-01-15

수익률:
  저장 시점: +12% (3개월 전)
  현재:      +15% (오늘)
  변화:      +3%p 상승

[현재 상태로 재분석하기]  [저장 시점 상세 보기]
```

---

## 9. 마이그레이션 플랜

### 9-1. 현재 상태 (Before)

```
Portfolio
 ├─ Holding (종목 보유 정보)
 ├─ CandidateHolding (매수 예비 후보)
 └─ AnalysisRun
```

### 9-2. 목표 상태 (After)

```
Wallet
 ├─ WalletHolding (← 이전 Holding 내용 이관)
 └─ WalletSnapshot (신규)

Portfolio (의미 재정의)
 └─ wallet_holding_ids (선택된 WalletHolding 참조)

AnalysisRun (Portfolio FK 관계 유지)
```

### 9-3. 마이그레이션 단계

**Phase 0: 사전 확인**
1. Stock 모델에 `sector`, `industry` 필드 존재 여부 확인
2. 없으면 Stock 모델에 필드 추가 (결정 RV2-b의 전제)
3. Stock의 sector/industry 데이터 소스 확정 (FMP `/profile` 엔드포인트)

**Phase 1: 모델 추가 (기존 삭제 없음)**
1. `Wallet`, `WalletHolding`, `WalletSnapshot` 모델 추가
2. 기존 `Portfolio`, `Holding`은 일단 유지 (deprecated 표시)
3. 마이그레이션: 각 `Portfolio` → 동일 User의 `Wallet` 생성, `Holding` → `WalletHolding` 복사

**Phase 2: Portfolio 의미 전환**
1. `Portfolio`에 `wallet` FK 추가 (각 Portfolio를 동일 User의 Wallet에 연결)
2. `Portfolio`에 `wallet_holding_ids`, `save_type` 필드 추가
3. `wallet_holding_ids`는 초기값으로 해당 Portfolio의 모든 Holding의 ID 채움
4. `AnalysisRun.portfolio` FK는 변경 없음 (의미만 전환)

**Phase 3: 구 모델 제거**
1. `CandidateHolding`은 별도 검토 (Phase 2 Watchlist 기능과 통합 가능성)
2. `Holding` 삭제 (`WalletHolding`이 대체)
3. `Portfolio`의 기존 `holdings` related manager 제거 (`wallet_holding_ids` 사용)

**현재 시점 특성**: Stock-Vis는 아직 프로덕션 데이터 없음 → 마이그레이션은 `makemigrations` + 초기 데이터 없이 schema 교체로 가능.

### 9-4. 의존 파일 영향

| 파일 | 영향 |
|---|---|
| `models.py` | 대폭 수정 (3개 모델 추가 + 2개 모델 수정) |
| `presets.py` | `applicable_scope` 필드 추가 |
| `preset_metrics.py` | 영향 없음 |
| `metrics.py` | 영향 없음 |
| `metric-dictionary-v1.2.md` | "포트폴리오" 용어가 "분석 슬라이스" 의미라는 주석 1곳 추가 |
| `preset-design-v3.1.md` | 내용은 유지, 다만 INDEX.md에서 "Wallet 분리 이후의 Portfolio 의미"를 주석 처리 |

---

## 10. 확정 결정 목록

이 문서에 반영된 결정:

| # | 결정 | 내용 |
|---|---|---|
| F3 | 전략 저장 수준 | 일회성 + 명명 그룹 하이브리드 |
| G3 | 개별/포트폴리오 전략 구분 | 프리셋별 `applicable_scope` 필드 |
| H3 | 자산 변경 시 그룹 처리 | 참조 링크 + 자동 필터링 |
| I2-a-refined | 모델 재설계 | Wallet 신규 + Portfolio 의미 재정의 |
| A1 | Wallet 시계열 구현 | WalletSnapshot 모델 (주기 배치 없음) |
| W2.5 | Wallet 분석 범위 | 시나리오 A (시계열 변화) + B (배경 대조), C (후보 추천) 제외 |
| ③ | Saved Analysis 스냅샷 | Saved는 스냅샷, Temp는 라이브 |

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 — 세션 D 결정 사항 중 데이터 아키텍처 영역 완전 문서화 |
