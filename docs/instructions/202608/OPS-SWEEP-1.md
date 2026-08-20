# OPS-SWEEP-1 — NEO4J 사건 사후 위생·SMTP 복구·차기 확인 (원샷 지시서)

- 발행: 2026-08-20 (디렉터). 0번째 게이트 디렉터 유예 — §0-0 자기 커밋으로 감사 흔적 확보.
- 위임 근거 (명시 인용): 병진 지시 "나머지 잔여는 전부 지시서로 해결할수 있도록 해줘."
  (2026-08-20) — 문서 커밋·TASKQUEUE 갱신·push를 CC 집행으로 위임한다.
- 위임 불가 유지 (규약): ①launchctl·서비스 조작 실행 ②브랜치·worktree·파일 삭제
  (D-BRANCH-DELETE-MANUAL 영구 유보) ③시크릿 값 취급. 본 지시서는 이들을 "검증된 명령
  블록 상신 + 병진 개입 지점 명시"로 처리한다.

## 세션 계약
- worktree: 신규 monorepo/sess-ops-sweep.
- **~/Desktop/stock_vis 접촉 금지** — 타 세션 브랜치(sess-signal-fwd-recon) 점유 중.
  checkout·pull·머지 일절 금지, read-only 관찰만.
- 허용 쓰기: 세션 브랜치 커밋(지시서 사본·runbook 보강·addendum 추기·TASKQUEUE) + §6 push.
- 금지: launchctl 실행 / 삭제류 / 시크릿 값 출력(len·head[:4]만 허용) / .env 수정 /
  git add -A / heat 소급.
- HALT-0 기본·machine clock only·foreground 전용·2분 트런케이션 유의(#88).

## §0 부트스트랩
0. 본 지시서 전문을 docs/instructions/202608/OPS-SWEEP-1.md로 저장·단독 커밋·해시 출력.
1. clock / git fetch / health_check + ~/Desktop/stock_vis의 브랜치·dirty 상태 read-only
   기록(관찰만, 조치 금지).

## §1 runbook 보강 커밋 (P2 설치에서 드러난 결손 반영)
scripts/ops/launchd/NEO4J-RESTORE-P2-runbook.md 수정:
1. 선결 0단계로 `mkdir -p ~/Library/Logs/stockvis` 추가 + 사유 주석(launchd는 로그
   디렉토리를 생성하지 않음 — 부재 시 무기록 침묵 사망 재현).
2. "운영 규칙" 절 신설: 설치 후 의도적 정지는 `neo4j stop`이 아니라
   `launchctl bootout gui/$(id -u)/com.stockvis.neo4j` (KeepAlive가 stop을 30초 내
   무효화). 재개는 bootstrap. 임시 정지 후 재개 예시 병기.
3. "소스 정본" 주석: plist·runbook은 origin/main에 영구 존재 — worktree 소멸과 무관,
   재설치 시 main 체크아웃 어디서든 cp 가능.

## §2 addendum 추기 커밋 (docs/reports/202608/TH-NEO4J-RECON-1-report.md)
- P2 설치 완료: 2026-08-20 08:14 UTC Started·launchd status 0·bolt LISTEN·.env 인증 통과·
  죽은 homebrew.mxcl.neo4j 엔트리 제거.
- 그래프 규모 변화 기재: NODE 1181→1084·REL 17699→18916. 레거시 정리 로그로 노드
  감소분이 설명되는지 1줄 실측(read-only) — 설명되면 원인 명기, 불명이면 관찰로만 기재
  (추정 확정 금지).
- 관찰: ~/Desktop/stock_vis가 sess-signal-fwd-recon 점유 중(worktree-per-세션 규율
  관찰 사항, 해당 트랙 소유라 본 세션은 무조치).

## §3 위생 명령 상신 (CC 실행 금지 — 병진 `!` 실행용 블록 제작)
사전 검증(read-only): worktree 경로 실존 / origin/main..monorepo/sess-neo4j-recon = 0
재확인 / 홈 헬퍼 파일 실존 목록. 검증 결과와 함께 최종 보고에 아래 블록 제시:
  git -C <본세션 worktree 경로> worktree remove ~/worktrees/sv-neo4j-recon
  git -C <본세션 worktree 경로> branch -d monorepo/sess-neo4j-recon
  rm -f ~/setpw.sh ~/alter.sh ~/.neo4j/.cypher_shell_history
- `-d` 거부 예상 시(HEAD:main 직push는 upstream 무설정 — common-bugs 기존 패턴)
  `--set-upstream-to=origin/main` 선행 명령을 병기. `-D` 금지 명기.

## §4 SMTP 복구 (OPS-SMTP-CRED — 개입 지점 최소화 설계)
1. 실측(read-only): 리포트 발송 코드가 읽는 SMTP 설정 키 전수(.env 변수명·호스트·포트·
   계정 식별 — 값은 len/head만), 그리고 리포트 태스크를 소화하는 워커가 어느 것인지
   (기본 워커 vs 별도 큐) 확정 → 재기동 최소 대상 판정.
2. 병진 개입 A 안내문 작성: ①Google 계정에서 앱 비밀번호 신규 발급(브라우저 — 사람만
   가능) ②.env의 <실측된 키>를 새 값으로 교체(에디터 직접 수정, **표시되는 4×4 공백
   제거** 유의, 클립보드 히스토리 앱 사용 시 항목 삭제 권고).
3. 병진 "교체 완료" 통보 후: .env 직독 SMTP 로그인 검증 스크립트 실행(smtplib
   login만·발송 0건·값 비노출 len/head 출력). 실패 시 원인 판독 상신.
4. 통과 시 워커 재기동 명령 블록 상신(병진 `!` 실행용, §4-1 실측 기반 최소 대상):
   launchctl bootout + bootstrap 각 1줄. CC 실행 금지.
5. 발송 복구 판정은 §5 시간 게이트에서 통합 수행.

## §5 시간 게이트 (machine clock ≥ 2026-08-20 23:10 UTC 확인 후 진행)
- SignalAccuracy signal_date=2026-08-18 존부 (CLOSE-1 §3 이월분).
- 21:00/22:00 UTC 리포트 발화의 SMTP 결과: 535 소멸·발송 성공 여부 (§4 완료가 전제 —
  미완이면 그 사실만 기재).
- 미도래 시: 여기서 "§5 대기" HALT. 병진의 "§5 재개" 한 마디로 이어서 실행.

## §6 TASKQUEUE 갱신 + push (위임)
- 반영: NEO4J-RESTORE-P2 종결 / OPS-SMTP-CRED 상태 갱신(§4 진행분) / runbook 보강 완료 /
  sess-signal-fwd-recon 점유 관찰 등재 / §5 판정 결과.
- git fetch → behind 확인 → merge origin/main(auto-merge만, docs 외 충돌 시 HALT) →
  push HEAD:main → 착지 해시 보고.

## §7 종료 보고 + HALT
전 커밋·push 해시 / §3 위생 블록(검증 결과 포함) / §4 개입 지점 A 안내문·재기동 블록 /
§5 판정(또는 대기 상태) / 병진 잔여 액션 리스트를 한 표로 정리 → HALT.
