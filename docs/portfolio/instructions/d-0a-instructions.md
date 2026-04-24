# D-0a Instructions: Data Model Refactoring

> **세션**: D-0a
> **목적**: Wallet/Portfolio 개념 분리 + Coach 대화/의사결정 모델 추가
> **대상 에이전트**: Claude Code (또는 동급 코딩 에이전트)
> **버전**: v1.0 (2026-04-20)
> **상태**: 작업 대기 — 이 지시서와 참조 문서만으로 실행 가능해야 함

---

## 0. 에이전트가 먼저 읽을 것

이 지시서는 **자기완결적이지 않다**. 아래 문서를 참조하며 작업한다.

**필수 참조**:
1. `docs/portfolio/design/wallet-portfolio-architecture-v1.md` — 데이터 모델 상세 설계 (§3 전체)
2. `docs/portfolio/design/coach-llm-design-v1.md` — ChatSession/Message/Decision 모델 (§5-3, §6-2)
3. `docs/portfolio/implementation/models.py` — 현재 상태 (수정 대상)

**선택 참조** (맥락 이해 필요 시):
4. `docs/portfolio/design/return-tracking-design-v1.md` — Stock 모델 sector/industry 활용 정책 (§2-2)
5. `docs/portfolio/INDEX.md` — 전체 결정 목록 (§4-2 세션 D 결정 34개)

---

## 1. 목표

`docs/portfolio/implementation/models.py` 를 세션 D 설계에 맞게 리팩토링한다.

### 1-1. 완료 시점의 모델 구성 (목표 상태)

| # | 모델 | 상태 | 변경 유형 |
|---|---|---|---|
| 1 | `Wallet` | 신규 | 추가 |
| 2 | `WalletHolding` | 신규 | 추가 |
| 3 | `WalletSnapshot` | 신규 | 추가 |
| 4 | `Portfolio` | 기존 → 재정의 | 전면 수정 |
| 5 | `AnalysisRun` | 기존 + 수정 | 필드 1개 추가 |
| 6 | `MetricResult` | 유지 | 변경 없음 |
| 7 | `DiagnosticCard` | 유지 | 변경 없음 |
| 8 | `LLMComment` | 유지 | 변경 없음 |
| 9 | `StoredAnalysis` | 기존 + 확장 | 필드 2개 추가 |
| 10 | `PercentileCache` | 유지 | 변경 없음 |
| 11 | `ChatSession` | 신규 | 추가 |
| 12 | `Message` | 신규 | 추가 |
| 13 | `Decision` | 신규 | 추가 |
| 14 | `Holding` | 삭제 | 제거 (데이터 이관 불필요) |
| 15 | `CandidateHolding` | 삭제 | 제거 (Phase 2 Watchlist로 이연) |

**최종 모델 수**: 13개.

### 1-2. 이 지시서에서 제외되는 작업

- Pydantic 스키마 작성 (D-0b 세션)
- LLM 프롬프트 작성 (D-1 이후 세션)
- 뷰/API 엔드포인트 (세션 D 범위 외)
- 프론트엔드 (세션 D 범위 외)

---

## 2. 사전 조건 (작업 시작 전 확인)

### 2-1. 환경 전제

- [x] Stock 모델 확인 완료: `stocks/models.py`에 `sector`, `industry` 필드 존재 (CharField, max_length=100, null=True)
- [x] Stock 모델에 `sector`, `industry` 인덱스 존재
- [x] RV2-b 경로 확정: WalletHolding은 `stocks.Stock` FK로 sector/industry 조회
- [x] RV2-a 폴백 불필요 (WalletHolding에 sector/industry 캐시 금지)

### 2-2. 데이터 전제

- 프로덕션 데이터 없음 → 기존 `Holding`, `CandidateHolding`, `Portfolio` 테이블 drop + recreate 가능
- 마이그레이션 파일은 **기존 파일 삭제 후 새로 생성** 허용 (`python manage.py makemigrations` 에서 0001_initial부터 새로 생성)

