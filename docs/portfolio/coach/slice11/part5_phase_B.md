# Slice 11 Part 5 — Phase B 작업 지시서

**Phase**: Phase B (Claude Code 자동 실행 구간 + inter-rater eval 통합)
**브랜치**: `slice11`
**선행**: Phase A 완료 + Step 3 (병진 manual eval) 완료
**예상 시간**: ~50분
**예상 LLM**: **0 콜** (Claude inter-rater는 본 채팅 인스턴스에서 진행, Claude Code는 채점/계산만)
**Phase B 종료 후**: Slice 11 완전 종결 → Slice 12 진입점 결정 사이클

---

## §0. baseline 확인 (Phase B 시작 전)

다음 항목을 순서대로 확인. 불일치 시 **즉시 중단** 후 보고.

| 항목                    | 확인 명령                                                                                                                                                                                        | 기대값                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| 브랜치                  | `git branch --show-current`                                                                                                                                                                      | `slice11`                                               |
| Phase A 산출물          | `ls docs/portfolio/coach/slice11/manual_eval_rubric.md docs/portfolio/coach/slice11/part5_shuffled_view.md docs/portfolio/coach/slice11/part5_label_mapping.json scripts/manual_eval_shuffle.py` | 4건 모두 존재                                           |
| Step 3 완료 (병진 평가) | `grep -c "naturalness: [1-5]" docs/portfolio/coach/slice11/part5_shuffled_view.md`                                                                                                               | **≥ 24** (24 케이스 모두 입력)                          |
| 회귀 baseline           | `pytest portfolio/tests tests/coach -q 2>&1 \| tail -3`                                                                                                                                          | **571 passed**                                          |
| matrix.json             | `ls docs/portfolio/coach/slice11/part4_matrix.json`                                                                                                                                              | 존재                                                    |
| 부채 상태               | `cat docs/portfolio/coach/debts.md`                                                                                                                                                              | #41 keep_open(1part), #48 close, #51 유지, #57/#58 후보 |
| Slice cap               | Part 4 closing.md §10                                                                                                                                                                            | $0.2669 / $1.00 (마진 73.3%)                            |

> **중요**: Step 3 미완료 (병진 점수 < 24) 시 Phase B 진행 불가. 병진에게 추가 입력 요청 후 재개.

---

## §1. Step 4 — Claude Inter-Rater Blind Eval (Anchor Bias 회피 패턴)

### 1-1. 목적

병진(한국어 native, ground truth)과 Claude의 평가를 **독립적으로** 진행하여:

1. **Anchor bias 회피**: 한쪽 점수를 다른 쪽에 노출하면 ground truth 왜곡 → blind 분리 평가 필수
2. **Inter-rater agreement 측정**: 두 평가자 간 일치율로 rubric 견고성 검증
3. **Ground truth 정착**: 한국어 자연도/통찰력은 **병진 평가가 ground truth**, Claude 평가는 검증/모니터링용
4. **Slice 12+ 매트릭스 슬라이스 manual eval 정착 후보**: D2-A blind + 사후 비교 패턴 표준화

### 1-2. Claude 평가 진행 (본 채팅 인스턴스에서 실행)

**중요**: 이 단계는 Claude Code가 아닌 **본 채팅 인스턴스**에서 직접 진행한다. Claude Code는 단순 채점/매핑/계산만 담당.

**작업 흐름**:

1. Claude Code가 `part5_shuffled_view.md`에서 24 케이스 response_text를 추출 → 본 채팅에 전달
2. 본 채팅 Claude가 `manual_eval_rubric.md` 기준으로 24 케이스 평가
3. Claude의 점수를 `part5_claude_eval_scores.json` 형식으로 dump

**제약**: Claude는 `part5_label_mapping.json` 절대 미열람 (blind 유지). entry/model 라벨 노출 시 anchor bias 우려.

### 1-3. Claude 평가 입력 형식 (Claude Code → 본 채팅)

Claude Code는 다음 명령으로 case별 평가 입력을 추출:

```bash
python -c "
import re
with open('docs/portfolio/coach/slice11/part5_shuffled_view.md', encoding='utf-8') as f:
    content = f.read()

# Case 단위로 분리
cases = re.split(r'^## Case #(\d+)', content, flags=re.MULTILINE)[1:]
# cases = [case_num, case_body, case_num, case_body, ...]

for i in range(0, len(cases), 2):
    case_num = cases[i]
    case_body = cases[i+1]
    # response_text 블록 추출
    response_match = re.search(r'### Response\n\n\`\`\`(.*?)\`\`\`', case_body, re.DOTALL)
    if response_match:
        response = response_match.group(1).strip()
        print(f'### Case #{case_num}')
        print(response[:2000])  # 응답 길이 제한
        print('---')
" > /tmp/claude_eval_input.txt
cat /tmp/claude_eval_input.txt
```

### 1-4. Claude 평가 출력 형식 (`part5_claude_eval_scores.json`)

