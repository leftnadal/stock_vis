# EVT-IMPL-3 — 초회 적재 + beat 가동 (write: 원장 실쓰기 인가)

전제: EVT-2 main 착지 + 사용자 worker 재시작 완료 후 착수. 앵커 v1.1 준수, 충돌 시 HALT.
범위 밖: 연합 읽기·FE = 4호. push는 "푸시" 지시 대기(D-PUSH-DELEG).

## §0
0-1. fetch → sv-evt-1 재사용, origin/main 역머지(auto 한정, 충돌 HALT). 해시 보고.
0-2. [활성화≠배포 검증 — 하드] celery inspect registered로 실행 중 worker가
     collect_calendar_events를 인식하는지 확인. 미인식이면 HALT("worker 재시작 필요").
0-3. [0번 게이트] 지시서 → docs/instructions/EVT-IMPL-3.md 커밋(1파일).
0-4. health baseline 기록(상속 ❌ 1건은 기록 후 진행). foreground·기계 시계·-A 금지.

## STEP 1 — 초회 적재 (foreground)
1-1. 예산 확인 → collect_calendar_events(dry_run=False) 1회 foreground 실행.
1-2. 검증 SQL: 총 행수(dry-run fetched 합 ~13.7k 대비 dedup 감안 정합) / 유형별·status별
     분포(scheduled 다수 + trailing occurred 일부) / event_date min·max / 절단·실패창 0.
1-3. 멱등성 증명: 즉시 2회차 실행 → 재관측 다수(date_observed_count 2) + 신규 행 비율
     <1%(FMP 실시간 추가분 허용). **>5%면 HALT**(멱등키 결함 의심). stale 전이 0 확인(동일일).

## STEP 2 — beat 등록 (DB PeriodicTask — dict-only 금지)
2-1. collect-calendar-events 등록: crontab 17:45 ET(CELERY_TIMEZONE 실측 확인), enabled=True.
2-2. 등록 검증: PeriodicTask 행 존재·enabled·crontab 값 SQL 인용.
2-3. beat 스케줄러의 신규 등록 감지 방식 실측(DatabaseScheduler 자동 반영 여부) —
     재시작 필요하면 진행 멈추지 말고 "사용자 수동 재시작 필요"로 보고에 명기.

## STEP 3 — 관찰 게이트 등재 (TASKQUEUE)
[EVT-OBS-1] 익일 17:45 ET 이후 검증 — 증거는 last_run_at이 아니라 DB 행: 당일 last_seen_at
갱신 행 수 / 신규 행 수 / stale 전이 수 / bisect 텔레메트리(depth 4 도달 또는 콜 상한
근접 시 상한 재결정 에스컬레이션). 검증 예정일 명시.

## STEP 4 — 검증·보고: 전체 스위트(상속 1건 외 GREEN)·health(신규 이상 0)·git log·status.
## HALT: 0-2 미인식 / 초회 적재 절단·실패창 발생 / 1-3 신규 행 >5% / 예상 밖 일체.
