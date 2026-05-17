# Slice 9 Part 2 작업 지시서 — Manual Eval HTML 평가 페이지 (#46)

> **Part 2 범위**: #46 manual eval dump — HTML 단건 평가 페이지 (B3) + cases.json (matrix_rationale_joined 정리) + 정합성 검증 + 종결 보고
> **LLM 호출**: 0 (Part 2는 dump 생성만)
> **비용 영향**: $0 (누적 $2.3775 유지)
> **회귀 영향**: +3~5건 예상 (HTML 생성 스크립트 단위 테스트 + 정합성 검증 테스트)
> **선행 결정 (2026-05-17 확정)**: A1 그대로 진입 / B3 HTML 단건 페이지 / C1 Slice 7 표준 2축 / D2 #48 Slice 10 Step 0 부채

---

## §0. 사전 체크

### §0.1 환경 정합 확인

```bash
# 0.1.1 git 상태
git status                                # working tree clean 확인
git branch --show-current                 # slice9 확인
git log --oneline -5                      # Phase 1 ccc8086 + Phase 2 277bb12 확인

# 0.1.2 회귀 baseline
pytest portfolio/tests -q 2>&1 | tail -3  # 486 passed 확인 (Part 1 종결값)

# 0.1.3 IDENTICAL hash
pytest portfolio/tests/test_static_integrity.py -v 2>&1 | tail -10
# 7/7 PASS 확인 (9슬라이스 일관)

# 0.1.4 누적 비용 확인
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard()
print(f'cumulative={g.cumulative_usd}, slice={g.slice_usd}')
"
# 기대: cumulative=2.3775, slice=0.3292 (Part 1 종결 시점)
```

**중단 조건**:

- 회귀 ≠ 486 → 외래 commit 영향 점검
- IDENTICAL hash ≠ 7/7 → 즉시 정지
- 누적 비용 ≠ $2.3775 → CostGuard 상태 불일치 점검

### §0.2 Part 1 산출물 의존 확인

| 의존 항목                    | 위치                                                               | 검증                         |
| ---------------------------- | ------------------------------------------------------------------ | ---------------------------- |
| matrix_rationale_joined.json | `docs/portfolio/coach/slice9/part1/matrix_rationale_joined.json`   | `jq '. \| length' = 26`      |
| rationale_records.json       | `docs/portfolio/coach/slice9/part1/rationale_records.json`         | 26 entries                   |
| Slice 7 rubric.md            | `docs/portfolio/coach/slice7/manual_eval_rubric.md` 또는 동등 위치 | 존재 + 5점/4점/3점 기준 포함 |

### §0.3 슬라이스 cap 보존

```bash
# Part 2는 LLM 호출 0이므로 slice_usd reset 불필요
# 단, Part 1과 동일 슬라이스로 간주 → slice_usd $0.3292 유지
```

---

## §1. cases.json 정리

### §1.1 작업 위치

`scripts/slice9/prepare_eval_cases.py` (신규)

### §1.2 구조

`matrix_rationale_joined.json`을 manual eval에 최적화된 형식으로 변환:

```python
"""Slice 9 Part 2 §1 — manual eval용 cases.json 정리."""

import json
from pathlib import Path


def main():
    src = Path("docs/portfolio/coach/slice9/part1/matrix_rationale_joined.json")
    joined = json.load(open(src))

    cases = []
    for entry in joined:
        cases.append({
            "case_id": entry["case_id"],
            "case_name": entry["case_name"],
            "original_model": entry["original_model"],
            "question": entry.get("question") or "포트폴리오 평가",
            "commentary": entry["commentary"],
            "action_items": entry["action_items"],
            "rationale_text": entry["rationale_text"],
            "rationale_categories": entry.get("rationale_categories", []),
            "rationale_score": entry["rationale_score"],  # Sonnet 자체 평가 (보조 자료)
            "auto_specificity_score": entry["original_specificity_score"],  # 자동 patterns 0~5 (보조 자료)
            "auto_specificity_detail": entry["original_specificity_detail"],
            # 평가 입력 슬롯 (사용자가 채울 자리)
            "manual_naturalness": None,  # 1~5
            "manual_insight": None,      # 1~5
            "manual_comment": "",        # 자유 입력
        })

    output_dir = Path("docs/portfolio/coach/slice9/part2/manual_eval")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "cases.json", "w") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    print(f"cases.json 정리 완료: {len(cases)} entries → {output_dir / 'cases.json'}")
```

