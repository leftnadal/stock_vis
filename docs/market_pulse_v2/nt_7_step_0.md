# NT-7 STEP 0 — mp_calc_regime_15min FileNotFoundError 진단 (읽기 전용 · 작업 금지)

## 컨텍스트

market_pulse로 핸드오프된 NT-7: mp_calc_regime_15min 작업이 FileNotFoundError로 실패.
이번 세션은 "고친다"가 아니라 "이 15min regime 계산이 존재해야 하는가"를 판정하기 위한
ground truth 측정만 한다. market_pulse 설계 원칙은 "일(daily) 단위 데이터로 충분,
intraday는 불필요한 오버헤드" — 15min은 이 원칙과 충돌하므로, 잔재(삭제 대상)일 가능성과
의도된 기능(수정 대상)일 가능성을 둘 다 열고 측정한다. 코드는 만지지 않는다.

## 절대 규칙

- 파일 수정·생성·삭제, 커밋, 브랜치/worktree 생성, task 실행, 마이그레이션 전부 금지.
  읽기·조회(grep·cat·git log·git blame)만.
- 추측 금지. 확인 못 한 항목은 "미확인"으로 남긴다.
- 측정만으로 결론을 내리지 말 것 — 고침/삭제 결정은 내가 가중합으로 닫는다.

## 측정 1 — 에러의 실체

- mp_calc_regime_15min 의 정의 위치(task 함수/파일), 무엇을 하는 코드인지 1~2줄.
- FileNotFoundError가 정확히 어느 줄에서, 무슨 파일/경로를 찾다 나는지.
- 그 "없는 파일"이 무엇인가: 다른 task가 만들어줘야 하는 산출물인지, 설정/캐시/모델
  asset인지, 경로 상수 오타인지. 생성 책임이 어디에 있(었)는지.

## 측정 2 — 호출자/스케줄 전수 (살아있는 기능인지)

- mp_calc_regime_15min 을 호출·스케줄하는 곳 전수 grep: Celery beat schedule, tasks,
  views, 다른 서비스. 누가 언제 이걸 도는가.
- beat schedule에 등록돼 실제 주기 실행되는지 vs 등록만 남고 안 도는지.
- "15min"·intraday·900(초) 류 키워드로 관련 잔재가 더 있는지 동반 grep.

## 측정 3 — daily 경로와의 관계 (핵심 판정)

- market_pulse의 정규 regime 산출 경로(daily/EOD regime, 우리가 방금 만진
  eod_regime_calculator/DynamicRegimeCalculator 포함)와 mp_calc_regime_15min의 관계:
  · 15min이 daily 경로의 입력/선행인가, 완전 별개 병렬 경로인가, daily로 대체된 구버전인가.
  · 산출물(레짐 값)을 소비하는 다운스트림이 있는가, 아무도 안 쓰는가.
- git log/blame로 mp_calc_regime_15min 도입 시점과 최근 손댄 시점 — 최근 active인지 방치인지.

## 측정 4 — 삭제 가정 시 영향 / 수정 가정 시 범위

- 만약 삭제한다면: 함께 지워질 것(task·schedule·관련 파일·테스트), 깨질 소비자(측정 2·3
  기준 0이어야 안전), prod/운영(beat 등록 해제) 영향.
- 만약 고친다면: "없는 파일"을 누가 만들게 해야 하는지, daily 산출 주기와 어떻게 정합되는지,
  intraday 데이터 소스가 현재 파이프라인에 있긴 한지(없으면 수정=신규 인프라).

## 측정 5 — 관련 테스트/문서

- mp_calc_regime_15min·15min regime을 다루는 테스트·DECISIONS·common-bugs·TASKQUEUE 항목.
  (특히 과거에 이 기능을 의도적으로 넣은/뺀 결정 기록이 있는지 — 있으면 그게 방향을 가른다.)

## 보고 형식

1. 한 줄 판정 — "NT-7은 잔재(삭제 유력)/의도된 기능(수정 유력)/불명(추가 측정 필요)으로 보인다".
2. 측정표 — 측정 1~5 결과를 항목/실측값으로.
3. 고침 vs 삭제 근거 매트릭스 — 각 방향에 이번 실측이 주는 찬/반(결정은 내리지 말 것).
4. HALT 사유 — 예상 밖 상태(있으면).
5. 다음 단계 준비 — 삭제 유력 시 지울 목록 / 수정 유력 시 필요한 선행(없는 파일 생성 책임)
   을 "목록만"(실행 금지).

작업은 하지 말고 위 보고만 돌려줘.
