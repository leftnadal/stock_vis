# Stock-Vis 야간 자동화 시스템 — 실행 프롬프트 모음

> Claude Code 인터랙티브 세션 또는 `claude -p`에서 사용
> 순서대로 실행하면 됨

---

## 0단계: 사전 준비 프롬프트

### 0-1. 프로젝트 상태 확인 (먼저 실행)

```
Stock-Vis 프로젝트의 현재 상태를 빠르게 확인해줘.

1. git status && git branch --show-current
2. pytest tests/ -q --tb=line 2>&1 | tail -5
3. cd frontend && npx tsc --noEmit 2>&1 | tail -5
4. cat frontend/package.json | grep -E "vitest|testing-library" || echo "FE 테스트 인프라 미설치"
5. command -v codex && echo "Codex 설치됨" || echo "Codex 미설치"
6. ls docs/infra/STOCK_VIS_NIGHTLY_SYSTEM_v2.md 2>/dev/null && echo "야간 시스템 문서 있음" || echo "야간 시스템 문서 없음"

결과를 요약 테이블로 보여줘.
```

### 0-2. FE 테스트 인프라 설치 (수동 — 1회만)

```
frontend/ 에 Vitest + React Testing Library 테스트 인프라를 설치해.

1. cd frontend
2. npm i -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
3. vitest.config.ts 생성:

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['__tests__/**/*.{test,spec}.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
})

4. vitest.setup.ts 생성:

import '@testing-library/jest-dom'

5. npx vitest run --reporter=verbose 으로 설치 확인 (테스트 0개여도 에러 없으면 OK)
6. git add -A && git commit -m "chore(frontend): Vitest + RTL 테스트 인프라 설치"

package.json scripts에 "test": "vitest run" 추가도 해줘.
```

---

## 1단계: Tier 1 즉시 수정 (오늘 밤 바로)

### 1-1. 전체 Tier 1을 한번에 실행하는 스크립트 생성

```
아래 4개 작업을 순차 실행하는 bash 스크립트를 ~/stock-vis-nightly/run_tier1.sh 로 생성해.

작업 1: TS 컴파일 에러 수정
- 브랜치: fix/ts-compile-errors
- frontend/lib/thesis/mock.ts의 MOCK_DASHBOARD 지표 3개에 description: '', recommendation_reason: '' 추가
- frontend/components/news/NewsCard.tsx의 article.image_url null 처리
- 검증: cd frontend && npx tsc --noEmit 에러 0
- 커밋: git add -A && git commit -m "fix(frontend): TS 컴파일 에러 4개 수정"

작업 2: 깨진 테스트 수정
- 브랜치: fix/broken-tests
- tests/news/test_collect_category_news.py FAILED 수정
- tests/serverless/test_keyword_service.py 4건 ERROR 수정
- 원칙: 소스 변경 최소화, 테스트를 현재 구현에 맞게 수정
- 검증: pytest tests/news/test_collect_category_news.py tests/serverless/test_keyword_service.py -v
- 커밋: git add -A && git commit -m "fix(tests): 깨진 테스트 5건 수정"

작업 7: FE 타입 안전성
- 브랜치: fix/fe-type-safety
- npx tsc --noEmit 에러 전부 수정 (null 체크, optional chaining)
- 새 기능 추가 금지
- 검증: npx tsc --noEmit exit code 0
- 커밋: git add -A && git commit -m "fix(frontend): strict null 위반 일괄 수정"

작업 8: Dead code 정리
- 브랜치: chore/dead-code-cleanup
- validation/, chainsight/, sec_pipeline/, thesis/, macro/ 의 unused import 제거
- 삭제 전 __all__ / re-export 확인 필수
- 검증: pytest tests/ -x -q 전체 통과
- 커밋: git add -A && git commit -m "chore(backend): unused import 정리"

각 작업은:
- 원래 브랜치에서 새 브랜치 생성
- claude -p로 실행
- 완료 후 원래 브랜치로 복귀
- 브랜치 이미 존재하면 스킵

스크립트 상단에 PROJECT_DIR="$HOME/stock-vis" 설정.
마지막에 생성된 브랜치 목록 + 커밋 수 요약 출력.

실행 권한도 부여해: chmod +x ~/stock-vis-nightly/run_tier1.sh
```

