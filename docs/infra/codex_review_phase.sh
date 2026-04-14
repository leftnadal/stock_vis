# ============================================================
#  Codex 리뷰 Phase — nightly_v2.sh의 Phase 3 뒤에 삽입
#
#  매일 작업 흐름:
#    Phase 1: 코드 스캔 (Haiku)
#    Phase 2: 자동 수정 (Sonnet)
#    Phase 3: 수정 검증 (Haiku)
#    Phase 4: ★ Codex 크로스 리뷰 (GPT-5-Codex) ← 이것
#    Phase 5: 요일별 심층 분석 (Sonnet↔Opus 루프)
#    Phase 최종: 아침 리포트 통합 (Opus)
# ============================================================


# ── Phase 4: Codex 크로스 리뷰 ────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Phase 4: Codex 크로스 리뷰 (GPT-5-Codex)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CODEX_REPORT="$REPORT_DIR/daily/codex_review_${DATE}.md"
CODEX_LOG="$LOG_DIR/${DATE}_codex.log"

if ! command -v codex &> /dev/null; then
    echo "   ⚠️ codex CLI 미설치. Phase 4 스킵."
    echo "   설치: npm i -g @openai/codex"
    echo "SKIPPED: codex not installed" > "$CODEX_REPORT"
else
    # ── 4-1. 야간 수정 브랜치가 있으면 그 diff를 리뷰 ────────
    if git show-ref --verify --quiet "refs/heads/$FIX_BRANCH"; then

        echo "   📋 4-1: 야간 자동 수정 diff 리뷰..."

        # diff를 파일로 추출
        DIFF_FILE="$WORK_DIR/nightly_diff_${DATE}.patch"
        git diff "$ORIGINAL_BRANCH..$FIX_BRANCH" > "$DIFF_FILE" 2>/dev/null

        if [ -s "$DIFF_FILE" ]; then
            codex exec \
                --approval-mode full-auto \
                --output-last-message "$WORK_DIR/codex_diff_review_${DATE}.txt" \
                "아래 diff는 오늘 밤 Claude가 자동으로 수정한 코드야.
이 변경사항을 리뷰해줘.

$(head -500 "$DIFF_FILE")

리뷰 관점:
1. 의도하지 않은 동작 변경이 있는지
2. 타입 안전성이 오히려 나빠진 곳
3. 테스트 수정이 실제 버그를 숨기는지 (테스트를 약화시킨 건 아닌지)
4. import 제거가 실제로 사용되는 심볼을 지운 건 아닌지
5. 전체적으로 머지해도 안전한지 (SAFE / CAUTION / BLOCK)

한국어로 답변해." \
                >> "$CODEX_LOG" 2>&1

            echo "   ✅ diff 리뷰 완료"
        else
            echo "   ⏭️ diff 없음. 스킵."
        fi
    fi

    # ── 4-2. 전체 코드베이스 스팟 리뷰 ────────────────────────
    echo "   📋 4-2: 코드베이스 스팟 리뷰..."

    # 최근 변경된 파일 중 핵심 파일만 리뷰
    CHANGED_FILES=$(git log --since="48 hours ago" --name-only --pretty=format: | sort -u | grep -E '\.(py|tsx?|jsx?)$' | head -15)

    if [ -n "$CHANGED_FILES" ]; then
        codex exec \
            --approval-mode read-only \
            --output-last-message "$WORK_DIR/codex_spot_review_${DATE}.txt" \
            "최근 48시간 내 변경된 아래 파일들을 리뷰해줘:

$CHANGED_FILES

각 파일에 대해:
1. 잠재적 버그 (null 참조, 경계값, race condition)
2. 보안 이슈 (인젝션, 인증 우회, 시크릿 노출)
3. 성능 문제 (N+1, 불필요한 루프, 큰 메모리 할당)
4. 설계 개선점 (DRY 위반, 결합도, 책임 분리)

P0(즉시 수정)/P1(이번 주)/P2(나중에)로 분류해.
한국어로 답변해." \
            >> "$CODEX_LOG" 2>&1

        echo "   ✅ 스팟 리뷰 완료"
    else
        echo "   ⏭️ 최근 변경 파일 없음. 스킵."
        echo "변경 파일 없음" > "$WORK_DIR/codex_spot_review_${DATE}.txt"
    fi

    # ── 4-3. 리포트 통합 ──────────────────────────────────────
    {
        echo "# 🔍 Codex 크로스 리뷰 — $DATE"
        echo ""
        echo "*모델: GPT-5-Codex (OpenAI)*"
        echo "*목적: Claude 분석의 크로스 체크, 다른 모델 관점에서의 blind spot 발견*"
        echo ""

        if [ -f "$WORK_DIR/codex_diff_review_${DATE}.txt" ]; then
            echo "## 야간 자동 수정 diff 리뷰"
            echo ""
            cat "$WORK_DIR/codex_diff_review_${DATE}.txt"
            echo ""
        fi

        if [ -f "$WORK_DIR/codex_spot_review_${DATE}.txt" ]; then
            echo "## 코드베이스 스팟 리뷰"
            echo ""
            cat "$WORK_DIR/codex_spot_review_${DATE}.txt"
            echo ""
        fi

        echo "---"
        echo "*이 리뷰는 Claude와 독립적으로 실행되었습니다.*"
    } > "$CODEX_REPORT"

    echo "   📄 Codex 리포트: $CODEX_REPORT"

    # 중간 파일 정리
    rm -f "$WORK_DIR/codex_"*"_${DATE}.txt" "$WORK_DIR/nightly_diff_${DATE}.patch" 2>/dev/null || true
fi