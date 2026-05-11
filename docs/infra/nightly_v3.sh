#!/bin/bash
# ============================================================
#  Stock-Vis 야간 자동화 시스템 v3
#
#  변경사항 (v2 → v3):
#    - 리포트 경로: docs/nightly_auto_system/YYYYMM/DD/
#    - 기준선(baseline) 비교: 지난주 감사 결과 대비 변화 추적
#    - 주간 트렌드 추적: CRITICAL/HIGH 이슈 증감
#
#  구조:
#    매일    → 코드 건강성 체크 + 자동 수정 + Codex 리뷰
#    요일별  → 심층 분석 + Sonnet↔Opus 검증 루프 (최대 5회)
#    아침    → 전체 통합 리포트
#
#  리포트 저장 경로:
#    docs/nightly_auto_system/202604/15/
#      ├── morning_report.md        ← 아침에 이걸 봄
#      ├── scan.md                  ← Phase 1 결과
#      ├── auto_fix_verify.md       ← Phase 3 결과
#      ├── codex_review.md          ← Phase 4 결과
#      ├── security_audit.md        ← 요일별 심층 (수요일 예시)
#      ├── performance_audit.md     ← 요일별 심층 (수요일 예시)
#      └── baseline_comparison.md   ← 기준선 대비 변화
#
#  crontab: 0 23 * * * ~/stock-vis-nightly/nightly_v3.sh
# ============================================================

set -uo pipefail

# ── 설정 ──────────────────────────────────────────────────────
PROJECT_DIR="$HOME/stock-vis"
SYSTEM_DIR="$HOME/stock-vis-nightly"
WORK_DIR="$SYSTEM_DIR/work"
LOG_DIR="$SYSTEM_DIR/logs"

# 날짜 관련
DATE=$(date +%Y-%m-%d)
YEAR_MONTH=$(date +%Y%m)
DAY=$(date +%d)
DAY_OF_WEEK=$(date +%u)        # 1=월 ~ 7=일
DAY_NAME=$(date +%A)
TIMESTAMP=$(date +%Y%m%d_%H%M)

# 리포트 경로: docs/nightly_auto_system/YYYYMM/DD/
REPORT_BASE="$PROJECT_DIR/docs/nightly_auto_system"
REPORT_DIR="$REPORT_BASE/$YEAR_MONTH/$DAY"

# 지난주 같은 요일 리포트 (기준선 비교용)
PREV_YEAR_MONTH=$(date -v-7d +%Y%m 2>/dev/null || date -d '7 days ago' +%Y%m)
PREV_DAY=$(date -v-7d +%d 2>/dev/null || date -d '7 days ago' +%d)
PREV_REPORT_DIR="$REPORT_BASE/$PREV_YEAR_MONTH/$PREV_DAY"

# 어제 리포트 (일일 트렌드용)
YEST_YEAR_MONTH=$(date -v-1d +%Y%m 2>/dev/null || date -d '1 day ago' +%Y%m)
YEST_DAY=$(date -v-1d +%d 2>/dev/null || date -d '1 day ago' +%d)
YEST_REPORT_DIR="$REPORT_BASE/$YEST_YEAR_MONTH/$YEST_DAY"

MAX_LOOP_ROUNDS=5
PERMISSION_MODE="auto"

# ── 디렉토리 준비 ────────────────────────────────────────────
mkdir -p "$REPORT_DIR" "$WORK_DIR" "$LOG_DIR"

# ── 중복 실행 방지 ───────────────────────────────────────────
LOCKFILE="$SYSTEM_DIR/.nightly.lock"
if [ -f "$LOCKFILE" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f%m "$LOCKFILE" 2>/dev/null || stat -c%Y "$LOCKFILE" 2>/dev/null) ))
    if [ "$LOCK_AGE" -lt 14400 ]; then
        echo "[$TIMESTAMP] 이전 실행 진행 중. 스킵."
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
echo "║  🌙 Stock-Vis 야간 자동화 v3                                ║"
echo "║  날짜: $DATE ($DAY_NAME)                                    ║"
echo "║  리포트: docs/nightly_auto_system/$YEAR_MONTH/$DAY/         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""


