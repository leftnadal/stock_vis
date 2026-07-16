# TIMING-P0 · RECON 보고 (실측 전용 — 코드/DB 변경 0)

> 발행: 2026-07-16 계획 세션 · 대상 HEAD `811c475`(D-MONITOR-TIMING-PIVOT ADR 등재 직후)
> 목적: ADR §9 미확정 5건을 결정 가능 상태로 — 재사용/확장/신규 판정 + 충돌·리스크 노출
> 제약: 읽기·측정만 수행. 코드·마이그레이션·DB·beat 변경 0.

---

## STEP 0 — 공통 실측

### 테스트 기준선

| 항목 | 직전 | 현재 실측 | 델타 |
|---|---|---|---|
| monitor pytest | 135 | **135 passed** | 0 |
| 전체 pytest | 3866 (0 실패) | **3872 passed · 53 skipped** | +6 |
| 전체 vitest | 692 | **695 passed** (89 파일) | +3 |
| tsc | 0 | **0** (소스 클린) | 0 |

- tsc 주의: 초기 실행 시 `.next/types/validator.ts`가 삭제된 thesis 라우트(`app/thesis/*/page.js`)를 참조하는 stale 에러 16건 → thesis→monitor 재건 전 빌드 캐시 잔재. `.next/types` 제거 후 재실행 = **0 errors**(소스 클린). 실 소스 문제 아님.

### vitest +28 델타 (P1.5 이월 게이트) — 통과, HALT 불요

- **테스트 파일 삭제 0건**(P1.5 윈도우 `468e29a..HEAD`, `--diff-filter=D` 공집합). 전체 히스토리 유일 삭제 커밋 `7d8a319`(2026-07-08, P1 thesis FE 철거 5파일)은 P1.5 착수(07-14)보다 6일 앞선 윈도우 밖 → 순증 은폐 정황 없음.
- **순증 출처**: monitor P1.5 고유 기여 **+4뿐**(신규 파일 0, monitor 3파일에 it 4개). 잔여분 전량 `frontend/__tests__` 공유 스위트에 랜딩한 **타 세션분** — chainsight ego `+17`·credit `+13`·impression `+9`·mp2-analog `+3`. 케이스 단위 트랙 간 카운트 오염.

### 지표 2행 표시 원인 (미수정, 원인만)

- 위치: `frontend/app/monitor/[id]/page.tsx:48` `IndicatorRow` 이름 span.
- 원인: `justify-between` 플렉스에서 이름 span에 `truncate`/`whitespace-nowrap`/`flex-1 min-w-0` **누락**. 카탈로그명 `"EOD 종합 신호"`가 공백 포함 → 폭 좁아지면 줄바꿈 2행. DB는 1행(정상), 순수 CSS 결함. close-preview backfill/이중 나열 아님.
- 대조군: `components/monitor/CloseModal.tsx:211` 지표행은 `min-w-0 flex-1 truncate` 적용되어 한 줄 고정. 상세 IndicatorRow에만 방어 누락.

---

## §2 — Claim 스키마 (① 가격 시나리오 필드 자리)

**전 필드**(`apps/monitor/models/monitor.py:79-142`): `id`·`monitor`(FK)·`assertion`(TextField)·**`deadline`(DateField, null=True, blank=True — line 113)**·`status`(active/resolved)·`outcome`(5멤버)·`proposed_verdict`(3멤버,null)·`resolved_by`(FK,null)·`factor_tags`(ArrayField, FactorTag 4종)·`retro_memo`(TextField)·`created_at`·`resolved_at`(null).

- ADR "deadline"의 실체 = `Claim.deadline: DateField(null=True)`.
- **가격 필드 충돌 대조**: `entry_price`·`target_price`·`stop_price`·적정가 밴드 전부 **부재 = 신규(충돌 0)**. 정밀도 관례 = `DecimalField(max_digits=15, decimal_places=4)`(packages/shared/stocks/models.py OHLC·타깃가 공통), 거래대금만 `(20,2)`.
- **기한만료 감지 경로**: `Claim.deadline`은 현재 ① 상세 표시(`[id]/page.tsx:73`) + ② 정렬 키(`api/views.py:89` `next_deadline=Min(claims.deadline)`)로만 소비. **만료 감지·발화 소비자 없음.** `expired` 상태는 `Monitor.target_date_end`가 판정(`state_machine.py:77`). beat는 **1개**(`monitor-refresh-daily`→`refresh_monitors_task`)가 매일 evaluate 내부에서 이미 `target_date_end` 만료 검사 중 → "기한만료" verdict는 **신규 beat 불요**, 기존 refresh 흐름에 `Claim.deadline` 만료 검사를 얹거나 `target_date_end` 재사용.
  - ※ ADR가 언급한 "기존 beat 4태스크"는 폐기된 thesis 4태스크(`sync_monitor_beat`가 회수). 현 monitor beat는 1개.