### 2-3. 의존 파일 영향

| 파일 | 수정 필요 여부 | 비고 |
|---|---|---|
| `docs/portfolio/implementation/models.py` | **예** | 메인 작업 대상 |
| `docs/portfolio/implementation/metrics/definitions/presets.py` | 아니오 (D-0a에선 건드리지 않음) | `applicable_scope` 추가는 D-0b 이후 |
| `docs/portfolio/implementation/metrics/definitions/*.py` | 아니오 | 지표/매핑 정의는 이번 작업 영향 없음 |
| `stocks/app` 전체 | 아니오 | Stock 모델은 이미 완비됨 |

---

## 3. 작업 스코프

### 3-1. In Scope

- `models.py` 리팩토링 (13개 모델 최종 상태로)
- Django 마이그레이션 생성 (`makemigrations` 단계까지)
- 모델 간 FK 관계 재설정
- Meta 옵션 (indexes, constraints, ordering) 정의
- 문자열 표현(`__str__`) 메소드 유지/작성

### 3-2. Out of Scope

- `migrate` 실행 (마이그레이션 파일 생성까지만)
- 테스트 코드 작성 (별도 세션)
- 시드 데이터 생성
- 기존 데이터 이관 스크립트 (데이터 없으므로 불필요)
- Pydantic 스키마 (D-0b)

---

## 4. 단계별 작업 명세

각 단계는 순서대로 진행. 각 단계의 **완료 기준**을 충족한 후 다음 단계로.

### Step 1: Wallet 모델 추가

**설계 문서 참조**: `wallet-portfolio-architecture-v1.md` §3-2

**작업 내용**:
- `Wallet` 모델 신규 작성
- 위치: `models.py` 상단, `Portfolio` 정의보다 앞
- `User` FK 포함 (`settings.AUTH_USER_MODEL` 사용 — 기존 코드 관례 따름)

**완료 기준**:
- 필드: `id` (UUID PK), `user` (FK), `name` (CharField, default="My Wallet"), `created_at`, `updated_at`
- Meta: `indexes = [models.Index(fields=["user"])]`
- `__str__` 메소드 정의
- `on_delete=models.CASCADE` (User 삭제 시 Wallet도 삭제)
- `related_name="wallets"` 유지

**비고**:
- MVP는 사용자당 Wallet 1개 사용하지만 모델은 1:N 구조로 열어둠 (unique constraint 없이)
- Phase 2에 다중 Wallet 지원 가능

### Step 2: WalletHolding 모델 추가

**설계 문서 참조**: `wallet-portfolio-architecture-v1.md` §3-3

**작업 내용**:
- `WalletHolding` 모델 신규 작성
- 기존 `Holding` 모델의 모든 필드 이관 (avg_cost, shares, first_bought_at, investment_thesis, buy_snapshot 등)
- FK 대상 변경: `Portfolio` → `Wallet`

**완료 기준**:
- 필드 목록:
 - `id` (UUID PK)
 - `wallet` (FK → Wallet, on_delete=CASCADE, related_name="holdings")
 - `stock` (FK → "stocks.Stock", on_delete=PROTECT, related_name="wallet_holdings")
 - `shares` (DecimalField, max_digits=14, decimal_places=4)
 - `avg_cost` (DecimalField, max_digits=12, decimal_places=4)
 - `first_bought_at` (DateField)
 - `investment_thesis` (TextField, blank=True)
 - `buy_snapshot` (JSONField, null=True, blank=True)
 - `created_at`, `updated_at`
- Meta:
 - `indexes = [Index(["wallet"]), Index(["wallet", "stock"])]`
 - `unique_together = [("wallet", "stock")]` — 같은 Wallet에 같은 Stock 중복 불가

**중요 원칙 (RV2-b)**:
- `sector`, `industry` 필드는 **여기 두지 않는다**
- 필요 시 `wallet_holding.stock.sector`, `wallet_holding.stock.industry` 경로로 접근
- sector/industry 캐시 필드 추가는 **명시적으로 금지** (RV2-a 폴백은 불필요)

