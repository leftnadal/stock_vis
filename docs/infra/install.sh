#!/bin/bash
# ============================================================
#  Stock-Vis 야간 자동화 v3 설치
# ============================================================

set -euo pipefail
SYSTEM_DIR="$HOME/stock-vis-nightly"
PROJECT_DIR="$HOME/stock-vis"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Stock-Vis 야간 자동화 v3 설치                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Claude Code
echo "1️⃣  Claude Code..."
if command -v claude &> /dev/null; then
    echo "   ✅ $(claude --version 2>/dev/null || echo 'installed')"
else
    echo "   ❌ npm i -g @anthropic-ai/claude-code"; exit 1
fi

# 2. 프로젝트
echo "2️⃣  프로젝트..."
if [ -d "$PROJECT_DIR" ]; then
    echo "   ✅ $PROJECT_DIR"
else
    echo "   ❌ PROJECT_DIR을 nightly_v3.sh에서 수정하세요."; exit 1
fi

# 3. 디렉토리
echo "3️⃣  디렉토리..."
mkdir -p "$SYSTEM_DIR"/{work,logs}
mkdir -p "$PROJECT_DIR/docs/nightly_auto_system"
echo "   ✅ $SYSTEM_DIR/{work,logs}"
echo "   ✅ $PROJECT_DIR/docs/nightly_auto_system/"

# 4. 권한
echo "4️⃣  실행 권한..."
chmod +x "$SYSTEM_DIR"/*.sh
echo "   ✅ 완료"

# 5. Codex
echo "5️⃣  Codex (선택)..."
if command -v codex &> /dev/null; then
    echo "   ✅ Codex 설치됨"
else
    echo "   ⏭️ 미설치 (Phase 4 스킵됨)"
fi

# 6. crontab
echo "6️⃣  crontab..."
if crontab -l 2>/dev/null | grep -q "nightly_v3"; then
    echo "   ✅ 이미 등록됨"
else
    read -p "   등록할까요? (y/n): " CONFIRM
    if [ "$CONFIRM" = "y" ]; then
        CRON_PATH=$(echo $PATH)
        (crontab -l 2>/dev/null; cat << EOF

# Stock-Vis 야간 자동화 v3
0 23 * * * PATH=$CRON_PATH $SYSTEM_DIR/nightly_v3.sh >> $SYSTEM_DIR/logs/cron.log 2>&1
0  8 * * * PATH=$CRON_PATH $SYSTEM_DIR/morning_notify.sh >> $SYSTEM_DIR/logs/cron_morning.log 2>&1
EOF
        ) | crontab -
        echo "   ✅ 등록 완료"
    fi
fi

# 7. .gitignore
echo "7️⃣  .gitignore..."
cd "$PROJECT_DIR"
if ! grep -q "nightly_auto_system" .gitignore 2>/dev/null; then
    read -p "   docs/nightly_auto_system/ 을 Git에 포함할까요? (y=포함/n=제외): " GIT_INCLUDE
    if [ "$GIT_INCLUDE" = "n" ]; then
        echo "docs/nightly_auto_system/" >> .gitignore
        echo "   ✅ .gitignore에 추가"
    else
        echo "   ✅ Git에 포함 (리포트 이력 추적)"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 설치 완료!"
echo ""
echo "📂 리포트 경로: $PROJECT_DIR/docs/nightly_auto_system/YYYYMM/DD/"
echo "📂 로그 경로:   $SYSTEM_DIR/logs/"
echo ""
echo "🕐 스케줄: 매일 23:00 분석 → 08:00 알림"
echo ""
echo "테스트: $SYSTEM_DIR/nightly_v3.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"