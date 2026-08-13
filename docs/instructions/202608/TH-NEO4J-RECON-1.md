# TH-NEO4J-RECON-1 — Neo4j 다운 read-only 정찰 (원샷 지시서)

- 발행: 2026-08-13 (디렉터 세션). 0번째 게이트는 이번에 한해 디렉터 유예 —
  대신 §0-0에서 본 문서를 세션 브랜치에 즉시 커밋해 감사 흔적을 확보한다.
- 선행 결정: 후보 3안 가중합 NEO4J 4.45 / Q19 2.85 / EXPOSURE 2.30, 마진 1.60 > 1.00 자동 결정.
- 독립성: G-sunmon(08-17)·TH 라이브 파이프라인과 무접촉. 라이브 자동화 트리(origin/main 추적 라이브 트리) 접근 금지.

## 세션 계약
- 종류: read-only 정찰. HALT-0 기본 적용 — HALT 해제는 디렉터 전권.
- worktree: 신규 `monorepo/sess-neo4j-recon` 생성. 기존 worktree 무접촉.
- 허용된 쓰기 = 딱 두 파일의 세션 브랜치 커밋: ① 본 지시서 사본 ② §3 보고서.
  파일 명시 add만 (`git add -A` 금지). push 전면 금지(D-PUSH-DELEG: "푸시" 명시어 없음).
- 그 외 전면 금지: DB 쓰기 / launchctl·서비스 조작(조회 포함 — 명령문 상신만) / 브랜치·worktree 삭제.
- 시간 판정 = machine clock만. 대형·장기 명령 = foreground 전용.
- 시크릿: shell 파이프 마스킹 금지, Python len/head[:4]만.

## §0 부트스트랩 + 통상 실측 (baseline 이월 금지 — 전부 재측정)
0. worktree 생성 직후, 본 지시서 전문을 `docs/instructions/202608/TH-NEO4J-RECON-1.md`에
   저장하고 단독 커밋한다 (메시지: "docs(instructions): TH-NEO4J-RECON-1 directive (session-committed, gate waived by director)").
   커밋 해시를 즉시 출력한다.
1. machine clock (`date -u`, `date`)
2. `git worktree list` / `git fetch origin` 후 origin/main HEAD 기록
3. `scripts/health_check.py` 결과
4. `docs/reports/` 기존 경로 규약 확인 → §3 보고서 경로 확정 (없으면 `docs/reports/202608/`)
5. 위 결과를 세션 계약 헤더에 기입

## §1 다운 진단
1. **다운 시작 시점 확정**: heat 계열 로그에서 Neo4j connection refused/failure 최초 발생 시각 역추적.
   "≤08-03"은 미검증 추정 — 실측값으로 대체, 근거 로그 경로·라인 인용.
2. **launchd 등재 여부**: launchctl은 실행하지 않는다. 병진 수동 실행용 명령문
   (`launchctl list | grep -i neo4j` 등)과 출력 판독 기준을 §3 절차서에 포함.
3. **원인 후보 좁히기**: 프로세스 부재 vs 기동 실패 반복 vs 포트/설정 문제.
   Neo4j 설치 경로·conf에서 log dir 확인 후 read-only 열람. 마지막 정상 기동/종료 기록 인용.
4. **데이터 안전 실측**: 데이터 디렉토리 실존·최근 수정 시각·크기(du).
   유실/손상 정황 발견 시 절차서 작성보다 즉시 HALT + 상신이 우선.

## §2 의존 지도
1. Neo4j 참조 코드 전수 grep (bolt / 7687 / neo4j driver / 설정 키).
   소비처 목록화: heat 5개 섹터 경로 / Chain Sight 조회 / nightly / 기타.
   각 소비처의 다운 기간 열화 양태(예외 삼킴·부분 계산·전체 실패)를 코드+로그로 판정.
2. **Q19 분리 실측**: co-mention 단절 시작(04-25~)과 Neo4j 다운 시작 시각 비교 → 별개 사안임을 실측 고정.
   동일 원인 정황이 나오면 병합 추정하지 말고 정황 자체를 상신.

## §3 상신 (HALT로 종료)
보고서: §0-4 확정 경로에 `TH-NEO4J-RECON-1-report.md` 세션 브랜치 커밋 (push 금지).
1. §1·§2 전 실측 결과 — 모든 수치·시각에 근거 명령/로그 경로 병기
2. **복구 절차서 초안 (병진 수동 실행용)**: 기동 명령 후보 / 기동 후 검증 체크리스트
   ① bolt 7687 응답 확인법 ② 다음 heat 발화(22:00 UTC) 11/11 섹터 복원 확인법 ③ 실패 시 판단 기준
3. 조치 선택지 골격: (a) 단순 재기동 충분 vs (b) 재발 방지 설계 필요 — 근거만, 결정은 디렉터.
지시서 커밋 해시(§0-0) + 보고서 커밋 해시를 세션 출력 말미에 명시 → HALT.

## 즉시 HALT 트리거
- 데이터 디렉토리 유실/손상 정황
- read-only 범위를 넘어야 진단 가능한 상황
- 라이브 자동화 트리 접촉이 불가피한 상황