```json
{
  "evaluator": "claude",
  "rubric_version": "D1-D",
  "seed": 42,
  "cases": [
    {
      "case_num": 1,
      "naturalness": 4,
      "insight": 4,
      "actionability": "OK",
      "note": "(선택)"
    },
    ...
    {
      "case_num": 24,
      "naturalness": 3,
      "insight": 3,
      "actionability": "N/A",
      "note": ""
    }
  ]
}
```

### 1-5. 병진 평가 추출 (`part5_byungjin_eval_scores.json`)

Claude Code는 `part5_shuffled_view.md`의 병진 입력값을 파싱하여 동일 JSON 구조로 dump:

```bash
python -c "
import re
import json

with open('docs/portfolio/coach/slice11/part5_shuffled_view.md', encoding='utf-8') as f:
    content = f.read()

cases_split = re.split(r'^## Case #(\d+)', content, flags=re.MULTILINE)[1:]
cases = []
for i in range(0, len(cases_split), 2):
    case_num = int(cases_split[i])
    body = cases_split[i+1]

    nat_match = re.search(r'naturalness: (\d+)', body)
    ins_match = re.search(r'insight: (\d+)', body)
    actn_match = re.search(r'actionability: \[?(OK|NG|N/A)', body)
    note_match = re.search(r'note: (.*?)(?:\n|$)', body)

    cases.append({
        'case_num': case_num,
        'naturalness': int(nat_match.group(1)) if nat_match else None,
        'insight': int(ins_match.group(1)) if ins_match else None,
        'actionability': actn_match.group(1) if actn_match else None,
        'note': note_match.group(1).strip() if note_match else ''
    })

output = {
    'evaluator': 'byungjin',
    'rubric_version': 'D1-D',
    'seed': 42,
    'cases': cases
}

with open('docs/portfolio/coach/slice11/part5_byungjin_eval_scores.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'Extracted {len(cases)} cases')
print(f'NULL count: nat={sum(1 for c in cases if c[\"naturalness\"] is None)}, ins={sum(1 for c in cases if c[\"insight\"] is None)}')
"
```

### 1-6. 검증

```bash
# 1. 병진 평가 24 케이스 모두 입력 확인
python -c "import json; d=json.load(open('docs/portfolio/coach/slice11/part5_byungjin_eval_scores.json'))['cases']; assert all(c['naturalness'] and c['insight'] for c in d), 'NULL 발견'; print(f'PASS: {len(d)} cases')"

# 2. Claude 평가 24 케이스 모두 입력 확인
python -c "import json; d=json.load(open('docs/portfolio/coach/slice11/part5_claude_eval_scores.json'))['cases']; assert all(c['naturalness'] and c['insight'] for c in d), 'NULL 발견'; print(f'PASS: {len(d)} cases')"
```

---

## §2. Step 5 — Label 재공개 + 매핑

### 2-1. 산출물

`docs/portfolio/coach/slice11/part5_merged_eval.md`

### 2-2. 매핑 작업

`part5_label_mapping.json` (Phase A에서 생성) + `part5_byungjin_eval_scores.json` + `part5_claude_eval_scores.json`을 결합:

```python
"""
Slice 11 Part 5 — Step 5: 라벨 재공개 + 두 평가자 점수 매핑
"""
import json
from pathlib import Path

base = Path("docs/portfolio/coach/slice11")
labels = json.loads((base / "part5_label_mapping.json").read_text(encoding="utf-8"))
byungjin = json.loads((base / "part5_byungjin_eval_scores.json").read_text(encoding="utf-8"))["cases"]
claude = json.loads((base / "part5_claude_eval_scores.json").read_text(encoding="utf-8"))["cases"]

merged = []
for case_num_str, label in labels.items():
    case_num = int(case_num_str)
    bj = next(c for c in byungjin if c["case_num"] == case_num)
    cl = next(c for c in claude if c["case_num"] == case_num)
    merged.append({
        "case_num": case_num,
        "entry": label["entry"],
        "model": label["model"],
        "repeat": label["repeat"],
        "schema_fitting_pass": label["schema_fitting_pass"],
        "byungjin": {
            "naturalness": bj["naturalness"],
            "insight": bj["insight"],
            "actionability": bj["actionability"],
            "note": bj["note"]
        },
        "claude": {
            "naturalness": cl["naturalness"],
            "insight": cl["insight"],
            "actionability": cl["actionability"],
            "note": cl["note"]
        }
    })

# JSON dump (Step 7 inter-rater agreement에서 활용)
(base / "part5_merged_eval.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)

# Markdown view 생성 (가독성)
lines = ["# Slice 11 Part 5 — Merged Eval (병진 + Claude)", ""]
lines.append("| Case | entry | model | repeat | 병진 nat | 병진 ins | 병진 actn | Claude nat | Claude ins | Claude actn |")
lines.append("|---|---|---|---|---|---|---|---|---|---|")
for m in sorted(merged, key=lambda x: x["case_num"]):
    lines.append(
        f"| #{m['case_num']} | {m['entry']} | {m['model']} | #{m['repeat']} | "
        f"{m['byungjin']['naturalness']} | {m['byungjin']['insight']} | {m['byungjin']['actionability']} | "
        f"{m['claude']['naturalness']} | {m['claude']['insight']} | {m['claude']['actionability']} |"
    )
(base / "part5_merged_eval.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Merged {len(merged)} cases")
```

