#!/bin/bash
# ============================================================
#  아침 리포트 알림 v3 — 매일 오전 8시 cron 실행
#  리포트 경로: docs/nightly_auto_system/YYYYMM/DD/
# ============================================================

PROJECT_DIR="$HOME/stock-vis"
YEAR_MONTH=$(date +%Y%m)
DAY=$(date +%d)
DATE=$(date +%Y-%m-%d)
REPORT_DIR="$PROJECT_DIR/docs/nightly_auto_system/$YEAR_MONTH/$DAY"
MORNING_REPORT="$REPORT_DIR/morning_report.md"

# ── 설정 ──────────────────────────────────────────────────────
SLACK_WEBHOOK=""
DISCORD_WEBHOOK=""
NOTIFY_MACOS="true"

# ── 리포트 확인 ──────────────────────────────────────────────
if [ ! -f "$MORNING_REPORT" ]; then
    if [ "$NOTIFY_MACOS" = "true" ] && command -v osascript &> /dev/null; then
        osascript -e "display notification \"야간 분석 리포트 없음. 로그 확인 필요.\" with title \"Stock-Vis ⚠️\" sound name \"Basso\""
    fi
    exit 1
fi

REPORT_CONTENT=$(cat "$MORNING_REPORT")

# 상태 판별
if echo "$REPORT_CONTENT" | grep -q "🔴"; then
    STATUS="🔴 문제 발견"
elif echo "$REPORT_CONTENT" | grep -q "🟡"; then
    STATUS="🟡 확인 필요"
else
    STATUS="🟢 정상"
fi

# 오늘 리포트 파일 개수
REPORT_COUNT=$(ls "$REPORT_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

# ── macOS 알림 ───────────────────────────────────────────────
if [ "$NOTIFY_MACOS" = "true" ] && command -v osascript &> /dev/null; then
    osascript -e "display notification \"$STATUS | 리포트 ${REPORT_COUNT}개 생성\" with title \"Stock-Vis 아침 리포트\" subtitle \"$DATE\" sound name \"Glass\""

    osascript -e "
    tell application \"Terminal\"
        activate
        do script \"echo ''; echo '☀️ Stock-Vis 아침 리포트 — $DATE'; echo '📂 docs/nightly_auto_system/$YEAR_MONTH/$DAY/'; echo ''; cat $MORNING_REPORT; echo ''; echo '---'; echo '📂 전체 리포트:'; ls -la $REPORT_DIR/*.md; echo ''; echo '🔧 수정 브랜치: git diff main..nightly/auto-fix-$DATE'\"
    end tell
    " 2>/dev/null || true
fi

# ── Slack ─────────────────────────────────────────────────────
if [ -n "$SLACK_WEBHOOK" ]; then
    SUMMARY=$(sed -n '/## 한눈에 보기/,/^## /p' "$MORNING_REPORT" | head -10)

    SLACK_TEXT="*☀️ Stock-Vis 아침 리포트 — ${DATE}*\n"
    SLACK_TEXT+="*상태:* ${STATUS} | 리포트 ${REPORT_COUNT}개\n"
    SLACK_TEXT+="*경로:* \`docs/nightly_auto_system/$YEAR_MONTH/$DAY/\`\n\n"
    SLACK_TEXT+="$(echo "$SUMMARY" | head -8)\n\n"

    URGENT=$(sed -n '/## ⚠️ 즉시 조치/,/^## /p' "$MORNING_REPORT" | head -5)
    [ -n "$URGENT" ] && SLACK_TEXT+="*⚠️ 즉시 조치:*\n${URGENT}\n"

    SLACK_JSON=$(echo "$SLACK_TEXT" | python3 -c "import sys,json; print(json.dumps({'text': sys.stdin.read()}))")
    curl -s -X POST -H 'Content-type: application/json' --data "$SLACK_JSON" "$SLACK_WEBHOOK" > /dev/null 2>&1
fi

# ── Discord ───────────────────────────────────────────────────
if [ -n "$DISCORD_WEBHOOK" ]; then
    DISCORD_MSG="**☀️ Stock-Vis 아침 리포트 — ${DATE}**\n${STATUS} | 리포트 ${REPORT_COUNT}개\n경로: \`docs/nightly_auto_system/$YEAR_MONTH/$DAY/\`"
    DISCORD_JSON=$(python3 -c "import json; print(json.dumps({'content': '''$DISCORD_MSG'''}))")
    curl -s -X POST -H 'Content-type: application/json' --data "$DISCORD_JSON" "$DISCORD_WEBHOOK" > /dev/null 2>&1
fi

# ── HTML 리포트 ───────────────────────────────────────────────
HTML_REPORT="$REPORT_DIR/morning_report.html"

cat > "$HTML_REPORT" << 'HTMLHEAD'
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Stock-Vis 아침 리포트</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #1a1a2e; color: #e0e0e0; }
  h1 { color: #64ffda; } h2 { color: #82b1ff; border-bottom: 1px solid #333; padding-bottom: 8px; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th, td { border: 1px solid #444; padding: 10px; text-align: left; }
  th { background: #16213e; color: #64ffda; }
  tr:nth-child(even) { background: #16213e; }
  code { background: #0f3460; padding: 2px 6px; border-radius: 4px; }
  pre { background: #0f3460; padding: 16px; border-radius: 8px; overflow-x: auto; }
  a { color: #82b1ff; }
  .file-list { background: #16213e; padding: 12px; border-radius: 8px; margin: 8px 0; }
</style>
</head>
<body>
HTMLHEAD

python3 -c "
import re
with open('$MORNING_REPORT', 'r') as f:
    content = f.read()
content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.M)
content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.M)
content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.M)
content = re.sub(r'^\- \[ \] (.+)$', r'<label><input type=\"checkbox\"> \1</label><br>', content, flags=re.M)
content = re.sub(r'^\- (.+)$', r'<li>\1</li>', content, flags=re.M)
content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
content = re.sub(r'\`(.+?)\`', r'<code>\1</code>', content)
lines = content.split('\n')
in_table = False; result = []
for line in lines:
    if '|' in line and not line.strip().startswith('#'):
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if all(c.replace('-','').strip() == '' for c in cells): continue
        if not in_table:
            result.append('<table><tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>'); in_table = True
        else:
            result.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    else:
        if in_table: result.append('</table>'); in_table = False
        if line.strip() == '': result.append('<br>')
        else: result.append(line)
if in_table: result.append('</table>')
print('\n'.join(result))
" >> "$HTML_REPORT" 2>/dev/null || cat "$MORNING_REPORT" >> "$HTML_REPORT"

echo "<hr><div class='file-list'><strong>📂 리포트 목록:</strong><ul>" >> "$HTML_REPORT"
for f in "$REPORT_DIR"/*.md; do
    echo "<li>$(basename "$f")</li>" >> "$HTML_REPORT"
done
echo "</ul></div></body></html>" >> "$HTML_REPORT"

if command -v open &> /dev/null; then
    open "$HTML_REPORT" 2>/dev/null || true
fi

echo ""
echo "📄 경로: docs/nightly_auto_system/$YEAR_MONTH/$DAY/"
echo "📌 상태: $STATUS"
echo "📊 리포트: ${REPORT_COUNT}개"