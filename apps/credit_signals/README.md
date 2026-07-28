# credit_signals — FRED 크레딧 신호 백본 (Phase 1)

"채권이 먼저 말한다" 축의 첫 슬라이스. FRED의 ICE BofA OAS(크레딧 스프레드)를
매일 수집·**영구 누적**하고, Robust Z(MAD) 기반 상태등급을 계산해
`credit_signal_state`에 기록한다. 소비처(Dashboard/Chain Sight/Thesis)는 이
상태 테이블만 읽는다.

## ⚠ 3년 제한 배경 (이 앱의 존재 이유 절반)

FRED의 ICE BofA 시리즈는 **2026년 4월부터 최근 3년 관측치만** 제공한다.
따라서 `macro_series_history`에 수집 즉시 **영구 적재**하는 것이 핵심이다.
오래된 데이터를 절대 덮어쓰거나 삭제하지 않는다 — 삭제 로직을 작성하지 않는다.
(revise 시에도 value만 갱신하고 `ingested_at`(최초 적재)은 유지, `revised_at` 별도 기록.)

## signal_key 계약표

`signal_key`는 Thesis Layer E가 나중에 `HY_OAS_Z > 2` 형태로 참조할 **안정 계약**이다.
순서를 바꾸거나 rename하지 말 것.

| signal_key    | FRED series_id | 이름       | Phase 1 |
|---------------|----------------|-----------|---------|
| `HY_OAS`      | BAMLH0A0HYM2   | US HY OAS  | ✅ 계산  |
| `IG_OAS`      | BAMLC0A0CM     | US IG OAS  | ✅ 계산  |
| `BBB_OAS`     | BAMLC0A4CBBB   | BBB OAS    | ✅ 계산  |
| `CCC_OAS`     | BAMLH0A3HYC    | CCC- OAS   | ✅ 계산  |
| `CURVE_10Y2Y` | T10Y2Y         | 10Y-2Y     | ✅ 계산  |
| `VIX`         | VIXCLS         | VIX Close  | ✅ 계산  |
| `CCC_MINUS_BB`| (BB 미수집)     | CCC−BB 스프레드 | 🔒 키만 예약 (Phase 2) |
| `BBB_MINUS_A` | (A 미수집)      | BBB−A 스프레드  | 🔒 키만 예약 (Phase 2) |

> Phase 1은 6종만 수집·계산. BB·A 등급 시리즈는 수집 목록에 없으므로
> `CCC_MINUS_BB`/`BBB_MINUS_A`는 **키만 예약**하고 계산하지 않는다.
> 수집 시리즈를 6→8로 늘리는 것은 스코프 위반(금지).

## grade 규칙

- z-score = Robust Z(MAD 기반, `MAD_FLOOR` 적용) — Thesis Control 확정 수학 모델과 동일 규약.
- `z < 1` → gray · `1 ≤ z < 2` → yellow · `z ≥ 2` → orange
- **red** = orange 조건(z≥2) + `HY_OAS` 절대값 ≥ 8.0 (800bp), **HY_OAS 한정**
- 관측치 60개 미만 → `z_score=null`, `grade=gray` (콜드스타트)

## 운영

### flag guard
- `CREDIT_SIGNALS_ENABLED` (기본 `false`): 수집·계산·verify 태스크 최상단 guard.
  flag-off이면 no-op. 활성화 = `.env`에 `CREDIT_SIGNALS_ENABLED=true`.

### 백필 (최초 1회, 3년치)
```bash
# ★ 반드시 포그라운드 블로킹 실행 — 백그라운드(&, nohup)는 harness reaper가 살해함.
python manage.py backfill_macro_series --start 2023-07-01
```
완료 후 `compute_all_signals()`를 동기 호출해 초기 `CreditSignalState`를 생성한다(flag 무관).

### Beat 등록 (암묵 자동 등록 없음 — 명시 실행 필수)
```bash
python manage.py register_credit_beats --dry-run   # 충돌 검사 + 계획만
python manage.py register_credit_beats             # 등록/갱신 (멱등)
```
- `ingest_fred_daily_task`   매일 07:30 Asia/Seoul (미 동부 마감 + FRED 반영 이후)
- `check_credit_ingest_succeeded` 매일 09:00 Asia/Seoul
- 등록 전 동일 crontab (hour, minute) 슬롯의 기존 beat를 조회·출력한다.
  (기존 07:30/09:00 beat는 America/New_York tz이므로 실제 벽시계 충돌 아님 — 참고용 보고.)

### 데이터 흐름
```
ingest_fred_daily_task (07:30)
   └─ FRED 6종 최근 10일 창 조회 → upsert (macro_series_history)
   └─ 성공 시 in-code로 compute_credit_signals_task.delay()  ← Decision ⑨-C 체이닝
compute_credit_signals_task
   └─ 원장에서 z/grade 계산 → CreditSignalState upsert (credit_signal_state)
check_credit_ingest_succeeded (09:00)
   └─ 미 영업일 최신 데이터 존재 확인, 결측 시 ERROR 로그 (주말은 통과)
```

## API

```
GET /api/credit-signals/strip/       (read-only, 인증 필요 — 파생 자산)
→ 200 { "as_of": "2026-07-07", "signals": [
    {"key": "HY_OAS", "name": "US HY OAS", "value": 3.52, "z": 0.4, "grade": "gray",
     "spark": [{"date": "...", "value": ...} × 30]}, ...
  ]}
```
spark = 최근 30 관측치. N+1 금지(상태 1쿼리 + 시리즈별 단일 쿼리).

## 테스트
```bash
pytest tests/credit_signals/
```
upsert 멱등/revise · z-score(MAD)+floor · 콜드스타트 · grade 경계(red 승격) ·
flag off no-op · verify(결측 ERROR/주말 통과) · API 스키마+쿼리 상한.
