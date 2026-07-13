# SLICE 18-R 지시서 (개정2) — Portfolio Coach: 사용자 상태 그릇 (재사용 반영판)

> **이 문서는 원안을 대체(supersede)한다.** 원안은 STEP 0 실측에서 **HALT 2건**(의미 중복 + D1 전제 파기)이 확정되어 폐기됐다. git 히스토리는 `원안 → HALT findings(STEP0_FINDINGS.md) → 이 개정본`으로 진실하게 남는다.
>
> **왜 개정됐나 (미래 세션이 반드시 읽을 것):** 원안은 4종(UserGoal·WatchlistItem·WalletHolding·CashBalance)을 전부 신규 생성하도록 지시했다. 그러나 STEP 0 실측 결과:
> - `apps/portfolio.WalletHolding`(models.py:78)이 **이미 존재**하고 신규 요구의 상위집합(stock+shares+avg_cost+first_bought_at+investment_thesis+buy_snapshot). 같은 앱 동명 클래스 신규 정의 = **Django 정의 충돌(불가)**.
> - `shared/users.WatchlistItem`(users/models.py:215)이 **이미 존재**하고 상위집합(stock+target_entry_price+notes+added_at+position_order), REST CRUD 완비. `apps/dashboard/services/strip_service.py:84`, `apps/chain_sight`(WatchlistViewSet)가 **직접 소비** → 이미 교차앱 자산이라 shared 소속이 정당. 원안 D1 전제("portfolio만 소비")가 거짓.
> - `CashBalance`·`UserGoal`은 유사 모델 0 → 신규 정당.
> - `AUTH_USER_MODEL = users.User` (확인).
>
> **결론: 신규 2종(UserGoal·CashBalance)만 만들고, WalletHolding·WatchlistItem은 재사용한다.**
>
> **세션 종류:** 실행 세션. 설계 결정은 §4에서 재확정됨(D1'·D2'·D3', DECISIONS.md `SLICE18R`). STEP 0가 전제를 깨면 HALT(§7).

---

## 0. 산출물 정의 (DoD)
1. 신규 모델 **2종**(UserGoal · CashBalance)이 `apps/portfolio`에 존재. WalletHolding·WatchlistItem 생성하지 않음.
2. 두 신규 모델이 house 스코핑 패턴(컨테이너 경유)에 정렬(§4 D2': CashBalance→Wallet FK, UserGoal→user FK).
3. 두 신규 모델의 user 스코프 CRUD 동작.
4. 교차 사용자 격리 테스트가 신규 2종 커버·통과(§4 D3').
5. DECISIONS.md에 원안 폐기 사유 + D1'·D2'·D3' 기록, 모델 커밋보다 앞섬.
6. 재사용 결선: 신규 모델 ↔ 기존 WalletHolding·WatchlistItem 조회 경로 명시(문서/주석).
7. 회귀 보존: baseline 574 green → 종료 재측정, 기존 깨짐 0.
8. health_check 통과, 아키텍처 테스트 통과, 동결 증가 0.

## 1. 절대 규칙 (§7 HALT)
- WalletHolding·WatchlistItem 새로 만들지 않음(재사용).
- 수치 재측정. 한 방향(apps→shared). 가산 슬라이스(기존 불변). 파괴적 작업 유보. D 재오픈 금지.
- **기존 WalletHolding·WatchlistItem 정의·마이그레이션 무접촉**(참조만).

## 2. STEP 0 (실측 완료 — 2026-07-13, base 8dd5ca9)
- (a) worktree `monorepo/sess-slice18r-container`, base origin/main `8dd5ca9`.
- (b) baseline `pytest apps/portfolio tests/architecture` = **574/0**.
- (c) 재사용 2종 재확인 + CashBalance/UserGoal 중복 0.
- **(d) STEP 0.5 house 스코핑 = 컨테이너 경유** (WalletHolding·WalletSnapshot·Portfolio 전부 `wallet=FK(Wallet)`, `Wallet.user=FK`; WatchlistItem=`watchlist__user`).
- (e) cash/goal 교차앱 소비자 0 → D1' 전제 유지.
- (f) AUTH_USER_MODEL=`users.User`.

## 4. 재설계 결정 (DECISIONS.md `SLICE18R` 참조)
- **D1'**: 신규 UserGoal·CashBalance만 apps/portfolio. WatchlistItem=shared 유지, WalletHolding=portfolio 기존 유지, 둘 다 재사용.
- **D2'**: house(컨테이너 경유) 정렬. CashBalance→`wallet=OneToOne(Wallet)`, UserGoal→`user=OneToOne(AUTH_USER_MODEL)`. 추상베이스 강제 안 함(YAGNI).
- **D3'**: user 차원 신규 테이블 = 누수-0 격리 테스트 필수. 신규 2종 + 재사용 2종 스모크 + 등록 가드.

## 5. 실행 계획
- Part A: DECISIONS 기록(원안 폐기 + D1'-D3') + 지시서 rev2 교체. 커밋.
- Part B: models_my.py에 UserGoal·CashBalance(19a 최소 필드). makemigrations(신규만)·--check. 커밋+회귀.
- Part C: user 스코프 CRUD(표준 스코프 경로). 커밋+회귀.
- Part D: 격리 테스트(신규 2 + 재사용 스모크 + 등록 가드). 커밋+전체 pytest.
- Part E: 재사용 결선 문서 + codegen drift 0. 커밋.
- Part F: 닫기 보고 + health_check + 아키텍처 테스트.

## 7. HALT 트리거
WalletHolding/WatchlistItem 생성 필요 / 재사용 전제 뒤집힘 / baseline red / cash·goal 교차앱 소비 / STEP 0.5 모호 / 기존 마이그레이션 재생성 / 파괴적 작업.

## 8. 다음(19a)
UserGoal(목표) vs WalletHolding(실보유 재사용)+CashBalance(현금 신규) 비교, WatchlistItem(관심 후보 shared 재사용)을 갭에 대어 권유. 18-R은 신규 2종 필드를 19a 최소로.