---

## 2단계: Tier 2 테스트 작성 (1회성)

### 2-1. BE 테스트 일괄 실행 스크립트

```
아래 4개 BE 테스트 작성 작업을 순차 실행하는 bash 스크립트를
~/stock-vis-nightly/run_tier2_be.sh 로 생성해.

작업 3: validation 앱 테스트 (0→40개)
- 브랜치: test/validation-unit-tests
- tests/unit/validation/ 에 생성
- 사전 파악: find validation/services/ -name '*.py' -not -path '*__pycache__*' | head -30
  파악한 실제 파일/클래스/함수를 기반으로 테스트를 작성해.
- 대상 (validation/services/ 하위):
  preset_generator.py, benchmark_calculator.py, metric_calculator.py,
  relative_metrics.py, interpretation.py
- 패턴: pytest 클래스, @pytest.mark.django_db, FMP mock
- 기존 tests/unit/thesis/ 스타일 참조
- 검증: pytest tests/unit/validation/ -v
- 커밋: git add -A && git commit -m "test(validation): 단위 테스트 신규 작성"

작업 4: sec_pipeline 앱 테스트 (0→30개)
- 브랜치: test/sec-pipeline-tests
- tests/unit/sec_pipeline/ 에 생성
- 사전 파악: find sec_pipeline/ -name '*.py' -not -path '*__pycache__*' -not -path '*/migrations/*' | head -30
  파악한 실제 파일/클래스/함수를 기반으로 테스트를 작성해.
  주의: sec_pipeline에는 services/ 서브디렉토리가 없음. 모든 모듈이 루트 레벨에 있음.
- 대상 (sec_pipeline/ 루트 하위):
  collector.py (SEC EDGAR 수집, HTTP mock 필수),
  extractor.py (10-K 텍스트에서 공급망/사업모델 추출),
  normalizer.py (데이터 정규화),
  ticker_matcher.py (회사명→티커 매칭),
  models.py (모델 생성/조회),
  quality_checks.py (품질 검증 로직)
- 검증: pytest tests/unit/sec_pipeline/ -v
- 커밋: git add -A && git commit -m "test(sec_pipeline): 단위 테스트 신규 작성"

작업 5: users 앱 테스트 (0→25개)
- 브랜치: test/users-unit-tests
- tests/unit/users/ 에 생성
- 사전 파악: find users/ -name '*.py' -not -path '*__pycache__*' -not -path '*/migrations/*' | head -30
  파악한 실제 파일/클래스/함수를 기반으로 테스트를 작성해.
- 대상:
  jwt_views.py (JWT login, token refresh, blacklist),
  views.py (Portfolio CRUD: 생성, 조회, 수정, 삭제, 종목 추가/제거),
  serializers.py (시리얼라이저 유효성 검증)
  Watchlist: 추가, 제거, 목록 조회 (기존 tests/unit/test_watchlist.py 스타일 참조)
- APIClient 사용. tests/unit/test_watchlist.py 스타일 참조
- 검증: pytest tests/unit/users/ -v
- 커밋: git add -A && git commit -m "test(users): 단위 테스트 신규 작성"

작업 13: rag_analysis 최소 테스트 (0→35개)
- 브랜치: test/rag-analysis-unit-tests
- tests/unit/rag_analysis/ 에 생성
- 사전 파악: find rag_analysis/services/ -name '*.py' -not -path '*__pycache__*' | head -30
  파악한 파일 중 Neo4j 의존성이 없는 파일만 테스트 대상으로 선정해.
  (neo4j_service.py, graphrag_scorer.py, semantic_cache.py는 제외)
- 대상 (Neo4j 의존성 0인 파일만):
  cache.py, context.py, entity_extractor.py, context_compressor.py
- 절대 금지: from neo4j import, Neo4j 연결 필요한 서비스 테스트
- LLM 호출 mock
- 검증: pytest tests/unit/rag_analysis/ -v
- 커밋: git add -A && git commit -m "test(rag_analysis): Neo4j-free 서비스 단위 테스트"

각 작업은 별도 브랜치에서 실행. 완료 후 원래 브랜치 복귀.
마이그레이션(makemigrations, migrate) 절대 실행 금지.
마지막에 각 브랜치별 테스트 수 요약 출력.
```

