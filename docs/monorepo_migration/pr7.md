PR7 진입 — portfolio → apps/portfolio/ 이관 (STEP 0 위험 0 판정 완료, 풀 회귀)

[전제] STEP 0 완료: IDENTICAL=정적무결성(binary 해시 아님), 거짓양성 위험 0,
외부결합 0, 슬라이스 병행 0, rename 없음. 변환 규모 ~380건(단일 앱 최대).
plan "최고 위험"이나 메커니즘상 PR6 동급 + 규모만 큼.

[프롬프트 자체 확인]
① main HEAD = c25576e 확인 (아니면 STOP·보고)
② tag monorepo-pre-pr7 존재 확인 (롤백 지점)
③ git status clean 재확인 (STEP 0-G 이후 변경 없어야 함. 더러우면 STOP)
④ 답습 자산: 부록 A 8건 + PR3 4건 + PR4 4건 (regex import / Django 패치 /
label 보존 / 환경fail 분리) 로드
⑤ #28 MERGED 확인 (gh pr view 28 --json state). OPEN이면 보고 후 진행 무방

──────────────────────────────────────────────
STEP 1 — pre-cleanup (ruff format 사전 분리, 답습)

- ruff format 먼저 단독 커밋 (scope 외 format 격리)

STEP 2 — mv portfolio → apps/portfolio/ (rename 없음, 위치만)

- git mv portfolio apps/portfolio (히스토리 보존)
- ★ 백엔드 Django 앱만. frontend portfolio 자산 있으면 범위 밖(B-3 답습)
- 커밋: "PR7: mv portfolio -> apps/portfolio"

STEP 3 — import 재작성 (regex 답습, ast-grep 금지, 최대 규모 ~380건)

- regex dotted-path: portfolio -> apps.portfolio
  · portfolio/ 내부 자기참조 340건
  · 외부 tests/ 40건 + scripts/ 일부
  · ready() 내 'from portfolio.api import openapi_extensions' 포함 (0-A 발견)
- ★ --maxfail 단계적 풀 회귀로 동적 import 추적 (PR2 교훈, 규모 크니 특히 주의)
- 동적 import / mock.patch 문자열 경로 발견 시 → 갱신 + 박기, 누락 시 HALT
- 커밋: "PR7: rewrite imports portfolio -> apps.portfolio"

STEP 4 — Django 패치 + label 보존 (PR4/PR6 핵심 답습)

- INSTALLED_APPS: 'portfolio.apps.PortfolioConfig' -> 'apps.portfolio.apps.PortfolioConfig'
- AppConfig.name = "apps.portfolio"
- ★ AppConfig.label = "portfolio" 명시 추가 (0-A: 현재 미명시, 자동추론과
  동일하나 답습 일관성 + 0-F migration to= 11건 보존 보장)
- ★ config/urls.py 2건 갱신 (0-F):
  · include('portfolio.urls') -> include('apps.portfolio.urls')
  · include('apps.portfolio.api.urls', namespace='portfolio_api')
  ※ namespace='portfolio_api' 문자열은 유지 (reverse() 호출 보존)
- ast-grep 미커버 3종 manual 점검

STEP 5 — .gitignore 사전 점검 (부록 A)

STEP 6 — 검증: 풀 회귀 (PR7 = 검증 최강도, plan §⑤)

1. pytest 풀 회귀 — PR6 baseline 3172/52 와 델타 0 = PASS
   · 신규 fail → main(c25576e)에서 동일 재현 대조 (환경 vs 진짜, PR4 학습 4)
   · main 미재현 = 진짜 회귀 → HALT
2. ★ IDENTICAL: pytest portfolio/tests/test_static_integrity.py -v
   → 7+ PASSED 확인 (0-B 기준). import 갱신 정확하면 자동 통과.
   FAIL이면 → import 누락 신호, HALT·보고
3. vitest (frontend 회귀, 있으면)
4. Django check PASS
5. makemigrations --dry-run PASS
   → ★ label='portfolio' 보존으로 신규 migration 0 이어야 함.
   migration 생성되면 = label 보존 실패, HALT·보고
6. ruff 델타 0 (main 1009 기준)
7. health_check.py → 6✅/0⚠/1❌ 평행. ❌ 신규 격상 → HALT
8. (선택) cost_ledger 임계 — portfolio 이동은 LLM 호출 0이라 비용 0,
   임계 영향 없음 확인만

STEP 7 — 문서 갱신

- DECISIONS: PR7 = portfolio -> apps/portfolio, label 보존, namespace 보존,
  IDENTICAL=정적무결성 7/7 박음 + SHA
- PROGRESS 갱신 (PR7 완료, 루트 잔존 7앱 = PR8 대상)
- ★ 신규 학습 후보 박기: "IDENTICAL=정적무결성(binary 해시 아님), import
  재작성과 양립 — plan 위험등급이 메커니즘 미확인 기반이었음" (PR8 답습)

STEP 8 — (보류 마킹 불필요 — portfolio 실존, 유령 아님)

STEP 9 — 마감

- tag monorepo-pre-pr8 박음 (PR8 롤백 지점)
- PR 생성 → ff-only push (PR1~6 일관) → 머지 후
  monorepo/pr7-portfolio 브랜치 원격·로컬 삭제
- pytest 최종 수치 + IDENTICAL 7/7 박음

──────────────────────────────────────────────
HALT 트리거 (정지·보고):

1. STEP 3 동적 import / mock.patch 문자열 경로 누락
2. STEP 6-1 신규 fail이 main 미재현 (진짜 회귀)
3. STEP 6-2 IDENTICAL test_static_integrity FAIL (import 누락)
4. STEP 6-5 makemigrations 신규 migration 생성 (label 보존 실패)
5. STEP 6-7 health_check ❌ 신규 격상
6. classifier 광범위 sweep 차단 → fail 파일 한정 manual sweep 우회
7. reset --hard 시 untracked 폐기 주의 (PR2 pr_2.md 사고 답습 방지)
   ──────────────────────────────────────────────
