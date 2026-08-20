# NEO4J-CLOSE-1 — sync 재활성화·게이트 판정·트랙 종결 (원샷 지시서)

- 발행: 2026-08-20 (디렉터). 0번째 게이트 디렉터 유예 — §0-0 자기 커밋으로 감사 흔적 확보.
- 위임 근거 (명시 인용): 병진 지시 "잔여작업 남은것도 지시서로 해결할수 있도록 해줘. 수동이
  아닌 지시서로 할꺼야." (2026-08-20) — 이에 따라 아래 §1·§2의 쓰기와 §6의 push를 CC 집행으로
  위임한다. 본 인용이 없었다면 전부 병진 수동 영역이다.
- 선행: SYNC-REENABLE 조사 (차단 이슈 없음 판정), ⑰-M 결정①의 예정된 재활성화 조건 충족.

## 세션 계약
- worktree: monorepo/sess-neo4j-recon 지속 사용(존재 시). 부재 시 재생성 후 진행.
- 허용 쓰기 (이것만): ① PeriodicTask 3종 enable(.save()) ② sync_relations_to_neo4j.delay()
  enqueue ③ 본 지시서 사본·addendum·TASKQUEUE 갱신의 세션 브랜치 커밋 ④ §6 push.
- 전면 금지 유지: launchctl·서비스 조작 실행 / 브랜치·worktree 삭제(후보 보고만,
  D-BRANCH-DELETE-MANUAL) / 시크릿 취급·출력 / heat 소급 / `git add -A` / .env 수정.