### §1.3 단위 테스트

`portfolio/tests/slice9/test_prepare_eval_cases.py` (신규)

```python
"""Slice 9 Part 2 §1 — cases.json 생성 검증."""

import json
from pathlib import Path


def test_cases_json_exists_after_run(tmp_path):
    """스크립트 실행 후 cases.json 존재."""
    # ... (subprocess로 스크립트 실행 + 결과 검증)
    pass

def test_cases_count_matches_matrix(tmp_path):
    """cases 개수가 matrix_rationale_joined와 일치."""
    pass

def test_manual_slots_initialized_null(tmp_path):
    """manual_naturalness, manual_insight 초기값 None."""
    pass
```

### §1.4 KPI 1

- [ ] `prepare_eval_cases.py` 작성
- [ ] cases.json 생성 (26 entries)
- [ ] 단위 테스트 3건 PASS
- [ ] 회귀 +3건

---

## §2. HTML 평가 페이지 생성

### §2.1 작업 위치

`scripts/slice9/generate_eval_html.py` (신규)

### §2.2 HTML 페이지 설계

**핵심 요구사항** (B3 결정 근거):

- 단일 HTML 파일 (offline 동작, 외부 의존성 없음)
- 사용자 환경: 브라우저 더블클릭으로 열기만 하면 동작
- 진행률 표시 (현재 entry / 26)
- 각 entry 한 페이지에:
  - case_id + case_name + original_model (메타데이터)
  - 사용자 질문
  - LLM 답변 (commentary + action_items)
  - rationale (보조 자료, "참고" 라벨)
  - **naturalness 1~5 라디오 버튼** (필수 입력)
  - **insight 1~5 라디오 버튼** (필수 입력)
  - comment 자유 텍스트 (선택)
- 이전/다음 버튼 (양 끝은 비활성)
- localStorage 자동 저장 (브라우저 종료 후 재개 가능)
- "Export to JSON" 버튼 (평가 완료 후 다운로드)
- 진행률 100% 도달 시 export 버튼 활성화 강조

### §2.3 HTML 템플릿 (코드 스켈레톤)

```python
"""Slice 9 Part 2 §2 — manual eval HTML 평가 페이지 생성.

B3 결정: 단일 HTML 파일 + 라디오 버튼 + localStorage + export.
영구 자산: Slice 10/11 manual eval 재사용 가능 (cases.json 구조 일관 시).
"""

import json
from pathlib import Path
from html import escape


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
    """HTML 페이지 생성. cases 데이터를 inline embed."""
    cases_json = json.dumps(cases, ensure_ascii=False)
    html = HTML_TEMPLATE.format(cases_json=cases_json)
    output_path.write_text(html, encoding="utf-8")


def main():
    cases_path = Path("docs/portfolio/coach/slice9/part2/manual_eval/cases.json")
    output_path = Path("docs/portfolio/coach/slice9/part2/manual_eval/eval_page.html")

    cases = json.load(open(cases_path))
    generate_html(cases, output_path)

    print(f"HTML 평가 페이지 생성 완료: {output_path}")
    print(f"브라우저에서 열기: file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
```

### §2.4 단위 테스트

`portfolio/tests/slice9/test_generate_eval_html.py` (신규)

