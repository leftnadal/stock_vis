#!/bin/bash
# ============================================================
#  아침 리포트 알림 (매일 오전 8시 cron 실행)
#  야간 분석 결과를 개발자에게 전달
# ============================================================

SYSTEM_DIR="$HOME/stock-vis-nightly"
REPORT_DIR="$SYSTEM_DIR/reports"
DATE=$(date +%Y-%m-%d)
FINAL_REPORT="$REPORT_DIR/morning_report_${DATE}.md"

# ── 설정 (하나 이상 활성화) ───────────────────────────────────
SLACK_WEBHOOK=""                  # ← Slack Incoming Webhook URL 입력
DISCORD_WEBHOOK=""                # ← Discord Webhook URL (선택)
NOTIFY_MACOS="true"              # macOS 알림 사용 여부

# ── 리포트 존재 확인 ─────────────────────────────────────────
if [ ! -f "$FINAL_REPORT" ]; then
    echo "❌ 오늘자 리포트 없음: $FINAL_REPORT"
    
    # macOS 알림으로라도 알려줌
    if [ "$NOTIFY_MACOS" = "true" ] && command -v osascript &> /dev/null; then
        osascript -e "display notification \"야간 분석 리포트가 생성되지 않았습니다. 로그를 확인하세요.\" with title \"Stock-Vis ⚠️\" sound name \"Basso\""
    fi
    exit 1
fi

# ── 리포트 내용 읽기 ─────────────────────────────────────────
REPORT_CONTENT=$(cat "$FINAL_REPORT")

# 요약 추출 (한눈에 보기 테이블만)
SUMMARY=$(sed -n '/## 📊 한눈에 보기/,/^## /p' "$FINAL_REPORT" | head -10)

# 상태 이모지 결정
if echo "$REPORT_CONTENT" | grep -q "🔴"; then
    STATUS="🔴 문제 발견"
    URGENCY="urgent"
elif echo "$REPORT_CONTENT" | grep -q "🟡"; then
    STATUS="🟡 확인 필요"
    URGENCY="normal"
else
    STATUS="🟢 정상"
    URGENCY="low"
fi


# ── 방법 1: macOS 네이티브 알림 ──────────────────────────────
if [ "$NOTIFY_MACOS" = "true" ] && command -v osascript &> /dev/null; then
    osascript -e "display notification \"$STATUS — 리포트 확인: cat $FINAL_REPORT\" with title \"Stock-Vis 아침 리포트\" sound name \"Glass\""
    
    # 터미널 열어서 리포트 보여주기 (선택)
    osascript -e "
    tell application \"Terminal\"
        activate
        do script \"echo ''; echo '☀️ Stock-Vis 아침 리포트'; echo ''; cat $FINAL_REPORT; echo ''; echo '---'; echo '브랜치 확인: git diff main..nightly/auto-fix-$DATE'\"
    end tell
    " 2>/dev/null || true
    
    echo "✅ macOS 알림 전송 완료"
fi


# ── 방법 2: Slack Webhook ────────────────────────────────────
if [ -n "$SLACK_WEBHOOK" ]; then
    # Slack은 메시지 길이 제한이 있으므로 요약만 전송
    SLACK_TEXT="*☀️ Stock-Vis 아침 리포트 — ${DATE}*\n\n"
    SLACK_TEXT+="*상태:* ${STATUS}\n\n"
    SLACK_TEXT+="$(echo "$SUMMARY" | head -8)\n\n"
    
    # 수동 확인 필요 항목 추출
    MANUAL_CHECK=$(sed -n '/## ⚠️ 수동 확인 필요/,/^## /p' "$FINAL_REPORT" | head -5)
    if [ -n "$MANUAL_CHECK" ]; then
        SLACK_TEXT+="*⚠️ 수동 확인 필요:*\n${MANUAL_CHECK}\n\n"
    fi
    
    SLACK_TEXT+="전체 리포트: \`cat $FINAL_REPORT\`\n"
    SLACK_TEXT+="수정 diff: \`git diff main..nightly/auto-fix-${DATE}\`"

    # JSON 이스케이프
    SLACK_JSON=$(echo "$SLACK_TEXT" | python3 -c "import sys,json; print(json.dumps({'text': sys.stdin.read()}))")
    
    curl -s -X POST \
        -H 'Content-type: application/json' \
        --data "$SLACK_JSON" \
        "$SLACK_WEBHOOK" \
        > /dev/null 2>&1
    
    echo "✅ Slack 알림 전송 완료"
