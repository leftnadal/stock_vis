# Slice 12 Step 0 — 작업 지시서 (mini-slice multi-debt)

**브랜치**: `slice12` (신규 분기 from `slice11` 890b86c)
**선행 commit**: Slice 11 종결 890b86c
**Step 0 구성**: **DS-1-B** = #58 parse trailing tolerance + #59 action measurability E3
**예상 시간**: ~2h (Step 0a ~45분 + Step 0b ~1h + 검증 ~15분)
**예상 LLM**: 4 콜 (E3 micro-matrix: haiku × 2 + sonnet × 2)
**예상 비용**: ~$0.10~0.20 (slice cap $1.00 마진 80%+)
**패턴**: Slice 10 mini-slice + Slice 11 Step 0 multi-debt 융합 → multi-debt mini-slice 첫 사례

---

## §0. baseline 확인 (Step 0 시작 전)

순서대로 확인. 불일치 시 **즉시 중단** 후 보고.

| 항목                 | 확인 명령                                                      | 기대값                                                             |
| -------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| Slice 11 종결 commit | `git log -1 --format='%H %s'`                                  | 890b86c 또는 후속                                                  |
| 브랜치 분기          | `git checkout -b slice12 890b86c` 또는 `git checkout slice12`  | `slice12`                                                          |
| 회귀 baseline        | `pytest portfolio/tests tests/coach -q 2>&1 \| tail -3`        | **571 passed**                                                     |
| 누적 비용            | `cat docs/portfolio/coach/COST_POLICY.md \| grep "cumulative"` | $2.6444 / $4.00 (마진 33.9%)                                       |
| 부채 상태            | `cat docs/portfolio/coach/debts.md`                            | #51 유지, #41 keep_open(#58 dep), #58 신규 PS 1.0, #59 신규 PS 1.5 |
| IDENTICAL            | `pytest portfolio/tests/test_identical_hash.py -q`             | 7/7 PASS                                                           |
| matrix.json          | `ls docs/portfolio/coach/slice11/part4_matrix.json`            | 존재 (E3/haiku/#1 케이스 참조용)                                   |
| Part 5 merged eval   | `ls docs/portfolio/coach/slice11/part5_merged_eval.json`       | 존재 (NG E3 50% 데이터 참조)                                       |

---

## §1. Slice 12 사전 결정 확정

| ID       | 결정        | 채택                                             | 가중합    |
| -------- | ----------- | ------------------------------------------------ | --------- |
| **DS-1** | Step 0 구성 | **DS-1-B** (#58 + #59 multi-debt mini)           | 4.10      |
| **DS-2** | 본 work     | **preset 일반화** (PS 3.0, 스코어링 엔진 일반화) | 4.25 압승 |
| **DS-3** | Step 9 슬롯 | **생략** (Step 0 multi-debt 흡수)                | 4.40      |

### Slice 12 전체 구조 (사전 등록)

| 구간                   | 작업                                                  | 예상 시간 | 비용        |
| ---------------------- | ----------------------------------------------------- | --------- | ----------- |
| **Step 0** (본 지시서) | #58 + #59 multi-debt mini                             | ~2h       | ~$0.10~0.20 |
| Part 1 (사전 등록)     | preset scoring base class + 5 preset adapter 스켈레톤 | ~1h       | $0          |
| Part 2 (사전 등록)     | 5 preset adapter 풀 구현 + 회귀                       | ~2h       | $0          |
| Part 3 (사전 등록)     | smoke + 부분 matrix                                   | ~2h       | $0.05~0.15  |
| Part 4 (사전 등록)     | manual eval (D1-D + D2-A blind)                       | ~2h       | $0          |
| **합계**               |                                                       | ~9h       | ~$0.15~0.35 |

### Slice 12 임계 / cap

- 누적 임계: $4.00 (마진 33.9% 잔여)
- Slice 12 cap: **$1.00** (Slice 9~11 동일 정책 유지)
- LLM 호출 한도: **50/슬라이스** (#33 PER_SLICE 표준)
- Step 0 cap 비율: ~$0.20 / $1.00 = 20% 사용 예상 (마진 80%)
- Fallback 비상 정지 임계: cap 80% ($0.80) 도달 시

---

## §2. Step 0a — #58 parse_json_response Trailing Characters Tolerance

### 2-1. 산출물

| #   | 파일                                                   | 변경 유형                            |
| --- | ------------------------------------------------------ | ------------------------------------ |
| 1   | `portfolio/services/coach/parsers.py` (또는 해당 위치) | 보강 (regex tolerance 도입)          |
| 2   | `tests/coach/test_parse_json_response.py`              | 단위 테스트 +3~5 (trailing 패턴 3종) |
| 3   | `docs/portfolio/coach/debts.md`                        | #58 close, #41 자연 close            |
| 4   | `docs/portfolio/coach/slice12/step0a_58_closing.md`    | 종결 보고                            |

### 2-2. 4.17% FAIL 케이스 분석 (선행 분석)

**기준 케이스**: `docs/portfolio/coach/slice11/part4_matrix.json` 의 E3/haiku/#1 (schema_fitting_pass=False)

**패턴 추출**:

```bash
python -c "
import json
data = json.load(open('docs/portfolio/coach/slice11/part4_matrix.json'))
for c in data['cases']:
    if c['entry']=='e3' and c['model']=='haiku' and c['repeat']==1:
        print(c['response_text'])
"
```

**예상 패턴**:

```
{
  "summary": "...",
  "key_observations": [...],
  "action_items": [...],
  "risk_flags": [...],
  "confidence": 4
}
---

## 📊 추가 코멘트
이 분석은...
```

**문제**: `json.loads()`가 valid JSON 뒤 trailing markdown에서 `json.JSONDecodeError: Extra data` 발생.

### 2-3. 구현 명세

#### 2-3-1. 핵심 로직 (트리오 패턴 — try-progressive)

````python
import json
import re

def parse_json_response(response_text: str, expected_schema=None):
    """
    LLM 응답에서 첫 valid JSON 블록만 추출 (Slice 12 Step 0 #58 보강).

    Tolerance 패턴:
    1. valid JSON 단독 → json.loads() 그대로
    2. ```json ... ``` 코드펜스 → 펜스 제거 후 parse (Slice 1 기존)
    3. valid JSON + trailing 마크다운 → 첫 JSON 블록 추출 후 parse (Slice 12 #58 신규)

    Raises:
        ValidationError: 3 시도 모두 실패 시
    """
    text = response_text.strip()

    # Tier 1: 직접 parse (Slice 1 기존)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tier 2: 코드펜스 제거 (Slice 1 기존)
    fence_match = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Tier 3: trailing characters tolerance (Slice 12 #58 신규)
    # 첫 { 부터 매칭되는 } 까지만 추출
    decoder = json.JSONDecoder()
    try:
        obj, end_idx = decoder.raw_decode(text)
        # end_idx 이후 trailing 문자가 있으면 명시적 log (silent하게 무시 X)
        if end_idx < len(text):
            trailing = text[end_idx:].strip()
            if trailing:
                # log 또는 메타데이터에 trailing 보존 (선택)
                pass
        return obj
    except json.JSONDecodeError as e:
        raise ValidationError(f"parse_json_response failed: {e}") from e
````

#### 2-3-2. raw_decode 활용 근거

- `json.JSONDecoder().raw_decode(text)` 는 첫 valid JSON 객체만 반환 + end_idx 제공
- trailing 문자 무시 자연 처리
- Python 표준 라이브러리 (외부 의존 0)

#### 2-3-3. 호환성 확인 사항

- Tier 1/2는 기존 동작 그대로 (backward-compat 100%)
- Tier 3는 신규 — 기존 Tier 1/2에서 통과하던 케이스는 Tier 3까지 진입 안 함
- 따라서 회귀 영향 = 0 (FAIL 케이스만 신규 PASS)

### 2-4. 단위 테스트 +5 (3 패턴 × 1 + edge case × 2)

````python
# tests/coach/test_parse_json_response_trailing.py
import pytest
from portfolio.services.coach.parsers import parse_json_response, ValidationError

class TestParseJsonTrailingTolerance:
    """Slice 12 Step 0 #58: trailing characters tolerance"""

    def test_trailing_markdown_separator(self):
        """valid JSON + --- + 마크다운"""
        text = '{"key": "value"}\n---\n\n## 추가 코멘트\n본문...'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_trailing_korean_text(self):
        """valid JSON + 한국어 텍스트"""
        text = '{"summary": "한국어"}\n\n이 분석은 추가로...'
        result = parse_json_response(text)
        assert result == {"summary": "한국어"}

    def test_trailing_second_json_object(self):
        """valid JSON + 다른 JSON (첫 객체만 추출)"""
        text = '{"first": 1}\n{"second": 2}'
        result = parse_json_response(text)
        assert result == {"first": 1}

    def test_clean_json_unchanged(self):
        """trailing 없는 valid JSON은 그대로 (backward-compat)"""
        text = '{"key": "value"}'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_code_fence_unchanged(self):
        """코드펜스 케이스 그대로 (backward-compat)"""
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        """parse 불가능한 경우 명시적 raise"""
        text = "completely invalid text without any json"
        with pytest.raises(ValidationError):
            parse_json_response(text)
````

### 2-5. #58 close 트리거 검증 (Slice 11 케이스 재현)

```bash
# Part 4 E3/haiku/#1 raw response로 재현 테스트
python -c "
import json
from portfolio.services.coach.parsers import parse_json_response

data = json.load(open('docs/portfolio/coach/slice11/part4_matrix.json'))
fail_case = next(c for c in data['cases'] if c['entry']=='e3' and c['model']=='haiku' and c['repeat']==1)
response = fail_case['response_text']

# Slice 12 #58 보강 후: 정상 parse 기대
result = parse_json_response(response)
print('PASS:', list(result.keys()))
"
```

**기대 출력**: `PASS: ['summary', 'key_observations', 'action_items', 'risk_flags', 'confidence']`

### 2-6. #41 자연 close (dependency 해소)

`docs/portfolio/coach/debts.md` 갱신:

```markdown
## #41: schema fitting → close (Slice 12 Step 0 #58 dependency 해소)

- Slice 11 Part 5 keep_open (#58 dep) → Slice 12 Step 0 #58 close 시 자연 close 확정
- 4.17% FAIL 패턴 완전 해소

## #58: parse_json_response trailing tolerance → close (Slice 12 Step 0)

- 구현: raw_decode 기반 Tier 3 tolerance
- 단위 테스트 6/6 PASS (3 trailing 패턴 + 2 backward-compat + 1 invalid)
- Slice 11 Part 4 E3/haiku/#1 케이스 재현 PASS
- 기존 Tier 1/2 backward-compat 100%
```

---

## §3. Step 0b — #59 Action Measurability E3 Prompt 보강

### 3-1. 산출물

| #   | 파일                                                         | 변경 유형                              |
| --- | ------------------------------------------------------------ | -------------------------------------- |
| 1   | `portfolio/services/coach/prompt_builder.py` E3PromptBuilder | 보강 (action_items measurability 강제) |
| 2   | `tests/coach/test_prompt_builder_e3.py` 또는 신규            | 단위 테스트 +3                         |
| 3   | E3 micro-matrix 4 케이스 (haiku × 2 + sonnet × 2)            | 검증 LLM 콜                            |
| 4   | `docs/portfolio/coach/slice12/step0b_59_micro_matrix.json`   | 매트릭스 결과                          |
| 5   | `docs/portfolio/coach/slice12/step0b_59_closing.md`          | 종결 보고                              |

### 3-2. NG 패턴 분석 (Slice 11 Part 5 데이터)

```bash
# E3 case에서 actionability NG 사례 추출
python -c "
import json
data = json.load(open('docs/portfolio/coach/slice11/part5_merged_eval.json'))
for m in data:
    if m['entry']=='e3' and m['byungjin']['actionability']=='NG':
        print(f'Case #{m[\"case_num\"]} model={m[\"model\"]} note={m[\"byungjin\"][\"note\"]}')"
```

**예상 패턴**:

- "모니터링 필요" / "검토하세요" / "주시하세요" 단독 (구체성 0)
- 종목/지표 인용 없는 일반론
- priority "high"인데 description은 모니터링 수준

### 3-3. Prompt 보강 명세

#### 3-3-1. 신규 action_items 작성 규칙 (E3 prompt 안에 직접 명시)

```
### action_items 작성 규칙 (필수 준수)

1. **구체성 필수**: 각 action_item의 description에 다음 중 하나 이상 포함
   - 종목 ticker (예: "MSFT 비중 조정")
   - 정량 지표 (예: "HHI 0.2125 → 0.15 목표")
   - 비율/수치 (예: "기술 섹터 35% → 25% 축소")

2. **측정 가능성 필수**: description에 다음 중 하나 이상 포함
   - 목표 수치 (예: "Top3 비중 65% → 50%")
   - 기한 또는 시기 (예: "분기 리밸런싱 시", "현재 분기 내")

3. **금지 패턴** (위 항목 충족 시 사용 가능, 단독 사용 금지):
   - "모니터링 필요" 단독
   - "검토하세요" 단독
   - "주시하세요" 단독
   - 종목/지표 인용 없는 일반론 ("장기적 관점에서 다각화")

4. **priority 정합성**:
   - high: 즉각 행동 필요 (예: "1주 내 비중 조정")
   - medium: 분기 단위 검토 (예: "다음 리밸런싱 시")
   - low: 장기 모니터링 (단, 구체적 지표 + 임계 명시 필수)
```

#### 3-3-2. E3PromptBuilder 코드 보강

```python
# portfolio/services/coach/prompt_builder.py 의 E3PromptBuilder.build_user_prompt 안에 추가

E3_ACTION_RULES = """
### action_items 작성 규칙 (필수 준수)
1. 구체성 필수: ticker 또는 정량 지표 또는 비율/수치 중 하나 이상 포함
2. 측정 가능성 필수: 목표 수치 또는 기한 중 하나 이상 포함
3. "모니터링 필요"/"검토하세요"/"주시하세요" 단독 사용 금지
4. priority 정합성: high=즉각, medium=분기, low=장기(임계 명시 필수)
"""

# build_user_prompt() 안에서 E3 prompt body 다음에 추가
prompt += E3_ACTION_RULES
```

### 3-4. 단위 테스트 +3

```python
# tests/coach/test_prompt_builder_e3_action_rules.py
class TestE3ActionRules:
    """Slice 12 Step 0 #59: E3 prompt action measurability 규칙"""

    def test_e3_prompt_includes_action_rules(self):
        """E3 prompt에 action_items 규칙 명시되어 있음"""
        builder = E3PromptBuilder()
        msgs = builder.build_messages(sample_e3_input)
        user_content = msgs[1]["content"]
        assert "action_items 작성 규칙" in user_content
        assert "구체성 필수" in user_content
        assert "측정 가능성 필수" in user_content

    def test_e3_prompt_forbids_single_monitor(self):
        """금지 패턴 명시"""
        builder = E3PromptBuilder()
        msgs = builder.build_messages(sample_e3_input)
        user_content = msgs[1]["content"]
        assert "모니터링 필요" in user_content
        assert "단독 사용 금지" in user_content

    def test_e3_prompt_priority_consistency(self):
        """priority 정합성 규칙 명시"""
        builder = E3PromptBuilder()
        msgs = builder.build_messages(sample_e3_input)
        user_content = msgs[1]["content"]
        assert "priority 정합성" in user_content
```

### 3-5. E3 Micro-Matrix 검증 (4 케이스)

#### 3-5-1. 실행 명령

```bash
python scripts/slice12_step0b_e3_micro_matrix.py
```

#### 3-5-2. 매트릭스 명세

| 케이스 | model  | repeat | 입력                                                |
| ------ | ------ | ------ | --------------------------------------------------- |
| 1      | haiku  | 1      | portfolio_a2 fixture E3 입력 (Slice 11 Part 4 동일) |
| 2      | haiku  | 2      | 동일                                                |
| 3      | sonnet | 1      | 동일                                                |
| 4      | sonnet | 2      | 동일                                                |

**비용 예상**: 4 케이스 × 평균 $0.01 ≈ $0.04

#### 3-5-3. NG ratio 비교 (Before vs After)

| 시점                     | E3 NG ratio    | source            |
| ------------------------ | -------------- | ----------------- |
| Slice 11 Part 5 (Before) | **50%** (2/4)  | merged_eval.json  |
| Slice 12 Step 0 (After)  | **목표 < 30%** | micro_matrix.json |

**검증 방법**: 동일 D1-D rubric으로 본 채팅 Claude가 4 케이스 actionability 평가 → NG ratio 산출. (Slice 11 Part 5 manual eval rubric 그대로 재활용)

> Note: 정식 ground truth는 병진(한국어 native)이지만, Step 0 검증은 작업 분량 통제 위해 Claude 단독 평가로 단축. Slice 12 Part 4 매트릭스에서 정식 D1-D + D2-A blind 재검증.

### 3-6. #59 close 트리거 검증

```python
# Step 0b 종결 시 다음 조건 모두 충족 시 #59 close
condition_1 = nat_ratio < 30%  # E3 NG ratio 운영 기준 30% 이하
condition_2 = all([c["actionability"] in ["OK", "N/A"] for c in micro_matrix_cases])  # 4/4 NG 0건
condition_3 = unit_tests_pass == 3/3  # 단위 테스트 모두 PASS

if condition_1 and condition_2:
    debt_status = "close"
elif condition_1:
    debt_status = "keep_open"  # NG 1건 이상이지만 30% 이하
else:
    debt_status = "escalate"  # PS 1.5 → 2.0
```

> Step 0b close 기준: NG 0/4 (이상적) 또는 NG 1/4=25% (운영 기준 이하). NG 2/4=50% 또는 그 이상이면 keep_open + Slice 13 Step 0 후보 재진입.

---

## §4. Step 0 검증 (회귀 + IDENTICAL + Cap)

### 4-1. 회귀 측정

```bash
pytest portfolio/tests tests/coach -q 2>&1 | tail -3
```

**기대값**:

- 회귀: 571 → **579~585** (+8~14)
  - #58 단위 테스트 +6
  - #59 단위 테스트 +3
  - 기타 classifier 등 ±1~2
- 슬라이스 유형: mini-slice (KPI 10 임계 +13~20 적용 — Slice 11 D5-A 갱신 기준)
- **KPI 10 임계 +13~20에서 +8~14 UNDER 가능** → 사유: multi-debt mini-slice (Slice 10 single-debt 패턴과 다름) → KPI 10 임계 보정 후보 (Slice 12 종결 시 검토)

### 4-2. IDENTICAL 확인

```bash
pytest portfolio/tests/test_identical_hash.py -q 2>&1 | tail -3
```

**기대값**: 7/7 PASS (Slice 11 baseline 그대로)

### 4-3. Cap 사용

| 항목                 | 값                                     |
| -------------------- | -------------------------------------- |
| Slice 12 Step 0 비용 | ~$0.05~0.20 (E3 micro-matrix 4 케이스) |
| Slice 12 cap 사용    | ~5~20% / $1.00 (마진 80%+)             |
| 전체 누적 임계       | ~$2.69~2.85 / $4.00 (마진 ~29~33%)     |

---

## §5. 회신 형식 (Claude Code → 병진)

```
## Slice 12 Step 0 완료 보고 (mini-slice multi-debt)

### baseline 확인
- [O/X] 브랜치: slice12 (from 890b86c)
- [O/X] 회귀 baseline: 571
- [O/X] 부채 상태 확인 (#51/#41/#58/#59)

### Step 0a: #58 parse trailing tolerance
- [O/X] parsers.py raw_decode Tier 3 tolerance 보강
- [O/X] 단위 테스트 +6 (trailing 3 + backward-compat 2 + invalid 1)
- [O/X] Slice 11 E3/haiku/#1 케이스 재현 PASS
- [O/X] #58 close
- [O/X] #41 자연 close (dependency 해소)

### Step 0b: #59 action measurability E3
- [O/X] E3PromptBuilder action 규칙 4종 명시
- [O/X] 단위 테스트 +3
- [O/X] E3 micro-matrix 4 케이스 실행
  - haiku: NG _/2
  - sonnet: NG _/2
  - 종합 NG ratio: _%
  - 비용: $_
- [O/X] #59 close 또는 keep_open (NG ratio < 30% 시 close)

### 회귀 + IDENTICAL
- 회귀: 571 → N (변화 +Δ)
- KPI 10: PASS / UNDER (multi-debt mini-slice 패턴, Slice 12 종결 시 임계 보정 후보)
- IDENTICAL: 7/7 PASS

### 비용 누적
- Step 0 단독: $_
- Slice 12 누적: $_ / $1.00 (마진 _%)
- 전체 누적: $_ / $4.00 (마진 _%)

### 부채 변화
- close: #58, #41 (#58 dependency), #59 (NG < 30% 시)
- 유지: #51 (Slice 13 Step 0 자연 진입 후보)

### 산출물 dump (8건)
1. portfolio/services/coach/parsers.py (raw_decode Tier 3 보강)
2. tests/coach/test_parse_json_response_trailing.py (신규 +6)
3. portfolio/services/coach/prompt_builder.py (E3 action 규칙)
4. tests/coach/test_prompt_builder_e3_action_rules.py (신규 +3)
5. scripts/slice12_step0b_e3_micro_matrix.py (신규)
6. docs/portfolio/coach/slice12/step0a_58_closing.md
7. docs/portfolio/coach/slice12/step0b_59_micro_matrix.json
8. docs/portfolio/coach/slice12/step0b_59_closing.md
9. docs/portfolio/coach/debts.md (갱신)

### git commit
- commit message: "Slice 12 Step 0: #58 parse trailing tolerance + #59 E3 action measurability (multi-debt mini)"

### 다음 단계 (사용자에게)
1. Step 0 종결 확정 여부
2. Slice 12 Part 1 진입 (preset scoring base class) 또는 결정 사이클 추가
```

---

## §6. Fallback 가이드

| 상황                                                | 대응                                                                                               |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| baseline 회귀 ≠ 571                                 | 즉시 중단, 보고. Slice 11 종결 확정 여부 확인                                                      |
| Slice 11 E3/haiku/#1 재현 실패 (#58 검증)           | parsers.py Tier 3 로직 점검. raw_decode 동작 확인                                                  |
| #58 보강 후 기존 회귀 깨짐 (backward-compat 실패)   | 즉시 중단. Tier 1/2 호환성 점검. raw_decode가 우선 진입 안 하는지 확인                             |
| E3 micro-matrix NG ratio ≥ 50% (#59 보강 효과 없음) | #59 escalate (PS 1.5 → 2.0), keep_open 처리. Slice 12 Part 1 진입 전 추가 분석                     |
| E3 micro-matrix NG ratio 30~50%                     | #59 keep_open (개선 있으나 운영 기준 미달). Slice 13 Step 0 재진입                                 |
| Step 0 비용 > $0.50 (cap 50% 도달)                  | 비상 정지. 비용 분석 후 사용자 보고                                                                |
| IDENTICAL ≠ 7/7                                     | 즉시 중단. 어떤 hash 변경됐는지 보고                                                               |
| KPI 10 UNDER (회귀 < +13)                           | UNDER 표시 + 사유 작성 ("multi-debt mini-slice 첫 사례"). Slice 12 종결 시 KPI spec 보정 후보 등록 |

---

## §7. KPI Matrix (Step 0 단독)

| #   | KPI                              | 측정값 | 기대값      | PASS/FAIL                       |
| --- | -------------------------------- | ------ | ----------- | ------------------------------- |
| 1   | #58 parsers.py Tier 3 보강       | O      | O           | PASS                            |
| 2   | #58 단위 테스트 +6               | \_     | 6           | PASS                            |
| 3   | #58 Slice 11 케이스 재현         | \_     | PASS        | PASS                            |
| 4   | #58 backward-compat 100%         | \_     | 회귀 영향 0 | PASS                            |
| 5   | #58 close                        | \_     | close       | PASS                            |
| 6   | #41 자연 close                   | \_     | close       | PASS                            |
| 7   | #59 E3 prompt action 규칙 명시   | O      | O           | PASS                            |
| 8   | #59 단위 테스트 +3               | \_     | 3           | PASS                            |
| 9   | #59 E3 micro-matrix 4/4 실행     | \_     | 4/4         | PASS                            |
| 10  | #59 NG ratio < 30%               | \_%    | < 30%       | PASS/FAIL                       |
| 11  | #59 close 또는 keep_open 처리    | \_     | 처리        | PASS                            |
| 12  | 회귀 +Δ (mini-slice 임계 +13~20) | \_     | +13~20      | PASS/UNDER (multi-debt 첫 사례) |
| 13  | IDENTICAL                        | \_     | 7/7         | PASS                            |
| 14  | Slice cap 사용 < 30% ($0.30)     | \_%    | < 30%       | PASS                            |

---

## §8. Slice 13 사전 등록 (Step 0에서 미루는 부채)

| ID                            | 사유                                                     | Slice 13 진입 시점         |
| ----------------------------- | -------------------------------------------------------- | -------------------------- |
| #51 output_token multivariate | Slice 12 Step 0 multi-debt에서 의도적 미룸 (DS-1-B 결정) | Slice 13 Step 0 1순위 후보 |
| (#59 keep_open 시) #59 재진입 | NG ratio 30% 이상 잔존 시                                | Slice 13 Step 0 후보       |

---

## §9. Slice 12 Part 1 진입 준비 (Step 0 종결 후)

Step 0 회신 후 Slice 12 Part 1 (preset scoring base class) 작업 지시서 별도 작성 예정.

**사전 등록 사항**:

- Part 1 산출물: `portfolio/services/scoring/base.py` (scoring engine base class) + 5 preset adapter 스켈레톤
- Part 1 회귀 예상: +9 (Slice 11 Part 1 패턴 — 표준 슬라이스 임계 +9~15)
- Part 1 비용: $0 (LLM 호출 없음)
- IDENTICAL: 7/7 유지

---

## 📋 Step 0 작업 요약 (Stock-Vis Portfolio Coach의 어느 부분?)

**서비스 위치**: Slice 12 본 work(preset 스코어링 엔진 일반화) **진입 전 부채 청산** 단계. 두 부채를 동시에 처리하는 **mini-slice multi-debt** 첫 사례 (Slice 10 mini-slice + Slice 11 Step 0 multi-debt 패턴 융합).

### 무엇을 진행하나? (2건)

| Step    | 부채                             | 작업                                                           | 사용자 영향                                                                                                 |
| ------- | -------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Step 0a | #58 parse trailing tolerance     | parsers.py raw_decode Tier 3 보강                              | 매트릭스 슬라이스 fitting 4.17% FAIL → 0%                                                                   |
| Step 0b | #59 action measurability E3 우선 | E3PromptBuilder action_items 규칙 4종 강제 + micro-matrix 검증 | E3 진단 코멘트 NG 50% → < 30% (실 사용자 50%가 받던 모니터링 수준 액션 → 구체 수치/기한 명시 액션으로 개선) |

### 예상 결과

- **회귀**: 571 → 579~585 (+8~14)
- **부채 변화**: close 3 (#58, #41, #59 NG<30% 시), 유지 1 (#51)
- **비용**: ~$0.05~0.20 (slice cap 마진 80%+)
- **IDENTICAL**: 7/7 유지
- **패턴 정착**: multi-debt mini-slice 첫 사례 → Slice 13+ 표준화 후보

### 사용자 영향 (Step 0 완료 직후)

| 영역                       | 변화                                                                                   |
| -------------------------- | -------------------------------------------------------------------------------------- |
| **앱 사용자 UX (E3 진단)** | "MSFT 비중 조정 검토" → "MSFT 비중 25% → 18% (현재 분기 리밸런싱 시)" 형태로 즉시 개선 |
| **시스템 안정성**          | E3 응답 JSON 파싱 4.17% 실패 → 0% (매트릭스 슬라이스 + 실 운영 모두)                   |
| **개발 신뢰성**            | Slice 12 Part 1~4 (preset 일반화) 작업 시 fitting 부담 0                               |

### 다음 흐름

Step 0 회신 → Slice 12 Part 1 (preset scoring base class) 작업 지시서 작성 → 본 work 진입 → Slice 12 Part 2/3/4 → Slice 12 종결 결정 사이클.
