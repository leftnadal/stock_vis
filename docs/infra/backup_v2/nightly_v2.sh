#!/bin/bash
# ============================================================
#  Stock-Vis 야간 자동화 시스템 v2
#  
#  구조:
#    매일    → 코드 건강성 체크 + 자동 수정 (가볍게)
#    요일별  → 심층 분석 + Sonnet↔Opus 검증 루프 (깊게)
#
#  Sonnet↔Opus 루프:
#    Round 1: Sonnet이 분석 → Opus가 검증/비판/보완 지시
#    Round 2: Sonnet이 보완 → Opus가 재검증
#    ...최대 5회 또는 Opus가 APPROVED 할 때까지
#
#  crontab: 0 23 * * * ~/stock-vis-nightly/nightly_v2.sh
# ============================================================

set -uo pipefail

# ── 설정 ──────────────────────────────────────────────────────
PROJECT_DIR="$HOME/stock-vis"
SYSTEM_DIR="$HOME/stock-vis-nightly"
REPORT_DIR="$SYSTEM_DIR/reports"
LOG_DIR="$SYSTEM_DIR/logs"
WORK_DIR="$SYSTEM_DIR/work"    # Sonnet↔Opus 중간 파일
DATE=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%u)        # 1=월 ~ 7=일
DAY_NAME=$(date +%A)
TIMESTAMP=$(date +%Y%m%d_%H%M)
MAX_LOOP_ROUNDS=5

mkdir -p "$REPORT_DIR"/{daily,monday,tuesday,wednesday,thursday,friday,saturday,sunday,weekly}
mkdir -p "$LOG_DIR" "$WORK_DIR"

# ── 중복 실행 방지 ───────────────────────────────────────────
LOCKFILE="$SYSTEM_DIR/.nightly.lock"
if [ -f "$LOCKFILE" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f%m "$LOCKFILE" 2>/dev/null || stat -c%Y "$LOCKFILE" 2>/dev/null) ))
    if [ "$LOCK_AGE" -lt 14400 ]; then
        echo "[$TIMESTAMP] 이전 실행 진행 중 (${LOCK_AGE}초). 스킵."
        exit 0
    fi
fi
echo "$$" > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# ── 로깅 ─────────────────────────────────────────────────────
MAIN_LOG="$LOG_DIR/nightly_${DATE}.log"
exec > >(tee -a "$MAIN_LOG") 2>&1

cd "$PROJECT_DIR"
ORIGINAL_BRANCH=$(git branch --show-current)

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🌙 Stock-Vis 야간 자동화 v2                                ║"
echo "║  날짜: $DATE ($DAY_NAME)                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""


# ================================================================
#  공통 함수: Sonnet↔Opus 검증 루프
# ================================================================
#
#  사용법:
#    run_analysis_loop "작업명" "카테고리폴더" "Sonnet 프롬프트" "Opus 검증 프롬프트"
#
#  동작:
#    1. Sonnet이 분석 → work/작업명_draft_R1.md
#    2. Opus가 검증   → work/작업명_review_R1.md (APPROVED 또는 보완 지시)
#    3. APPROVED 아니면 Sonnet이 보완 → work/작업명_draft_R2.md
#    4. 반복 (최대 5회)
#    5. 최종본을 reports/카테고리/작업명_날짜.md 로 복사