## §3 — 지표 파이프라인 (② S계열 산출 = 기술 관문)

- **EODSignal 실체**(`packages/shared/stocks/models.py:1012`): `composite_score`(Float)·`change_percent`(Float)·**`close_price`(Decimal, 종가만)**·`volume`(BigInt)·`dollar_volume`(Decimal)·signals(JSON). **OHLC 중 고가/저가 없음.** 현재 ingest는 EODSignal 3필드 복사(`ingest.py:25`).
- **히스토리 깊이(읽기 전용 실측)**:
  - EODSignal: **최대 84행/종목**(25,293행·519종목, 2026-02-25~2026-07-15, ~5개월)
  - DailyPrice: **757행/종목**(398,732행, 2023-07-10~2026-07-15, 3년, 풀 OHLC)
- **S계열 요구 대조**:

| S계열 | 요구행 | EODSignal(84) | DailyPrice(757) | 소스 |
|---|---|---|---|---|
| 추세괴리(200 SMA) | 200 | ❌ | ✅ | close |
| 12-1 모멘텀 | 252 | ❌ | ✅ | close |
| 52주 근접 | 252 | ❌ | ✅ | high/close |
| 거래량 비율 | 20 | ✅ | ✅ | volume |
| MACD | 26~35 | ✅ | ✅ | close |
| 오실레이터(RSI/Stoch) | 14 | ✅ | ✅ | close (Stoch=H/L/C) |
| ATR(L계열 손절) | 14 | ❌(고저 없음) | ✅ | H/L/C |

  → **판정: S/L계열 전부 DailyPrice에서 산출 가능. EODSignal(close·84행)로는 장기지표·ATR 불가.** DailyPrice 3년치라 **FMP 백필 불요**(호출 확인만, 미실행).
- **프리셋 등록 구조**: 카탈로그 = **코드 상수**(`catalog.py` `STOCK_INDICATOR_CATALOG` list-of-dict, DB 아님). 6종 추가 = 코드 상수 편집(마이그레이션 불요). 단 reading은 raw 복사가 아니라 **계산 산출** → 신규 ingest 경로(DailyPrice→derived compute→IndicatorReading) 필요. **근거강도 메타** = 카탈로그 dict key(무마이그) 가능. 지표 인스턴스별 저장 원하면 `MonitorIndicator` additive 필드(현재 strength 없음).
- **z-정규화 적용성**: `indicator_scorer`는 robust-Z(MAD)+decay(`indicator_scorer.py:35`). 52주 근접도 등 **[0,1] 유계 지표에도 계산되나 "자기 최근 분포 대비 상대강도"만 의미** → 절대 근접 의미 희석. **적용 가능하나 의미 왜곡 주의**(override_score 우회 or 신규 스코어링 모드 자연스러움).
- **재사용 자산**: `packages/shared/stocks/indicators.py` `TechnicalIndicators`(순수함수 SMA·EMA·RSI·MACD·Bollinger·Stochastic·**ATR**·OBV). 입력=H/L/C 리스트(DailyPrice 제공).

## §4 — 상태기·알림 (③④ 구조 불변 제약 하)