fi


# ── 방법 3: Discord Webhook ──────────────────────────────────
if [ -n "$DISCORD_WEBHOOK" ]; then
    # Discord 메시지 (2000자 제한)
    DISCORD_MSG="**☀️ Stock-Vis 아침 리포트 — ${DATE}**\n\n"
    DISCORD_MSG+="**상태:** ${STATUS}\n\n"
    DISCORD_MSG+="$(echo "$SUMMARY" | head -8)\n\n"
    DISCORD_MSG+="전체 리포트: \`cat $FINAL_REPORT\`"

    DISCORD_JSON=$(python3 -c "import json; print(json.dumps({'content': '''$DISCORD_MSG'''}))")
    
    curl -s -X POST \
        -H 'Content-type: application/json' \
        --data "$DISCORD_JSON" \
        "$DISCORD_WEBHOOK" \
        > /dev/null 2>&1
    
    echo "✅ Discord 알림 전송 완료"
fi


# ── 방법 4: 로컬 HTML 리포트 (브라우저 자동 열기) ────────────
HTML_REPORT="$REPORT_DIR/morning_report_${DATE}.html"

cat > "$HTML_REPORT" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Stock-Vis 아침 리포트</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #1a1a2e; color: #e0e0e0; }
  h1 { color: #64ffda; }
  h2 { color: #82b1ff; border-bottom: 1px solid #333; padding-bottom: 8px; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th, td { border: 1px solid #444; padding: 10px; text-align: left; }
  th { background: #16213e; color: #64ffda; }
  tr:nth-child(even) { background: #16213e; }
  code { background: #0f3460; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #0f3460; padding: 16px; border-radius: 8px; overflow-x: auto; }
  .status-good { color: #64ffda; } .status-warn { color: #ffd54f; } .status-bad { color: #ff5252; }
  .summary-box { background: #16213e; border-left: 4px solid #64ffda; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0; }
</style>
</head>
<body>
HTMLEOF

# Markdown → 간단 HTML 변환 (python3 사용)
python3 -c "
import sys, re

with open('$FINAL_REPORT', 'r') as f:
    content = f.read()

# 간단한 Markdown → HTML
content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.M)
content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.M)
content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.M)
content = re.sub(r'^\- \[ \] (.+)$', r'<label><input type=\"checkbox\"> \1</label><br>', content, flags=re.M)
content = re.sub(r'^\- (.+)$', r'<li>\1</li>', content, flags=re.M)
content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
content = re.sub(r'\`(.+?)\`', r'<code>\1</code>', content)

# 테이블 처리
lines = content.split('\n')
in_table = False
result = []
for line in lines:
    if '|' in line and not line.strip().startswith('#'):
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if all(c.replace('-','').strip() == '' for c in cells):
            continue
        if not in_table:
            result.append('<table>')
            result.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
            in_table = True
        else:
            result.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    else:
        if in_table:
            result.append('</table>')
            in_table = False
        if line.strip() == '':
            result.append('<br>')
        else:
            result.append(line)
if in_table:
    result.append('</table>')

print('\n'.join(result))
" >> "$HTML_REPORT" 2>/dev/null || cat "$FINAL_REPORT" >> "$HTML_REPORT"

echo "</body></html>" >> "$HTML_REPORT"

# 브라우저에서 열기 (macOS)
if command -v open &> /dev/null; then
    open "$HTML_REPORT" 2>/dev/null || true
    echo "✅ 브라우저에서 리포트 열기 완료"
fi


echo ""
echo "📄 리포트 파일: $FINAL_REPORT"
echo "🌐 HTML 리포트: $HTML_REPORT"
echo "📌 상태: $STATUS"