# SFI_SPLIT_GUARD_INSTRUCTION — I3-SPLIT-GUARD 구현 (B안: 전용 모델 + nightly)

> 세션 종류: 미니슬라이스 (예산 캡 $0.50 · LLM 호출 0 — 순수 배관)
> 시한: 🕒 2026-09-01 h21 첫 만기 前 (TASKQUEUE I3-SPLIT-GUARD, D-ARC-NEXT)

## 결정 근거
- 2026-08-13 결정 사이클: B안(전용 모델 + nightly 수집) 확정.
- 병진 override: 디렉터 추천 C(4.25) 대비 B(3.80), 마진 −0.45 수용. 사유 = 정합·확장성(배당/합병 등 기업행위 일반화).
- DECISIONS D-SPLIT-1 등재(override 마진 명기).

## 절대 규칙
1. append-only: 기존 AnalystSignalSnapshot·DailyPrice·채점 결과 무접촉.
2. prod 접촉 2종(migrate·beat 등록)은 각각 HALT → 병진 승인문 수취 후 집행(D-PROBE-PRODWRITE-RULE).
3. 채점 산식 무변경 — unscoreable 분기 추가만. 산출 상이 시 HALT.
4. shared→apps 역참조 금지(경계 가드 통과 필수).

## STEP 0 — ground truth (전제 검증)
a. DailyPrice 소속·FK · b. 가격 ingest 태스크 소속 · c. sync_analyst_signals_beat 구조 ·
d. 마이그 최신·pending 0 · e. nightly 체인 슬롯 충돌 · f. resolve_realized 시그니처.

## Part 1 — StockSplit 모델 (shared.stocks)
stock(FK to_field=symbol)·date·numerator·denominator·split_type·source(default fmp)·created_at.
unique_together (stock, date). 인덱스 (stock, date). makemigrations→커밋. **HALT ①**(prod migrate 前).

## Part 2 — FMP 래퍼
`fmp/client.py`에 `get_stock_splits(symbol)`(/stable/splits). 기존 메서드 무수정.

## Part 3 — nightly 태스크 + beat
`ingest_stock_splits`(apps.portfolio, _coach_universe 재사용) → StockSplit upsert(append/skip).
beat 슬롯 19:45 ET dow 1-5. sync_stock_splits_beat 커맨드. **HALT ②**(beat 등록 前).

## Part 4 — 채점 접합
resolve_realized: capture_date < split.date ≤ realized_date인 StockSplit → unscoreable:corporate_action.
재현 헤더 additive: +splits_input_rows +splits_max_date. SCORING_VERSION: 산출 IDENTICAL이면 1 유지, 상이 시 **HALT ③**.

## Part 5 — 테스트·게이트
모델 unique · 래퍼 파싱 · ingest 멱등 · 채점 분기(구간 내/외/경계·epoch 무관).
pytest 전체 회귀 0 · 경계 가드 · health 15/0/0 · Part 4 IDENTICAL.

## Part 6 — 등재·랜딩
DECISIONS D-SPLIT-1 · TASKQUEUE I3-SPLIT-GUARD ✅done + 💤 SPLIT-CALENDAR-PREVIEW·BRANCH-REF-SWEEP.
첫 발화 검증 예약(익일 19:45 ET). D-LAND-ATOMIC.