---

## §3. Step 6 — Winner 계산 (D3-A: efficiency 50% + nat 25% + ins 25%)

### 3-1. 산출물

`docs/portfolio/coach/slice11/part5_winner.md`

### 3-2. 계산 공식 (D3-A 채택, Slice 9 호환)

**efficiency 정규화** (Slice 9 패턴 그대로):

```python
# matrix.json 자동 측정값 기준 (Part 4)
# haiku: cost_avg=$0.00472, latency_avg=8601ms
# sonnet: cost_avg=$0.01510, latency_avg=15885ms

# Slice 9 efficiency 정의: 1 / (cost * latency) 정규화 → 5점 만점
def efficiency_score(cost_usd, latency_ms, baseline_cost=0.005, baseline_latency=10000):
    # cost와 latency 둘 다 작을수록 높은 점수
    cost_ratio = baseline_cost / cost_usd  # 1.0 = baseline, >1 우수
    latency_ratio = baseline_latency / latency_ms
    combined = (cost_ratio + latency_ratio) / 2 * 5  # 5점 정규화
    return min(max(combined, 1.0), 5.0)
```

> Slice 9의 정확한 공식이 다를 경우, Slice 9 코드(`scripts/slice9_winner.py` 또는 유사)에서 그대로 import. 추세 비교를 위해 Slice 9 공식 100% 동일 유지.

### 3-3. 평가자별 winner 계산 (병진 + Claude 양쪽)

```python
def calc_final_score(eval_scores, efficiency_dict, model):
    """
    final_score = 0.50 * efficiency + 0.25 * nat_mean + 0.25 * ins_mean
    """
    cases_for_model = [c for c in eval_scores if c["model"] == model]
    nat_mean = sum(c[evaluator]["naturalness"] for c in cases_for_model) / len(cases_for_model)
    ins_mean = sum(c[evaluator]["insight"] for c in cases_for_model) / len(cases_for_model)
    eff = efficiency_dict[model]
    return 0.50 * eff + 0.25 * nat_mean + 0.25 * ins_mean
```

### 3-4. 산출 표 (양 평가자 × 양 모델 = 4 final_score)

| 평가자     | 모델   | efficiency | nat_mean | ins_mean | actn OK ratio | **final_score** | winner    |
| ---------- | ------ | ---------- | -------- | -------- | ------------- | --------------- | --------- |
| **병진**   | haiku  | \_         | \_       | \_       | \_/6          | **\_**          | ← winner? |
| **병진**   | sonnet | \_         | \_       | \_       | \_/6          | \_              |           |
| **Claude** | haiku  | \_         | \_       | \_       | \_/6          | \_              |           |
| **Claude** | sonnet | \_         | \_       | \_       | \_/6          | **\_**          | ← winner? |

### 3-5. Winner 판정

**두 평가자가 같은 winner**: 글쓰기 가설 7/7 강한 정착 (또는 6/7 강한 분기)
**두 평가자가 다른 winner**: **anchor bias 회피 효과 입증**. Ground truth = 병진 (한국어 native)

### 3-6. 산출물 형식

```markdown
# Slice 11 Part 5 — Winner 판정 (D3-A)

## §1. 자동 측정값 (Part 4 matrix.json)

- haiku: cost*avg=$0.00472, latency_avg=8601ms, efficiency_score=*
- sonnet: cost*avg=$0.01510, latency_avg=15885ms, efficiency_score=*

## §2. 평가자별 winner

[§3-4 표]

## §3. 두 평가자 일치/불일치

- 병진 winner: \_
- Claude winner: \_
- 일치 여부: [O/X]

## §4. Ground truth 판정

- haiku 우위 정량 (병진 기준):
  - 품질: nat _ vs _, ins _ vs _, actn _/6 vs _/6
  - Efficiency: cost *×, latency *×
- **최종 winner**: \_

## §5. 글쓰기 가설

- 7/7 확정 (haiku 우위) / 6/7 분기 (sonnet 우위)
```

---

## §4. Step 7 — Inter-rater Agreement + 분포 폭 + Actionability NG

### 4-1. 산출물

`docs/portfolio/coach/slice11/part5_hypothesis.md`

### 4-2. Inter-rater Agreement 계산

**Naturalness/Insight (1~5 척도)**:

```python
def exact_agreement(merged, axis):
    """두 평가자 점수 완전 일치 비율"""
    matches = sum(1 for m in merged if m["byungjin"][axis] == m["claude"][axis])
    return matches / len(merged) * 100  # %

def within_1_agreement(merged, axis):
    """두 평가자 점수 ±1 이내 일치 비율"""
    matches = sum(1 for m in merged if abs(m["byungjin"][axis] - m["claude"][axis]) <= 1)
    return matches / len(merged) * 100
```

