# Stock-Vis 야간 자동화 — 실행 프롬프트 v3

> Claude Code에서 순서대로 실행
> 리포트 경로: docs/nightly_auto_system/YYYYMM/DD/

---

## 0단계: 사전 준비

### 0-1. 상태 확인

```
Stock-Vis 프로젝트 현재 상태 확인.

1. git status && git branch --show-current
2. pytest tests/ -q --tb=line 2>&1 | tail -5
3. cd frontend && npx tsc --noEmit 2>&1 | tail -5
4. cat frontend/package.json | grep -E "vitest|testing-library" || echo "FE 테스트 인프라 미설치"
5. command -v codex && echo "Codex 설치됨" || echo "Codex 미설치"
6. ls docs/nightly_auto_system/ 2>/dev/null && echo "리포트 디렉토리 있음" || echo "리포트 디렉토리 없음"

결과를 요약 테이블로 보여줘.
```

### 0-2. FE 테스트 인프라 설치 (수동, 1회만)

```
frontend/에 Vitest + React Testing Library 설치해.

1. cd frontend
2. npm i -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
3. vitest.config.ts 생성 (environment: jsdom, globals: true, alias '@' 설정)
4. vitest.setup.ts 생성 (import '@testing-library/jest-dom')
5. package.json scripts에 "test": "vitest run" 추가
6. npx vitest run 으로 확인 (테스트 0개여도 에러 없으면 OK)
7. git add -A && git commit -m "chore(frontend): Vitest + RTL 테스트 인프라 설치"
```

---

## 1단계: Tier 1 즉시 수정

### 1-1. Tier 1 스크립트 생성 + 실행

```
아래 4개 작업을 순차 실행하는 bash 스크립트 ~/stock-vis-nightly/run_tier1.sh 생성해.

작업 1: TS 컴파일 에러 수정
- 브랜치: fix/ts-compile-errors
- 대상 파일 구조 먼저 확인: find frontend/lib/thesis/ frontend/components/news/ -name "*.ts" -o -name "*.tsx"
- mock.ts에 누락 필드 추가, NewsCard.tsx null 처리
- 검증: npx tsc --noEmit 에러 0
- 커밋: "fix(frontend): TS 컴파일 에러 수정"

작업 2: 깨진 테스트 수정
- 브랜치: fix/broken-tests
- 대상 파일 구조 먼저 확인: find tests/news/ tests/serverless/ -name "*.py"
- 소스 변경 최소화, 테스트를 현재 구현에 맞게 수정
- 검증: pytest 해당 파일 -v
- 커밋: "fix(tests): 깨진 테스트 5건 수정"

작업 7: FE 타입 안전성
- 브랜치: fix/fe-type-safety
- npx tsc --noEmit 에러 전부 수정
- 검증: exit code 0
- 커밋: "fix(frontend): strict null 위반 일괄 수정"

작업 8: Dead code 정리
- 브랜치: chore/dead-code-cleanup
- 대상 앱 파일 구조 먼저 확인: find validation/ chainsight/ sec_pipeline/ thesis/ macro/ -name "*.py" | head -50
- __all__ / re-export 확인 필수
- 검증: pytest tests/ -x -q
- 커밋: "chore(backend): unused import 정리"

각 작업은 새 브랜치에서 실행, 완료 후 원래 브랜치 복귀.
브랜치 이미 존재하면 스킵.
마지막에 브랜치 목록 + 커밋 수 요약.
chmod +x 도 해줘.
```

---

## 2단계: Tier 2 테스트 작성

### 2-1. BE 테스트 스크립트

```
아래 4개 BE 테스트 작성을 순차 실행하는 ~/stock-vis-nightly/run_tier2_be.sh 생성해.

모든 작업에서: 대상 앱의 실제 파일 구조를 먼저 확인해.
find [앱경로]/ -name "*.py" -not -path "*__pycache__*" | head -30
파악한 실제 파일/클래스/함수 기반으로 테스트 작성.
마이그레이션 절대 실행 금지.

작업 3: validation (0→40개) — 브랜치: test/validation-unit-tests
작업 4: sec_pipeline (0→30개) — 브랜치: test/sec-pipeline-tests
작업 5: users (0→25개) — 브랜치: test/users-unit-tests
작업 13: rag_analysis (0→35개) — 브랜치: test/rag-analysis-unit-tests
  Neo4j import 0인 파일만 (cache, context, entity_extractor, context_compressor)
  from neo4j import 금지

패턴: pytest 클래스, @pytest.mark.django_db, 외부 API mock.
마지막에 브랜치별 테스트 수 요약.
```

### 2-2. FE 테스트 스크립트

```
아래 2개 FE 테스트 작성을 순차 실행하는 ~/stock-vis-nightly/run_tier2_fe.sh 생성해.

선행 확인: cd frontend && npx vitest --version (미설치면 중단)

작업 11: thesis 컴포넌트 (0→15개) — 브랜치: test/fe-thesis-components
  대상 파일 먼저 확인: find frontend/components/thesis/dashboard/ -name "*.tsx"
  컴포넌트당 최소 3개 (렌더링, 인터랙션, 엣지케이스)

작업 12: validation+chainsight (0→18개) — 브랜치: test/fe-validation-chainsight
  대상 파일 먼저 확인: find frontend/components/validation/ frontend/components/chainsight/ -name "*.tsx"
  컴포넌트당 최소 3개

Vitest + RTL. API 호출은 vi.mock().
마지막에 총 FE 테스트 수 요약.
```

---

## 3단계: Tier 3 감사 보고서

### 3-1. 감사 일괄 실행

