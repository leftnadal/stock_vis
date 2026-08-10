# 지시서 TH-SUNMON-REEXTRACT-1 (CC 전달용)

**트랙**: TH / CORPUS-SUNMON-EMPTYKW 조치
**결정 근거**: D-SUNMON-REEXTRACT = 선택지 ①. 추출 스케줄·창 정의(localdate KST) 무접촉. av-broad 수집 완료에 체이닝된 재추출 트리거만 추가. C(창 재정의)는 관찰 보류 — 이 지시서 범위 밖.
**작성일**: 2026-08-10

---

## §-1. 배달 커밋 (0번째 게이트)

이 지시서를 `docs/instructions/TH-SUNMON-REEXTRACT-1.md`로, D-SUNMON-REEXTRACT 결정(선택지 3안·가중합·병진 승인)을 `DECISIONS.md`에 커밋 후 착수. **미커밋 상태로 §0 진입 금지**.

## §0. 실측 (read-only)

1. origin/main HEAD·worktree 동기 (base가 12639c2c 이후 전진했어도 통상 — 최신 기준).
2. `keyword_extractor`의 skip 로직 원문 확인 (`status=='completed'`만 skip인지, failed 재호출 시 실제로 재추출되는지 코드 경로 실측).
3. `collect-av-broad-news` 태스크의 완료 지점 — 체이닝을 걸 수 있는 구조인지(TNV→heat 체인과 동일 패턴 적용 가능 여부).
4. 현재 failed DailyNewsKeyword 전수: 날짜 목록 + 각 날짜의 NewsArticle 실존 수 (= 백필로 구제 가능한 날짜 vs 기사 자체가 없어 구제 불가한 날짜 구분).

**HALT 조건**: 2·3에서 전제와 다른 구조 발견 시 즉시 상신.

## §1. 구현

1. av-broad 완료 후 체이닝: "당일+전일(KST)의 `status=='failed'` DailyNewsKeyword 재추출" — TH-TNV-CHAIN에서 입증된 체인 패턴 재사용.
2. **completed 가드 (절대)**: 재추출 대상 선별은 failed만. completed 행은 어떤 경로로도 재기록 금지 — 코드 레벨 필터 + 테스트로 입증.
3. 파일 로깅: S1 패턴(apps 로거)으로 `SUNMON_REEXTRACT date=<d> before=failed after=<status> keywords=<n>` 형식 기록 — 주말 게이트의 검증 재료.

## §2. 검증 게이트 (suite)

- 신규 테스트: failed 재추출 성공 경로 / completed 무접촉 경로 / 기사 0건 시 failed 유지 경로.
- 기존 suite GREEN (회귀 격리).
- 가드 실증: 로컬에서 completed 1행·failed 1행 픽스처로 재추출 실행 → completed 행 byte 동일 대조.

## §3. 배포 (병진 수동)

착지 push·worker 재기동은 병진. CC는 원자 push 스크립트(3파일 scope 가드 패턴) + 재기동 명령을 스크립트 파일로 준비·상신 후 HALT. (#88: 스크립트화·별도 터미널)

## §4. 백필 상신 (실행 병진)

§0-4의 구제 가능 날짜 목록 기반으로 과거 failed 일괄 재추출 명령을 스크립트로 준비·상신. keywords 복구까지만 이 트랙 범위. 복구된 날짜의 TNV/heat 소급 재계산은 별도 후보로 목록만 상신(§C 백필 기계 재사용 가능성 포함) — 병진이 수치 보고 다음 결정.

## §5. 관측 게이트 (G-sunmon)

배포 후 첫 주말(08-15/16) 경과 시점 실측 — 기대: 08-16(일) DailyNewsKeyword가 월요일 01:01 UTC 재추출로 failed→completed 전이 + `SUNMON_REEXTRACT` 파일 로그 실기록 + 화요일 TNV에 일요일 keywords 반영. 통과 시 트랙 종결 보고, C 관찰 카운터(주말 2회) 시작.