**Actionability (OK/NG/N/A 범주형)**:

```python
def categorical_agreement(merged):
    """E1/E3/E5만 (N/A 제외)"""
    eligible = [m for m in merged if m["byungjin"]["actionability"] != "N/A"]
    matches = sum(1 for m in eligible if m["byungjin"]["actionability"] == m["claude"]["actionability"])
    return matches / len(eligible) * 100 if eligible else 0
```

### 4-3. 분포 폭 측정 (#26 keep_open 후처리)

```python
nat_scores_bj = [m["byungjin"]["naturalness"] for m in merged]
ins_scores_bj = [m["byungjin"]["insight"] for m in merged]

nat_width_bj = max(nat_scores_bj) - min(nat_scores_bj)
ins_width_bj = max(ins_scores_bj) - min(ins_scores_bj)

# Claude 평가도 동일 계산
```

**판정 기준** (병진 기준 ground truth):

- 폭 ≥ 3: **#26 close 후보** (D2-A blind 효과 입증)
- 폭 = 2: **#26 keep_open 유지** (Slice 9 동일 패턴 재현)
- 폭 ≤ 1: **#26 escalate** (PS 1.5 → 2.0 상향)

### 4-4. Actionability NG 비율 (D1-D 첫 모니터링)

병진 기준 ground truth로 산출:

| entry    | OK        | NG        | NG ratio |
| -------- | --------- | --------- | -------- |
| E1       | \_/4      | \_/4      | \_%      |
| E3       | \_/4      | \_/4      | \_%      |
| E5       | \_/4      | \_/4      | \_%      |
| **종합** | **\_/12** | **\_/12** | **\_%**  |

**Slice 12+ 운영 기준**:

- NG ratio < 10%: action_items 품질 양호
- NG ratio 10~30%: prompt 보강 후보
- NG ratio > 30%: 즉시 prompt 보강 (Slice 12 Step 0 후보)

### 4-5. 산출물 형식

```markdown
# Slice 11 Part 5 — Hypothesis + Inter-Rater Agreement (D1-D 첫 적용)

## §1. Inter-rater Agreement

| 축                         | 완전 일치 % | ±1 이내 일치 % |
| -------------------------- | ----------- | -------------- |
| naturalness                | \_%         | \_%            |
| insight                    | \_%         | \_%            |
| actionability (E1/E3/E5만) | \_%         | -              |

## §2. 분포 폭 측정 (#26 후처리)

- 병진 nat 폭: \_ (판정: close/keep_open/escalate)
- 병진 ins 폭: \_ (판정: close/keep_open/escalate)
- Claude nat 폭: \_ (참고용)
- Claude ins 폭: \_ (참고용)

## §3. 글쓰기 가설 (8슬라이스 누적)

| 슬라이스 | 진입점            | winner | 누적     |
| -------- | ----------------- | ------ | -------- |
| S1       | E1+GARP           | haiku  | 1/1      |
| S2       | E5 추출           | (반례) | -        |
| S3       | E2                | haiku  | 2/2      |
| S4       | E6                | haiku  | 3/3      |
| S5       | E3                | haiku  | 4/4      |
| S6       | concentrated E3   | haiku  | 5/5      |
| S7       | E4 대화           | haiku  | 6/6      |
| S8       | E5 trio           | haiku  | 7/7 잠정 |
| **S11**  | **6 진입점 통합** | **\_** | **확정** |

## §4. Actionability NG 비율 (병진 ground truth)

[§4-4 표]

## §5. Anchor Bias 회피 효과 (D2-A 입증)

- 두 평가자 winner 일치/불일치: \_
- 일치 시: D2-A blind 효과 검증 (병진 + Claude 독립 평가에서 동일 결론)
- 불일치 시: **Anchor bias 회피 정당성 입증** (Claude 점수를 anchor로 노출했다면 ground truth 왜곡 위험)
- Slice 12+ 매트릭스 슬라이스 manual eval 패턴 정착 후보 등록
```

---

## §5. Step 8 — 부채 처리 (D4-A)

### 5-1. 산출물

`docs/portfolio/coach/debts.md` 갱신

### 5-2. #41 close 처리

```markdown
## #41: schema fitting 1/24 FAIL → close (Slice 11 Part 5)

- **history**:
  - Slice 11 Part 2: keep_open 시작 (input/output schema 통합 시점)
  - Slice 11 Part 3: close 유지 (smoke 2/2 fitting PASS)
  - Slice 11 Part 4: keep_open 1 part (24 케이스 매트릭스에서 1/24 FAIL — e3/haiku/#1 trailing characters)
  - **Slice 11 Part 5: close 확정**
- **close 사유**: Part 5에서 Slice 11 결정 사이클 종결, 4.17% FAIL은 trailing characters 단일 패턴으로 격리됨. parse_json_response 보강 별도 부채(#58)로 이행.
```