- HALT-0 기본. machine clock only. 대형 명령 foreground. 2분 트런케이션 유의(#88) —
  대기성 검증은 짧은 read-only 조회 반복으로.

## §0 부트스트랩
0. 본 지시서 전문을 docs/instructions/202608/NEO4J-CLOSE-1.md로 저장, 단독 커밋, 해시 출력.
1. machine clock / git fetch / health_check.
2. baseline 실측 기록: neo4j_synced_at max / neo4j_dirty=True 건수 / 3종 PeriodicTask enabled
   현황 / Redis 캐시키 chainsight:related_to_cleanup_v1 존부(레거시 정리 발동 예보).

## §1 재활성화 (위임 쓰기)
- 대상: chainsight-sync-relations-neo4j · chainsight-sync-profiles-neo4j ·
  chainsight-neo4j-dirty-sync (3종. 병진이 명단을 줄였다면 그 명단이 결정).
- 방법: 각각 t.enabled=True; t.save() (**.update() 금지** — DatabaseScheduler 미감지, #28 계열)
  + django_celery_beat.models.PeriodicTasks.update_changed() 호출.
- 3종의 enabled 상태를 재조회로 확인 출력.

## §2 즉시 따라잡기 + 게이트 판정 (위임 enqueue)
1. sync_relations_to_neo4j.delay() — task id 기록. (crontab 대기 없이 당일 판정 확보 목적)
2. 판정 루프 (read-only 조회를 1~2분 간격 반복, 최대 20분):
   - neo4j_synced_at max 전진 여부 / dirty 건수 추이 / neo4j 큐 워커 로그 tail.
   - 레거시 정리 발동 시(§0-2 캐시키 부재 or 로그의 RELATED_TO cleanup 문구): dirty가 4587을
     넘어 급증할 수 있음 — **HALT 사유 아님**, 설계된 재생성. 발동 사실·규모만 기록하고 루프 지속.
3. PASS 기준: neo4j_synced_at max > 2026-07-11 (전진 확인). dirty 잔량은 0 도달이 이상적이나
   감소 추세 확인이면 PASS 가능(잔량·추세 수치 보고). 20분 내 전진 자체가 없으면 HALT + 로그 상신.

## §3 시간 조건부 확인
- machine clock ≥ 2026-08-20 23:10 UTC이면: SignalAccuracy signal_date=2026-08-18 row 존부 확인.
- 미도래면 addendum에 "차기 확인 항목(08-20 23:00 발화 후)"으로 기재하고 생략.

## §4 addendum 커밋
docs/reports/202608/TH-NEO4J-RECON-1-report.md에 "실행 addendum" 절 추가 커밋. 필수 내용:
- 사건 서사 최종본: 타르볼 05-01 정지(launchd 부재+JAVA_HOME 결손) → 07-13 sync 3종 의도적
  비활성(⑰-M, 기록 있음) → 08월 클립보드 오염으로 비번 미상화 → auth-off 결정론적 리셋 →
  celery 15.8h 정지(시한 가드 미집행이 유일 실손 원인) → 08-18 결번 확정 → 재활성화·게이트.
- (b)가설 반증 기록: homebrew 04-03 이후 무활동. synced_at 07-11 스탬프 경위=미해명
  (역사적 의문, git log neo4j_sync.py 프로브로 판별 가능 — 저순위).
- known-gaps: 08-18 MonitorSnapshot·PortfolioSnapshot·AdvisoryRun·브리핑·일집계·리포트·heat 결번
  / EODDashboardSnapshot 08-18(target_date 경로 미생성) / 인트라데이 5분 샘플 희소.
- common-bugs 등재 4건: ①시크릿 클립보드 경유 금지(.env 직독만) ②시간 가드는 소유자(알람)
  지정 없이는 무효 ③row 0≠미발화 — no-op 설계 태스크 먼저 소거 ④celery 로그=KST, 감사 전
  타임존 앵커 실측.
## §5 TASKQUEUE 갱신 커밋
- 종결: GRAPH-NEO4J-SYNC-DEACTIVATE(조건 충족·재활성화 완료) / NEO4J-GAP-BACKFILL-RECON(§2에서
  dirty 소진 확인 시 "자연 해소"로 종결, 미소진 시 잔량 명시로 축소 재정의).
- 등재: NEO4J-RESTORE-P2(launchd, §7) / OPS-SMTP-CRED(선존, 병진 수동 로테이션 필요) /
  synced_at-07-11 스탬프 경위 프로브(저순위) / EODDashboardSnapshot target_date 경로 개선(저순위)
  / Q19 재측정(sync 재개 후 신규 고유 페어 관측 + 9562 지표 정의 실측 선행).

## §6 push (D-PUSH-DELEG 발동 — 본 지시서가 병진의 push 지시)
1. git fetch origin → behind 확인. behind>0이면 git merge origin/main (auto-merge만 허용,
   docs 외 충돌 발생 시 즉시 HALT).
2. push HEAD:main → 착지 해시 보고.

## §7 Phase 2 준비물 제작 (집행 아님 — launchctl 실행 절대 금지)
1. scripts/ops/launchd/com.stockvis.neo4j.plist 초안 작성·커밋:
   Label=com.stockvis.neo4j / ProgramArguments=[~/neo4j/bin/neo4j, console] /
   EnvironmentVariables에 JAVA_HOME=/opt/homebrew/opt/openjdk@21 **필수 명기** /
   KeepAlive=true / RunAtLoad=true / StandardOut·ErrorPath 로그 지정 / 절대경로 사용.
2. plutil -lint로 문법 검증 결과 출력.
3. 설치 runbook(병진 수동 3줄: 죽은 homebrew.mxcl.neo4j 엔트리 처리 후보 보고 포함 — 파일
   제거·bootout·bootstrap 자체는 병진)을 plist와 같은 위치에 커밋. 현행 수동 기동 프로세스와의
   교대 절차(중복 기동 방지: 기존 pid 확인→정지→bootstrap 순서) 포함.

## §8 종료 보고 + HALT
- 게이트 판정표(§2·§3) / 전 커밋 해시 / push 착지 해시 / dirty 최종 잔량 /
  브랜치·worktree 정리 후보 목록(삭제 금지, 보고만) / 병진 수동 잔여(=P2 runbook 3줄, SMTP
  로테이션)를 명시하고 HALT. 이 작업들 전부 진행해줘. 내가 승인한거야.