**기존 Holding 모델과의 차이점**:
- FK 대상: Portfolio → Wallet
- related_name: "holdings" 유지 (단 Wallet 기준)
- 나머지 필드 동일하게 이관

### Step 3: WalletSnapshot 모델 추가

**설계 문서 참조**: `wallet-portfolio-architecture-v1.md` §3-5

**작업 내용**:
- `WalletSnapshot` 모델 신규 작성
- 결정 A1: 주기 배치 없이 이벤트 기반 생성

**완료 기준**:
- 필드 목록:
 - `id` (UUID PK)
 - `wallet` (FK → Wallet, on_delete=CASCADE, related_name="snapshots")
 - `triggered_by` (CharField, choices=[("initial_setup", ...), ("saved_analysis", ...), ("periodic_batch", ...), ("manual", ...)])
 - `triggered_by_ref` (UUIDField, null=True, blank=True) — 트리거한 StoredAnalysis 등의 ID
 - `holdings_json` (JSONField) — 스냅샷 시점의 WalletHolding 구조화
 - `aggregate_metrics` (JSONField) — 집계 지표 (sector_distribution, total_value 등)
 - `created_at`
- Meta:
 - `indexes = [Index(["wallet", "-created_at"]), Index(["triggered_by"])]`

**choices 전체 값**:
- `("initial_setup", "Initial Setup")`
- `("saved_analysis", "Saved Analysis")`
- `("periodic_batch", "Periodic Batch (Phase 2)")`
- `("manual", "Manual")`

### Step 4: Portfolio 모델 재정의

**설계 문서 참조**: `wallet-portfolio-architecture-v1.md` §3-4 + §7 (H3 참조 링크 정책)

**작업 내용**:
- 기존 `Portfolio` 모델을 **의미 재정의** (분석 대상 슬라이스)
- 기존 필드 중 유지/제거/신규 구분

**완료 기준**:
- 기존 필드 처리:
 - `id` — 유지
 - `user` — **제거** (Wallet이 user 참조하므로 Portfolio는 wallet을 통해 간접 참조)
 - `name` — 유지, **Nullable로 변경** (null=True, blank=True, max_length=100) — 임시 그룹은 null 가능
 - `description` — 유지
 - `is_default` — **제거** (의미 없음 — 분석 그룹은 기본값 개념 불필요)
 - `created_at`, `updated_at` — 유지
- 신규 필드 추가:
 - `wallet` (FK → Wallet, on_delete=CASCADE, related_name="portfolios")
 - `wallet_holding_ids` (JSONField) — 선택된 WalletHolding UUID 리스트. help_text에 "매도된 종목은 effective_holdings()에서 자동 필터링" 명시
 - `save_type` (CharField, max_length=20, choices=[("named", "Named"), ("temporary", "Temporary")], default="temporary")
- Meta 수정:
 - 기존 `unique_default_portfolio_per_user` constraint **제거**
 - 신규 indexes: `[Index(["wallet", "save_type"]), Index(["wallet", "name"])]`
 - `ordering = ["-created_at"]` 유지
- **신규 메소드**: `effective_holdings(self)` — H3 정책 구현
 ```python
 def effective_holdings(self):
 """
 실행 시점에 유효한 WalletHolding만 필터링 (결정 H3).
 wallet_holding_ids에 있지만 Wallet에서 삭제된 종목은 자동 제외.
 """
 return WalletHolding.objects.filter(
 id__in=self.wallet_holding_ids,
 wallet=self.wallet,
 )
 ```

### Step 5: AnalysisRun 수정

**설계 문서 참조**: `wallet-portfolio-architecture-v1.md` §3-6

**작업 내용**:
- 기존 `AnalysisRun` 모델에 필드 1개 추가
- 기존 필드는 **모두 유지**