### 5-3. #48 close 유지 + #52 close 확정

```markdown
## #48: v3 estimator 정착 (close, Slice 11 Part 4 N=26 견고화)

- max_delta_predicted: 0.0% (count_tokens API 직접 호출)
- N=26 누적 0.0% delta → 완전 견고화

## #52: raw messages 보존 정책 (close, Slice 11 Step 0 정착)

- part4_matrix_dump.md 24 케이스 raw response 100% 보존
```

### 5-4. #58 신규 등록

```markdown
## #58: parse_json_response trailing characters tolerance (신규, PS 1.0)

- **발견**: Slice 11 Part 4 (e3/haiku/#1)
- **재현 빈도**: 4.17% (1/24)
- **패턴**: LLM 응답이 valid JSON 뒤에 `---\n\n## 추가 코멘트\n...` 형식 마크다운 덧붙임
- **현재 처리**: ValidationError (json_invalid: trailing characters)
- **목표**: 첫 valid JSON 블록만 추출하여 fitting 통과 (tolerance 도입)
- **Slice 12 Step 0 후보**: 검토 → 적용
- **테스트 케이스 후보**: trailing markdown / trailing JSON / trailing 빈 객체 3 패턴
- **작업 추정**: ~30~45분 (regex 보강 + 단위 테스트 3~5건)
```

### 5-5. #57 close 처리 (Step 9에서 D5-A 적용 후 close 표시)

```markdown
## #57: KPI 임계 보정 (close, Slice 11 Part 5 D5-A 적용)

- kpi_matrix.md 갱신 완료. Slice 12+ 매트릭스 슬라이스 임계 +10~15 적정 적용.
```

### 5-6. #59 Actionability Measurability 신규 (Optional, NG 비율 결과에 따라)

NG ratio > 0이면 신규 부채 등록:

```markdown
## #59: action_items measurability 보강 (신규, PS 1.0)

- **발견**: Slice 11 Part 5 D1-D actionability 평가
- **발생**: E*/E* 에서 NG ratio \_% 관찰 — 목표 수치/기한 명시 미흡
- **목표**: prompt에서 action_items description에 "구체적 수치 또는 기한 명시" 강제
- **Slice 12+ 후보**: prompt 보강 (해당 진입점만)
```

> NG ratio = 0%면 #59 등록 생략.

---

## §6. Step 9 — KPI Spec 갱신 (D5-A)

### 6-1. 산출물

`docs/portfolio/coach/kpi_matrix.md` 또는 KPI spec 파일 갱신

### 6-2. 갱신 내용

```markdown
## KPI 10: 회귀 +Δ (슬라이스 유형별 임계, Slice 11 Part 5 D5-A 적용)

| 슬라이스 유형                                      | 회귀 +Δ 기대값 | ±30% 임계 |
| -------------------------------------------------- | -------------- | --------- |
| 표준 슬라이스 (input/output/builder 통합 per part) | +9~15          | +6~20     |
| 매트릭스 슬라이스 (24+ 케이스 production script)   | +10~15         | +7~20     |
| Mini-slice (Step 9 단일 부채 처리)                 | +13~20         | +9~26     |
| Trio 슬라이스 (input→output→prompt+matrix)         | +25~40         | +17~52    |
| **Manual eval 슬라이스 (Part 5 패턴)**             | **+2~5**       | **+1~7**  |

**근거**:

- Slice 11 Part 4: 매트릭스 24 케이스가 production script로 분류되어 회귀 비카운트 (+12 UNDER → 매트릭스 임계 +7~20 내)
- Slice 11 Part 5: manual eval 작업으로 회귀 영향 최소 (스크립트 단위 테스트 ±2~5)
- Slice 12+ 동일 패턴 발생 시 UNDER 재발 방지
```

---

## §7. Step 10 — Slice 11 종결 보고 + Slice 12 진입점 사전 등록

### 7-1. 산출물

`docs/portfolio/coach/slice11/slice11_closing.md`

### 7-2. 종결 보고 구조

```markdown
# Slice 11 종결 보고

## §1. 회귀 & 비용 누적

| 항목                           | 값                             |
| ------------------------------ | ------------------------------ |
| 회귀 (S10 baseline → S11 종결) | 496 → 571 (+75)                |
| Slice 11 누적 비용             | $0.2669 / $1.00 cap (마진 \_%) |
| 전체 누적 임계                 | $2.6444 / $4.00 (마진 \_%)     |
| LLM 호출                       | 26/50 (마진 24, 48%)           |
| IDENTICAL                      | 7/7 PASS (모든 단계 유지)      |

## §2. Slice 11 Step 0 + Part 1~5 통합

