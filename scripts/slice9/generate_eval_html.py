"""Slice 9 Part 2 §2 — manual eval HTML 평가 페이지 생성.

B3 결정: 단일 HTML 파일 + 라디오 버튼 + localStorage + export.
영구 자산: Slice 10/11 manual eval 재사용 가능 (cases.json 구조 일관 시).

Python str.format() 사용 — 모든 CSS/JS 중괄호는 {{, }}로 escape.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Slice 9 Manual Eval — Stock-Vis Portfolio Coach</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 24px; line-height: 1.6; color: #333; }}
  .header {{ position: sticky; top: 0; background: #fff; padding: 16px 0; border-bottom: 2px solid #ddd; z-index: 10; }}
  .progress {{ height: 12px; background: #eee; border-radius: 6px; overflow: hidden; margin: 8px 0; }}
  .progress-bar {{ height: 100%; background: linear-gradient(90deg, #4caf50, #8bc34a); transition: width 0.3s; }}
  .case-meta {{ background: #f5f5f5; padding: 12px; border-radius: 8px; margin: 16px 0; font-size: 14px; }}
  .case-meta span {{ margin-right: 16px; }}
  .question {{ background: #e3f2fd; padding: 12px; border-radius: 8px; margin: 16px 0; font-weight: 500; }}
  .commentary {{ background: #fff; border: 1px solid #ddd; padding: 16px; border-radius: 8px; margin: 16px 0; white-space: pre-wrap; }}
  .action-items {{ background: #fff3e0; padding: 12px; border-radius: 8px; margin: 16px 0; }}
  .action-items ul {{ margin: 8px 0; padding-left: 24px; }}
  .rationale {{ background: #fafafa; border-left: 4px solid #888; padding: 12px; margin: 16px 0; font-size: 13px; color: #666; }}
  .rationale-label {{ font-weight: 600; color: #888; }}
  .rating-section {{ background: #f1f8e9; padding: 16px; border-radius: 8px; margin: 24px 0; }}
  .rating-row {{ display: flex; align-items: center; gap: 12px; margin: 8px 0; }}
  .rating-label {{ width: 120px; font-weight: 500; }}
  .rating-options label {{ margin-right: 16px; cursor: pointer; }}
  .nav-buttons {{ display: flex; gap: 12px; margin-top: 24px; justify-content: space-between; }}
  button {{ padding: 10px 20px; font-size: 14px; border: none; border-radius: 6px; cursor: pointer; background: #2196f3; color: #fff; }}
  button:disabled {{ background: #ccc; cursor: not-allowed; }}
  button.export {{ background: #4caf50; padding: 14px 24px; font-size: 16px; font-weight: 600; }}
  button.export:disabled {{ background: #ccc; }}
  .comment-input {{ width: 100%; padding: 8px; font-size: 14px; border: 1px solid #ddd; border-radius: 6px; min-height: 60px; box-sizing: border-box; }}
  .status-badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px; }}
  .status-complete {{ background: #4caf50; color: #fff; }}
  .status-incomplete {{ background: #ff9800; color: #fff; }}
  .auto-score {{ font-size: 12px; color: #999; margin-left: 8px; }}
</style>
</head>
<body>

<div class="header">
  <h1>Slice 9 Manual Eval <span id="case-counter">1 / 26</span></h1>
  <div class="progress"><div class="progress-bar" id="progress-bar" style="width: 0%"></div></div>
  <div>완료: <span id="completed-count">0</span> / 26</div>
</div>

<div id="case-content"></div>

<div class="nav-buttons">
  <button id="prev-btn" onclick="prevCase()">← 이전</button>
  <button id="next-btn" onclick="nextCase()">다음 →</button>
</div>

<div style="text-align: center; margin-top: 32px;">
  <button id="export-btn" class="export" onclick="exportResults()" disabled>
    Export to JSON (모든 평가 완료 시 활성화)
  </button>
</div>

<script>
const CASES = {cases_json};
const STORAGE_KEY = "slice9_manual_eval_v1";

let currentIndex = 0;
let evaluations = loadEvaluations();

function loadEvaluations() {{
  try {{
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  }} catch (e) {{}}
  return CASES.map(c => ({{
    case_id: c.case_id,
    manual_naturalness: null,
    manual_insight: null,
    manual_comment: ""
  }}));
}}

function saveEvaluations() {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(evaluations));
}}

function renderCase() {{
  const c = CASES[currentIndex];
  const e = evaluations[currentIndex];

  document.getElementById("case-counter").textContent = `${{currentIndex + 1}} / ${{CASES.length}}`;

  const completedCount = evaluations.filter(ev => ev.manual_naturalness !== null && ev.manual_insight !== null).length;
  document.getElementById("completed-count").textContent = completedCount;
  document.getElementById("progress-bar").style.width = `${{(completedCount / CASES.length) * 100}}%`;
  document.getElementById("export-btn").disabled = completedCount < CASES.length;

  const isComplete = e.manual_naturalness !== null && e.manual_insight !== null;
  const statusBadge = isComplete
    ? '<span class="status-badge status-complete">완료</span>'
    : '<span class="status-badge status-incomplete">미평가</span>';

  const actionItemsHtml = c.action_items.map(a =>
    `<li><strong>${{escapeHtml(a.title)}}</strong> (${{a.priority}}) — ${{escapeHtml(a.description)}}</li>`
  ).join("");

  document.getElementById("case-content").innerHTML = `
    <div class="case-meta">
      <span><strong>${{c.case_id}}</strong>${{statusBadge}}</span>
      <span>시나리오: ${{escapeHtml(c.case_name)}}</span>
      <span>원본 모델: ${{c.original_model}}</span>
      <span class="auto-score">자동 patterns score: ${{c.auto_specificity_score}}/5</span>
    </div>

    <div class="question"><strong>질문:</strong> ${{escapeHtml(c.question)}}</div>

    <div class="commentary">
      <strong>답변:</strong><br>
      ${{escapeHtml(c.commentary)}}
    </div>

    <div class="action-items">
      <strong>액션 아이템:</strong>
      <ul>${{actionItemsHtml}}</ul>
    </div>

    <div class="rationale">
      <span class="rationale-label">참고 — Sonnet 자체 평가 rationale (점수: ${{c.rationale_score}}/5):</span><br>
      ${{escapeHtml(c.rationale_text)}}
    </div>

    <div class="rating-section">
      <div class="rating-row">
        <div class="rating-label">Naturalness:</div>
        <div class="rating-options">
          ${{[1,2,3,4,5].map(n => `
            <label>
              <input type="radio" name="naturalness" value="${{n}}" ${{e.manual_naturalness === n ? "checked" : ""}}
                     onchange="updateRating('naturalness', ${{n}})">
              ${{n}}
            </label>
          `).join("")}}
        </div>
      </div>
      <div class="rating-row">
        <div class="rating-label">Insight:</div>
        <div class="rating-options">
          ${{[1,2,3,4,5].map(n => `
            <label>
              <input type="radio" name="insight" value="${{n}}" ${{e.manual_insight === n ? "checked" : ""}}
                     onchange="updateRating('insight', ${{n}})">
              ${{n}}
            </label>
          `).join("")}}
        </div>
      </div>
      <div class="rating-row">
        <div class="rating-label">Comment (선택):</div>
        <textarea class="comment-input" id="comment-input"
                  onchange="updateComment(this.value)">${{escapeHtml(e.manual_comment)}}</textarea>
      </div>
    </div>
  `;

  document.getElementById("prev-btn").disabled = currentIndex === 0;
  document.getElementById("next-btn").disabled = currentIndex === CASES.length - 1;
}}

function updateRating(field, value) {{
  evaluations[currentIndex][`manual_${{field}}`] = value;
  saveEvaluations();
  renderCase();
}}

function updateComment(value) {{
  evaluations[currentIndex].manual_comment = value;
  saveEvaluations();
}}

function nextCase() {{
  if (currentIndex < CASES.length - 1) {{
    currentIndex++;
    renderCase();
  }}
}}

function prevCase() {{
  if (currentIndex > 0) {{
    currentIndex--;
    renderCase();
  }}
}}

function exportResults() {{
  const merged = CASES.map((c, i) => ({{
    ...c,
    manual_naturalness: evaluations[i].manual_naturalness,
    manual_insight: evaluations[i].manual_insight,
    manual_comment: evaluations[i].manual_comment,
  }}));
  const blob = new Blob([JSON.stringify(merged, null, 2)], {{ type: "application/json" }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "slice9_manual_eval_results.json";
  a.click();
  URL.revokeObjectURL(url);
}}

function escapeHtml(str) {{
  if (str == null) return "";
  return String(str).replace(/[&<>"']/g, m => ({{
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }})[m]);
}}

renderCase();
</script>
</body>
</html>
"""


def generate_html(cases: list[dict], output_path: Path) -> None:
    """HTML 페이지 생성. cases 데이터를 inline embed.

    cases_json은 </script> 토큰 분할로 XSS 회피 (case 본문에 </script>가
    포함될 경우 HTML 컨텍스트 깨짐 방지).
    """
    cases_json = json.dumps(cases, ensure_ascii=False).replace("</", "<\\/")
    html = HTML_TEMPLATE.format(cases_json=cases_json)
    output_path.write_text(html, encoding="utf-8")


def main() -> int:
    cases_path = REPO_ROOT / "docs/portfolio/coach/slice9/part2/manual_eval/cases.json"
    output_path = REPO_ROOT / "docs/portfolio/coach/slice9/part2/manual_eval/eval_page.html"

    cases = json.loads(cases_path.read_text())
    generate_html(cases, output_path)

    print(f"HTML 평가 페이지 생성 완료: {output_path.relative_to(REPO_ROOT)}")
    print(f"브라우저에서 열기: file://{output_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
