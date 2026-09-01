# MP-MACRO-CAL-1 — 거시 캘린더 수집기 정비 (별건 · market_pulse 소유 · 디렉터 초안 2026-08-31)

> 지위: **초안**. 결정·집행은 market_pulse 트랙(해당 앱 프로젝트)에서. ops/EVT 트랙은 소비자로서 결함을 보고하고 계약 조건만 건다.
> 발견 경위: EVT-IMPL-4 이벤트 캘린더 실화면(2026-08-31)에서 거시 원천 결함 3건 노출.

## 결함 (실측·코드 좌표)
1. **시각 시간대 불일치** — `apps/market_pulse/tasks/macro.py:183` FMP `date`(UTC)의 HH:MM을 그대로 `EconomicEvent.event_time`에 저장. 모델(`macro/models/indicators.py:291`) help_text는 'ET'. 결과: 모든 소비자가 +4h(EDT)/+5h(EST) 오표시. market_pulse 자체 화면(serializers.py:69 event_time 노출)도 동일 영향 추정 — 실측 필요.
2. **실제값 미백필** — 수집 창 `today .. +14일`(macro.py:164~166). 이벤트가 지나가면 `actual_value`가 갱신되지 않음 → 과거 이벤트의 실제값·서프라이즈 계산 불가(EVT 캘린더 "지난 7일 발표됨" 거시 34건 전부 실제값 없음).
3. **중요도 인플레** — 매핑 `High→critical, Medium→high, else→medium`(macy.py:178). FMP impact High가 실업수당 4주평균·JOLTS까지 포함 → 97일 창 critical 34·high 60. 모델 정의(CRITICAL = FOMC·NFP·CPI·GDP)와 불일치. 부수: 선행 창 14일이라 "45일 창" 소비자(EVT 스트립)가 실제로는 2주만 받음.

## EVT 트랙이 거는 계약 조건 (변경 시 EVT-CORR-4 파손 방지)
- **`event_time`의 저장 의미는 UTC로 유지**하고 help_text만 'UTC(FMP 원문)'로 정정한다. ET로 바꾸려면 EVT-CORR-4(읽기 계층 UTC 해석)와 동시 변경 + 기존 행 데이터 마이그레이션이 필요 — 권장하지 않음.
- `event_id` 해시(date_event_country)는 유지(멱등 upsert 키 안정).

## 제안 (market_pulse 결정 사이클용 선택지 — 가중합은 그쪽에서)
A. 수집 창 `today−7 .. today+45`(FMP economic-calendar 단일 콜, 캡 실측 필요) → 실제값 백필 + 45일 선행 실현. 일 1콜 유지.
B. 중요도 = 제목 화이트리스트 우선(FOMC·Fed Funds·NFP/Nonfarm·CPI·Core PCE·GDP·Retail Sales·ISM = critical/high 표), 그 외는 FMP impact High→high, Medium→medium, Low→low. 기존 행 재분류는 다음 수집 run의 update_or_create로 자연 치유(창 밖 과거 행은 잔존 — 허용).
C. 시간대: 저장 UTC 유지 + help_text 정정 + market_pulse 자체 소비처(serializer/FE)의 표시 변환 점검.
D. 텔레메트리: run당 saved/updated(actual 신규 채움 수)/importance 분포 로그 1줄.

## 검증 제안
- 표본 3건(Initial Jobless Claims 08:30 ET·ISM 10:00 ET·FOMC 14:00 ET) 저장값·표시값 대조.
- 과거 7일 거시 actual_value 채움률(전/후).
- EVT 캘린더 both: 거시 건수·critical 건수 전/후(현재 94 / 34).
