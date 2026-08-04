# 지시서 TH-RECON-1 — TH 트랙 기상 전 상황 파악 (읽기 전용 전수 실측)

**트랙:** TH (Theme Heat) — SEC β 종결로 트리거 발화됨 (TH-TRIGGER-FIRED)
**세션 종류:** 순수 정찰 (read-only recon). **이 세션은 아무것도 고치지 않는다** — 50일+ 동결된 트랙의 현재 상태를 측정해 보고서 1장을 만드는 것이 전부다. TH Session 1 실행 지시서는 이 보고서를 근거로 디렉터가 별도 작성한다 (결정-실행 분리 · 고밀도 로직은 신선한 세션 머리에).
**worktree:** 신규 생성, 브랜치 `monorepo/sess-th-recon`
**작성일:** 2026-08-03 (디렉터 세션)

---

## §-1. 배달 게이트

1. 이 지시서를 `docs/instructions/TH-RECON-1.md`로 저장, **단독 커밋** (이 세션의 유일한 허용 쓰기). 커밋 해시 보고 첫 줄 기록.
2. 명시적 파일 지정만 — `git add -A` 금지.

## §I. 불변 (전 구간)

- **repo 쓰기 = §-1 커밋 1건뿐.** 그 외 커밋·파일 수정·마이그레이션 적용 0.
- **DB 쓰기 0** (prod/dev 불문). 조회는 read-only 쿼리만.
- **LLM 호출 0 · 외부 API 실호출 0** (FMP 포함 — 백필 규모는 코드·DB로 추산, 실호출 검증은 Session 1 이후).
- **launchctl·plist·워커·beat 상태 변경 0** — 관찰만 (§H 경계).
- 이 세션에서 발견하는 모든 이상은 **고치지 않고 기록**한다. 예외 1건만 즉시 HALT: §3에서 TH 관련 워커/태스크가 *실제 가동 중*으로 관찰되는 경우 (동결 전제 자체가 깨진 것 — 즉시 보고).

## §0. 공통 실측

1. `git fetch` → main HEAD·origin 동기 기록.
2. 신규 worktree `monorepo/sess-th-recon` 생성, 셸 위치를 worktree 원장과 대조 (common-bugs #3).
3. 브랜치·worktree 전수 목록 (SEC β 삭제 후보 정리 여부도 관찰 기록).
4. 베이스라인 재실측: full suite → "N GREEN / M pre-existing (사유)" 앵커. 직전 관측 4561/0/53은 이월 금지·참고만 (D-SECB-BASELINE · #79).

## §1. TH 코드·브랜치·마이그레이션 실측

1. TH 관련 동결 브랜치 전수 식별 (브랜치명·최종 커밋 해시·일자).
2. 각 동결 브랜치 vs origin/main: **3-dot diff로 실제 신규분** 산출 (#78 — 2-dot 오판 금지). 변경 파일 수·핵심 파일 목록.
3. **마이그레이션 충돌 실측**: 동결 브랜치의 TH 마이그 번호 vs 현 main의 해당 앱 최신 번호 → renumber 필요 목록 (앱별 "브랜치 N번 vs main 최신 M번" 형식). `makemigrations --dry-run`·`showmigrations`는 읽기 전용이므로 허용 — `migrate` 실행 금지.
4. 동결 기간 main 전진분이 TH 코드와 겹치는 파일 (충돌 예상 지점) 목록.
5. ThemeTermOverride 사전: 코드/fixture/DB 어디에 있는지, 215행 현존 여부 (아래 §2와 교차).

## §2. 데이터 상태 실측 (prod read-only)

정적 총건수는 게이트 금지 — 전부 **날짜 스코프 불변식**으로 기록한다.

1. **corpus 갭**: 뉴스/코퍼스 최신 수집 일시, 07-12 동결 시점과의 갭 일수, 일평균 수집량(동결 前 30일 기준) → 백필 예상 규모 (건수 구간 추정 + 산식 명기).
2. **TNV 백필 범위**: 07-12→현재 대상 심볼 수·레코드 갭, 백필 소요 추정 근거.
3. **heat score**: 마지막 계산 일자·대상 테마 수. 재계산 대상 범위.
4. **ThemeTermOverride**: 215행 현존·최종 수정 일자 (판결 완료 상태 그대로인지).
5. EstimateSnapshot 등 가동 중 트랙과 TH의 데이터 접점 여부 (있으면 목록만).

## §3. 자동화·워커 상태 실측 (관찰만 — 변경 절대 금지)

1. **beat 3종 분리 확인**: 가동 중으로 알려진 3종(estimate·filings·heat-daily)과 TH 재활성 대상의 목록을 분리해 각각 PeriodicTask `enabled` 플래그 실측.
2. **플래그 ≠ 배포** 이중 확인 (common-bugs — 3회 재발 항목): DB 플래그와 별개로, 실행 중 워커 프로세스(`ps`)·최근 로그에서 TH 태스크 실행 흔적 유무 확인. **TH 태스크 실행 흔적 발견 → 즉시 HALT** (§I 예외).
3. beat 프로세스 개수 확인 (dual-beat 이중발화 위험 — 1개 초과면 기록).
4. launchd: TH 관련 plist 존재·load 상태 **조회만** (`launchctl list` 등). 08-04 백업 삭제 이행 여부도 관찰 기록.
5. nightly 자동화가 TH 경로를 참조하는지 (worktree 격리 관점 — live 자동화는 origin/main 추적 트리만 참조해야 함).

## §4. 하네스·원장 실측

1. TASKQUEUE에서 TH 관련 항목 전수 발췌 (TH-DEPLOY·TH-DSS-IMPL·TH-HEAT-C1-RETRO 포함, 원문 그대로).
2. DECISIONS에서 TH 동결 결정·재개 조건 관련 항목 발췌.
3. common-bugs에서 TH 재개 시 적용될 항목 번호 목록 (beat 관련·백필 foreground 규칙 등).
4. TH-DEPLOY 정의 문서 존재·경로·커밋 해시 (renumber·reverse-merge·워커 재기동 절차가 문서화되어 있는지).

## §R. 보고 형식 (Session 1 설계의 입력물)

1. 실측 총괄표 (§0~§4 수치·해시 전부).
2. **차단 요인 목록**: Session 1 착수 전 반드시 풀어야 하는 것 (예: 마이그 renumber 충돌 N건).
3. **리스크 목록**: 착수는 가능하나 주의할 것.
4. **디렉터 결정 후보 목록**: 선택지가 갈리는 지점만 추출 (예: 백필 슬라이스 단위, reverse-merge vs rebase). 결정하지 말고 상신만.
5. 백필 규모·소요 추정 (산식 포함 — 검증 안 된 숫자에 반드시 "추정" 표기).

## HALT 조건

배달 게이트 실패 / TH 태스크 실제 가동 흔적 / 읽기 전용으로 확인 불가능한 항목에 쓰기가 필요해지는 모든 경우 / 예상 밖 dirty 상태 — 즉시 중지·보고. 임기응변 금지.