run_analysis_loop() {
    local TASK_NAME=$1
    local CATEGORY=$2
    local SONNET_BASE_PROMPT=$3
    local OPUS_REVIEW_PROMPT=$4
    local FINAL_REPORT="$REPORT_DIR/$CATEGORY/${TASK_NAME}_${DATE}.md"
    local TASK_LOG="$LOG_DIR/${DATE}_${TASK_NAME}.log"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 심층 분석: $TASK_NAME (최대 ${MAX_LOOP_ROUNDS}라운드)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local APPROVED=false

    for round in $(seq 1 $MAX_LOOP_ROUNDS); do
        echo ""
        echo "   ┌─ Round $round/$MAX_LOOP_ROUNDS ─────────────────────────┐"

        # ── Sonnet: 분석/보완 ────────────────────────────────
        local DRAFT="$WORK_DIR/${TASK_NAME}_draft_R${round}.md"
        local PREVIOUS_REVIEW="$WORK_DIR/${TASK_NAME}_review_R$((round-1)).md"

        local SONNET_PROMPT="$SONNET_BASE_PROMPT"

        if [ "$round" -gt 1 ] && [ -f "$PREVIOUS_REVIEW" ]; then
            SONNET_PROMPT="이전 라운드에서 Opus 검증자가 아래와 같은 피드백을 줬어.
이 피드백을 반영해서 분석을 보완해.

=== Opus 피드백 (Round $((round-1))) ===
$(cat "$PREVIOUS_REVIEW")
=== 피드백 끝 ===

보완할 때:
- 피드백에서 지적한 누락/오류를 우선 수정
- 새로 추가한 내용은 [R${round} 추가] 로 표시
- 이전 분석에서 정확했던 부분은 유지

원본 분석 내용:
$(cat "$WORK_DIR/${TASK_NAME}_draft_R$((round-1)).md")

$SONNET_BASE_PROMPT

결과를 $DRAFT 에 저장해."
        else
            SONNET_PROMPT="$SONNET_BASE_PROMPT

결과를 $DRAFT 에 저장해."
        fi

        echo "   │ 📝 Sonnet 분석 중..."
        claude -p "$SONNET_PROMPT" \
            --model sonnet \
            --permission-mode auto \
            >> "$TASK_LOG" 2>&1

        if [ ! -f "$DRAFT" ]; then
            echo "   │ ❌ Sonnet 분석 파일 생성 실패. 스킵."
            break
        fi
        echo "   │ ✅ Sonnet 분석 완료 ($(wc -l < "$DRAFT" | tr -d ' ')줄)"

        # ── Opus: 검증/비판 ──────────────────────────────────
        local REVIEW="$WORK_DIR/${TASK_NAME}_review_R${round}.md"

        echo "   │ 🔍 Opus 검증 중..."
        claude -p "당신은 시니어 아키텍트이자 검증자야. 
아래 분석 보고서를 엄격하게 검증해.

=== 분석 보고서 (Round $round) ===
$(cat "$DRAFT")
=== 보고서 끝 ===

$OPUS_REVIEW_PROMPT

검증 결과를 $REVIEW 에 저장해.

반드시 아래 형식으로 시작해:
VERDICT: APPROVED 또는 NEEDS_REVISION

APPROVED 기준:
- 주장에 구체적 근거(파일명, 라인, 코드 조각)가 있음
- 누락된 중요 관점이 없음
- 제안이 Stock-Vis 아키텍처와 현실적으로 맞음
- 우선순위가 합리적

NEEDS_REVISION이면:
- 구체적으로 뭘 보완해야 하는지 번호 매겨서 지시
- 각 지시마다 왜 부족한지 근거 제시" \
            --model opus \
            --permission-mode auto \
            >> "$TASK_LOG" 2>&1

        if [ ! -f "$REVIEW" ]; then
            echo "   │ ❌ Opus 검증 파일 생성 실패. 현재 draft 사용."
            cp "$DRAFT" "$FINAL_REPORT"
            break
        fi

        # APPROVED 여부 확인
        if head -3 "$REVIEW" | grep -qi "APPROVED"; then
            echo "   │ ✅ Opus APPROVED! (Round $round)"
            APPROVED=true

            # 최종본 = 마지막 draft + Opus 승인 코멘트 첨부
            {
                cat "$DRAFT"
                echo ""
                echo "---"
                echo "*검증: Opus 4.6 | Round ${round}/${MAX_LOOP_ROUNDS} | APPROVED*"
                echo ""
                echo "### Opus 검증 코멘트"
                tail -n +2 "$REVIEW"
            } > "$FINAL_REPORT"

            break
        else
            echo "   │ 🔁 Opus: NEEDS_REVISION → 다음 라운드"
        fi

        echo "   └──────────────────────────────────────────────┘"
    done

    # 최대 라운드 도달 시
    if [ "$APPROVED" = false ] && [ -f "$DRAFT" ]; then
        {
            cat "$DRAFT"
            echo ""
            echo "---"
            echo "*검증: Opus 4.6 | ${MAX_LOOP_ROUNDS}라운드 소진 | NOT FULLY APPROVED*"
            echo "*사람의 추가 검토가 필요합니다.*"
            if [ -f "$REVIEW" ]; then
                echo ""
                echo "### 마지막 Opus 피드백"
                cat "$REVIEW"
            fi
        } > "$FINAL_REPORT"
        echo "   ⚠️ ${MAX_LOOP_ROUNDS}라운드 소진. 수동 확인 필요."
    fi

    echo "   📄 최종 리포트: $FINAL_REPORT"

    # 중간 파일 정리
    rm -f "$WORK_DIR/${TASK_NAME}_"*.md 2>/dev/null || true
}


