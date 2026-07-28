# Slice 18-R — 재사용 결선 (19a 조회 경로)

> 목적: 19a "목표-대비 권유 엔진"이 신규 2종 + 재사용 2종을 **한 사용자 경계** 안에서
> 어떻게 함께 조회하는지 이음새를 명시(코드가 아니라 경로 규약). 실제 19a 로직은 다음 슬라이스.

## 4개 데이터 · 한 사용자 경계 조회 경로

| 축 | 모델 | 소속 | 조회 경로(user 스코프) | 상태 |
|---|---|---|---|---|
| **목표** | `UserGoal` | apps/portfolio (신규) | `UserGoal.objects.for_user(user).first()` (`user` 직접) | 사용자당 1 |
| **현재-보유** | `WalletHolding` | apps/portfolio (재사용) | `WalletHolding.objects.filter(wallet__user=user)` (컨테이너 경유) | 지갑 N종목 |
| **현재-현금** | `CashBalance` | apps/portfolio (신규) | `CashBalance.objects.for_user(user)` (`wallet__user`) | 지갑당 1 |
| **후보** | `WatchlistItem` | shared/users (재사용) | `WatchlistItem.objects.filter(watchlist__user=user)` (컨테이너 경유) | 관심 M종목 |

- **한 지갑 = 보유(WalletHolding) + 현금(CashBalance)**: 둘 다 동일 `Wallet` 컨테이너에 매달림 → `wallet__user` 동일 경로로 사용자 순자산(net worth) 구성 가능.
- **목표는 사용자 전역**: UserGoal은 지갑이 아니라 `user`에 직접(사용자당 하나의 투자 철학).
- **후보는 shared 자산**: WatchlistItem은 dashboard·chain_sight도 소비하는 범용 자산(shared 정당) — portfolio는 소비만.

## 19a 비교 연산 스케치 (다음 슬라이스, 여기선 배선만)

```
goal    = UserGoal.objects.for_user(user).first()                    # 목표 수익/기간/리스크/제외
holdings= WalletHolding.objects.filter(wallet__user=user)            # 실보유 (재사용)
cash    = CashBalance.objects.for_user(user)                         # 현금 (신규)
cands   = WatchlistItem.objects.filter(watchlist__user=user)         # 후보 (shared 재사용)

# 19a: (보유+현금)로 현재 상태 구성 → goal 대비 갭 산출
#      → goal.exclusions로 cands 필터 → 갭 채우는 매수/관망 권유
```

## 스코프 이음새 규약 (D2')

- 신규 2종은 공통 `ScopedManager.for_user()`(각 모델 `USER_SCOPE_LOOKUP` 사용)로 스코프 조회를 한 곳에 모음.
- 재사용 2종은 기존 정의 무접촉 → `filter(<container>__user=user)` 직접(기존 관례).
- **추상 모델 베이스는 두지 않음**(YAGNI: 두 신규 모델이 직접/컨테이너 상이 가지). 이음새 = 일관된 조회 경로.

## 경계 준수

- `apps → shared` 단방향: portfolio가 `shared/users.WatchlistItem`을 소비(합법). shared는 신규 모델 미참조.
- 기존 WalletHolding·WatchlistItem 정의·마이그레이션 무접촉(재사용=참조만).
