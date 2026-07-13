# SLICE 19A-R 지시서 (개정) — 목표-대비 권유 엔진: 정직한 A (진행+배치 갭 · RelationConfidence 드라이버)

> **이 문서는 원안을 대체(supersede)한다.** 원안은 STEP 0 **A-게이트 실패**(forward 기대수익 정본 신호 부재)로 폐기됐다.
>
> **왜 개정됐나 (미래 세션 필독):** STEP 0 신호 인벤토리(`STEP0_SIGNAL_INVENTORY.md`) 실측 —
> - analyst_target_price·analyst_rating·forward_pe = **유령 필드**(선언만, writer 없음, 항상 null).
> - EstimateSnapshot/리비전 모델 부재. 프리셋 스코어링 엔진 = 0~100 **품질점수(기대수익 아님)** + 고아(미배선).
> - return_12m 등 = 리졸버 부재 + 본질 후행.
> - **사용 가능:** RelationConfidence(해자, symbol_a/b=티커 → WatchlistItem 직접 매핑) ✅, Stock.currency(USD/KRW, default USD 오판 주의) ✅.
> → "목표수익 − 현재기대수익" 갭의 forward 항을 채울 정본이 0. 없는 예측치를 프록시로 지어내는 건 유령 필드 실수의 반복이므로 금지. **갭을 데이터가 실제로 받쳐주는 두 축(진행·배치)으로 재정의하고, 후보 랭킹은 RelationConfidence가 몰게 한다(디렉터+사용자 확정).**
>
> **제품 정체성(승인됨):** 19a는 "이 종목이 X% 오른다"는 **수익 예측기가 아니다.** "너는 여력이 있고(현금/목표 미달) + 관심 후보 중 신뢰도·진입가가 좋은 건 이것들"이라 말하는 **목표-의식 + 신뢰도 기반 배치 코치**다.
>
> **base:** `origin/main = 50a1738`, pytest 582 green — STEP 0 재측정.

## 0. 산출물 정의 (DoD)
1. **카디널리티:** `CashBalance` `OneToOne(Wallet)` → **`FK(Wallet)`+`unique(wallet,currency)`**. 마이그레이션·dev, 격리/CRUD 테스트 갱신. (`SLICE18R-CARDINALITY-REVISIT` 종결. UserGoal은 OneToOne 유지.)
2. **정직한 갭(뼈대 A):**
   - **진행 갭** = 현재 포트폴리오 실현/미실현 수익률(avg_cost vs 현재가, DailyPrice) − 목표수익률. 후행·사실, 예측 아님.
   - **배치 갭** = 유휴현금 비중(현금 평가액 / 총평가액). 구조·사실.
   - **모드 분기:** (유휴현금 큼 ‖ 목표 미달) → 매수 / (완전투자 & 목표 달성) → 방어.
3. **후보 랭킹(B-min):** 매수 모드에서 WatchlistItem을 **RelationConfidence(주) + 진입가 여유(distance_from_entry, 부)** 로 정렬. **기대수익 프록시 금지, 가중치 없음(19b).** 스코어링 엔진·유령 필드 금지.
4. **가드레일(C-min) + 통화:** (1) 유휴현금 임계 미만 → 매수 억제, (2) 집중도 초과 → TRIM. **통화별 매수여력 분리**(USD→USD, KRW→KRW, 환전 없음). Stock.currency 판별, default-USD 모호 시 오배분 방지.
5. **산출 계약(D4):** BUY/HOLD/TRIM(+종목·통화·근거·점수) + 목표-대비 요약(진행 갭·배치 갭·모드). **"예측 아님" 명시.** Slice 20 소비.
6. **테스트:** 갭 2종·모드·랭킹·가드레일·통화 분리 + 경계(빈 watchlist·현금0·목표 달성). 카디널리티 전환 격리/CRUD green.
7. **기술부채·미래 등재:** 유령 필드 3종·스코어링 고아·FX 저장 부재 TASKQUEUE 부채, forward 신호 인프라 미래 슬라이스.
8. **회귀:** 582 → 종료 재측정, 기존 깨짐 0. 아키텍처·동결 0. apps→shared 유지.