# ================================================================
#  공통 함수: Sonnet↔Opus 검증 루프
# ================================================================

run_analysis_loop() {
    local TASK_NAME=$1
    local SONNET_BASE_PROMPT=$2
    local OPUS_REVIEW_PROMPT=$3
    local FINAL_REPORT="$REPORT_DIR/${TASK_NAME}.md"
    local TASK_LOG="$LOG_DIR/${DATE}_${TASK_NAME}.log"

    # 지난주 같은 분석이 있으면 기준선으로 제공
    local BASELINE_CONTEXT=""
    if [ -f "$PREV_REPORT_DIR/${TASK_NAME}.md" ]; then
        BASELINE_CONTEXT="

=== 지난주 분석 결과 (기준선) ===
$(head -100 "$PREV_REPORT_DIR/${TASK_NAME}.md")
=== 기준선 끝 ===

위 기준선과 비교하여:
- 해결된 이슈는 ✅ 표시
- 새로 발견된 이슈는 🆕 표시
- 악화된 이슈는 ⬆️ 표시
- 변화 없는 이슈는 ➡️ 표시"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 심층 분석: $TASK_NAME (최대 ${MAX_LOOP_ROUNDS}라운드)"
    if [ -n "$BASELINE_CONTEXT" ]; then
        echo "   📊 기준선 있음: $PREV_REPORT_DIR/${TASK_NAME}.md"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local APPROVED=false

    for round in $(seq 1 $MAX_LOOP_ROUNDS); do
        echo ""
        echo "   ┌─ Round $round/$MAX_LOOP_ROUNDS ─────────────────────────┐"

        # ── Sonnet: 분석/보완 ────────────────────────────────
        local DRAFT="$WORK_DIR/${TASK_NAME}_draft_R${round}.md"
        local PREVIOUS_REVIEW="$WORK_DIR/${TASK_NAME}_review_R$((round-1)).md"

        local SONNET_PROMPT="$SONNET_BASE_PROMPT $BASELINE_CONTEXT"

        if [ "$round" -gt 1 ] && [ -f "$PREVIOUS_REVIEW" ]; then
            SONNET_PROMPT="이전 라운드에서 Opus 검증자가 아래 피드백을 줬어.
이 피드백을 반영해서 분석을 보완해.

=== Opus 피드백 (Round $((round-1))) ===
$(cat "$PREVIOUS_REVIEW")
=== 피드백 끝 ===

보완할 때:
- 피드백에서 지적한 누락/오류를 우선 수정
- 새로 추가한 내용은 [R${round} 추가] 로 표시
- 이전 분석에서 정확했던 부분은 유지

원본 분석:
$(cat "$WORK_DIR/${TASK_NAME}_draft_R$((round-1)).md")

$SONNET_BASE_PROMPT $BASELINE_CONTEXT

결과를 $DRAFT 에 저장해."
        else
            SONNET_PROMPT="$SONNET_PROMPT

결과를 $DRAFT 에 저장해."
        fi

        echo "   │ 📝 Sonnet 분석 중..."
        claude -p "$SONNET_PROMPT" \
            --model sonnet \
            --permission-mode "$PERMISSION_MODE" \
            >> "$TASK_LOG" 2>&1

        if [ ! -f "$DRAFT" ]; then
            echo "   │ ❌ Sonnet 분석 파일 생성 실패. 스킵."
            break
        fi
        echo "   │ ✅ Sonnet 완료 ($(wc -l < "$DRAFT" | tr -d ' ')줄)"

        # ── Opus: 검증/비판 ──────────────────────────────────
        local REVIEW="$WORK_DIR/${TASK_NAME}_review_R${round}.md"

        echo "   │ 🔍 Opus 검증 중..."
        claude -p "시니어 아키텍트로서 아래 분석을 엄격하게 검증해.

=== 분석 보고서 (Round $round) ===
$(cat "$DRAFT")
=== 보고서 끝 ===

$OPUS_REVIEW_PROMPT

검증 결과를 $REVIEW 에 저장해.

반드시 첫 줄에: VERDICT: APPROVED 또는 VERDICT: NEEDS_REVISION

APPROVED 기준:
- 주장에 구체적 근거(파일명, 라인, 코드)가 있음
- 누락된 중요 관점이 없음
- 제안이 Stock-Vis 아키텍처와 현실적으로 맞음
- 기준선 대비 변화 추적이 정확함 (기준선 있을 때)

NEEDS_REVISION이면 구체적 보완 지시를 번호 매겨서." \
            --model opus \
            --permission-mode "$PERMISSION_MODE" \
            >> "$TASK_LOG" 2>&1

        if [ ! -f "$REVIEW" ]; then
            echo "   │ ❌ Opus 검증 파일 생성 실패."
            cp "$DRAFT" "$FINAL_REPORT"
            break
        fi

        if head -3 "$REVIEW" | grep -qi "APPROVED"; then
            echo "   │ ✅ Opus APPROVED! (Round $round)"
            APPROVED=true
            {
                cat "$DRAFT"
                echo ""
                echo "---"
                echo ""
                echo "*검증: Opus 4.6 | Round ${round}/${MAX_LOOP_ROUNDS} | APPROVED*"
                echo "*리포트 경로: docs/nightly_auto_system/$YEAR_MONTH/$DAY/${TASK_NAME}.md*"
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

    if [ "$APPROVED" = false ] && [ -f "$DRAFT" ]; then
        {
            cat "$DRAFT"
            echo ""
            echo "---"
            echo "*검증: Opus 4.6 | ${MAX_LOOP_ROUNDS}라운드 소진 | NOT FULLY APPROVED*"
            echo "*⚠️ 사람의 추가 검토가 필요합니다.*"
            if [ -f "$REVIEW" ]; then
                echo ""
                echo "### 마지막 Opus 피드백"
                cat "$REVIEW"
            fi
        } > "$FINAL_REPORT"
        echo "   ⚠️ ${MAX_LOOP_ROUNDS}라운드 소진. 수동 확인 필요."
    fi

    echo "   📄 → $FINAL_REPORT"
    rm -f "$WORK_DIR/${TASK_NAME}_"*.md 2>/dev/null || true
}


# ================================================================
#  매일 실행: Phase 1~4
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  📋 매일 작업: 코드 건강성 체크               ║"
echo "╚══════════════════════════════════════════════╝"

# ── Phase 1: 코드 스캔 (Haiku) ────────────────────────────────
echo ""
echo "━━ Phase 1: 코드 스캔 (Haiku) ━━"

DAILY_SCAN="$REPORT_DIR/scan.md"

# 어제 스캔 결과 비교 컨텍스트
YEST_SCAN_CTX=""
if [ -f "$YEST_REPORT_DIR/scan.md" ]; then
    YEST_SCAN_CTX="

어제 스캔 결과:
$(cat "$YEST_REPORT_DIR/scan.md")

위 결과와 비교해서 '어제 대비 변화' 섹션을 추가해."
fi

claude -p "Stock-Vis 빠른 점검.

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
${YEST_SCAN_CTX}

코드 수정 금지." \
    --model haiku \
    --permission-mode "$PERMISSION_MODE" \
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
        --permission-mode "$PERMISSION_MODE" \
        > "$LOG_DIR/${DATE}_phase2.log" 2>&1

    git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true
    echo "   ✅ Phase 2 완료"
fi

# ── Phase 3: 수정 검증 (Haiku) ────────────────────────────────
echo ""
echo "━━ Phase 3: 수정 검증 (Haiku) ━━"
DAILY_VERIFY="$REPORT_DIR/auto_fix_verify.md"

if git show-ref --verify --quiet "refs/heads/$FIX_BRANCH"; then
    git checkout "$FIX_BRANCH" 2>/dev/null || true

    claude -p "수정된 코드 검증. pytest + tsc + ruff 실행.
수정 전/후 비교표 작성. $DAILY_VERIFY 에 저장.
코드 수정 금지." \
        --model haiku \
        --permission-mode "$PERMISSION_MODE" \
        > "$LOG_DIR/${DATE}_phase3.log" 2>&1

    git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true
    echo "   ✅ Phase 3 완료"
fi

# ── Phase 4: Codex 크로스 리뷰 ────────────────────────────────
echo ""
echo "━━ Phase 4: Codex 크로스 리뷰 ━━"

CODEX_REPORT="$REPORT_DIR/codex_review.md"

if command -v codex &> /dev/null; then
    if git show-ref --verify --quiet "refs/heads/$FIX_BRANCH"; then
        DIFF_FILE="$WORK_DIR/nightly_diff_${DATE}.patch"
        git diff "$ORIGINAL_BRANCH..$FIX_BRANCH" > "$DIFF_FILE" 2>/dev/null

        if [ -s "$DIFF_FILE" ]; then
            codex exec \
                --approval-mode full-auto \
                --output-last-message "$WORK_DIR/codex_diff_${DATE}.txt" \
                "아래 diff는 Claude가 자동 수정한 코드야. 리뷰해줘.
$(head -500 "$DIFF_FILE")

판정: SAFE / CAUTION / BLOCK
한국어로 답변해." \
                >> "$LOG_DIR/${DATE}_codex.log" 2>&1
        fi
    fi

    CHANGED_FILES=$(git log --since="48 hours ago" --name-only --pretty=format: | sort -u | grep -E '\.(py|tsx?|jsx?)$' | head -15)
    if [ -n "$CHANGED_FILES" ]; then
        codex exec \
            --approval-mode read-only \
            --output-last-message "$WORK_DIR/codex_spot_${DATE}.txt" \
            "최근 48시간 변경 파일 리뷰:
$CHANGED_FILES
P0/P1/P2로 분류. 한국어로." \
            >> "$LOG_DIR/${DATE}_codex.log" 2>&1
    fi

    {
        echo "# 🔍 Codex 크로스 리뷰 — $DATE"
        echo ""
        echo "*모델: GPT-5-Codex | 경로: docs/nightly_auto_system/$YEAR_MONTH/$DAY/codex_review.md*"
        echo ""
        [ -f "$WORK_DIR/codex_diff_${DATE}.txt" ] && {
            echo "## diff 리뷰"
            echo ""
            cat "$WORK_DIR/codex_diff_${DATE}.txt"
            echo ""
        }
        [ -f "$WORK_DIR/codex_spot_${DATE}.txt" ] && {
            echo "## 스팟 리뷰"
            echo ""
            cat "$WORK_DIR/codex_spot_${DATE}.txt"
            echo ""
        }
    } > "$CODEX_REPORT"

    rm -f "$WORK_DIR/codex_"*"_${DATE}.txt" "$WORK_DIR/nightly_diff_${DATE}.patch" 2>/dev/null || true
    echo "   ✅ Phase 4 완료"
else
    echo "   ⏭️ Codex 미설치. 스킵."
    echo "SKIPPED: codex not installed" > "$CODEX_REPORT"
fi


# ================================================================
#  요일별 심층 분석 (Sonnet↔Opus 루프)
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  🔬 오늘의 심층 분석: $DAY_NAME               ║"
echo "╚══════════════════════════════════════════════╝"

case $DAY_OF_WEEK in

# ── 월: UI/UX ─────────────────────────────────────────────────
1)
    run_analysis_loop "component_consistency" \