### 2-2. FE 테스트 일괄 실행 스크립트

```
아래 2개 FE 테스트 작성 작업을 순차 실행하는 bash 스크립트를
~/stock-vis-nightly/run_tier2_fe.sh 로 생성해.

선행 조건 확인:
- cd frontend && npx vitest --version 으로 Vitest 설치 확인
- 미설치면 에러 메시지 출력하고 중단

작업 11: thesis 컴포넌트 테스트 (0→15개)
- 브랜치: test/fe-thesis-components
- frontend/__tests__/thesis/ 에 생성
- 사전 파악: find frontend/components/thesis/ -name '*.tsx' | head -30
  파악한 실제 컴포넌트 파일을 기반으로 테스트 대상을 선정해.
- 대상 5개 컴포넌트 (실제 존재하는 파일):
  (1) dashboard/IndicatorRow.tsx — 펼침/접힘, 값 포맷팅
  (2) dashboard/RealValueIndicatorCard.tsx — 값/변동률, null 처리
  (3) dashboard/QuarterlySparkline.tsx — 분기 데이터 렌더링
  (4) dashboard/DashboardHeader.tsx — 헤더 렌더링
  (5) list/ThesisListCard.tsx — 카드 렌더링, 상태 표시
- 패턴: render() → screen.getByText/getByRole/fireEvent
- mock 데이터: frontend/lib/thesis/mock.ts 참조
- API 호출: vi.mock()으로 차단
- 각 컴포넌트당 최소 3개 (렌더링, 인터랙션, 엣지케이스)
- 검증: cd frontend && npx vitest run --reporter=verbose
- 커밋: git add -A && git commit -m "test(frontend): thesis 컴포넌트 테스트 15개"

작업 12: validation + chainsight 컴포넌트 테스트 (0→18개)
- 브랜치: test/fe-validation-chainsight
- frontend/__tests__/validation/, frontend/__tests__/chainsight/ 에 생성
- 사전 파악:
  find frontend/components/validation/ -name '*.tsx' | head -20
  find frontend/components/chainsight/ -name '*.tsx' | head -20
  파악한 실제 컴포넌트 파일을 기반으로 테스트 대상을 선정해.
- 대상 6개 컴포넌트 (실제 존재하는 파일):
  (1) validation/PeerContextBar.tsx — 프리셋 탭, 커스텀 입력
  (2) validation/MetricCard.tsx — 값 렌더링, 벤치마크 바
  (3) validation/SignalSummaryCard.tsx — 시그널 요약 점수
  (4) chainsight/GraphCanvas.tsx — 그래프 렌더링 (ForceGraph2D mock)
  (5) chainsight/NodeDetailPanel.tsx — 노드 상세 정보 패널
  (6) chainsight/RelationCardPanel.tsx — 관계 카드 목록
- 각 컴포넌트당 최소 3개
- 검증: cd frontend && npx vitest run --reporter=verbose
- 커밋: git add -A && git commit -m "test(frontend): validation+chainsight 컴포넌트 테스트 18개"

마지막에 총 FE 테스트 수 요약 출력.
```

---

## 3단계: Tier 3 감사 보고서 (읽기 전용, 병렬 가능)

### 3-1. 감사 일괄 실행 스크립트

