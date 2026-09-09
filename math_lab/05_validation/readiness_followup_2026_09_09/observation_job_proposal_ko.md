# DailyPrice Read-only Observation — Job Proposal

- Status: Proposal / Not Queued / Not Executed
- Proposed new Job ID: SV-MATH-DP-OBSERVATION-002 (예약·등록하지 않은 제안 식별자)
- Parent Job: SV-MATH-DP-READINESS-001 (재사용/재실행 금지)
- Parent candidate: 1f5fa8420a02fbd683a31d75a5bd8724d78f188c
- Required code: math-lab/readiness-boundary-fix-v0.1의 검토된 수정 candidate
- Authority: 2026-09-09 Chat → Work Decision Handoff는 proposal 준비까지만 승인

## Purpose

현재 StockVis DailyPrice가 실제로 어떤 상태인지 관측한다. 예측 연구 입력 승인, 모델 실행, 백테스트, 최종 바스켓 선정은 수행하지 않는다.

## Entry conditions

1. Chat/CEO가 관측 Job의 실제 실행 범위·기준 candidate·정지 조건을 승인한다.
2. 사용자의 `/Users/byeongjinjeong/Desktop/stock_vis_lab_automation` source 및 최신 local runner를 보존한다. Remote checkout으로 대체하지 않는다.
3. 별도 작업 branch/worktree에 수정 candidate가 정확히 준비됐는지 검증한다. 원 candidate branch 및 historical artifacts는 변경하지 않는다.
4. 이미 허용된 DB read-only 접근 경로만 사용한다. 접근 확대, 새로운 credentials 배포, production schema 수정이 필요하면 정지한다.
5. 실제 등록 시 새 run UUID와 출력 폴더를 생성하고 이전 출력 경로를 재사용하지 않는다. 정확한 runner Job JSON은 local v0.1.4 코드를 읽고 그 기존 contract로 작성해야 한다. 이번 bundle에 없는 최신 runner contract를 추정해 새 공통 스키마를 만들지 않는다.

## Intended work

- 대표 SPY/AAPL/JPM/XOM/WMT/UNH의 존재/부재, 행 수 및 날짜 범위.
- 기본 OHLCV anomaly 및 통화·created_at 인벤토리.
- split/dividend 기록 및 지원되는 adversarial 모드 평가.
- unsupported/not_assessable/not_run/failed 상태를 구분.
- 거래 전 READ ONLY와 REPEATABLE READ를 서버에서 확인하고 rollback/cleanup 기록.
- 관측 시점·source commit·probe source fingerprint·접근 대상·한계 기록.
- Inventory permission과 declared-use eligibility를 별도로 출력. 허용된 실험 범위를 확대하지 않음.

## Expected evidence / Acceptance

1. 실제 DB 결과의 representative table은 6종목 모두를 표시하되 미존재와 미관측을 혼동하지 않는다.
2. 지원 모드는 실제 관측에 근거해 평가하며 10개 모드 전체 통과를 요구하지 않는다. 미지원·관측 불가 사유를 보존한다.
3. DB query failure는 완료된 이전 증거를 남기고 partial로 보고한다. 접속 실패를 데이터 불량으로 판정하지 않는다.
4. SQL transaction guard 실패 시 데이터 쿼리를 실행하지 않는다. 안전장치 우회 또는 권한 확대를 자동 시도하지 않는다.
5. F1/F2 회귀 테스트 통과 및 오류 산출물의 synthetic redaction 검증 결과를 별도로 연결한다.
6. 관측 결과를 현재 스냅샷 인벤토리로 한정한다. Sealed DataView가 없으면 content_fingerprint=null을 유지하고 결과 요약 지문으로 대체하지 않는다.
7. 새 run/artifact lineage와 parent candidate를 연결한다. 원 Job의 재시도·recovery로 기록하지 않는다.

## Not decided

최소 이력/행 수, 결측 허용률, 일반 fatal 규칙, 통과 종목 비율, 최종 바스켓, 수정주가/배당 정책, PIT/기업행동 ontology/Research Data Layer, confirmation admission, prediction target/model/backtest/production 사용.

## Stop and handoff

숫자 threshold가 필요하거나 PIT·lineage·corporate action 의미론 때문에 진행이 막히면 관측된 사실만 보존해 Chat으로 넘긴다. DB 권한 확대, production schema 변경, 대규모 backfill, 유료 provider, 다른 Lab authority 충돌, 공통 Lab Automation contract 변경, promotion이 필요하면 정지한다.

## Recommendation

Strong: 수정 candidate를 검토한 뒤 위 범위의 별도 관측 Job 실행을 승인받는다. 실제 데이터 인벤토리가 다음 판단의 가장 직접적인 근거다. 이미 봉인된 동등한 실제 관측 증거가 있다면 새 실행 대신 그 증거 검토가 우선일 수 있다.

현재 push/merge/deploy/main promotion 권한 없음. 이 문서는 Job 등록이나 실행 승인이 아니다.