"frontend/components/ 전체 UI 일관성 분석.
1. 같은 역할인데 다르게 구현된 컴포넌트
2. 색상 하드코딩 vs Tailwind 디자인 토큰 비율
3. 반응형 누락 (고정 폭 26건 추적)
4. 접근성: alt, aria-label, 키보드 네비게이션
5. 로딩/에러/빈 상태 처리 누락
6. Chain Sight 마켓뷰 UX (노드→중심이동→히스토리)
7. 한국 개인 투자자(20~40대) 관점 불편한 점" \
"검증: 190개 중 몇 개 실제 분석했는지, 파일명/라인 근거 있는지"

    run_analysis_loop "mobile_ux_audit" \
"모바일 UX 감사.
1. 고정 폭(w-[NNpx]) 26건 → 모바일 375px overflow 분석
2. 터치 타겟 44x44pt 미만 (thesis 지표 카드, validation 탭, chainsight 노드)
3. 모바일 네비게이션 (hamburger/bottom nav 존재 여부)
4. Recharts 모바일 대응, virtualization
심각도 BLOCKER/MAJOR/MINOR." \
"검증: 실제 Tailwind 클래스 기반 분석인지, 터치 타겟 계산 근거"
    ;;

# ── 화: 데이터 & API ─────────────────────────────────────────
2)
    run_analysis_loop "api_dependency_audit" \