**완료 기준**:
- 신규 필드 추가:
 - `wallet_snapshot_at_execution` (FK → WalletSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name="analyses_at_time")
 - help_text: "실행 시점 Wallet 스냅샷 (Saved로 승격 시 자동 생성)"
- `portfolio` FK **의미만** 재정의됨 (코드 변경 없음) — Portfolio가 이제 "분석 대상 슬라이스"
- 기존 불변성 로직(`save()` 메소드), 버전 번들 컬럼, `portfolio_hash` 등 **모두 유지**
- Meta 변경 없음

### Step 6: StoredAnalysis 확장

**설계 문서 참조**: `return-tracking-design-v1.md` §6-2

**작업 내용**:
- 기존 `StoredAnalysis` 모델에 필드 2개 추가 (RV4-b 저장 시점 수익률)

**완료 기준**:
- 신규 필드 추가:
 - `portfolio_return_breakdown` (JSONField, null=True, blank=True) — help_text: "저장 시점 Portfolio 수익률 breakdown. 불변."
 - `wallet_return_breakdown` (JSONField, null=True, blank=True) — help_text: "저장 시점 Wallet 수익률 breakdown. 불변."
- 나머지 필드 유지

**비고**: 이 2개 필드는 MVP에서 **null 허용**. 실제 값 채우기는 `ReturnCalculator` 구현 후 (별도 세션).

### Step 7: ChatSession 모델 추가

**설계 문서 참조**: `coach-llm-design-v1.md` §5-3

**작업 내용**:
- `ChatSession` 모델 신규 작성
- AnalysisRun과 느슨한 연결 (`on_delete=SET_NULL` — AnalysisRun 삭제돼도 ChatSession은 유지)

**완료 기준**:
- 필드 목록:
 - `id` (UUID PK)
 - `user` (FK → settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="chat_sessions")
 - `analysis_run` (FK → AnalysisRun, on_delete=SET_NULL, null=True, blank=True, related_name="chat_sessions")
 - `started_at` (auto_now_add=True)
 - `ended_at` (DateTimeField, null=True, blank=True)
 - `session_summary` (TextField, blank=True) — Tier 2 요약
- Meta:
 - `indexes = [Index(["user", "-started_at"]), Index(["analysis_run"])]`

### Step 8: Message 모델 추가

**설계 문서 참조**: `coach-llm-design-v1.md` §5-3

**작업 내용**:
- `Message` 모델 신규 작성
- ChatSession 하위

**완료 기준**:
- 필드 목록:
 - `id` (UUID PK)
 - `session` (FK → ChatSession, on_delete=CASCADE, related_name="messages")
 - `role` (CharField, max_length=20, choices=[("user", "User"), ("assistant", "Assistant")])
 - `content` (TextField)
 - `metadata` (JSONField, default=dict) — help_text: "예: 조정 요청 시 overrides_json, 진단 카드 생성 시 cards_json"
 - `created_at` (auto_now_add=True)
- Meta:
 - `indexes = [Index(["session", "created_at"])]`

### Step 9: Decision 모델 추가

**설계 문서 참조**: `coach-llm-design-v1.md` §6-2

**작업 내용**:
- `Decision` 모델 신규 작성
- 결정 D3 하이브리드 구조 (raw는 Message, 구조화는 Decision)

**완료 기준**:
- 필드 목록:
 - `id` (UUID PK)
 - `user` (FK → settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="decisions")
 - `decision_type` (CharField, max_length=40, choices=[...]) — 6개 선택지
 - `decision_at` (DateTimeField)
 - `context_analysis_run` (FK → AnalysisRun, on_delete=SET_NULL, null=True, blank=True)
 - `rationale_text` (TextField)
 - `structured_payload` (JSONField)
 - `source_messages` (JSONField, default=list) — Message UUID 리스트
 - `created_at` (auto_now_add=True)
- Meta:
 - `indexes = [Index(["user", "-decision_at"]), Index(["decision_type"])]`