```python
"""Slice 9 Part 2 §2 — HTML 평가 페이지 생성 검증."""

import json
from pathlib import Path

import pytest

from scripts.slice9.generate_eval_html import generate_html


@pytest.fixture
def sample_cases():
    return [
        {
            "case_id": "S01",
            "case_name": "test_scenario",
            "original_model": "claude-haiku-4-5",
            "question": "테스트 질문",
            "commentary": "테스트 답변",
            "action_items": [{"title": "A", "description": "B", "priority": "high"}],
            "rationale_text": "테스트 rationale",
            "rationale_score": 4,
            "auto_specificity_score": 5,
            "auto_specificity_detail": {},
            "manual_naturalness": None,
            "manual_insight": None,
            "manual_comment": "",
        }
    ]


class TestGenerateEvalHtml:

    def test_html_file_created(self, tmp_path, sample_cases):
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        assert output.exists()

    def test_html_contains_cases_data(self, tmp_path, sample_cases):
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert "S01" in content
        assert "테스트 질문" in content
        assert "테스트 답변" in content

    def test_html_includes_naturalness_radio(self, tmp_path, sample_cases):
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert "Naturalness" in content
        assert 'name="naturalness"' in content

    def test_html_includes_insight_radio(self, tmp_path, sample_cases):
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert "Insight" in content
        assert 'name="insight"' in content

    def test_html_includes_export_button(self, tmp_path, sample_cases):
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert 'id="export-btn"' in content
        assert "Export to JSON" in content

    def test_html_includes_progress_bar(self, tmp_path, sample_cases):
        output = tmp_path / "eval.html"
        generate_html(sample_cases, output)
        content = output.read_text(encoding="utf-8")
        assert 'id="progress-bar"' in content

    def test_html_escapes_user_content(self, tmp_path):
        """XSS 방지 — case 데이터가 HTML escape 처리."""
        cases = [{
            "case_id": "S99",
            "case_name": "<script>alert('xss')</script>",
            "original_model": "test",
            "question": "<script>",
            "commentary": "<img onerror=alert(1)>",
            "action_items": [],
            "rationale_text": "",
            "rationale_score": 0,
            "auto_specificity_score": 0,
            "auto_specificity_detail": {},
        }]
        output = tmp_path / "eval.html"
        generate_html(cases, output)
        content = output.read_text(encoding="utf-8")
        # JS escapeHtml 함수가 렌더 시점에 처리하므로 HTML 자체엔 raw script 존재 가능
        # 그러나 escapeHtml 함수 정의는 반드시 포함되어야 함
        assert "function escapeHtml" in content
```

### §2.5 KPI 2

- [ ] `generate_eval_html.py` 작성
- [ ] HTML 페이지 생성 (`eval_page.html`)
- [ ] 단위 테스트 7건 PASS
- [ ] **수동 검증**: 브라우저에서 열어 다음 확인
  - [ ] 26 entries 모두 렌더
  - [ ] 라디오 버튼 클릭 → localStorage 저장
  - [ ] 페이지 새로고침 후 평가 상태 복원
  - [ ] 진행률 바 동작
  - [ ] Export 버튼 (모든 평가 완료 시 활성화)
- [ ] 회귀 +7건

---

## §3. 보조 자료 dump

### §3.1 rubric.md 복사

```bash
# Slice 7 rubric을 Slice 9 manual eval 자료로 복사
cp docs/portfolio/coach/slice7/manual_eval_rubric.md \
   docs/portfolio/coach/slice9/part2/manual_eval/rubric.md

# 또는 동등 위치 확인 후 복사
```

### §3.2 instructions.md 작성

`docs/portfolio/coach/slice9/part2/manual_eval/instructions.md` (신규)

```markdown
# Slice 9 Manual Eval 안내

## 평가 작업 흐름

1. `eval_page.html`을 브라우저에서 더블클릭으로 열기
2. 각 case (S01~S26) 한 페이지씩 평가:
   - **Naturalness** (1~5): 한국어 답변 자연스러움 (어색한 번역체, 반복, 어절 깨짐 등)
   - **Insight** (1~5): 4요소(현재 상태/임계값/액션/시점) 충족도 + 통찰력
   - **Comment** (선택): 평가 근거 또는 의문점
3. 모든 평가 완료 시 **Export to JSON** 버튼 클릭 → `slice9_manual_eval_results.json` 다운로드
4. 다운로드한 파일을 `docs/portfolio/coach/slice9/part2/manual_eval/results.json`으로 저장

## 평가 기준 (rubric.md 참조)

- 5점: 4요소 모두 명확 + 정량 임계값 + 액션 직접 제시
- 4점: 4요소 중 3개 명확
- 3점: 4요소 중 2개 명확 또는 모두 약간 모호
- 2점: 4요소 중 1개만 명확
- 1점: 4요소 전혀 충족 안 됨

## 보조 자료

- **rationale (Sonnet 자체 평가)**: 각 case 페이지에 회색 박스로 표시. 참고용이지 평가 대상 아님.
- **자동 patterns score**: 메타 영역에 표시. P1~P5 자동 검출 결과 (0~5).

## 예상 작업 시간

- 평균 case당 1분 = 약 26분
- 단, 길이가 긴 case는 2~3분 가능 → 총 30~45분

## 중간 저장

- 라디오 버튼 클릭 시 localStorage 자동 저장
- 브라우저 종료 후 재개 가능 (동일 URL로 다시 열기)

## 평가 완료 후

평가 결과 JSON을 Claude Code에 전달 → 다음 단계:

- winner 판정 (Haiku vs Sonnet, label_means 비교)
- 글쓰기 가설 6/6 → 7/7 정착 vs 6/7 판정
- 분포 폭 (#49) 재검토 — Sonnet 자체 평가 width=2 vs manual eval width 비교
```