"외부 API 장애 대응 감사.
1. FMP 18파일: 에러 핸들링, 402 처리, rate limit (Starter 300/min)
2. Gemini 28파일: 429 처리, timeout 설정(현재 0/28), JSON 파싱
3. FRED, Neo4j, SEC EDGAR 장애 시 영향
4. Circuit Breaker: 현재 뉴스 3개만 → FMP/Gemini 도입 후보
5. 17:00-18:00 ET FMP 1,015+ 호출 폭주 구간 해소 여부
6. Blast Radius (장애 전파 경로) 업데이트" \
"검증: 실제 파일/라인 기반인지, rate limit 계산 현실적인지, 새 CB 구현 확인"

    run_analysis_loop "data_integrity_audit" \
"데이터 무결성 감사.
1. FK orphan: on_delete=SET_NULL 13곳 → 정리 로직 존재 여부
2. CASCADE 체인: Stock 삭제 시 27+ 테이블 연쇄 → PROTECT 전환 여부
3. Neo4j↔PG 동기화: signals/tasks 실패 재시도, drift 감지
4. UniqueConstraint / update_or_create atomic 적용 현황
5. 시계열 데이터 보존 정책, stale 감지 (72h asof)" \
"검증: on_delete 설정을 실제 models.py에서 확인했는지"
    ;;