# ================================================================
#  매일 실행: 코드 건강성 (Phase 1~4, 가볍게)
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  📋 매일 작업: 코드 건강성 체크               ║"
echo "╚══════════════════════════════════════════════╝"

# ── Phase 1: 빠른 스캔 (Haiku) ────────────────────────────────
echo ""
echo "━━ Phase 1: 코드 스캔 (Haiku) ━━"
DAILY_SCAN="$REPORT_DIR/daily/scan_${DATE}.md"

claude -p "Stock-Vis 프로젝트 빠른 점검. 아래를 실행하고 결과 정리:

1. pytest tests/ -q --tb=line 2>&1 | tail -20
2. cd frontend && npx tsc --noEmit 2>&1 | tail -20  
3. ruff check . --statistics 2>&1 | tail -10
4. git log --since='24 hours ago' --oneline | head -20

$DAILY_SCAN 에 저장. 형식:
# 일일 코드 스캔 — $DATE
## 테스트: X passed / Y failed / Z error
## TypeScript: N개 에러
## 린트: N개 경고
## 최근 커밋: N개
## 종합: 🟢/🟡/🔴

코드 수정 금지. 점검만." \
    --model haiku \
    --permission-mode auto \
    > "$LOG_DIR/${DATE}_phase1.log" 2>&1

echo "   ✅ Phase 1 완료"

# ── Phase 2: 자동 수정 (Sonnet) ───────────────────────────────
echo ""
echo "━━ Phase 2: 자동 수정 (Sonnet) ━━"

FIX_BRANCH="nightly/auto-fix-${DATE}"
if git show-ref --verify --quiet "refs/heads/$FIX_BRANCH"; then
    echo "   ⏭️ 브랜치 이미 존재. 스킵."
else
    git checkout -b "$FIX_BRANCH" 2>/dev/null || true

    claude -p "$DAILY_SCAN 를 읽고 발견된 문제 중 안전하게 수정 가능한 것만 수정.

수정 가능: 테스트 실패(테스트 코드 수정), TS 컴파일 에러, ruff --fix
수정 금지: DB 마이그레이션, .env, settings.py, 새 기능, 의미적 로직

수정마다 커밋: git add -A && git commit -m 'nightly-fix: 내용'
수정 요약을 $WORK_DIR/fixes_${DATE}.txt 에 저장." \
        --model sonnet \
        --permission-mode auto \
        > "$LOG_DIR/${DATE}_phase2.log" 2>&1

    git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true
    echo "   ✅ Phase 2 완료"
fi

# ── Phase 3: 수정 검증 (Haiku) ────────────────────────────────
echo ""
echo "━━ Phase 3: 수정 검증 (Haiku) ━━"
DAILY_VERIFY="$REPORT_DIR/daily/verify_${DATE}.md"

if git show-ref --verify --quiet "refs/heads/$FIX_BRANCH"; then
    git checkout "$FIX_BRANCH" 2>/dev/null || true

    claude -p "수정된 코드 검증. pytest + tsc + ruff 실행.
수정 전/후 비교표 작성. $DAILY_VERIFY 에 저장.
코드 수정 금지." \
        --model haiku \
        --permission-mode auto \
        > "$LOG_DIR/${DATE}_phase3.log" 2>&1

    git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true
    echo "   ✅ Phase 3 완료"
fi


# ================================================================
#  요일별 심층 분석 (Sonnet↔Opus 루프)
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  🔬 오늘의 심층 분석: $(date +%A)              ║"
echo "╚══════════════════════════════════════════════╝"