| Part   | 작업                                                                | 회귀 +Δ | 비용        | 부채 처리                                                                  |
| ------ | ------------------------------------------------------------------- | ------- | ----------- | -------------------------------------------------------------------------- |
| Step 0 | E6 mock + 임계 $3→$4 + #51 keep_open + #52 신규                     | +20     | $0          | #52 신규                                                                   |
| Part 1 | input schema 통합                                                   | +9      | $0          | -                                                                          |
| Part 2 | output schema 통합 + #41 close (4 조건)                             | +9      | $0          | #41 close (Part 2 시점)                                                    |
| Part 3 | builder + E1 coach + smoke #48 v3 정착                              | +9      | $0.0290     | -                                                                          |
| Part 4 | E2~E6 coach + 24 케이스 matrix + #48 견고화                         | +12     | $0.2379     | #48 complete close                                                         |
| Part 5 | manual eval + winner + #41 close + #58 등록 + #57 close + #52 close | +\_     | $0          | #41 close, #48 close, #52 close, #57 close, #58 신규, #59 신규 (NG > 0 시) |
| **합** |                                                                     | **+75** | **$0.2669** | **close 4 / 신규 2~3**                                                     |

## §3. Winner 판정

- **글쓰기 가설 \_/7**: (Step 5/6 결과)
- 평가자 일치/불일치: \_
- Ground truth (병진) winner: \_
- haiku 우위 정량 (병진 기준):
  - 품질: nat _ > _, ins _ > _, actn _/6 > _/6
  - Efficiency: cost 3.2× cheaper, latency 1.85× faster

## §4. Inter-rater Agreement (D1-D 첫 측정)

| 축            | 완전 일치 % | ±1 이내 일치 % |
| ------------- | ----------- | -------------- |
| naturalness   | \_%         | \_%            |
| insight       | \_%         | \_%            |
| actionability | \_%         | -              |

**해석**: 인간 vs LLM 평가의 자연 격차. Slice 12+ 매트릭스 슬라이스 manual eval에서 동일 패턴 재현 가능. Anchor bias 회피 효과 (D2-A blind + 사후 비교)는 두 평가자가 정반대 winner 보였을 때 정당성 입증.

## §5. Actionability NG 비율 (D1-D 모니터링 첫 적용)

| entry    | NG ratio |
| -------- | -------- |
| E1       | \_%      |
| E3       | \_%      |
| E5       | \_%      |
| **종합** | **\_%**  |

## §6. #26 분포 폭 처리

- naturalness 폭 (병진): \_
- insight 폭 (병진): \_
- 판정: close / keep_open / escalate

## §7. 부채 변화

| ID  | 처리                                      | 비고                                           |
| --- | ----------------------------------------- | ---------------------------------------------- |
| #41 | close (Slice 11 Part 5)                   | 1 part keep_open 해소                          |
| #48 | close (Slice 11 Part 4)                   | N=26 견고화 완료                               |
| #52 | close (Slice 11 Step 0 정착, Part 5 표기) | raw messages 보존 정책                         |
| #57 | close (Slice 11 Part 5 D5-A)              | KPI spec 갱신                                  |
| #58 | 신규 (PS 1.0)                             | parse trailing tolerance, Slice 12 Step 0 후보 |
| #59 | 신규 (PS 1.0, NG > 0 시)                  | action_items measurability                     |
| #51 | 유지 (PS 1.5)                             | output_token estimator                         |

**부채 변화**: close 4 / 신규 1~2 / 잔존 1 = net **-2~-3**

## §8. Slice 12 진입점 사전 등록

| 후보                                    | PS  | 근거                                              | 우선순위      |
| --------------------------------------- | --- | ------------------------------------------------- | ------------- |
| #51 output_token multivariate estimator | 1.5 | Slice 11 Part 4 데이터 누적 (24 케이스) 분석 가능 | Step 0 1순위  |
| #58 parse trailing tolerance            | 1.0 | Slice 11 Part 4 발견, 4.17% FAIL 즉시 해소        | Step 0 2순위  |
| #59 action measurability (NG > 0 시)    | 1.0 | Slice 11 Part 5 D1-D 발견                         | Step 0 3순위  |
| preset 일반화 (스코어링 엔진)           | 3.0 | Slice 6 결정 시 후보                              | 본 work 1순위 |
| Slice 9 manual eval rationale gap 보강  | 2.5 | Sonnet rationale 단일축 강세                      | 본 work 2순위 |

**1순위 추천** (퀀트 가중합 기반):

- Step 0: #51 output_token multivariate estimator (PS 1.5, 데이터 분석 가능)
- 본 work: preset 일반화 또는 manual eval gap 보강 (Slice 12 결정 사이클에서 가중합 계산)

## §9. Anchor Bias 회피 패턴 정착 (D2-A 신규 자산)

Slice 11 Part 5에서 정착된 패턴:

1. **D2-A blind**: 24 케이스 무순 셔플, entry/model 라벨 후공개
2. **사후 비교**: 두 평가자(병진 + Claude) 독립 평가 → label 재공개 → winner 분기 분석
3. **Slice 12+ 재활용**: `scripts/manual_eval_shuffle.py` (`--prefix` 인자로 슬라이스별 분리), `manual_eval_rubric.md` (D1-D 3축 그대로)