**decision_type choices 전체**:
- `("preset_adjustment", "Preset Adjustment (Level 1)")`
- `("preset_switch", "Preset Switch")`
- `("holding_change_intent", "Holding Change Intent")`
- `("thesis_note", "Thesis Note (Wallet Holding)")`
- `("portfolio_creation", "Portfolio (Analysis Group) Creation")`
- `("preference_signal", "Preference Signal (Subjective)")`

### Step 10: Holding 모델 삭제

**작업 내용**:
- 기존 `Holding` 모델 **완전 제거**
- 데이터 이관 불필요 (프로덕션 데이터 없음)
- WalletHolding이 Holding의 역할 완전 대체

**완료 기준**:
- `class Holding`으로 시작하는 클래스 `models.py`에서 제거
- 다른 모델의 Holding 참조 없음 확인 (기존 `MetricResult`, `DiagnosticCard` 등에 Holding FK 없음 — 확인 후 제거)

### Step 11: CandidateHolding 모델 삭제

**작업 내용**:
- 기존 `CandidateHolding` 모델 **완전 제거**
- Phase 2의 Watchlist 기능과 통합 재설계 예정 (지금은 제거만)

**완료 기준**:
- `class CandidateHolding`으로 시작하는 클래스 `models.py`에서 제거
- 현재 `CandidateHolding`을 참조하는 다른 모델 없음 확인

**결정 근거**: INDEX.md §4-2 "F3 전략 저장: 일회성 + 명명 그룹" + 세션 D 결정 H3 (참조 링크). Phase 2 Watchlist 설계는 별도 진행.

### Step 12: MetricResult, DiagnosticCard, LLMComment, PercentileCache

**작업 내용**: **변경 없음**. 그대로 유지.

**완료 기준**:
- 이 모델들의 FK 체인이 깨지지 않았는지 확인
- 모두 `AnalysisRun` 또는 독립 모델이라 Wallet/Portfolio 구조 변경의 영향 없음

### Step 13: 마이그레이션 생성

**작업 내용**:
- 기존 마이그레이션 파일 삭제 (데이터 없음)
- `python manage.py makemigrations portfolio` 실행
- 0001_initial.py 재생성

**완료 기준**:
- `makemigrations` 명령이 에러 없이 실행됨
- 새 0001_initial.py 파일이 생성됨
- 마이그레이션 파일을 실행(migrate)하지는 **않음** (별도 검증 필요)

---

## 5. 마이그레이션 정책

### 5-1. 기본 원칙

- 프로덕션 데이터 없음 → **drop + recreate 허용**
- 기존 0001~NNNN 마이그레이션 파일 삭제 후 0001만 새로 생성
- migrate 실행은 이 지시서 범위 **외** (사용자가 별도 실행)

### 5-2. 구체적 절차

```bash
# 1. 기존 마이그레이션 삭제
rm docs/portfolio/implementation/migrations/0*.py
# 또는 앱 내 migrations/ 폴더 정리

# 2. 새로 생성
python manage.py makemigrations portfolio

# 3. (이후 사용자가 수동 검증 후)
# python manage.py migrate portfolio zero
# python manage.py migrate portfolio
```

### 5-3. DB 스키마 충돌 시

- 기존 테이블이 DB에 남아있는 경우: `migrate portfolio zero`로 제거 후 재마이그레이션
- `--fake-initial` 사용 **금지** (데이터 없으므로 실제 마이그레이션 실행이 맞음)

---

## 6. 검증 지점

각 Step 완료 후 검증.

### 6-1. Python 코드 유효성

- `python -c "from portfolio.models import Wallet, WalletHolding, Portfolio, AnalysisRun, ChatSession, Message, Decision, WalletSnapshot"` 실행 시 ImportError 없어야 함
- 모든 FK 참조 문자열이 올바른지 확인 (`"stocks.Stock"`, `"auth.User"`)

### 6-2. Django 시스템 체크