case $DAY_OF_WEEK in

# ────────────────────────────────────────────────────────────
# 월요일: UI/UX 분석
# ────────────────────────────────────────────────────────────
1)
    run_analysis_loop "component_consistency" "monday" \
"frontend/components/ 전체를 읽고 UI 일관성을 분석해.

1. 같은 역할인데 다르게 구현된 컴포넌트 (버튼, 카드, 모달 등)
2. 색상 하드코딩 vs Tailwind 디자인 토큰 사용 비율
3. 반응형 처리 누락 (sm/md/lg 브레이크포인트)
4. 접근성: alt 누락, aria-label 없는 인터랙티브 요소, 키보드 네비게이션
5. 로딩/에러/빈 상태(empty state) 처리 누락된 컴포넌트
6. Chain Sight 마켓뷰의 노드 클릭→중심이동→좌측히스토리 UX 구현 상태
7. 체인 스토리 피드가 Finimize/Robinhood 스타일에 얼마나 근접한지

한국 개인 투자자(20~40대) 관점에서 불편할 점도 지적." \
\
"검증 관점:
- 지적된 문제마다 구체적 파일명과 라인이 있는가
- 190개 FE 컴포넌트 중 몇 개를 실제로 분석했는지 커버리지
- 제안이 Next.js + Tailwind 환경에서 현실적인지
- 우선순위가 사용자 임팩트 기준으로 합리적인지"

    run_analysis_loop "user_flow" "monday" \
"Stock-Vis의 핵심 사용자 플로우를 코드로 추적해.

플로우 1: Dashboard → Chain Sight → Node 클릭 → 1차 검증
플로우 2: EOD Screening → 종목 선택 → Thesis Control 생성  
플로우 3: News 피드 → 관련 종목 → 관계 탐색

각 플로우에서:
- 페이지 전환 시 API 호출 수와 순서
- 로딩 중 사용자가 기다리는 구간 (waterfall)
- 에러 시 fallback UI 존재 여부
- 뒤로가기/새로고침 시 상태 보존
- 모바일에서의 터치 인터랙션 가능 여부" \
\
"검증 관점:
- 실제 라우터/페이지 파일을 근거로 분석했는지
- API 호출 순서가 코드와 일치하는지
- 누락된 중요 플로우가 없는지 (예: 로그인, 온보딩)"
    ;;

# ────────────────────────────────────────────────────────────
# 화요일: 데이터 & API 건강성
# ────────────────────────────────────────────────────────────
2)
    run_analysis_loop "fmp_dependency" "tuesday" \
"코드 전체에서 FMP API 호출을 추적해.

1. 모든 FMP 엔드포인트 사용 목록 (URL 패턴별)
2. 각 호출의 에러 핸들링: rate limit 429, 빈 응답, timeout, retry
3. FMP Starter(\$29) 제한 대비 실 사용량 추정
4. FMP 장애 시 서비스 전체 영향 범위 (의존 그래프)
5. 캐싱하는 곳 vs 매번 호출하는 곳
6. match_score clamping, dividend_yield semantic mismatch 등 기존 이슈 코드 반영 여부" \
\
"검증 관점:
- 실제 코드의 import/호출부를 근거로 했는지
- rate limit 계산이 현실적인지 (Starter 플랜 기준)
- 누락된 FMP 호출이 없는지 (grep으로 확인 가능)"

    run_analysis_loop "pipeline_health" "tuesday" \
"데이터 파이프라인 건강성 분석.

1. EOD 수집 → 가공 → 저장 경로 (Celery 태스크 추적)
2. News 수집 → 분석 → 저장 경로
3. 각 단계 실패 시 다음 단계 영향
4. stale 감지 로직 현황 (72시간 asof 기반)
5. PostgreSQL ↔ Neo4j 동기화: neo4j_dirty 플래그 사용 현황
6. FK on_delete=PROTECT 적용 현황
7. Circuit Breaker, 슬라이딩 윈도우 토큰 버킷 구현 상태" \
\
"검증 관점:
- Celery 태스크 의존 관계가 코드와 일치하는지
- neo4j_dirty → sync 흐름이 single-writer 원칙을 지키는지
- 누락된 파이프라인 경로가 없는지"
    ;;