- **8상태**(`Monitor.State`, `state_machine.py:24`): WARMING_UP·ACTIVE·STRENGTHENING·WEAKENING·CRITICAL·NEEDS_REVIEW·EXPIRED·PAUSED. 전이 조건=**하드코딩 임계**(WARMING_UP_DAYS=5·NEEDS_REVIEW_DAYS=90·CRITICAL_SCORE=−0.6·DAILY_CHANGE=0.3·TREND=0.15). 현 의미="가설 강도(종합점수 추세)".
- **재의미화 판정**: 현 상태는 score 추세 기반 → **라벨 교체만으로 "진입 구간 도달" 불가.** "진입 구간 도달"=가격이 진입가 근접이라는 새 판정축 → `determine_state` 임계 로직 수정 불가피. **구조 불변(additive-only)과 정면 긴장 — 결정 최우선 논점.**
- **알림 트리거**(`alerts.py:55` `detect_and_record_alert`): `state_changed`+`is_deterioration`(악화/개선) 프레임. "진입 구간 도달"은 좋은 신호이면서 행동 필요 → 이분법 밖 → **새 트리거 종류 or is_deterioration 재정의 필요.**
- **달 위상 매핑 파급**: BE 2곳 — `state_machine.py:152` `score_to_phase`(라벨 "가설이 빛나고 있어요") + `sparkline.py:19-23` `PHASE_BANDS`. FE는 phase→색만(상태→위상 테이블 FE 없음, `display.ts:1-4` "BE 단일 소스" 명시).

## §5 — verdict 재라벨 (⑤)

- **표시 문자열 위치**: BE choices label(`monitor.py:86`) + FE **2곳 분산** — `VerdictBadge.tsx:11-16`(적중/부분적중/빗나감/불명확) + `CloseModal.tsx:21-31`.
- **익절/부분/손절**: enum-keyed 문자열맵 → **표시 계층만 교체 가능(무마이그, additive)**. 단 FE 2곳 동시 수정(중앙화 안 됨).
- **기한만료**: `ClaimOutcome` 멤버 **아님**(expired는 MonitorState 레이어, `display.ts` STATE_META). ⑴ **INCONCLUSIVE 재활용**(라벨만, 무마이그, 권장) vs ⑵ 신규 outcome 멤버(TextChoices choices 마이그, DB 컬럼 불변, propose_verdict 밴드도 수정). ⑴이 압도적 저렴.
- **마감 루프 재사용**: `close_preview`/`close_claim`/`ClosureSnapshot`/`ClaimIndicatorResult` 그대로. **손익 동결 자리** = `ClosureSnapshot.payload`(JSONField dict, `closure.py:51`) → 진입가 대비 실현 손익률 **무마이그 추가 가능**. 단 `close_claim`은 종합점수만 동결 → 손익 계산 로직 신규.

## §6 — FE 어휘·빌더 (⑥)

- **"가설" 인벤토리(monitor 내부)**: `[id]/page.tsx:195,197` · `new/page.tsx:226,228,233`(4단계) · `page.tsx:201`(필터 칩) · `CloseModal.tsx:128,141`. 식별자 `assertion`·`Claim` 광범위. testid `step-claim`·`claim-row`·`claim-close-button`. **BE 잔재**: sparkline/state_machine 달위상 라벨 + closure 에러 메시지. **메일 템플릿 FE에 없음**(BE `alerts.py` 소유). 별개 앱(chainsight/screener/coach) "가설"은 피벗 무관.
- **빌더 4단계**: 전부 `app/monitor/new/page.tsx` `BuilderContent` 인라인 `<section>`(별도 스텝 컴포넌트 없음, `builder/`엔 ProgressBar만). 1=scope·2=target(symbol+name)·3=indicators·4=claim(assertion+deadline).
- **가격 3필드 자리**: 가격 입력 전무 → 자연스러운 자리 = **4단계(step-claim)**, `flex flex-col gap-3`라 input 추가 용이. **L계열 제안 슬롯**: 빌더 제안 UI 전무(제안은 CloseModal뿐) → 신규 필요. **ATR/지지선 계산**: `TechnicalIndicators.calculate_atr`(H/L/C) → DailyPrice **서버측** 권장(3년 OHLC 클라 전송 부담).

---

## §7 — 설계 대조표 (ADR 6요소)