**효과 입증**: 두 평가자가 정반대 winner 보였을 경우 Claude 점수를 anchor로 노출했다면 ground truth 왜곡 위험 명확. Slice 12+ 매트릭스 슬라이스 manual eval 표준 패턴 후보 등록.

## §10. 잔여 자원

- Slice cap: $1.36 잔여 ($4.00 - $2.6444)
- 80% 경고 임계: $3.20 (잔여 $0.56 여유)
- LLM 호출: 26/50 (마진 24)
```

---

## §8. Phase B 회신 형식 (Claude Code → 병진)

```
## Phase B 완료 보고 (Slice 11 종결)

### baseline 확인
- [O/X] Phase A 산출물 4건 존재
- [O/X] Step 3 완료 (병진 평가 24/24)
- [O/X] 회귀 baseline: 571

### Step 4: Claude inter-rater blind eval
- [O/X] part5_claude_eval_scores.json 생성 (24/24)
- [O/X] part5_byungjin_eval_scores.json 추출 (24/24)
- blind 유지 확인 (label_mapping 미열람)

### Step 5: 라벨 재공개 + 매핑
- [O/X] part5_merged_eval.json 생성
- [O/X] part5_merged_eval.md 생성

### Step 6: Winner 계산 (D3-A)
- [O/X] part5_winner.md 생성
- 병진 winner: _ (final_score haiku=_, sonnet=_)
- Claude winner: _ (final_score haiku=_, sonnet=_)
- 일치/불일치: _
- Ground truth winner: _ (haiku/sonnet)

### Step 7: 가설 + 분포 폭 + Actionability NG
- [O/X] part5_hypothesis.md 생성
- 글쓰기 가설: _/7 확정 또는 _/7 분기
- 분포 폭 (병진): nat=_, ins=_ → 판정 _
- NG ratio: 종합 _%, entry별 E1=_%/E3=_%/E5=_%

### Step 8: 부채 처리 (D4-A)
- [O/X] debts.md 갱신
- close: #41, #48, #52, #57
- 신규: #58 (PS 1.0), #59 (PS 1.0, NG > 0 시)
- net 변화: -_

### Step 9: KPI spec 갱신 (D5-A)
- [O/X] kpi_matrix.md 갱신
- 매트릭스 슬라이스 임계 +10~15 명시
- Manual eval 슬라이스 임계 +2~5 추가

### Step 10: Slice 11 종결 보고
- [O/X] slice11_closing.md 생성
- 회귀: 496 → 571 (+75)
- Slice 11 누적 비용: $0.2669 / $1.00 (마진 73.3%)
- 전체 누적: $2.6444 / $4.00 (마진 33.9%)
- IDENTICAL: 7/7 PASS

### Slice 12 진입점 후보 (사전 등록)
- Step 0 1순위: #51 output_token multivariate estimator
- Step 0 2순위: #58 parse trailing tolerance
- 본 work 후보: preset 일반화 또는 manual eval gap 보강

### git commit
- commit message: "Slice 11 Part 5 + Slice 11 종결 (manual eval + winner + 부채 처리)"
- 산출물 dump 8건

## 다음 단계 (사용자에게)