```
아래 7개 감사 작업을 순차 실행하는 bash 스크립트를
~/stock-vis-nightly/run_tier3_audits.sh 로 생성해.

모든 작업은 읽기 전용 — 코드 수정 절대 금지. 문서 출력만.
브랜치 생성 불필요 (현재 브랜치에서 실행).

작업 15: API 성능 감사 → docs/architecture/performance_audit.md
- N+1 쿼리 탐지 (views.py에서 루프 내 FK 접근)
- 인덱스 누락 (filter/order_by 필드 중 db_index 없는 것)
- 느린 Serializer (SerializerMethodField 추가 쿼리)
- 페이지네이션 누락
- HIGH/MED/LOW + 수정 난이도 분류

작업 16: 보안 감사 → docs/architecture/security_audit.md
- OWASP Top 10 기반
- 인증/인가: permission_classes 누락 APIView (17개 뷰 파일 전수 검사)
- 인젝션: cursor.execute() 4곳 파라미터 바인딩 확인
  (chainsight/services/seed_selection.py, serverless/services/admin_status_service.py,
   api_request/admin_views.py, config/views.py)
- Gemini 프롬프트 인젝션: 29개 파일 중 사용자 입력 직접 삽입 여부
- 시크릿, CORS, XSS, 에러 노출
- 심각도 CRITICAL/HIGH/MED/LOW/INFO

작업 17: FMP/Gemini 장애 대응 감사 → docs/architecture/api_dependency_audit.md
- FMP 호출 전수 조사 + 에러 핸들링 패턴
- Gemini 호출 전수 조사 + 429 처리
- FRED, Neo4j 장애 영향
- Circuit Breaker 도입 후보
- 의존성 매트릭스 + fallback 유무 테이블

작업 14: 데이터 무결성 감사 → docs/architecture/data_integrity_audit.md
- FK orphan: on_delete=SET_NULL 후 정리 로직
- CASCADE 체인 3단계 이상 삭제 영향
- Neo4j↔PG 동기화 실패 시 재시도/불일치 감지
- UniqueConstraint / update_or_create 사용 현황

작업 6: Beat 스케줄 감사 → docs/infra/beat_schedule_audit.md
- FMP rate limit 10/min 초과 구간
- Gemini 15 RPM 초과 구간
- neo4j queue 몰림 시간대
- 시간대별 API 호출 히트맵

작업 20: API 문서 감사 → docs/architecture/api_docs_audit.md
- drf-spectacular 설치 여부
- 전체 엔드포인트 수 (앱별)
- 도입 시 필요한 작업 목록

작업 10: 카탈로그 동기화 → docs/thesis_control/indicator_catalog_audit.md
- INDICATOR_CATALOG 동기화 (실제 위치):
  BE 정의: thesis/services/prompt_builder.py
  BE 후처리: thesis/services/llm_postprocess.py
  BE 매칭+keyword_rules: thesis/services/indicator_matcher.py
  FE 표시: frontend/components/thesis/AddIndicatorSheet.tsx
- BE ↔ FE 불일치, 빈 description, data_params 형식 차이

각 작업을 claude -p --model sonnet --permission-mode auto 로 실행.
mkdir -p 로 출력 디렉토리 먼저 생성.
완료 후 git add docs/ && git commit -m "docs: 코드베이스 감사 보고서 7건 생성"
마지막에 생성된 문서 목록 + 각 파일 줄 수 요약.
```

---

## 4단계: 야간 자동화 시스템 설치

### 4-1. 야간 시스템 설치 + crontab 등록

