# 지시서 TH-TNV-CHAIN-GOBS-1 — S1 관측성 실증 (G-obs) + 트랙 최종 정리

> **실행 결과(2026-08-10 배달 시점 추기):** G-obs **통과**(디렉터 인준·Neo4j caveat 포함). 종결선언 S6 착지 origin/main `9a715196`(초안 커밋→원자 rebase 착지). §0~§2 CC-문서분 완료, 파괴적 정리(브랜치 삭제·rm)는 병진 실행 대기. 본 파일은 §2 최종 정리 커밋과 함께 착지.

**트랙:** TH (TH-TNV-CHAIN 종결 후속 — 게이트 아님, 관찰 실증 + 청소)
**전제:** G-fire PASS(DB 입증) · S1 LOGGING apps 로거 배포 완료(worker-runtime 8a41c842) · S6 종결 선언 커밋 `9a715196`(초안 커밋, origin/main 8커밋 전진으로 union rebase 착지).
**검증 대상 발화:** theme-heat-daily ET 18:00 08-07(금) = KST 07:00 08-08(토). 기대 as_of = **2026-08-07** (G-fire 선례: 22:00 UTC 발화 → UTC 날짜 = ET 날짜). **실측 확인**.
**실행 구조:** CC = 실측·문서. push·삭제·스크립트 정리 = 병진 수동·별도 터미널(#88).
**작성일:** 2026-08-08 (디렉터 세션) · **집행일:** 2026-08-10

---

## §-1. 배달 게이트

이 지시서를 `docs/instructions/TH-TNV-CHAIN-GOBS-1.md`로 저장, §2 최종 정리 커밋과 함께 착지.

## §0. 실측 (읽기 전용 — #89: 시각 판정은 machine clock·last_run 전용) — **완료**

1. `git fetch` → S6 착지 여부. **초안 미착지 → 병진 원자 push(`th_land_atomic.sh`)로 `9a715196` 착지 확인 후 재개.**
2. machine clock(UTC·KST·ET 병기) + theme-heat-daily last_run·total_run 실측. **실측: total_run 20·last_run 08-09 22:00 UTC·08-07 발화 확인(TNV created 08-07 22:00:00 UTC).**
3. worker-runtime HEAD가 여전히 apps 로거 포함 커밋(8a41c842 이상)인지 확인. **확인: sv-worker-runtime, 후퇴 없음.**

## §1. G-obs 검증 4항 — **통과**

1. **파일 로그** `TNV_CHAIN date=2026-08-07 written=N zeroed=M` — S1 라우팅 수정 실증(본체). **✅ `written=3 zeroed=0` 파일 기록.**
2. DB 대조: TNV 08-07 행수 = 로그 written · created ≈ 22:00 UTC. **✅ TNV 3행·created 22:00:00 UTC(금요일 실데이터).**
3. 동일 실행 heat: 08-07 heat 행 created가 TNV 직후 인접. **✅ heat 6행·22:00:12~46 UTC(~12–46s).**
4. 오류·retry 0. 부수: `heat beat E2 증분` 로그도 파일에 찍히는지. **✅ heat E2 로그 파일 기록(선존갭 해소). ⚠️ 오류=선존 Neo4j-down(비체인·G-fire에도 동일·회귀 아님)→디렉터 인준 하 통과.**

**판정**: ①~④ 충족 → G-obs 통과. (Neo4j caveat=선존·비체인·롤백 트리거 미해당 → TH-HEAT-NEO4J-DOWN 백로그 등재.)

## §2. 통과 시 — 최종 정리 (이 트랙의 마지막 배치) — **CC 문서분 완료·병진 실행 대기**

1. 문서 커밋: TASKQUEUE G-obs ✅ + 종결 선언 최종 확정(`9a715196`·G-obs 결과) + §F3 롤백 후보 폐기 선언 + TH-HEAT-NEO4J-DOWN·OPS-SMTP-CRED 등재. **완료.**
2. 정리 후보 검증(읽기, #87 = `origin/main..<br>` 고유 커밋으로만 손실 판정): 본 세션 계열 `sess-th-chain`+`sv-th-chain`; SEC β 잔존 `sess-secb-kickoff`(+`sv-secb`)·`sess-secb-gate2-amend`·`sess-secb-progress`·원격 `origin/monorepo/sess-secb-g16`. → 병진 실행 명령 목록 상신. **완료(상신).**
3. HALT — 병진 실행 대기: ⓐ 최종 문서 커밋 push ⓑ §2-2 삭제 명령 ⓒ 임시 스크립트 정리 `rm ~/th_gap_tnv.sh ~/th_gap_heat.sh ~/th_deploy.sh ~/th_push.sh ~/th_land_atomic.sh`.
4. CC 사후 재실측 → 트랙 종결 최종 보고.

## HALT 조건

S6 미착지 / 08-07 발화 미발생 / ① 로그 재실패 / ②③ 체인 이상 / worker-runtime 후퇴 / 삭제 후보 중 미착지 내용 발견 / CC에 push·삭제·rm을 요구하는 모든 상황.
