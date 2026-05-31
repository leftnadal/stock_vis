PR6 진입 — chainsight → apps/chain_sight/ 이관 (snake_case rename, PR5 결번)

[프롬프트 자체 확인] 시작 전 점검:
① main HEAD = c3982c9 확인 (아니면 STOP·보고)
② tag monorepo-pre-pr5 존재 확인 (롤백 지점, PR4에서 박음)
③ 답습 자산 = DECISIONS 부록 A 8건 (regex import + Django 패치 + .gitignore)

- PR3 신규 4건 + PR4 신규 4건 (fact-check 강제 / trigger 보류 /
  AppConfig.label history 보존 / 환경fail 분리) 로드
  ④ #27 MERGED 확인 (gh pr view 27 --json state). OPEN이면 보고 후 진행 무방

──────────────────────────────────────────────
STEP 0 — fact-check: chainsight 실존 + rename + active/dormant + 외부결합 + frontend
[사용자 사전정보: chainsight(1단어) → apps/chain_sight/ snake_case rename.
PR4 market_pulse 패턴. 단, 코드로 재확인 (dashboard 유령 + circuit_breaker 교훈)]
0-A 실존 확인: - find . -type d -name "chainsight" -o -name "chain_sight" - 실존 X → HALT·보고 (유령 가능성, 재결정) - 실 디렉토리명 콘솔에 박음 (chainsight 확인)
0-B active/dormant 판정: - grep INSTALLED_APPS / grep -rn "chainsight" --include=\*.py - 등록 O 또는 실호출 O → active → target = apps/chain_sight/ - 둘 다 X → dormant → target = apps/\_dormant/chain_sight/ - 모호 → HALT·보고
0-C 외부 결합 조사 (PR4 circuit_breaker 답습): - chainsight를 apps 밖(rag_analysis·serverless·기타)에서 import하는 호출처 카운트 - 공유 유틸 성격 파일 발견 시 → 이번 PR 범위 밖, packages/shared 승격 후보로
콘솔에 박고 이연 (mv 대상에서 제외, circuit_breaker와 동일 처리)
0-D 보호 케이스 사전 식별 (PR4 학습 3 — rename history 보존): - migration to="chainsight.X" 참조 grep - model lazy ref ("chainsight.Model") grep - Celery task name 등 4-seg 문자열에 chainsight 포함분 grep - 발견분을 콘솔에 박음 → STEP 4에서 label='chainsight' 유지로 일괄 보존
0-E frontend 분리 (B-3 답습): - chain_sight 관련 Next.js/frontend 자산 존재 시 → 이번 PR 범위 밖, 백엔드만 이동
0-F 판정 결과 종합 박고 STEP 1 진행

STEP 1 — pre-cleanup (ruff format 사전 분리, PR1·PR4 교훈)

- ruff format 먼저 단독 커밋

STEP 2 — mv chainsight → STEP 0 확정 target (snake_case rename)

- git mv chainsight apps/chain_sight (히스토리 보존, 백엔드만)
- 커밋: "PR6: mv chainsight -> apps/chain_sight"

STEP 3 — import 재작성 (regex 답습, ast-grep 금지)

- regex dotted-path: chainsight -> apps.chain_sight
- --maxfail 단계적 풀 회귀로 동적 import 추적 (PR2 교훈)
- 동적 import 발견 → HALT·보고

STEP 4 — Django 패치 + rename history 보존 (PR4 핵심 학습 3)

- INSTALLED_APPS dotted-path: apps.chain_sight
- AppConfig.name = "apps.chain_sight"
- ★ AppConfig.label = "chainsight" 유지 (rename에도 app_label 불변 →
  STEP 0-D 보호 케이스 일괄 보존: migration to= / lazy ref / task name)
- urls.py URL 등록 경로 갱신
- ast-grep 미커버 3종 manual 점검

STEP 5 — .gitignore 사전 점검 (부록 A)

STEP 6 — 검증 5단계

1. pytest 풀 회귀 — PR4 baseline과 비교. 회귀 0 = PASS.
   ★ 환경/날짜 fail 분리 (PR4 학습 4): 신규 fail 발견 시 main(c3982c9)에서
   동일 fail 재현되는지 즉시 대조. main 동일 → PR6 무관. main 미재현 → 진짜 회귀, HALT
2. Django check PASS
3. makemigrations --dry-run PASS (★ label 보존으로 신규 migration 0 이어야 함.
   migration 생성되면 → label 보존 실패 신호, HALT·보고)
4. ruff 델타 0
5. health_check.py → 6✅/0⚠/1❌ 평행. ❌ 신규 격상 → HALT·보고

STEP 7 — 문서 갱신

- DECISIONS: PR6 = chainsight → apps/chain_sight rename, label 보존 박음 + SHA
- 외부결합 이연분(STEP 0-C 발견 시) packages/shared 후보로 등록
- PROGRESS 갱신

STEP 8 — (PR4와 달리 보류 마킹 불필요 — chain_sight는 실존, 유령 아님)

- STEP 7에 통합, 별도 작업 없음

STEP 9 — 마감

- tag monorepo-pre-pr7 박음 (다음 롤백 지점. PR5 결번이므로 pr6 다음은 pr7)
- PR 생성 → ff-only push (PR1~4 일관) → 머지 후
  monorepo/pr6-chain-sight 브랜치 원격·로컬 삭제
- pytest 최종 수치 박음 (+ 환경fail 7건이 여전히 동일한지 확인)

──────────────────────────────────────────────
HALT 트리거 (정지·보고):

1. STEP 0-A chainsight 실존 부재
2. STEP 0-B active/dormant 모호
3. STEP 3 동적 import 발견
4. STEP 6-1 신규 fail이 main 미재현 (진짜 회귀)
5. STEP 6-3 makemigrations가 신규 migration 생성 (label 보존 실패)
6. STEP 6-5 health_check ❌ 신규 격상
7. classifier 광범위 sweep 차단 → fail 파일 한정 manual sweep 우회
8. reset --hard 시 untracked 폐기 주의 (PR2 pr_2.md 사고 답습 방지)
   ──────────────────────────────────────────────
