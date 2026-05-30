PR4(승계) 진입 — apps/market_pulse 이관 (dashboard 유령 → market_pulse로 대상 교체)

[프롬프트 자체 확인] 시작 전 점검:
① main HEAD = bd4080c 확인 (아니면 STOP·보고)
② tag monorepo-pre-pr4 존재 확인 (롤백 지점, PR3에서 박음)
③ 답습 자산 = DECISIONS 부록 A 8건 (regex import 재변환 + Django 패치 7종

- .gitignore 사전 점검) + PR3 신규 학습 4건 로드

──────────────────────────────────────────────
STEP 0 — fact-check: market_pulse 실존 + active/dormant + frontend 분리 (결정 아님)
[dashboard 유령 사고 직접 답습 — plan/메모리 추정 금지, 코드에서 확인]
0-A 실존 확인 (최우선): - find . -type d -name "market_pulse" -o -name "marketpulse" 등으로 실 디렉토리 확인 - 실존 X → HALT·보고 (dashboard와 동일 유령. C 진행 불가, 재결정 필요) - 실존 O → 실제 경로를 콘솔에 박고 0-B
0-B active/dormant 판정: - grep INSTALLED_APPS 에서 market_pulse 등록 여부 - grep -rn "market_pulse" --include=\*.py 로 실호출/import 추적 - 등록 O 또는 실호출 O → active → target = apps/market_pulse/ - 등록 X 그리고 실호출 X → dormant → target = apps/\_dormant/market_pulse/ - 모호(엇갈림) → HALT·보고
0-C frontend 분리 확인 (PR2 B-3 답습): - market_pulse 관련 Next.js/frontend 코드 존재 여부 확인 - 존재하면 → 이번 PR 범위 밖(백엔드 Django 앱만 이동). 콘솔에 "frontend N건 제외" 박음
0-D 판정 결과 박고 STEP 1 진행

STEP 1 — pre-cleanup (PR1 교훈: ruff format 사전 분리)

- ruff format 먼저 단독 커밋 (scope 외 format 격리)

STEP 2 — mv market_pulse → STEP 0 확정 target

- git mv 로 히스토리 보존 (백엔드 Django 앱만, frontend 제외)
- 커밋: "PR4: mv market_pulse -> apps/"

STEP 3 — import 재작성 (regex 답습, ast-grep 금지)

- PR2 ast-grep 결함(dotted-name single segment 한정) 회피
- regex 기반 dotted-path 재작성: market_pulse -> apps.market_pulse
  (dormant면 apps.\_dormant.market_pulse)
- --maxfail 단계적 풀 회귀로 동적 import 추적 (PR2 교훈)
- 동적 import 발견 시 → HALT·보고

STEP 4 — Django 패치 7종 (부록 A)

- INSTALLED_APPS dotted-path 갱신
- AppConfig.name / label 갱신
- urls.py 등 URL 등록 경로 갱신 (iron_trading 선례: urls+settings 2건 수렴)
- 나머지 ast-grep 미커버 3종 manual 점검

STEP 5 — .gitignore 사전 점검 (부록 A)

- 이관 경로에 ignore 누락/충돌 없는지 확인

STEP 6 — 검증 5단계

1. pytest 풀 회귀 (PR3 baseline 3172/52 와 델타 0 = PASS 기준, 회귀 0건)
2. Django check PASS
3. makemigrations --dry-run PASS (스키마 변경 0)
4. ruff 델타 0 (main 1013 기준)
5. health_check.py → 6✅/0⚠/1❌ 평행 확인. ❌ 신규 격상 → HALT·보고

STEP 7 — dashboard 보류 마킹 (C 원안 포함분)

- execution_plan_v1.md: PR4=dashboard 항목을 "보류 — monorepo 트랙 외,
  신규 생성+코드 분리는 별도 설계. 트리거=독립 배포/모듈 경계 필요 시" 로 마킹
- market_pulse가 PR4 승계임을 plan에 명시 (결번 방지)
- DECISIONS: "dashboard 앱 분리 = monorepo 외 이연(트리거 명시), market_pulse
  PR4 승계" 1건 등록 + 본 PR SHA 박음

STEP 8 — 문서 갱신

- PROGRESS 갱신 (PR4 = market_pulse 이관 완료, dashboard 보류)

STEP 9 — 마감

- tag monorepo-pre-pr5 박음 (PR5 롤백 지점)
- PR 생성 → ff-only push (PR1~3 일관) → 머지 후
  monorepo/pr4-market-pulse 브랜치 원격·로컬 삭제
- pytest 최종 수치 박음

──────────────────────────────────────────────
HALT 트리거 (정지·보고):

1. STEP 0-A market_pulse 실존 부재 (dashboard 유령 재발) → C 재결정 필요
2. STEP 0-B active/dormant 모호
3. STEP 3 동적 import 발견
4. STEP 6 health_check ❌ 신규 격상
5. classifier 광범위 sweep 차단 → fail 파일 한정 manual sweep 우회
6. reset --hard 시 untracked 폐기 주의 (PR2 pr_2.md 사고 답습 방지
   — 폐기 전 untracked 목록 박고 확인)
   ──────────────────────────────────────────────