```
Stock-Vis 야간 자동화 시스템을 설치해.

docs/infra/STOCK_VIS_NIGHTLY_SYSTEM_v2.md 를 읽고 §10 설치 가이드를 따라 실행해.

구체적으로:

1. 디렉토리 생성:
   mkdir -p ~/stock-vis-nightly/{reports/{daily,monday,tuesday,wednesday,thursday,friday,saturday,sunday,weekly},logs,work}

2. nightly_v2.sh 가 ~/stock-vis-nightly/ 에 있는지 확인.
   없으면 알려줘.

3. nightly_v2.sh 상단의 PROJECT_DIR 확인:
   현재 프로젝트 경로와 일치하는지 체크

4. 실행 권한:
   chmod +x ~/stock-vis-nightly/*.sh

5. crontab 현재 상태 확인:
   crontab -l 2>/dev/null || echo "crontab 비어있음"

6. 이미 stock-vis 관련 항목이 없으면 crontab에 추가:

   0 23 * * * PATH=/usr/local/bin:/opt/homebrew/bin:$PATH ~/stock-vis-nightly/nightly_v2.sh >> ~/stock-vis-nightly/logs/cron.log 2>&1
   0  8 * * * PATH=/usr/local/bin:/opt/homebrew/bin:$PATH ~/stock-vis-nightly/morning_notify.sh >> ~/stock-vis-nightly/logs/cron_morning.log 2>&1

7. macOS 잠자기 방지 설정 확인:
   pmset -g | grep sleep

8. 설치 완료 후 상태 요약 테이블 출력

Codex가 설치되어 있으면 codex_review_phase.sh도 확인.
없으면 "Codex 미설치 — Phase 4 스킵됨" 으로 알려줘.
```

### 4-2. 야간 시스템 테스트 실행 (수동 1회)

```
야간 자동화 시스템을 테스트로 한번 실행해봐.

~/stock-vis-nightly/nightly_v2.sh 를 실행하되,
오늘 요일에 해당하는 심층 분석까지 전부 실행.

실행 전:
- git stash 필요하면 자동으로 해
- 현재 브랜치 기억해두고 끝나면 복원해

실행 후 확인:
1. 생성된 리포트 파일 목록
2. 로그에 에러가 있는지
3. nightly/auto-fix-오늘날짜 브랜치가 생겼는지
4. morning 리포트 내용 미리보기

문제 있으면 원인 분석하고 nightly_v2.sh 수정 제안해.
```

---

## 5단계: 설계서 갭 분석 (1회성 + 이후 주간 자동)

### 5-1. Chain Sight 설계서 갭 (가장 중요)

```
docs/chain_sight/plan/ 의 설계 문서들을 모두 읽고
chainsight/ 코드와 대조해서 구현 갭을 분석해.

코드 수정 없이 분석만.

분류:
(A) 완전 구현: 설계서의 모든 항목이 코드에 존재
(B) 부분 구현: 일부만 구현 (미구현 항목 구체적으로 나열)
(C) 미구현: 설계만 있고 코드 없음
(D) 폐기/대체: 설계 방향이 변경됨

특히 확인:
- redesign_v1_260409/ 가 기존 cs_* 문서를 대체하는지
- chainsight_seed_node_design.md의 Phase B+A → C → D 구현 현황
- chainsight_ui_ux_design.md v1.1의 화면 구조 (섹터 버튼바, 그래프 캔버스, 탐색 트레일, 체인 스토리 피드) 구현 현황
- chainsight_api_design.md의 API 엔드포인트 구현 현황
- 3-tier 증거 시스템, 5-stage 상태 머신 코드 존재 여부
- ForceGraph2D (react-force-graph) 사용 현황

task_done/*.md 완료 보고서와 cross-reference.

결과를 docs/chain_sight/design_gap_audit.md 에 저장.
mkdir -p docs/chain_sight 해서 디렉토리 먼저 만들어.

앱별 구현률 요약 테이블 포함:
| 설계서 파일 | 상태 | 구현률 | 미구현 핵심 항목 |
```

### 5-2. Thesis Control 설계서 갭

```
docs/thesis_control/ 의 설계 문서들을 읽고
thesis/ 코드 + frontend/components/thesis/ 코드와 대조해서 구현 갭 분석.

코드 수정 없이 분석만.

특히 확인:
- Layer A(OLS→칼만) ~ E(Rule-Based→Change Point) 각각의 구현 상태
- Stage 0 Data Validation 구현 (null→isfinite→min/max→stale→jump)
- moon-phase 상태 메타포 FE 구현 (MoonPhase 컴포넌트)
- LLM 원샷 가설 설계 (Gemini 2.5 Flash + Pydantic ConversationState)
- Perspective Balance (반론 생성) 구현
- FE-PR-1~5 진행 현황

결과를 docs/thesis_control/design_gap_audit.md 에 저장.
```