# ── 수: 보안 & 성능 ──────────────────────────────────────────
3)
    run_analysis_loop "security_audit" \
"OWASP Top 10 + LLM Top 10 보안 감사.
1. 인증/인가: serverless AllowAny 38개 뷰 해소 여부, permission_classes 누락 47개
2. SECRET_KEY/DEBUG/CORS/ALLOWED_HOSTS — CRITICAL 4건 해소 여부
3. Cypher 인젝션: chainsight/api/views.py:449 f-string 패턴
4. LLM 프롬프트 인젝션: thesis_builder, news, validation 4곳
5. JWT: Access 60분, Refresh 7일, blacklist, 인증 rate limit
6. 에러 노출: DEBUG 가드, 스택트레이스
심각도 CRITICAL/HIGH/MED/LOW/INFO." \
"검증: 각 발견에 파일:라인 있는지, CRITICAL 판정 근거 타당한지"

    run_analysis_loop "performance_audit" \
"API 성능 감사.
1. N+1 쿼리: LeaderComparisonView 90+ DB 히트, IndicatorComparison 2N쿼리
2. 인덱스 누락: NewsArticle.created_at, UserInterest 복합, rag_analysis 3건
3. Serializer: WatchListStock DailyPrice 2N, OverviewTab 6관계, ThesisDetail count()
4. 페이지네이션: 글로벌 설정 미적용 (PAG-01), Stock/User 무제한 반환
5. QuerySet 195건 vs select_related 20건 비율 변화 추적
HIGH/MED/LOW + 수정 난이도." \
"검증: N+1 판단이 실제 QuerySet 코드 기반인지, 수정 제안이 Django ORM에서 가능한지"
    ;;

# ── 목: 비즈니스 로직 ────────────────────────────────────────
4)
    run_analysis_loop "feature_completeness" \
"Stock-Vis 4대 필라 구현 완성도.
1. Chain Sight: 마켓뷰, 에고그래프, 시드노드(Phase B+A→C→D), Heat Score, ForceGraph2D
2. EOD Screening: 47개 시그널, static JSON baking, dollar volume filter
3. News Intelligence: 6단계 파이프라인, MarketAux/Finnhub, Redis CB
4. Thesis Control: Layer A(OLS→칼만)~E, moon-phase, Gemini 원샷 설계
각 기능: ✅완료/🔨진행중/📋설계만/❌미착수. 다음 구현 TOP 3." \
"검증: 설계 문서(docs/)를 실제로 읽고 코드와 대조했는지, ✅/🔨/📋/❌ 판정 정확성"

    run_analysis_loop "indicator_catalog_audit" \