# ────────────────────────────────────────────────────────────
# 수요일: 보안 & 성능
# ────────────────────────────────────────────────────────────
3)
    run_analysis_loop "security_scan" "wednesday" \
"전체 코드 보안 스캔.

1. 하드코딩된 시크릿 (API 키, 토큰, 비밀번호) — 파일명+라인
2. SQL injection 가능성 (raw SQL, extra(), RawSQL 사용처)
3. CORS 설정 (허용 origin 목록, credentials 설정)
4. JWT 토큰: 만료 시간, refresh 로직, blacklist 처리
5. 사용자 입력 검증 누락 (Serializer validation, URL 파라미터)
6. DEBUG 설정, ALLOWED_HOSTS
7. requirements.txt 패키지 중 알려진 취약점 (pip-audit 기준)" \
\
"검증 관점:
- 각 취약점에 구체적 파일/라인이 있는지
- false positive가 없는지 (예: .env.example은 실제 시크릿 아님)
- 심각도 분류(Critical/High/Medium/Low)가 합리적인지"

    run_analysis_loop "performance_bottleneck" "wednesday" \
"코드 기반 성능 병목 분석.

1. N+1 쿼리 패턴: select_related/prefetch_related 누락
2. 인덱스 누락: models.py Meta.indexes vs 실제 쿼리 필터/정렬 필드
3. 무거운 직렬화: nested serializer 깊이
4. FE 번들: lodash 전체 import, 불필요한 큰 라이브러리
5. 불필요하게 큰 API 응답 (과도한 필드 포함)
6. 캐싱 필요하지만 없는 빈번한 API
7. EOD static JSON baking 파이프라인 효율" \
\
"검증 관점:
- 실제 QuerySet 코드를 근거로 N+1 판단했는지
- 인덱스 제안이 실제 쿼리 패턴과 매칭되는지
- FE 번들 분석이 next.config.js/package.json 기반인지"
    ;;

# ────────────────────────────────────────────────────────────
# 목요일: 비즈니스 로직 & 기능 완성도
# ────────────────────────────────────────────────────────────
4)
    run_analysis_loop "feature_completeness" "thursday" \
"Stock-Vis 4대 필라 구현 완성도 평가.

1. Chain Sight (발견)
   - 마켓 뷰 설계서(seed_node_design.md, ui_ux_design.md, api_design.md) 대비 구현
   - 에고그래프, 시드 노드, Heat Score, 이벤트 전파 모델
   - 3-tier 증거 시스템, 5-stage 상태 머신 구현

2. EOD Screening (선별)
   - 47개 시그널 × 7 카테고리 구현 현황
   - static JSON baking 파이프라인
   - dollar volume filter, hierarchical news matching

3. News Intelligence (정보)
   - 6단계 파이프라인 구현 현황
   - MarketAux + Finnhub 연동
   - Redis 슬라이딩 윈도우, Circuit Breaker

4. Thesis Control (검증)
   - Layer A(OLS→칼만) ~ E(Rule-Based→Change Point) 구현
   - moon-phase 상태 메타포
   - LLM 원샷 가설 설계 (Gemini 2.5 Flash + Structured Output)

각 기능: ✅ 완료 / 🔨 진행중 / 📋 설계만 / ❌ 미착수
임팩트 높은 다음 구현 대상 TOP 3도 제안." \
\
"검증 관점:
- 설계 문서(docs/)를 실제로 읽고 코드와 대조했는지
- ✅/🔨/📋/❌ 판정이 코드 존재 여부와 일치하는지
- TOP 3 제안이 서비스 플로우(Dashboard→발견→검증) 순서에 맞는지
- 34개 검증 지표 프레임워크 반영 여부"

    run_analysis_loop "indicator_catalog_sync" "thursday" \
"지표 카탈로그 3곳 동기화 검증.

1. thesis/services/prompt_builder.py — INDICATOR_CATALOG
2. thesis/services/indicator_matcher.py — KEYWORD_RULES  
3. frontend/에서 indicator type/name 사용하는 곳