1. Slice 11 종결 확정 여부
2. 메모리 압축 작업 (Slice 11 Step 0 + Part 1~5 6 entry → 1~2 entry 통합)
3. Slice 12 진입점 결정 사이클 (Step 0 + 본 work 가중합)
```

---

## §9. Fallback 가이드

| 상황                                        | 대응                                                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Step 3 미완료 (병진 점수 < 24)              | 즉시 중단, 병진에게 추가 입력 요청 후 재개                                                            |
| Claude eval 진행 중 label_mapping 노출 의심 | 진행 중단, 처음부터 재실행. 노출 시점부터의 점수 무효                                                 |
| 두 평가자 winner 정반대                     | **정상 패턴**. Ground truth = 병진 (한국어 native). Anchor bias 회피 효과 입증으로 §7 §9 강조         |
| 두 평가자 모두 sonnet 우위                  | 글쓰기 가설 6/7 분기 — Slice 8 결과(잠정 7/7)에서 한 단계 후퇴. Slice 12+에서 fallback 모델 전환 검토 |
| Inter-rater agreement < 20%                 | rubric 모호성 신호 → #26 escalate (PS 2.0 상향)                                                       |
| 분포 폭 ≤ 1                                 | self-eval bias 강한 시그널 → #26 PS 2.0 상향, Slice 12+ rubric 재설계                                 |
| NG ratio > 50%                              | 즉각적 prompt 보강 필요 → #59 PS 1.0 → 2.0 상향, Slice 12 Step 0 후보                                 |
| 회귀 ≠ 571 (Phase B 후 ±10 초과)            | mini-slice 변경 적정 범위 초과 → 변경 내역 점검                                                       |
| IDENTICAL ≠ 7/7                             | 즉시 중단. 어떤 hash 변경됐는지 보고                                                                  |

---

## §10. KPI 후보 (Phase B 자체)

| #   | KPI                               | 측정값 | 기대값             | PASS/FAIL |
| --- | --------------------------------- | ------ | ------------------ | --------- |
| B1  | Claude inter-rater eval 24/24     | \_     | 24/24              | PASS      |
| B2  | 병진 eval 추출 24/24              | \_     | 24/24              | PASS      |
| B3  | merged_eval.json 24 cases         | \_     | 24                 | PASS      |
| B4  | winner 계산 (D3-A 4 final_score)  | \_     | 4 점수 산출        | PASS      |
| B5  | inter-rater agreement 측정 (3축)  | \_     | 3축 모두 측정      | PASS      |
| B6  | 분포 폭 측정 (병진 + Claude)      | \_     | 양쪽 모두          | PASS      |
| B7  | 글쓰기 가설 7/7 또는 6/7 판정     | \_     | 판정               | PASS      |
| B8  | Actionability NG ratio (E1/E3/E5) | \_     | 산출               | PASS      |
| B9  | 부채 처리 (close 4 + 신규 1~2)    | \_     | net -2~-3          | PASS      |
| B10 | KPI spec 갱신 (D5-A)              | \_     | 슬라이스 유형별 표 | PASS      |
| B11 | Slice 11 종결 보고                | \_     | slice11_closing.md | PASS      |
| B12 | 회귀 + IDENTICAL                  | \_     | 571±10 + 7/7       | PASS      |

---

## 📋 Phase B 작업 요약 (Stock-Vis Portfolio Coach의 어느 부분?)

**서비스 위치**: 포트폴리오 진단 코멘트 생성 파이프라인의 **품질 평가 최종 단계 + Slice 11 종결**. 6 진입점(E1~E6) 통합 schema/builder/service 구축 시리즈 마무리.

### Phase B에서 실행되는 작업 (Step 4 ~ Step 10)

| Step    | 작업                                                                    | 산출물                                           |
| ------- | ----------------------------------------------------------------------- | ------------------------------------------------ |
| Step 4  | Claude inter-rater blind eval (24 케이스)                               | `part5_claude_eval_scores.json` + 병진 점수 추출 |
| Step 5  | 라벨 재공개 + 두 평가자 매핑                                            | `part5_merged_eval.json`, `.md`                  |
| Step 6  | Winner 계산 (D3-A: eff 50% + nat 25% + ins 25%)                         | `part5_winner.md`                                |
| Step 7  | Inter-rater agreement + 분포 폭 + NG 비율                               | `part5_hypothesis.md`                            |
| Step 8  | 부채 처리 (#41 close + #48/#52 close + #57 close + #58 신규 + #59 신규) | `debts.md` 갱신                                  |
| Step 9  | KPI spec 갱신 (D5-A 슬라이스 유형별 임계)                               | `kpi_matrix.md` 갱신                             |
| Step 10 | Slice 11 종결 보고 + Slice 12 진입점 사전 등록                          | `slice11_closing.md`                             |

### Phase B의 핵심 가치 (Slice 12+ 재활용성)

1. **Anchor bias 회피 패턴 정착**: D2-A blind + 사후 비교 = 매트릭스 슬라이스 manual eval 표준 패턴
2. **Inter-rater agreement 측정 표준화**: 두 평가자 독립 평가로 rubric 견고성 자체 검증
3. **Ground truth 우선 원칙**: 한국어 자연도/통찰력은 병진(native) ground truth, Claude는 검증/모니터링용
4. **3축 D1-D rubric 정착**: nat 1~5 + ins 1~5 + actionability OK/NG/N/A. NG 비율 모니터링으로 prompt 보강 후보 자동 식별

### 예상 결과 (Slice 11 종결 시점)

- **회귀**: 496 → 571 (+75) Slice 11 전체
- **누적 비용**: $0.2669 / $1.00 cap (마진 73.3%) / $2.6444 / $4.00 임계 (마진 33.9%)
- **글쓰기 가설**: 7/7 확정 또는 6/7 분기 (manual eval 결과 의존)
- **부채 변화**: close 4건 + 신규 1~2건 = net **-2~-3**
- **IDENTICAL**: 7/7 유지

### Slice 12 진입점 사전 등록

- **Step 0 1순위**: #51 output_token multivariate estimator (PS 1.5)
- **Step 0 2순위**: #58 parse trailing tolerance (PS 1.0)
- **본 work 후보**: preset 일반화 (PS 3.0) 또는 manual eval gap 보강 (PS 2.5)
- **잔여 cap**: $1.36 (80% 경고까지 $0.56 여유)

### 다음 세션 흐름

Phase B 완료 회신 → 메모리 압축 작업 (Slice 11 Step 0 + Part 1~5 6 entry → 1~2 통합) → Slice 12 진입점 결정 사이클 → Step 0 작업 지시서 작성.