```
아래 7개 감사를 순차 실행하는 ~/stock-vis-nightly/run_tier3_audits.sh 생성해.

모든 작업은 읽기 전용 — 코드 수정 절대 금지.
결과는 docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/ 에 저장.
mkdir -p 로 디렉토리 먼저 생성.

작업 15: performance_audit.md — N+1, 인덱스, Serializer, 페이지네이션
작업 16: security_audit.md — OWASP Top 10 + LLM Top 10
작업 17: api_dependency_audit.md — FMP/Gemini/FRED/Neo4j 장애 대응
작업 14: data_integrity_audit.md — FK orphan, CASCADE, Neo4j↔PG
작업 6: beat_schedule_audit.md — 63개 태스크 시간 충돌
작업 20: api_docs_audit.md — drf-spectacular 현황
작업 10: indicator_catalog_audit.md — 3곳 동기화

각 작업을 claude -p --model sonnet --permission-mode auto 로 실행.
완료 후: git add docs/nightly_auto_system/ && git commit -m "docs(nightly): 초기 감사 보고서 7건"
마지막에 생성 문서 목록 + 줄 수 요약.
```

---

## 4단계: 야간 시스템 설치

### 4-1. 설치 + crontab

```
야간 자동화 v3을 설치해.

1. mkdir -p ~/stock-vis-nightly/{work,logs}
2. mkdir -p docs/nightly_auto_system/
3. nightly_v3.sh 상단 PROJECT_DIR 확인
4. chmod +x ~/stock-vis-nightly/*.sh
5. crontab -l 확인 → stock-vis 항목 없으면 추가:
   0 23 * * * PATH=... ~/stock-vis-nightly/nightly_v3.sh >> ~/stock-vis-nightly/logs/cron.log 2>&1
   0  8 * * * PATH=... ~/stock-vis-nightly/morning_notify.sh >> ~/stock-vis-nightly/logs/cron_morning.log 2>&1
6. pmset -g | grep sleep 확인
7. 상태 요약 출력
```

### 4-2. 테스트 실행

```
nightly_v3.sh를 테스트로 한번 실행해봐.

실행 후 확인:
1. docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/ 에 파일 생성됐는지
2. morning_report.md 내용 미리보기
3. nightly/auto-fix-날짜 브랜치 생성 여부
4. 로그에 에러 있는지

문제 있으면 nightly_v3.sh 수정 제안해.
```

---

## 5단계: 설계서 갭 분석

### 5-1. Chain Sight (가장 중요)

```
docs/chain_sight/plan/ 설계 문서를 모두 읽고 chainsight/ 코드와 대조해.
코드 수정 없이 분석만.

분류: (A)완전구현 (B)부분구현 (C)미구현 (D)폐기
특히: redesign_v1이 기존 cs_* 대체하는지, 3-tier 증거, 5-stage 상태, ForceGraph2D
task_done/*.md와 cross-reference.

결과를 docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/design_gap_chainsight.md 에 저장.
```

### 5-2. Thesis Control

```
docs/thesis_control/ 설계 문서를 읽고 thesis/ + frontend/components/thesis/ 대조.
Layer A~E, Stage 0, moon-phase, LLM 원샷, Perspective Balance.

결과를 docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/design_gap_thesis.md 에 저장.
```

### 5-3. SEC Pipeline + 나머지

```
docs/sec_pipeline/, docs/first_validation_system/, docs/news/ 설계 문서 대조.
Track A/B, Gold Set, 34개 지표, size bucket peer.

결과를 docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/design_gap_remaining.md 에 저장.
```

---

## 6단계: 운영 중 유용한 프롬프트

### 6-1. 아침 리포트 빠른 확인

```
오늘 아침 리포트를 읽고 핵심 3줄로 요약해.
cat docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/morning_report.md

요약: 1. 상태 2. 즉시 할 일 3. 머지 여부 (SAFE/CAUTION/BLOCK)
```

### 6-2. 감사 기반 수정

```
docs/nightly_auto_system/[YYYYMM]/[DD]/[감사 파일].md 를 읽고
HIGH 등급 이슈만 수정해.

브랜치: fix/audit-high-issues
수정마다 개별 커밋. 검증: pytest tests/ -x -q
```

### 6-3. 주간 진행상황

```
docs/nightly_auto_system/$(date +%Y%m)/ 아래 이번 주 폴더들을 읽고
주간 진행상황 요약해.

1. 매일 코드 상태 추세
2. 자동 수정 내역
3. 심층 분석 핵심 발견
4. 기준선 대비 이슈 증감
5. 다음 주 TOP 3
```

### 6-4. 날짜별 리포트 비교

```
두 날짜의 같은 감사를 비교해.

diff docs/nightly_auto_system/[YYYYMM]/[DD1]/[감사].md \
     docs/nightly_auto_system/[YYYYMM]/[DD2]/[감사].md

핵심 변화를 3줄로 요약해.
```

---

## 실행 순서 요약

```
오늘:
  0-1  상태 확인                              5분
  0-2  FE 테스트 인프라 수동 설치              5분

오늘 밤 (tmux):
  tmux new -s tonight
  1-1  Tier 1 즉시 수정                       ~45분
  2-1  Tier 2 BE 테스트                       ~100분
  2-2  Tier 2 FE 테스트                       ~45분
  3-1  Tier 3 감사 보고서                     ~105분
  # Ctrl+B, D 로 빠져나오기                   총 ~5시간

내일 아침:
  결과 확인 → 브랜치별 머지
  ls docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/

내일:
  4-1  야간 시스템 crontab 등록               10분
  4-2  테스트 실행                             확인만
  5-1~3 설계서 갭 분석                        ~45분

그 다음부터:
  매일 23:00 자동 → 08:00 리포트
  docs/nightly_auto_system/YYYYMM/DD/ 에 매일 축적
```