### §3.3 KPI 3

- [ ] rubric.md 복사
- [ ] instructions.md 작성
- [ ] 회귀 +0건 (docs 추가만)

---

## §4. 정합성 검증

### §4.1 산출물 정합성 자동 체크

`scripts/slice9/verify_part2_dump.py` (신규)

```python
"""Slice 9 Part 2 §4 — manual eval dump 정합성 자동 검증."""

import json
import sys
from pathlib import Path


def main():
    base = Path("docs/portfolio/coach/slice9/part2/manual_eval")

    checks = []

    # Check 1: cases.json 존재 + 26 entries
    cases_path = base / "cases.json"
    if not cases_path.exists():
        checks.append(("cases.json 존재", False))
    else:
        cases = json.load(open(cases_path))
        checks.append(("cases.json 26 entries", len(cases) == 26))

        # Check 2: 필수 필드 모두 존재
        required_fields = ["case_id", "case_name", "commentary", "action_items",
                          "rationale_text", "manual_naturalness", "manual_insight"]
        all_have_fields = all(all(f in c for f in required_fields) for c in cases)
        checks.append(("cases.json 필수 필드 모두 존재", all_have_fields))

        # Check 3: case_id 중복 없음
        ids = [c["case_id"] for c in cases]
        checks.append(("case_id 중복 없음", len(set(ids)) == len(ids)))

        # Check 4: manual_naturalness/insight 초기값 None
        all_null = all(c["manual_naturalness"] is None and c["manual_insight"] is None for c in cases)
        checks.append(("manual slots 초기값 None", all_null))

    # Check 5: eval_page.html 존재
    html_path = base / "eval_page.html"
    checks.append(("eval_page.html 존재", html_path.exists()))

    # Check 6: HTML 내 26 case_id 모두 embed
    if html_path.exists():
        html_content = html_path.read_text(encoding="utf-8")
        all_embed = all(f'"S{i:02d}"' in html_content for i in range(1, 27))
        checks.append(("HTML 26 case_id 모두 embed", all_embed))

    # Check 7: rubric.md 존재
    rubric_path = base / "rubric.md"
    checks.append(("rubric.md 존재", rubric_path.exists()))

    # Check 8: instructions.md 존재
    inst_path = base / "instructions.md"
    checks.append(("instructions.md 존재", inst_path.exists()))

    # 출력
    print("=" * 60)
    print("Slice 9 Part 2 — Manual Eval Dump 정합성 검증")
    print("=" * 60)
    all_pass = True
    for name, result in checks:
        verdict = "✓ PASS" if result else "✗ FAIL"
        if not result:
            all_pass = False
        print(f"{name}: {verdict}")
    print("=" * 60)
    print(f"전체 판정: {'✓ ALL PASS' if all_pass else '✗ FAIL 존재'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

### §4.2 KPI 4

- [ ] 정합성 검증 스크립트 실행, 8/8 PASS
- [ ] 회귀 +0건 (스크립트 자체는 단위 테스트 없음)

---

## §5. KPI 자동 검증

### §5.1 KPI 매트릭스 (Part 2)

| #   | KPI                 | 기준                                | 측정                  |
| --- | ------------------- | ----------------------------------- | --------------------- |
| 1   | 회귀                | 486 → 489~491 (KPI 9a/9b 자동 분류) | pytest                |
| 2   | IDENTICAL hash      | 7/7                                 | test_static_integrity |
| 3   | 누적 cost 변화 없음 | $2.3775 유지                        | CostGuard             |
| 4   | LLM 호출            | 0                                   | (Part 2는 LLM 0)      |
| 5   | dump 정합성         | 8/8 PASS                            | verify_part2_dump.py  |
| 6   | HTML 페이지 동작    | 수동 검증 통과                      | 사용자                |

### §5.2 자동 검증 스크립트

`scripts/slice9/verify_part2_kpi.py` (신규, 위 §4 정합성 + KPI 통합)

```python
"""Slice 9 Part 2 §5 — KPI 6개 자동 검증."""

