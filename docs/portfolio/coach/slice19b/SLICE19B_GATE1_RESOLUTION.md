# SLICE 19B — 게이트 1 HALT 해소 지시 (디렉터 판정, 2026-07-14)

> 본 지시서(`SLICE19B_INSTRUCTION.md`)의 **부록** — §2(b) 게이트 1 HALT를 해소하고 세션 재개를 지시한다. 본 지시서의 절대 규칙·DoD는 아래 수정분 외 전부 유효.
>
> **판정:** ① **매수일 환율 근사 + 신규 캡처** + **수동 정정 경로**. 가중합 4.63/2.85/3.35/2.70, 마진 1.28 자동확정 + 기존 WalletHolding 필드 추가 사용자 명시 승인(2026-07-14).
>
> **기각 근거(미래 세션용):** ②(현재 환율 근사)=과거 FX 손익을 수학적으로 0으로 만들어 KRW 교정 신호 소거(정직성 충돌). ③(신규만)=사용자 #1 현재 보유 미교정, 도그푸딩 0. ④=과잉.

## 1. KRW 취득원가 결정 로직 (우선순위 고정)
1. `WalletHolding.acquisition_fx_rate` not null → KRW 원가 = `avg_cost × shares × acquisition_fx_rate`. 라벨 **`exact`**.
2. null & `first_bought_at` ∈ 백필 창(5년) → 매수일(휴장일이면 직전 영업일) 백필 환율 근사. 라벨 **`approx_first_buy`**.
3. null & `first_bought_at` ∉ 창 → 창에서 가장 오래된 가용 환율. 라벨 **`approx_low_confidence`**.
- KRW 종목은 환산 없음(라벨 `native_krw`). default-USD 모호 종목은 19a 오배분 방지 유지.

## 2. 스키마 변경 (이 항목만 기존 모델 접촉 허용)
- `WalletHolding`에 `acquisition_fx_rate` 추가: **DecimalField, null=True, blank=True** (help_text "매수 시점 USD/KRW 환율, 사용자 정정 가능").
- 가산·nullable — 기존 행/테스트 무영향. 이 필드 외 변경이 `makemigrations --check`에 감지되면 HALT.
- 신규 캡처: 보유 생성 시 당시 spot rate 기본 채움(사용자 실환율 정정 가능).
- 추가매수 가중 재계산은 19b 밖 → TASKQUEUE 부채 `FX-ACQ-RATE-WEIGHTED-UPDATE`.

## 3. 산출 계약 v2
- 보유별 KRW 원가에 출처 라벨(`exact | approx_first_buy | approx_low_confidence | native_krw`) 포함.
- 요약에 근사 포함 여부 사실 명시. "예측 아님"과 동렬 정직성 장치.

## 4. 테스트 (§0-7 가산)
- 우선순위 3분기 각 1건 + 휴장일 fallback + 수동값 precedence + nullable 가산 증명.

## 5. 기록 (Part A 가산)
- DECISIONS: 게이트 1 판정(복원 불가+근거) + 해소 결정(①+수동, 마진 1.28+필드 추가 승인).
- TASKQUEUE: `FX-ACQ-RATE-WEIGHTED-UPDATE` 등재. 이 문서 A1 커밋.

## 6. 재개
- Part A부터 순서대로. HALT 트리거 전부 유효 + `acquisition_fx_rate` 외 마이그레이션 변경 시 HALT.

---

## STEP 0 게이트 판정 실측 (2026-07-14, base bb91c98)
- baseline pytest apps/portfolio+architecture = **592 green**.
- 게이트 1 = **불가**(avg_cost=USD 평단, buy_snapshot 환율 없음, 환전 이력 필드 0) → 본 해소로 처리.
- 게이트 2 = **통과**: FMP `get_forex_rates` spot + `USDKRW` 과거 **1373건/5년**(2021-07-14~2026-07-13, `/stable/historical-price-eod/full`). 백분위 창 = **5년**.
- 게이트 d = 중복 0(환율 저장 모델 없음). FX 모델 신설 정당.
- 소비처: 19a 산출 계약 소비처 0(Slice 20 미착수) → 의미 변경 안전.