## 1. 절대 규칙 (§7 HALT)
- **유령 신호 사용 금지**(analyst_*·forward_pe·스코어링 엔진 출력을 기대수익으로 쓰지 않음).
- **기대수익 프록시 금지**(distance_from_entry·과거수익률을 "기대수익인 척" 금지 — 진행 갭 상태지표·랭킹 부축으로만).
- 메모리 신뢰 금지. 한 방향(apps→shared). 분석엔진 직접의존 회피·신규 스코어러 발명 금지. 행위보존(카디널리티 외 불변, 582 green, prod 미적용). D 재오픈 금지.

## 2. STEP 0 (재측정, 차이 확인 중심)
- (a) worktree/브랜치·base·pytest 582 재확인.
- (b) STEP0_SIGNAL_INVENTORY.md 확인·미커밋이면 Part A 커밋(유실 방지).
- (c) 랭킹 재료: RelationConfidence 티커→WatchlistItem 매핑·Stock.currency 판별·default-USD 표본.
- (d) 그릇: UserGoal·WalletHolding(avg_cost·shares)·CashBalance·DailyPrice(현재가/과거가). REUSE_WIRING.
- A-게이트 HALT 없음(정직한-A 확정). 단 RelationConfidence 매핑·DailyPrice 조회 불가 시 뼈대 재료 부재 → HALT.

## 4. 닫힌 결정 (Part A 기록)
- 원안 폐기: A-게이트 실패 → 정직한-A.
- 제품의도: 현금 KRW+USD / 목표 단일 "수익"(총수익). 예측기 아님(배치 코치).
- 카디널리티: CashBalance FK+unique(wallet,currency). UserGoal OneToOne 유지.
- 갭: 진행 갭(수익률 vs 목표·후행) + 배치 갭(유휴현금 비중·구조). forward 없음.
- 랭킹: RelationConfidence(주)+distance_from_entry(부). 가중치 19b.
- FX: 통화별 여력 분리, 환전 없음(교차환전 19b).
- 부채(TASKQUEUE): SIGNAL-GHOST-FIELDS·SCORING-ENGINE-ORPHAN·FX-PERSIST-ABSENT.
- 미래 슬라이스: SIGNAL-FORWARD-INFRA(기대수익 정본 → 갭 slot-in, 정직한-A→기대수익-A 승격, 19a 밖).

## 5. 실행 계획
- Part A: DECISIONS §4 기록 + STEP0_SIGNAL_INVENTORY 커밋 + TASKQUEUE 부채 3+미래 1 + CashBalance FK+unique 전환(마이그레이션·dev, prod 미적용) + 격리/CRUD 테스트 갱신(통화별 다행). 커밋+회귀.
- Part B: 진행 갭 + 배치 갭 + 모드 분기. 커밋+회귀.
- Part C: 랭킹(RelationConfidence+진입가) + 가드레일 2종 + 통화 분리. 커밋+회귀.
- Part D: 산출 계약(예측-아님 명시) + 단위 테스트. 전체 pytest. 커밋.
- Part E: 닫기 보고 + health_check·아키텍처.

## 6. 닫기 보고 (§6 원안 축 준수)
좌표·회귀 / 카디널리티 전환 증명 / 정직한 갭 동작(유령·프록시 미사용 증명) / 랭킹·가드레일 / 산출 계약 / 부채·미래 등재 / 후보·HALT.

## 7. HALT 트리거
RelationConfidence 매핑·DailyPrice 조회 불가 / pytest red / 카디널리티 마이그레이션 예상밖 / shared→apps / 유령·프록시 강제 / 파괴적 작업.

## 8. 다음(19b)
가중 스코어(합=1.00: RelationConfidence/진입가/집중도/통화여력) + 교차환전. 이후 SIGNAL-FORWARD-INFRA가 기대수익 정본 마련 시 갭 slot-in. 그 위 Slice 20 화면.