```bash
python manage.py check portfolio
```
- 경고 1~2개까지는 허용 (예: related_name 충돌 경고가 있으면 조사)
- 에러는 모두 해결

### 6-3. 마이그레이션 생성 검증

```bash
python manage.py makemigrations portfolio --dry-run
```
- 예상되는 변경 사항 (기존 제거 + 신규 생성) 출력 확인

### 6-4. 교차 참조 검증

- `metrics/definitions/presets.py`, `preset_metrics.py`, `metrics.py`의 코드 import에 영향 없어야 함
- 구체적 체크: 이 파일들은 `models.py`의 클래스를 직접 import하지 않으므로 영향 없음 (확인만)

### 6-5. 완료 선언 기준

다음이 모두 충족되면 D-0a 완료:
- [ ] 13개 모델이 정확한 필드로 정의됨 (위 Step 1~12)
- [ ] `python manage.py check`에서 에러 없음
- [ ] `python manage.py makemigrations portfolio` 성공
- [ ] `models.py`의 모든 모델이 import 가능
- [ ] 기존 Holding, CandidateHolding 참조가 다른 파일에서 사라짐

---

## 7. 에이전트 판단 허용 범위

에이전트가 이 지시서를 벗어나 판단할 수 있는 범위와 금지 범위를 명시.

### 7-1. 허용되는 판단

- **스타일**: docstring, 주석 형식, import 순서 등 — PEP 8 준수 범위 내 자유
- **validators**: 기존 `models.py`의 `MinValueValidator` 등 validators는 유지하되, 신규 필드에 validators 추가는 에이전트 판단
- **null=True vs blank=True의 세부 조합**: 지시서에 명시되지 않은 경우 합리적 기본값 선택
- **help_text**: 지시서에 명시된 것 외에 추가로 작성 허용 (한국어 허용)
- **import 문 재정리**: 사용하지 않는 import 제거, 정리

### 7-2. 금지되는 판단

- **신규 모델 추가**: 지시서에 없는 모델을 추가하지 않음 (예: Watchlist, Trade 등)
- **지시서에 명시된 필드 삭제**: 필드가 목록에 있으면 반드시 포함
- **FK 방향 변경**: 지시서의 FK 관계 그대로 따름
- **sector/industry 필드를 WalletHolding에 추가**: RV2-a 폴백은 명시적으로 금지 (2-1 전제 참조)
- **Holding/CandidateHolding 삭제를 deprecated로 변경**: 완전 제거가 맞음

### 7-3. 판단이 어려운 경우

지시서와 설계 문서를 검토해도 결정이 어려운 경우:
1. 작업 중단
2. 해당 의사결정 포인트를 사용자에게 보고
3. 제안 2~3개 (A/B/C) + 각 단점 제시
4. 사용자 결정 대기

**보고 예시**:
```
## D-0a Step N에서 결정 요청

설계 문서 §XX에 YY 필드의 max_length가 명시되지 않았습니다.

옵션 A: max_length=100 (기존 관례)
옵션 B: max_length=200 (안전 마진)
옵션 C: TextField로 변경

이 중 어느 것으로 할까요?
```

---

## 8. 산출물

### 8-1. 이 세션에서 생성/수정되는 파일

**수정**:
- `docs/portfolio/implementation/models.py` — 전면 리팩토링 (약 300~400줄 예상 증가)

**신규** (Django가 자동 생성):
- `portfolio/migrations/0001_initial.py` — 재생성

**제거**:
- 기존 `portfolio/migrations/0001_*.py` ~ `NNNN_*.py` — 모두 삭제

### 8-2. 이 세션에서 생성하지 않는 파일

- Pydantic 스키마 (`schemas.py` 같은 파일) — D-0b
- 테스트 파일 (`test_models.py`) — 별도 세션
- 매니저/큐셋 (`managers.py`) — 현재 기본 Manager로 충분
- 시드 데이터, factories — 별도 세션

---

## 9. 완료 보고 포맷

작업 완료 시 다음 형식으로 사용자에게 보고:

