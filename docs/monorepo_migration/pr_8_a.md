PR8a 진입 — services/ 5앱 순차 이동 (옵션2: 3그룹, 1 PR, 그룹별 풀 회귀)

[전제] STEP 0 완료: rename 0·순환의존 0·공유유틸 0·실존 5/5. 규모 ~1100~1200건
(정적 779 + 동적 260). ★동적 mock.patch 260건 = 핵심 리스크(자동 sweep 사각).
순차 3그룹: 1차 독립 3앱 → 2차 news → 3차 serverless. PR은 1개, 그룹별 커밋.

[프롬프트 자체 확인]
① main HEAD = 3b74782 확인 (plan 정합화 커밋. 다르면 STOP·보고)
② tag monorepo-pre-pr8 존재 확인 (롤백 지점)
③ git status clean 확인 (더러우면 STOP)
④ 답습: 부록 A 8건 + PR3·4·7 학습 (regex import / Django label 보존 /
동적 import 추적 / 환경fail 분리 / fixture 보호) 로드
⑤ #29 MERGED 확인 (gh pr view 29). OPEN이면 보고 후 진행 무방

──────────────────────────────────────────────
STEP 1 — pre-cleanup (ruff format 사전 분리, 답습)

- 5앱 대상 ruff format 먼저 단독 커밋

──────────────────────────────────────────────
■ 그룹 1차 — rag_analysis + validation + sec_pipeline (독립, 패턴 검증)
──────────────────────────────────────────────
STEP 2-1 — mv 1차 3앱 → services/

- git mv rag_analysis services/rag_analysis
- git mv validation services/validation
- git mv sec_pipeline services/sec_pipeline
- 백엔드만. frontend 자산 있으면 범위 밖(B-3 답습)

STEP 3-1 — 정적 import 재작성 (regex 답습, ast-grep 금지)

- regex dotted-path: <app> -> services.<app> (3앱)
  rag_analysis -> services.rag_analysis (정적 40)
  validation -> services.validation (정적 68)
  sec_pipeline -> services.sec_pipeline (정적 252)

STEP 3-1b — ★ 동적 import 수동 점검 (핵심, 자동 sweep 사각)

- mock.patch 문자열 경로 grep (3앱):
  grep -rn "mock.patch\|patch(" tests/ --include=\*.py | grep -E "rag_analysis|validation|sec_pipeline"
- patch("rag_analysis.xxx") -> patch("services.rag_analysis.xxx") 형태 전수 갱신
  (1차 동적 추정: rag 36 + validation 0 + sec_pipeline 72 = ~108건)
- importlib / **import** 문자열 경로도 grep
- ★ 갱신 후 grep으로 구 경로 잔존 0 재확인 (누락 탐지)

STEP 4-1 — Django 패치 + label 명시 (3앱)

- INSTALLED_APPS dotted-path: services.<app>
- AppConfig.name = "services.<app>"
- ★ AppConfig.label = "<app>" 명시 추가 (자동추론 동일, 답습 일관성 +
  migration to= 보존: rag 5+ / sec_pipeline 3+ / validation 0)
- lazy ref: sec_pipeline 1건 점검
- Celery task name: rag 9 / validation 1 / sec_pipeline 3 점검

STEP 5-1 — ★ 1차 풀 회귀 (그룹 검증 = 옵션2 핵심)

- pytest 풀 회귀 → PR7 baseline 3172/52 델타 0 = PASS
- 신규 fail → main(3b74782)에서 동일 재현 대조 (환경 vs 진짜, PR4 학습4)
  · main 미재현 = 진짜 회귀 → ★ 1차 3앱 범위 안에서만 디버깅 (옵션2 효익)
- Django check + makemigrations(0, label 보존) + ruff 델타 확인
- 커밋: "PR8a-1: mv rag_analysis+validation+sec_pipeline -> services/"

──────────────────────────────────────────────
■ 그룹 2차 — news (rag_analysis 의존)
──────────────────────────────────────────────
STEP 2-2 — mv news → services/news (1차 패턴 답습)
STEP 3-2 — 정적 재작성 news -> services.news (정적 197)
★ news → rag_analysis 의존 1건: 1차에서 services.rag_analysis로 이동됐으니
news 내부의 rag_analysis import도 services.rag_analysis로 갱신 확인
STEP 3-2b — 동적 점검 (news mock.patch 89건) — 1차 STEP 3-1b 패턴 답습
STEP 4-2 — Django + label='news' (migration to= 2 / lazy ref 8 / Celery 38)
★ lazy ref 8건 = 5앱 중 최다, 문자열 "news.X" 형태 전수 점검
STEP 5-2 — ★ 2차 풀 회귀 (델타 0 + fail시 news 범위 디버깅)

- 커밋: "PR8a-2: mv news -> services/"

──────────────────────────────────────────────
■ 그룹 3차 — serverless (news + rag_analysis 의존)
──────────────────────────────────────────────
STEP 2-3 — mv serverless → services/serverless
STEP 3-3 — 정적 재작성 serverless -> services.serverless (정적 222)
★ serverless → news 1 + rag 1 의존: 둘 다 이미 services/로 이동됨,
serverless 내부 import를 services.news / services.rag_analysis로 갱신 확인
STEP 3-3b — 동적 점검 (serverless mock.patch 63건) — 패턴 답습
STEP 4-3 — Django + label='serverless' (migration to= 4+ / Celery 13)
STEP 5-3 — ★ 3차 풀 회귀 (델타 0 + fail시 serverless 범위)

- 커밋: "PR8a-3: mv serverless -> services/"

──────────────────────────────────────────────
STEP 6 — 통합 최종 검증 (3그룹 누적)

1. pytest 풀 회귀 — 3172/52 델타 0 최종 확인
2. ★ 동적 경로 전수 재확인: 구 경로(rag_analysis/validation/sec_pipeline/
   news/serverless 평면) import·patch 잔존 0건 grep (중간보고형 검산)
3. Django check + makemigrations --dry-run(0) PASS
4. ruff 델타 0 (main 1010 기준)
5. health_check.py 6✅/0⚠/1❌ 평행. ❌ 격상 → HALT
6. INSTALLED_APPS 5앱 전부 services.\* dotted-path 확인

STEP 7 — 문서 갱신

- DECISIONS: PR8a = 5앱 services/ 이동, label 5건 명시, 순차3그룹, 동적260
  처리 박음 + SHA
- PROGRESS 갱신 (PR8a 완료, 루트 잔존 = macro+thesis만)

STEP 8 — 마감

- tag monorepo-pre-pr8b 박음 (PR8b 롤백 지점)
- PR 생성 → ff-only push (PR1~7 일관) → 머지 후
  monorepo/pr8a-services 브랜치 원격·로컬 삭제
- pytest 최종 + 동적 잔존 0 박음

──────────────────────────────────────────────
HALT 트리거 (정지·보고):

1. 각 그룹 STEP 5에서 신규 fail이 main 미재현 (진짜 회귀) → 그룹 범위 보고
2. STEP 3b 동적 경로 갱신 후 구 경로 잔존 (누락) → 보고
3. STEP 6-2 통합 동적 재확인서 구 경로 발견 → 보고
4. makemigrations 신규 migration 생성 (label 보존 실패) → HALT
5. health_check ❌ 신규 격상 → HALT
6. classifier 광범위 sweep 차단 → fail 파일 한정 manual sweep 우회
   (PR2 동적 import sweep 교훈 — zsh escape 이슈 시 fail 한정)
7. reset --hard 시 untracked 폐기 주의 (PR2 pr_2.md 사고 답습 방지)
   ──────────────────────────────────────────────