| # | 요소 | 존재/부분/부재 | 근거 | 재사용/확장/신규 | 리스크·구조 불변 긴장 |
|---|---|---|---|---|---|
| ① | Claim=매수 시나리오 | 부분(기한만) | `deadline`(monitor.py:113)·가격3필드 부재 | 기한=재사용·가격3+적정가=신규(충돌0, Decimal 15,4) | 낮음(additive). 기한만료 결선만 신규 |
| ② | 지표=S계열 프리셋 | 부분(3종·소스 부적합) | 카탈로그 코드상수·EODSignal close·84행 | 계산=TechnicalIndicators 재사용·소스=DailyPrice 전환·6종=신규상수·ingest=신규 | 중 — 소스 전환·유계지표 z 왜곡 |
| ③ | 상태기 재의미화 | 존재(구조)·부재(의미) | 8상태 하드코딩 임계 | 구조=재사용·의미=라벨+임계 로직 신규 | **높음** — 진입 판정=가격축 신규, 라벨만 불가 |
| ④ | 알림=진입 즉시 | 부분 | detect_and_record_alert 악화/개선 | 발화 인프라=재사용·트리거=신규/재의미화 | 중 — 진입은 이분법 밖 |
| ⑤ | verdict 재라벨 | 부분 | outcome 5멤버·FE 라벨 2곳 | 익절/부분/손절=FE 스왑·기한만료=INCONCLUSIVE 재활용 | 낮음 — FE 2곳 동시성 |
| ⑥ | 빌더=시나리오+L슬롯 | 부분 | 4단계 인라인·제안 UI 전무 | 4단계 골격=재사용·가격입력·제안슬롯=신규(단일파일) | 낮음 — L계산 서버측 |

---

## 종합 — 결정 재료

### 신규 마이그레이션 후보 필드
- `Claim.entry_price`·`target_price`·`stop_price` — `DecimalField(15,4, null=True)` (충돌 0)
- 적정가 밴드 참조 — `fair_value_low`/`fair_value_high`(nullable Decimal) 또는 외부 FK 자리
- (선택) `Claim.outcome`에 EXPIRED 멤버 → choices 마이그(DB 스키마 불변) — INCONCLUSIVE 재활용 시 불요
- (선택) `MonitorIndicator` 근거강도 필드 — 카탈로그 dict key 대체 시 불요

### 신규 컴포넌트·상수 (마이그레이션 무관)
- S계열 6종 카탈로그 상수 + **DailyPrice→derived compute→IndicatorReading ingest 경로**(신규)
- 빌더 4단계 가격 3필드 input + L계열(지지선·ATR) 제안 슬롯(`new/page.tsx` 단일 파일)
- verdict 라벨 문자열 스왑(FE 2곳: VerdictBadge·CloseModal)
- 가격 손익 계산 → `ClosureSnapshot.payload` 동결
- "진입 구간 도달" 판정 로직(state_machine 임계 확장 — **구조 불변 예외 승인 필요**)

### 재사용 자산
`TechnicalIndicators`(indicators.py) · DailyPrice 3년 OHLC · `indicator_scorer` robust-Z · state_machine 8상태 골격 · `ClosureSnapshot.payload` JSON 슬롯 · alerts 발화 인프라 · 카탈로그 코드상수 구조 · `MonitorIndicator.source_key` 링크 · beat 1개(신규 불요)

### ADR 미확정 5건 결정 재료
1. **프리셋 목록**: S계열 6종 — 소스 **EODSignal 아님 DailyPrice**, 계산 TechnicalIndicators, ATR도 DailyPrice. 근거강도=카탈로그 dict key.
2. **가격 필드 스키마**: `DecimalField(15,4)`, Claim additive, 충돌 0.
3. **상태 라벨**: 8상태 구조 불변 가능하나 **"진입 구간 도달"은 임계 로직 수정 필요**(라벨만 불가) — additive-only 제약과 유일한 정면 긴장, 결정 세션 최우선.
4. **verdict 재라벨**: 익절/부분/손절=FE 문자열 스왑(무마이그 2곳). 기한만료=**INCONCLUSIVE 재활용 권장**(무마이그) vs 신규 멤버(choices 마이그+propose_verdict).
5. **통로(적정가 밴드) 자리**: Claim nullable 필드 또는 `ClosureSnapshot.payload`(JSON). 빌더 4단계 수동 입력 + L계열 서버 계산 제안.

---

**본 RECON은 읽기·측정만 수행했으며 코드·마이그레이션·DB·beat 스케줄에 어떠한 변경도 가하지 않았다.** (테스트 실행·읽기 전용 DB count·stale `.next` 빌드 캐시 제거만 — 소스·데이터 불변.)