### 5-3. SEC Pipeline + 나머지 설계서 갭

```
docs/sec_pipeline/, docs/first_validation_system/, docs/news/ 의
설계 문서들을 읽고 실제 코드와 대조해서 구현 갭 분석.

코드 수정 없이 분석만.

SEC Pipeline 특히 확인:
- Track A (supply chain 추출 → Neo4j) 구현 상태
- Track B (business model 분류 → PostgreSQL) 구현 상태
- Gold Set 30개 validation 구현
- neo4j_dirty 플래그 + 2-phase DB lock 구현
- 17개 PR spec 대비 구현 현황

1차 검증 특히 확인:
- 34개 지표 × 7 카테고리 구현
- Size bucket 기반 peer selection
- Recharts ComposedChart (Bar + Scatter + ErrorBar) 구현

결과를 docs/architecture/design_gap_remaining.md 에 저장.
```

---

## 6단계: 운영 중 유용한 프롬프트

### 6-1. 아침 리포트 빠른 확인

```
오늘 아침 리포트를 읽고 핵심 3줄로 요약해.

cat ~/stock-vis-nightly/reports/daily/morning_$(date +%Y-%m-%d).md

요약 형식:
1. 상태: 🟢/🟡/🔴
2. 즉시 할 일: (있으면)
3. 야간 수정: 머지해도 되는지 (SAFE/CAUTION/BLOCK)
```

### 6-2. 특정 감사 리포트 기반 수정

```
[감사 보고서 경로]를 읽고,
그 안에서 HIGH 등급인 이슈만 골라서 수정해.

수정 가능 범위:
- select_related/prefetch_related 추가
- db_index=True 추가 (마이그레이션 파일 생성만, migrate 실행 금지)
- permission_classes 누락 추가
- null 체크 추가

브랜치: fix/audit-high-issues
수정마다 개별 커밋.
검증: pytest tests/ -x -q
```

### 6-3. 이번 주 진행상황 확인

```
~/stock-vis-nightly/reports/ 아래 이번 주 생성된 파일들을 전부 읽고
주간 진행상황을 요약해.

포함:
1. 매일 코드 상태 추세 (테스트/TS/린트)
2. 자동 수정 내역 목록
3. 요일별 심층 분석 핵심 발견
4. Opus APPROVED 비율
5. 다음 주 추천 작업 TOP 3
```

### 6-4. 새 기능 개발 전 영향 분석

```
[기능명]을 개발하기 전에 영향 범위를 분석해.

확인:
1. 수정이 필요한 파일 목록 (BE + FE)
2. 영향 받는 기존 테스트
3. 필요한 새 테스트
4. DB 마이그레이션 필요 여부
5. Neo4j 스키마 변경 필요 여부
6. FMP/Gemini API 호출 추가 여부 (rate limit 영향)

결과를 개발 시작 전 체크리스트로 정리해.
```

---

## 실행 순서 요약

```
오늘:
  0-1  상태 확인                    ← 5분
  0-2  FE 테스트 인프라 설치 (수동)  ← 5분

오늘 밤 (tmux 또는 nohup):
  1-1  Tier 1 즉시 수정             ← ~45분
  2-1  Tier 2 BE 테스트             ← ~100분
  2-2  Tier 2 FE 테스트             ← ~45분
  3-1  Tier 3 감사 보고서           ← ~105분
  ─────────────────────────────────
  총 ~5시간 (자면서 실행)

내일 아침:
  결과 확인 → 브랜치별 머지

내일:
  4-1  야간 시스템 설치             ← 10분
  4-2  테스트 실행                  ← 확인만
  5-1~3 설계서 갭 분석              ← ~45분

그 다음부터:
  매일 23:00 자동 실행 → 아침 8:00 리포트
  6-1~4 운영 중 수시 사용
```