```markdown
# D-0a 완료 보고

## 변경 요약
- 신규 모델: Wallet, WalletHolding, WalletSnapshot, ChatSession, Message, Decision (6개)
- 재정의 모델: Portfolio
- 확장 모델: AnalysisRun, StoredAnalysis
- 삭제 모델: Holding, CandidateHolding (2개)
- 최종 모델 수: 13개

## 파일 변경
- 수정: docs/portfolio/implementation/models.py (N줄 → M줄)
- 마이그레이션: 0001_initial.py 재생성

## 검증 결과
- [✓] python manage.py check — 에러 0, 경고 N
- [✓] makemigrations 성공
- [✓] 13개 모델 import 성공

## 판단 포인트 (있으면)
- [기록 필요]: 지시서에 명시되지 않아 에이전트가 판단한 부분 목록

## 다음 세션 준비
- D-0b: Pydantic 스키마 작성 (AnalysisContext 전체)
- 다음 세션 시 models.py의 신규 모델 구조를 기반으로 Tier 2.5 스키마 설계
```

---

## 10. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판. 세션 D 결정 34개 반영. Claude Code 수준 에이전트 실행 가능한 구체성 확보. |

---

## 부록 A: 설계 문서 섹션 인덱스

에이전트가 빠르게 참조할 수 있도록 주요 섹션 정리.

**wallet-portfolio-architecture-v1.md**:
- §2: 핵심 개념 분리 (Wallet vs Portfolio)
- §3-2: Wallet 모델 상세
- §3-3: WalletHolding 모델 상세
- §3-4: Portfolio 재정의 상세 (+ effective_holdings 메소드)
- §3-5: WalletSnapshot 모델 상세
- §3-6: AnalysisRun 수정 상세
- §7: H3 정책 (참조 링크 + 자동 필터링)
- §9: 마이그레이션 플랜

**coach-llm-design-v1.md**:
- §5-3: ChatSession, Message 모델 정의
- §6-2: Decision 모델 정의

**return-tracking-design-v1.md**:
- §2-2: sector/industry 필드 위치 정책 (RV2-b)
- §6-2: StoredAnalysis 확장 (portfolio_return_breakdown, wallet_return_breakdown)

---

## 부록 B: 문자열 FK 참조 일관성

기존 `models.py`의 관례를 따라 다음 문자열 사용:

| 대상 모델 | FK 문자열 | 비고 |
|---|---|---|
| User | `settings.AUTH_USER_MODEL` | 기존 관례. from django.conf import settings 필요 |
| Stock | `"stocks.Stock"` | 외부 앱 |
| 동일 앱 내 모델 | 클래스명 직접 참조 | Wallet, Portfolio 등 |

---

## 부록 C: 자주 발생할 수 있는 실수

에이전트가 조심해야 할 패턴:

1. **WalletHolding에 sector/industry 필드 추가하지 않기**
 - RV2-b 확정 — Stock FK로 접근
 - "캐시 용도로" 라는 이유로 추가하려 하면 안 됨

2. **Portfolio의 user FK 유지하지 않기**
 - 새 Portfolio는 wallet을 통해 간접적으로 user 참조
 - `portfolio.wallet.user` 가 올바른 접근 경로

3. **Holding을 deprecated로 두지 않기**
 - 완전 삭제가 맞음
 - 데이터 없으므로 보존 이유 없음

4. **effective_holdings 메소드 빼먹지 않기**
 - H3 정책의 핵심 구현
 - Portfolio 모델에 반드시 포함

5. **기존 Portfolio의 is_default constraint 제거 필수**
 - 신규 Portfolio 의미에서는 무의미
 - Meta constraints에서 `unique_default_portfolio_per_user` 제거

---

**지시서 끝.**

에이전트는 이 지시서와 §0의 필수 참조 문서 3개를 읽은 후 작업 시작.
작업 중 판단이 어려운 경우 §7-3 보고 포맷으로 사용자에게 에스컬레이션.
