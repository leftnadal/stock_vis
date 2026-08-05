# 지시서 TH-TNV-CHAIN-1F — 체이닝 배포 (§F) + 실전 발화 게이트 (§G) 완결편

**트랙:** TH (TH-TNV-CHAIN-1의 §F·§G 완결 — §-1~§C는 완료·비준됨)
**전제 확정 사실:** §A 561892d9 · §B 8aa6ef64 (+18줄 additive, 테스트 3케이스) · §V 4580 GREEN/0/53 · §C 갭 백필 완결 판정(TNV 08-04 6행·HEAT 3줄·멱등 완결 비준). 세션 계보 3커밋 @ base 3518feec.
**실행 구조:** CC = 검증·명령 도출·문서. **push·런타임 트리 전진·워커 재기동 = 병진 수동·별도 터미널** (§H · #88).
**작성일:** 2026-08-04 (디렉터 세션)

---

## §-1. 배달 게이트

이 지시서를 `docs/instructions/TH-TNV-CHAIN-1F.md`로 저장·단독 커밋(세션 계보에 추가), 해시 보고 첫 줄 기록. 랜딩에 포함시킨다.

## §I. 불변

- CC의 launchctl·워커·beat 조작 0 (조회만). CC push 0. force·`git add -A` 금지.
- **병진 커맨드는 전부 별도 터미널** — CC 프롬프트 `!` 경유 금지 (#88, 2회 실측된 2분 truncate).
- 배포 명령은 **repo 참조 문서에서 도출** (worker_sync·런타임 트리 runbook 계열) — 문서 부재 항목은 창작 금지, 현행 프로세스 실측에서 역산하고 근거 명기.
- 부분 실패 → HALT.

## §0. 사전 실측 (읽기 전용)

1. **§C.2 사후 검증 완결** (미완이면 여기서): TNV 총행·08-04 6행 격자 / override 215·ovr_v1·07-22 불변 / corpus 무변경 — 사전 스냅샷 대조표.
2. **프로세스 지형 실측**: worker·beat 프로세스 각각의 PID·시작 시각·구동 경로(어느 트리의 코드인가) 실측. **theme-heat-daily 태스크를 실제 소비하는 프로세스가 worker임을 확인** (beat는 스케줄러일 뿐 — 재기동 대상 판별의 근거). plist ↔ 프로세스 대응 확인 (com.stockvis.celery-worker.plist 등, 조회만).
3. 런타임 트리 재실측: sv-worker-runtime 현 HEAD(직전 실측 442156ba detached)·origin/main 대비 뒤처짐 커밋 수.
4. 재기동 안전 시간대: beat 발화(±30분) 회피창 재확인 — 특히 **오늘 18:00 ET(theme-heat-daily) 前 완료가 목표** (오늘 밤 발화 = G-fire). 17:30 ET filings와의 간격도 고려해 **17:00 ET 이전 완료 권장**으로 산출.

## §F1. 랜딩

1. CC: `git fetch` → origin/main 재전진 시 rebase(문서·additive 코드라 충돌 기대 0, 충돌 시 HALT) → 재전진 조합에서 suite 재실행·앵커 → 최종 HEAD 보고 → **HALT, 병진 push 대기.**
2. 병진 (별도 터미널): `git -C ~/worktrees/sv-th-chain push origin HEAD:main`
3. CC: origin/main == HEAD 동기 재확인.

## §F2. 배포 2단 (병진 수동 — ⚠️ push만으로는 미배포, 3회 재발 함정)

1. CC가 정확한 명령을 **각 1줄씩** 제시 (경로·해시 실측값 대입, §0-2·3 근거):
   - ⓐ **런타임 트리 전진**: sv-worker-runtime을 origin/main 신규 HEAD로 (fetch + checkout --detach <신규 HEAD> 계열 — repo runbook 문서의 canonical 절차 우선, 문서와 실측 불일치 시 HALT·상신).
   - ⓑ **워커 재기동**: plist 기반 canonical 재기동 절차 (runbook 도출). beat 재기동 필요 여부는 §0-2 실측으로 판정해 명기 (태스크 코드는 worker 소비이므로 원칙상 worker만 — beat까지 필요하다는 실측 근거가 나오면 그 근거와 함께 제시).
2. 병진 (별도 터미널, §0-4 시간대): ⓐ→ⓑ 순서 실행, 출력 전달.
3. CC 배포 검증 (읽기): 워커 프로세스 재시작 시각 갱신 · 구동 트리 HEAD = 신규 HEAD · `TNV_CHAIN` 코드가 로드 대상 트리에 존재(`git -C <런타임 트리> show HEAD:apps/chain_sight/tasks/heat_tasks.py | grep TNV_CHAIN`) 확인. **"활성화≠배포"의 세 요소(코드 착지·트리 전진·프로세스 재기동) 전부 체크된 표**로 보고.

## §F3. 롤백 후보 준비 (실행 금지)

- `git revert 8aa6ef64` 가능성 사전 확인(충돌 없음 검증만)·롤백 절차 3줄(revert 커밋→push→트리 전진·재기동) 문서화. **G-fire 실패 판정 전 실행 절대 금지.**

## §G. G-fire — 실전 발화 게이트 (익일 아침, 세션 분리 가능)

배포 익일(첫 자연 발화 후, KST ~07:30 이후) 병진의 "게이트 확인해줘" 한 마디로 실행:

1. 워커 로그에 `TNV_CHAIN date=<발화일> written=N zeroed=M` 라인 존재 — **체인이 실전에서 돌았다는 직접 증거.**
2. 당일 TNV 행 실측: 수요일(08-05) 발화라면 키워드 실데이터 기대 → written>0이면 행 대조, keywords=[]로 판명되면 written=0 정상 판정 (corpus 당일 keywords 블록 수를 근거로 명기).
3. **동일 실행 내** heat 저장 확인 (TNV_CHAIN 로그 직후 heat 로그·당일 heat 행 created 시각 정합).
4. 태스크 오류·retry 기록 0.

**판정**: 4항 전부 충족 → G-fire PASS → CC가 TASKQUEUE `TH-TNV-CHAIN ✅완료` + G-fire 결과표 커밋 → 병진 push → **트랙 종결 선언.** 1항이라도 미충족 → HALT·원인 실측 보고·§F3 롤백 후보 회부 (판정은 디렉터).

## §R. 최종 보고 형식

§C.2 대조표 / §0-2 프로세스 지형표 / 착지 해시·동기 / §F2 배포 3요소 체크표 / §F3 롤백 절차 / (익일) §G 4항 결과표·종결 선언 / DECISIONS·TASKQUEUE diff.

## HALT 조건

배달 게이트 실패 / rebase 충돌 / suite 신규 실패 / runbook-실측 불일치 / 배포 후 검증 3요소 중 1개라도 미충족 / G-fire 4항 미충족 / CC에 워커 조작·push를 요구하는 모든 상황.