"지표 카탈로그 3곳 동기화.
1. prompt_builder.py INDICATOR_CATALOG (64개)
2. indicator_matcher.py KEYWORD_RULES (현재 11/64 = 17% 커버리지)
3. frontend AddIndicatorSheet.tsx INDICATOR_CATALOG
이름 불일치 4건(금리 3 + 부채비율 1) 해소 여부.
data_params 중 FMP 미존재 2건(foreign_net_buy, institutional_net_buy) 처리 현황.
keyword_rules 커버리지 17%→?% 변화 추적." \
"검증: 실제 딕셔너리 키를 비교했는지, 수치 정확성"

    run_analysis_loop "design_gap_chainsight" \
"Chain Sight 설계서 26개 vs 코드 갭.
docs/chain_sight/plan/ 읽고 chainsight/ 대조.
분류: (A)완전구현 (B)부분구현 (C)미구현 (D)폐기.
redesign_v1이 기존 cs_* 대체하는지 확인.
task_done/*.md와 cross-reference." \
"검증: 설계서를 실제로 읽었는지, 구현률 계산 근거"
    ;;

# ── 금: 아키텍처 ─────────────────────────────────────────────
5)
    run_analysis_loop "api_consistency_audit" \
"DRF API 응답 형식 일관성 감사.
1. success/error 래핑 패턴 (앱별)
2. HTTP 상태 코드 일관성
3. 에러 응답 형식 통일
4. 페이지네이션 적용 여부
앱별 응답 패턴 매트릭스 포함." \
"검증: 모든 views.py 읽었는지, 매트릭스에 빠진 앱 없는지"

    run_analysis_loop "api_docs_audit" \
"API 문서 자동생성 현황.
1. drf-spectacular 설치 여부
2. 전체 엔드포인트 수 (234개 기준) 변화
3. 수동 계약서 3개(chainsight, validation, sec_pipeline) 최신성
4. 도입 시 필요한 작업 목록
5. @extend_schema 데코레이터 사용 현황" \
"검증: 엔드포인트 수가 urls.py 기반인지"

    run_analysis_loop "architecture_evolution" \
"아키텍처 진화 제안.
1. 스케일 시 병목 (현재: 17:00 FMP 폭주, N+1 90+ 히트)
2. 4-layer 데이터 아키텍처 구현도
3. 기술 부채 TOP 5 (구체적 파일과 이유)
4. 솔로 개발자 환경에서 현실적인 다음 단계" \
"검증: 기술 부채가 코드 근거 있는지, 솔로 개발자 현실성"
    ;;

# ── 토: 전략 ─────────────────────────────────────────────────
6)
    run_analysis_loop "competitive_analysis" \
"Stock-Vis 서비스 차별화 분석.
1. 독보적 기능 (Chain Sight 관계 탐색)
2. 증권사 MTS/토스증권/TradingView 대비 차이
3. 한국 시장 특화 부족한 점 (KOSPI, 공시, 외국인 매매)
4. 'signals first, news second' 철학 반영도
5. MVP 출시까지 최소 기능 목록" \
"검증: 코드 근거 기반인지, MVP 범위 현실적인지"

    run_analysis_loop "beat_schedule_audit" \
"Celery Beat 63개 태스크 감사.
1. FMP 300/min 초과 구간 (17:00-18:00 CRITICAL 1,015+ 해소 여부)
2. Gemini 15 RPM 초과 구간
3. neo4j queue 몰림 시간대
4. 글로벌 리미터(10/min) vs Starter(300/min) 불일치 해소 여부
시간대별 API 호출 히트맵." \
"검증: crontab 표현식 기반 계산인지, rate limit 수치 정확성"

    run_analysis_loop "design_gap_remaining" \
"SEC Pipeline + validation + news 설계서 갭.
docs/sec_pipeline/, docs/first_validation_system/, docs/news/ 읽고 코드 대조.
SEC: Track A/B, Gold Set, neo4j_dirty, 17개 PR spec.
Validation: 34개 지표, size bucket peer, Recharts.
분류: (A)/(B)/(C)/(D)." \
"검증: 설계서 실제로 읽었는지"
    ;;

# ── 일: 주간 종합 ────────────────────────────────────────────
7)
    run_analysis_loop "weekly_summary" \
"이번 주 야간 분석 전체 종합.

이번 주 리포트 폴더들을 읽어:
$(for d in $(seq 6 -1 0); do
    WK_YM=$(date -v-${d}d +%Y%m 2>/dev/null || date -d "${d} days ago" +%Y%m)
    WK_D=$(date -v-${d}d +%d 2>/dev/null || date -d "${d} days ago" +%d)
    WK_DIR="$REPORT_BASE/$WK_YM/$WK_D"
    if [ -d "$WK_DIR" ]; then
        echo "- $WK_DIR/"
    fi
done)

포함:
1. 코드 상태 추세 (테스트/TS/린트 일별 변화)
2. 자동 수정 내역 총괄
3. 각 요일 심층 분석 핵심 발견 3줄 요약
4. Opus APPROVED 비율
5. CRITICAL/HIGH 이슈 증감 추세
6. 다음 주 추천 작업 TOP 5" \
"검증: 모든 요일 리포트를 실제로 읽었는지, 추세 분석 정확성"
    ;;

esac


# ================================================================
#  기준선 비교 요약 (매일 생성)
# ================================================================
echo ""
echo "━━ 기준선 비교 요약 생성 ━━"

BASELINE_REPORT="$REPORT_DIR/baseline_comparison.md"

{
    echo "# 📊 기준선 비교 — $DATE"
    echo ""
    echo "## 어제 대비"
    if [ -d "$YEST_REPORT_DIR" ]; then
        echo "어제 리포트: docs/nightly_auto_system/$YEST_YEAR_MONTH/$YEST_DAY/"
        echo ""
        # 어제 스캔이 있으면 핵심 수치 비교
        if [ -f "$YEST_REPORT_DIR/scan.md" ]; then
            echo "| 항목 | 어제 | 오늘 |"
            echo "|------|------|------|"
            echo "| 스캔 결과 | $(head -3 "$YEST_REPORT_DIR/scan.md" | tail -1) | $(head -3 "$REPORT_DIR/scan.md" 2>/dev/null | tail -1) |"
        fi
    else
        echo "어제 리포트 없음"
    fi
    echo ""
    echo "## 지난주 같은 요일 대비"
    if [ -d "$PREV_REPORT_DIR" ]; then
        echo "지난주 리포트: docs/nightly_auto_system/$PREV_YEAR_MONTH/$PREV_DAY/"
        echo ""
        echo "### 심층 분석 비교"
        for report in "$REPORT_DIR"/*.md; do
            FNAME=$(basename "$report")
            if [ "$FNAME" != "morning_report.md" ] && [ "$FNAME" != "scan.md" ] && \
               [ "$FNAME" != "baseline_comparison.md" ] && [ -f "$PREV_REPORT_DIR/$FNAME" ]; then
                echo "- **$FNAME**: 지난주 $(wc -l < "$PREV_REPORT_DIR/$FNAME" | tr -d ' ')줄 → 이번주 $(wc -l < "$report" | tr -d ' ')줄"
            fi
        done
    else
        echo "지난주 리포트 없음 (첫 실행이거나 해당 날짜 데이터 없음)"
    fi
    echo ""
    echo "## 이슈 추적 기준선 (초기 감사 기준)"
    echo ""
    echo "| 카테고리 | 초기 (2026-04-14) | 현재 | 변화 |"
    echo "|----------|------------------|------|------|"
    echo "| 보안 CRITICAL | 5 | 확인 필요 | — |"
    echo "| 보안 HIGH | 12 | 확인 필요 | — |"
    echo "| N+1 쿼리 HIGH | 4 | 확인 필요 | — |"
    echo "| 인덱스 누락 | 7 | 확인 필요 | — |"
    echo "| Circuit Breaker | 뉴스 3개만 | 확인 필요 | — |"
    echo "| Gemini timeout 미설정 | 28/28 | 확인 필요 | — |"
    echo "| serverless AllowAny | 38개 뷰 | 확인 필요 | — |"
    echo "| 글로벌 페이지네이션 | 미설정 | 확인 필요 | — |"
    echo "| FMP 17:00 폭주 | 1,015+ calls | 확인 필요 | — |"
    echo "| 카탈로그 keyword_rules | 17% (11/64) | 확인 필요 | — |"
    echo ""
    echo "*이 테이블은 심층 분석 결과로 '확인 필요' 칸이 채워집니다.*"
} > "$BASELINE_REPORT"

echo "   ✅ 기준선 비교 → $BASELINE_REPORT"


# ================================================================
#  아침 리포트 통합 (Opus)
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  📝 아침 리포트 통합 (Opus)                    ║"
echo "╚══════════════════════════════════════════════╝"

MORNING_REPORT="$REPORT_DIR/morning_report.md"

# 오늘 생성된 모든 리포트 파일 목록
TODAY_REPORTS=$(ls "$REPORT_DIR"/*.md 2>/dev/null | grep -v morning_report | sort)

claude -p "오늘의 모든 분석 결과를 종합해서 아침 리포트를 작성해.

입력 파일들 (전부 읽어):
$(for f in $TODAY_REPORTS; do echo "- $f"; done)

$MORNING_REPORT 에 저장. 형식:

# ☀️ Stock-Vis 아침 리포트 — $DATE ($DAY_NAME)
> 리포트 위치: docs/nightly_auto_system/$YEAR_MONTH/$DAY/

## 한눈에 보기
| 항목 | 상태 | 상세 |
|------|------|------|
| 테스트 | 🟢/🟡/🔴 | ... |
| TypeScript | 🟢/🟡/🔴 | ... |
| 린트 | 🟢/🟡/🔴 | ... |
| 야간 수정 | ✅/❌ | N개 커밋 |
| Codex 판정 | SAFE/CAUTION/BLOCK | ... |

## 🔧 야간 자동 수정
(수정 내역)

## 🔍 Codex 크로스 리뷰
(핵심만)

## 🔬 오늘의 심층 분석: $DAY_NAME
(각 분석의 핵심 발견 3줄)
(Opus 검증: APPROVED/NEEDS_REVISION)

## 📊 기준선 대비 변화
(초기 감사 대비 해결된 것 / 새로 발견된 것)

## ⚠️ 즉시 조치 필요
(CRITICAL/HIGH만)

## 💡 이번 주 제안 TOP 3

## 📋 오늘 할 일
- [ ] nightly/auto-fix-$DATE diff 확인
- [ ] (심층 분석 기반 제안)

## 📂 오늘 생성된 리포트
$(for f in $TODAY_REPORTS; do echo "- $(basename "$f")"; done)

톤: 간결, 핵심만, 실행 가능한 제안." \
    --model opus \
    --permission-mode "$PERMISSION_MODE" \
    > "$LOG_DIR/${DATE}_morning.log" 2>&1

echo "   ✅ 아침 리포트 → $MORNING_REPORT"


# ================================================================
#  리포트를 Git에 커밋
# ================================================================
echo ""
echo "━━ 리포트 커밋 ━━"
cd "$PROJECT_DIR"
git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true

if [ -d "$REPORT_DIR" ] && [ "$(ls -A "$REPORT_DIR")" ]; then
    git add "docs/nightly_auto_system/$YEAR_MONTH/$DAY/" 2>/dev/null || true
    git commit -m "docs(nightly): $DATE ($DAY_NAME) 야간 분석 리포트" 2>/dev/null || true
    echo "   ✅ 리포트 커밋 완료"
else
    echo "   ⏭️ 커밋할 리포트 없음"
fi


# ================================================================
#  완료 + 정리
# ================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  🌙 야간 작업 완료: $(date '+%H:%M:%S')                     ║"
echo "║  리포트: docs/nightly_auto_system/$YEAR_MONTH/$DAY/         ║"
echo "║  아침 리포트: morning_report.md                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 생성된 파일:"
ls -la "$REPORT_DIR"/*.md 2>/dev/null | awk '{print "   " $NF " (" $5 ")"}'

# 중간 파일 정리
rm -f "$WORK_DIR"/*.md "$WORK_DIR"/*.txt "$WORK_DIR"/*.patch 2>/dev/null || true

# 30일 이전 로그 정리
find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true

# 원래 브랜치 복원
git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true

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