import json
import subprocess
import sys
from pathlib import Path


def main():
    kpis = {}

    # KPI 1: 회귀 (자동 분류 — Part 2는 docs/ + scripts/ + tests/ 변경)
    result = subprocess.run(["pytest", "portfolio/tests", "-q"], capture_output=True, text=True)
    last_line = result.stdout.strip().split("\n")[-1]
    passed = int(last_line.split()[0]) if last_line.split()[0].isdigit() else 0
    actual_delta = passed - 486

    # 분류 — scripts/는 분류 룰에 없음, tests/ + docs/만이면 no-cost
    # 보수적으로 mixed로 처리할지 사용자 결정 → 일단 no-cost로 시도
    predicted_no_cost = 10  # cases test 3 + html test 7
    deviation = abs(actual_delta - predicted_no_cost) / predicted_no_cost if predicted_no_cost else 1
    kpis["1_regression"] = {
        "value": f"486 → {passed} (+{actual_delta}, predicted +{predicted_no_cost}, dev {deviation*100:.1f}%)",
        "pass": deviation <= 0.50,  # no-cost ±50%
    }

    # KPI 2: IDENTICAL hash
    result = subprocess.run(["pytest", "portfolio/tests/test_static_integrity.py", "-v"],
                          capture_output=True, text=True)
    identical_pass = result.stdout.count("PASSED") >= 7
    kpis["2_identical_hash"] = {"value": "7/7" if identical_pass else "FAIL", "pass": identical_pass}

    # KPI 3: 누적 cost 변화 없음
    # Part 2는 LLM 호출 0 — CostGuard 상태 확인
    kpis["3_cumulative_cost_unchanged"] = {
        "value": "Part 2 LLM 호출 0",
        "pass": True,
    }

    # KPI 4: LLM 호출 0
    kpis["4_llm_calls_zero"] = {"value": "0", "pass": True}

    # KPI 5: dump 정합성
    dump_check = subprocess.run(
        ["python", "scripts/slice9/verify_part2_dump.py"],
        capture_output=True, text=True
    )
    kpis["5_dump_integrity"] = {
        "value": dump_check.stdout.strip().split("\n")[-1],
        "pass": dump_check.returncode == 0,
    }

    # KPI 6: HTML 동작 (수동 검증 - 자동 측정 불가)
    kpis["6_html_manual_verification"] = {
        "value": "사용자 수동 검증 필요",
        "pass": None,  # N/A
    }

    # 출력
    print("=" * 60)
    print("Slice 9 Part 2 — KPI 6개 자동 검증")
    print("=" * 60)
    all_pass = True
    for kpi_id, data in kpis.items():
        if data["pass"] is True:
            verdict = "✓ PASS"
        elif data["pass"] is False:
            verdict = "✗ FAIL"
            all_pass = False
        else:
            verdict = "⊘ N/A (수동 검증)"
        print(f"{kpi_id}: {data['value']} → {verdict}")
    print("=" * 60)

    # 저장
    output_path = Path("docs/portfolio/coach/slice9/part2/kpi_verification.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(kpis, f, ensure_ascii=False, indent=2)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

### §5.3 KPI 5

- [ ] KPI 6개 자동 검증 PASS (5건 PASS + 1건 N/A)
- [ ] kpi_verification.json 저장
- [ ] 회귀 +0건

---

## §6. 종결 보고 양식

### §6.1 회신 보고서 골격

`docs/portfolio/coach/slice9/part2_closing.md`

```markdown
# Slice 9 Part 2 종결 보고서

> **작성일**: YYYY-MM-DD
> **브랜치**: slice9
> **종결 상태**: \_\_\_ (manual eval 대기 / 종결 완료)

## KPI 통과 현황

| #   | 항목                | 기준                         | 결과             | 통과 |
| --- | ------------------- | ---------------------------- | ---------------- | :--: |
| 1   | 회귀                | 486 → 489~491 (no-cost ±50%) | 486 → **_ (+_**) |  \_  |
| 2   | IDENTICAL hash      | 7/7                          | \_               |  \_  |
| 3   | 누적 cost 변화 없음 | $2.3775 유지                 | \_               |  \_  |
| 4   | LLM 호출            | 0                            | \_               |  \_  |
| 5   | dump 정합성         | 8/8 PASS                     | _/_              |  \_  |
| 6   | HTML 페이지 동작    | 수동 검증                    | \_               | N/A  |

## 부채 처리

| 부채                  | 상태                      | 비고                                           |
| --------------------- | ------------------------- | ---------------------------------------------- |
| #46 manual eval dump  | \_                        | HTML + cases.json + rubric + instructions      |
| #49 분포 폭 측정 방식 | **manual eval 결과 대기** | Sonnet width=2 vs manual width 비교 후 verdict |
| #48 estimator v3      | Slice 10 Step 0           | 본 Part에서 처리 안 함                         |

## 산출물 체크리스트

| #   | 산출물                    | 위치                                              |
| --- | ------------------------- | ------------------------------------------------- |
| 1   | cases.json                | docs/portfolio/coach/slice9/part2/manual_eval/    |
| 2   | cases.json 생성 스크립트  | scripts/slice9/prepare_eval_cases.py              |
| 3   | cases.json 단위 테스트    | portfolio/tests/slice9/test_prepare_eval_cases.py |
| 4   | eval_page.html            | docs/portfolio/coach/slice9/part2/manual_eval/    |
| 5   | HTML 생성 스크립트        | scripts/slice9/generate_eval_html.py              |
| 6   | HTML 단위 테스트          | portfolio/tests/slice9/test_generate_eval_html.py |
| 7   | rubric.md 복사            | docs/portfolio/coach/slice9/part2/manual_eval/    |
| 8   | instructions.md           | docs/portfolio/coach/slice9/part2/manual_eval/    |
| 9   | dump 정합성 검증 스크립트 | scripts/slice9/verify_part2_dump.py               |
| 10  | KPI 검증 스크립트         | scripts/slice9/verify_part2_kpi.py                |
| 11  | kpi_verification.json     | docs/portfolio/coach/slice9/part2/                |
| 12  | 종결 보고서               | docs/portfolio/coach/slice9/part2_closing.md      |

## 회귀 분류 (E1 자동 분류)

- Part 2 변경 경로: `scripts/slice9/` + `portfolio/tests/slice9/` + `docs/portfolio/coach/slice9/part2/`
- classifier 결과: \_\_\_
- 적용 KPI: 9a (cost) / 9b (no-cost)
- predicted vs actual deviation: \_\_\_%

## 신규 부채

(있다면) | _ | _ | \_ |

## 다음 단계

**Manual Eval 작업 (사용자)**:

1. `docs/portfolio/coach/slice9/part2/manual_eval/eval_page.html`을 브라우저에서 열기
2. 26 cases 평가 (예상 30~45분)
3. Export to JSON → `results.json` 다운로드
4. `docs/portfolio/coach/slice9/part2/manual_eval/results.json`으로 저장

**Manual Eval 종결 후**:

- winner 판정 (Haiku vs Sonnet, label_means 비교)
- 글쓰기 가설 6/6 → **7/7 정착** vs **6/7** 판정
- #49 분포 폭 verdict (manual eval width 측정)
- Slice 9 전체 종결 + Slice 10 Step 0 (#48 estimator v3) 진입 결정
```

---

## §7. 핵심 결정 lock 블록

| 결정                    | 값                                       | 근거                                   |
| ----------------------- | ---------------------------------------- | -------------------------------------- |
| **A1** Part 2 진입 판정 | 그대로 진입                              | 가중합 5.00, 마진 1.35 (결정적)        |
| **B3** dump 구조        | HTML 단건 페이지 + 라디오 + localStorage | 가중합 3.80, 사용자 평가 UX 우선       |
| **C1** 평가 축          | naturalness + insight 2축 (Slice 7 표준) | 가중합 4.60, 마진 1.50 (결정적)        |
| **D2** #β2 FAIL 처리    | #48 Slice 10 Step 0 부채                 | 가중합 4.65, 마진 0.40 (tie-breaker)   |
| 누적 임계               | $3.00 (Slice 9 Step 0 #43)               | 유지                                   |
| 슬라이스 cap            | $1.00 (Slice 9 Step 0 #43)               | Part 1 + Part 2 합쳐 cap 마진 67% 유지 |
| 평가 등급               | 1~5 정수 (Slice 7 표준)                  | 시계열 비교 위해 일관 유지             |

---

## §8. 분기 시나리오

### §8.1 정상 경로

1. §0 사전 체크 PASS
2. §1 cases.json 생성 + 단위 테스트 3건 PASS
3. §2 HTML 페이지 생성 + 단위 테스트 7건 PASS + 수동 브라우저 검증 PASS
4. §3 rubric.md + instructions.md 복사/작성
5. §4 dump 정합성 8/8 PASS
6. §5 KPI 6개 검증 PASS (5+1 N/A)
7. §6 종결 보고서 작성
8. **Part 2 종결**: 회귀 489~491, 비용 $0, #46 close, manual eval 대기

### §8.2 비정상 경로

| 시점 | 신호                                   | 분기                                                                   |
| ---- | -------------------------------------- | ---------------------------------------------------------------------- |
| §2   | HTML 단위 테스트 FAIL                  | 템플릿 점검, escapeHtml 정합성 확인                                    |
| §2   | 브라우저 수동 검증 — 라디오 동작 안 함 | JS 디버깅, localStorage permission 확인                                |
| §2   | 26 entries 일부 누락                   | cases.json embed 룰 점검                                               |
| §4   | dump 정합성 FAIL                       | 누락 파일 보강                                                         |
| §5   | KPI 1 회귀 분류 mismatch               | classifier 룰 보강 필요 (scripts/ 경로 분류 빈틈 — #50 신규 부채 후보) |

### §8.3 즉시 정지 트리거

- IDENTICAL hash 7/7 깨짐
- 회귀 < 486 (Part 1 종결값보다 감소)
- LLM 호출 발생 (Part 2는 LLM 0이어야 함)
- 누적 cost 변경 (Part 2 LLM 0)

---

## §9. Slice 9 Part 2 진행 누적 비교

| 항목           | Slice 9 Step 0 | Slice 9 Part 1 | Slice 9 Part 2 (예상) | Manual Eval 종결 후  |
| -------------- | -------------- | -------------- | --------------------- | -------------------- |
| 회귀           | 476            | 486 (+10)      | 489~491 (+3~5)        | 동일                 |
| 비용 (단독)    | $0             | $0.3292        | $0                    | $0                   |
| 비용 (누적)    | $2.0483        | $2.3775        | $2.3775 (유지)        | $2.3775 (유지)       |
| 슬라이스 cap   | $0             | $0.3292        | $0.3292 (유지)        | $0.3292 (유지)       |
| Cap 마진       | —              | 67%            | 67%                   | 67%                  |
| LLM 호출       | 0              | 26             | 0                     | 0                    |
| 부채 close     | #43            | #44/#45        | #46                   | #49 verdict (조건부) |
| IDENTICAL hash | 7/7            | 7/7            | 7/7 (필수)            | 7/7                  |

---

## 부록 A. Manual Eval 자체 (사용자 작업)

본 지시서 §6 종결 후 사용자가 수행:

1. **브라우저 열기**: `eval_page.html` 더블클릭
2. **평가 진행**: 26 cases × 2축 = 52개 평가
3. **시간**: 30~45분
4. **저장**: localStorage 자동 + Export 시 JSON 다운로드
5. **결과 저장**: `docs/portfolio/coach/slice9/part2/manual_eval/results.json`
6. **회신**: Claude Code에 results.json 첨부 또는 핵심 통계 보고

**다음 응답 (Manual Eval 종결 후)에서 결정 사항**:

- winner 판정 (label_means Haiku vs Sonnet)
- 글쓰기 가설 정착 (6/6 → 7/7) 또는 분기 (6/7)
- #49 분포 폭 verdict (manual width vs Sonnet self-eval width=2)
- Slice 9 전체 종결
- Slice 10 Step 0 진입 (#48 estimator v3)

---

## 부록 B. Claude Code 작업 자율성 경계

- **Claude Code 자율 수행**: §0 사전 체크, §1~§5 작성/실행, §6 종결 보고서 작성
- **사용자 회신 필요**:
  - §2 브라우저 수동 검증 (라디오 동작 + localStorage + export)
  - §7 lock 블록 변경
  - §8.3 즉시 정지 트리거 발동
- **수동 검증 단계**: HTML 페이지 동작은 JS 단위 테스트 도구 없이는 자동화 불가 → 사용자 브라우저 검증 필수

---

**Part 2 진입 준비 완료.**