확인: 카탈로그↔matcher 불일치, description 빈 항목, data_params 형식,
FE에서 사용하지만 BE에 정의 안 된 지표.
value_status, benchmark_basis, handling_mode 필드 현황도 확인." \
\
"검증 관점:
- 실제 딕셔너리 키를 비교해서 불일치를 찾았는지
- false positive 없는지 (alias나 매핑으로 연결되는 경우)"
    ;;

# ────────────────────────────────────────────────────────────
# 금요일: 아키텍처 & 기술부채
# ────────────────────────────────────────────────────────────
5)
    run_analysis_loop "architecture_evolution" "friday" \
"현재 아키텍처 분석 및 진화 제안.

현재 스택: Django/Celery/PostgreSQL/Neo4j/Next.js
          Gemini Flash for LLM, FMP for data

1. 스케일 시 가장 먼저 병목될 곳
2. 마이크로서비스 분리 후보와 시점
3. GraphRepository Protocol 추상화 현황
4. 4-layer 데이터 아키텍처(raw→metrics→chainsight PG→Neo4j) 구현도
5. 기술 부채 TOP 5 (구체적 파일과 이유)
6. Trading bot 4-layer signal stack 준비도
   (Chain Sight 전파 → 1차 검증 34 지표 → Thesis Control → EOD 시그널)" \
\
"검증 관점:
- 기술 부채 판단에 구체적 코드 근거가 있는지
- 마이크로서비스 제안이 현재 Django monolith에서 실현 가능한지
- 솔로 개발자 환경에서 현실적인 제안인지"

    run_analysis_loop "api_consistency" "friday" \
"전체 DRF ViewSet/APIView 응답 형식 일관성 감사.

1. success/error 래핑 패턴 사용 여부 (앱별)
2. HTTP 상태 코드 일관성
3. 에러 응답 형식 통일 여부
4. pagination 적용 여부
5. 앱별 응답 패턴 매트릭스" \
\
"검증 관점:
- 모든 views.py를 실제로 읽었는지
- 매트릭스가 빠진 앱 없이 완전한지"
    ;;

# ────────────────────────────────────────────────────────────
# 토요일: 경쟁 분석 & 서비스 전략
# ────────────────────────────────────────────────────────────
6)
    run_analysis_loop "competitive_analysis" "saturday" \
"Stock-Vis의 한국 개인 투자자 대상 서비스 차별화 분석.

코드와 설계를 기반으로:
1. Stock-Vis만의 독보적 기능 (Chain Sight 관계 탐색 등)
2. 증권사 MTS/HTS가 이미 잘하는 영역 (차트, 호가, 실시간)
3. 토스증권/카카오페이증권 대비 UX 차이
4. TradingView/Simply Wall St 대비 기능 차이
5. 한국 시장 특화 부족한 점 (KOSPI/KOSDAQ, 공시, 외국인 매매 등)
6. 'signals first, news second' 철학이 코드에 반영된 정도
7. MVP 출시까지 필요한 최소 기능 목록" \
\
"검증 관점:
- 차별화 분석이 코드 근거에 기반하는지 (막연한 추측 아닌지)
- 한국 시장 특수성을 정확히 반영했는지
- MVP 범위 제안이 솔로 개발자에게 현실적인지"

    run_analysis_loop "celery_schedule_audit" "saturday" \
"config/celery.py beat_schedule 감사.

1. 같은 시각 FMP API 호출 겹침 (rate limit 10/min 초과 구간)
2. 같은 시각 Gemini API 호출 겹침 (15 RPM 초과 구간)
3. neo4j queue 작업 몰림 시간대
4. 시간대별 API 호출 히트맵
5. 개선안 (시간 분산 제안)" \
\
"검증 관점:
- 히트맵 계산이 실제 crontab 표현식 기반인지
- rate limit 계산에 burst 고려했는지"
    ;;

# ────────────────────────────────────────────────────────────
# 일요일: 주간 종합
# ────────────────────────────────────────────────────────────
7)
    run_analysis_loop "weekly_summary" "weekly" \
"이번 주 생성된 모든 리포트를 종합해 주간 리포트 작성.

reports/ 하위의 이번 주 파일들을 모두 읽고:

1. 이번 주 코드 변화 요약 (커밋 통계, 변경된 앱)
2. 반복 등장하는 문제 패턴 (매일 같은 에러?)
3. 테스트 커버리지 추세
4. 자동 수정된 것 목록
5. 각 요일별 심층 분석 핵심 발견 요약
6. Opus가 APPROVED/NEEDS_REVISION한 비율
7. 다음 주 추천 작업 우선순위 TOP 5
8. Stock-Vis 전체 진행률 (Chain Sight, Thesis Control 등)

한국어로, 간결하게, 실행 가능한 제안 중심으로." \
\
"검증 관점:
- 모든 요일 리포트를 실제로 읽었는지
- 추세 분석이 이전 주와 비교 가능한지  
- TOP 5가 현실적이고 구체적인지"
    ;;

esac


# ================================================================
#  Phase 최종: 아침 리포트 통합 (Opus)
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  📝 아침 리포트 통합 (Opus)                    ║"
echo "╚══════════════════════════════════════════════╝"

MORNING_REPORT="$REPORT_DIR/daily/morning_${DATE}.md"
DAY_NAMES=("" "monday" "tuesday" "wednesday" "thursday" "friday" "saturday" "weekly")
TODAY_CATEGORY="${DAY_NAMES[$DAY_OF_WEEK]}"

claude -p "오늘의 모든 분석 결과를 종합해서 아침 리포트를 작성해.

입력 파일들:
- $DAILY_SCAN (일일 스캔)
- $DAILY_VERIFY (수정 검증, 있으면)
- $REPORT_DIR/$TODAY_CATEGORY/ 아래 오늘 날짜 파일들 (심층 분석)

$MORNING_REPORT 에 저장. 형식:

# ☀️ Stock-Vis 아침 리포트 — $DATE ($DAY_NAME)

## 한눈에 보기
| 항목 | 상태 | 상세 |
|------|------|------|
| 테스트 | 🟢/🟡/🔴 | ... |
| TS | 🟢/🟡/🔴 | ... |
| 린트 | 🟢/🟡/🔴 | ... |
| 야간 수정 | ✅/❌ | N개 커밋 |

## 🔧 야간 자동 수정
(수정 내역)

## 🔬 오늘의 심층 분석: $(date +%A)
(요일별 분석 핵심 발견 3줄 요약)
(Opus 검증 결과: APPROVED / NEEDS_REVISION)

## ⚠️ 즉시 조치 필요
(Critical/High만)

## 💡 이번 주 제안
(우선순위 TOP 3)

## 📋 오늘 할 일
- [ ] nightly/auto-fix-$DATE diff 확인
- [ ] (심층 분석 기반 제안)

톤: 간결하고 실용적. 핵심만." \
    --model opus \
    --permission-mode auto \
    > "$LOG_DIR/${DATE}_morning_report.log" 2>&1

echo "   ✅ 아침 리포트 완료: $MORNING_REPORT"


# ================================================================
#  정리
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🌙 야간 작업 완료: $(date '+%H:%M:%S')                     ║"
echo "║  아침 리포트: $MORNING_REPORT                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# 14일 이전 파일 정리
find "$LOG_DIR" -name "*.log" -mtime +14 -delete 2>/dev/null || true
find "$REPORT_DIR" -name "*.md" -mtime +14 -delete 2>/dev/null || true
find "$WORK_DIR" -name "*.md" -mtime +1 -delete 2>/dev/null || true

# 7일 이전 nightly 브랜치 정리
for old_branch in $(git branch --list 'nightly/auto-fix-*' | tr -d ' '); do
    BRANCH_DATE=$(echo "$old_branch" | grep -oP '\d{4}-\d{2}-\d{2}' || true)
    if [ -n "$BRANCH_DATE" ]; then
        BRANCH_AGE=$(( ( $(date +%s) - $(date -j -f "%Y-%m-%d" "$BRANCH_DATE" +%s 2>/dev/null || date -d "$BRANCH_DATE" +%s 2>/dev/null) ) / 86400 ))
        if [ "$BRANCH_AGE" -gt 7 ]; then
            git branch -D "$old_branch" 2>/dev/null || true
        fi
    fi
done

git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true