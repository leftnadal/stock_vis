# Slice 11 Part 5 — Phase A 작업 지시서

**Phase**: Phase A (Claude Code 자동 실행 구간)
**브랜치**: `slice11`
**선행 commit**: Part 4 종결 commit
**예상 시간**: ~30분
**예상 LLM**: **0 콜** (rubric + shuffle 스크립트만)
**Phase A 종료 후**: 병진이 Step 3 (manual eval) 직접 진행 → "Phase B 진행" 메시지로 Phase B 트리거

---

## §0. baseline 확인 (Phase A 시작 전)

다음 항목을 **순서대로** 확인하고 불일치 시 **즉시 중단** 후 보고.

| 항목          | 확인 명령                                                      | 기대값                                                  |
| ------------- | -------------------------------------------------------------- | ------------------------------------------------------- |
| 브랜치        | `git branch --show-current`                                    | `slice11`                                               |
| 회귀 baseline | `pytest portfolio/tests tests/coach -q 2>&1 \| tail -3`        | **571 passed**                                          |
| 누적 비용     | `cat docs/portfolio/coach/COST_POLICY.md \| grep "cumulative"` | $2.6444 / $4.00                                         |
| Slice cap     | Part 4 closing.md §10                                          | $0.2669 / $1.00 (마진 73.3%)                            |
| matrix.json   | `ls docs/portfolio/coach/slice11/part4_matrix.json`            | 존재                                                    |
| 부채 상태     | `cat docs/portfolio/coach/debts.md`                            | #41 keep_open(1part), #48 close, #51 유지, #57/#58 후보 |

baseline 불일치 시 **즉시 중단** 후 보고.

---

## §1. Step 1 — Manual Eval Rubric 작성 (D1-D 채택)

### 1-1. 산출물

**파일**: `docs/portfolio/coach/slice11/manual_eval_rubric.md`

### 1-2. Rubric 정의 (D1-D 3축 하이브리드)

**3축 구조**:

| 축                | 척도          | 적용 범위                                     |
| ----------------- | ------------- | --------------------------------------------- |
| **naturalness**   | 1~5           | 24 케이스 전수 (E1~E6 모두)                   |
| **insight**       | 1~5           | 24 케이스 전수 (E1~E6 모두)                   |
| **actionability** | OK / NG / N/A | E1/E3/E5 12 케이스 (action_items 있는 schema) |

**E2/E4/E6은 actionability N/A**: schema에 action_items 필드 없음 (Part 4 inventory.md §1).

### 1-3. Naturalness 척도 정의 (Slice 9 호환)

| 점수 | 정의                                                                                |
| ---- | ----------------------------------------------------------------------------------- |
| 5    | 한국어 표현 자연. 영어 직역체 없음. 전문 용어와 일반 표현 균형. 문장 흐름 매끄러움. |
| 4    | 한국어 자연. 1~2건 미세 직역체. 전반적 흐름 양호.                                   |
| 3    | 한국어 자연도 보통. 3~5건 직역체 또는 어색한 표현. 의미 전달은 OK.                  |
| 2    | 직역체 다수. 한국어로 어색하나 의미 추정 가능.                                      |
| 1    | 한국어 자연도 낮음. 의미 전달 어려움 또는 영어 단어 다수 미번역.                    |

### 1-4. Insight 척도 정의 (Slice 9 호환)

| 점수 | 정의                                                                                                   |
| ---- | ------------------------------------------------------------------------------------------------------ |
| 5    | 통찰력 우수. 입력 데이터 표면 너머의 의미(예: 섹터 편중 + ETF 간접 중복)를 식별. 비전문가도 이해 가능. |
| 4    | 통찰력 양호. 데이터 간 관계 식별. 1~2건 표면적 관찰 혼재.                                              |
| 3    | 통찰력 보통. 데이터 나열 수준 + 1~2건 의미 부여.                                                       |
| 2    | 통찰력 부족. 데이터 나열 중심. 의미 부여 미흡.                                                         |
| 1    | 통찰력 없음. 단순 데이터 복창 또는 일반론.                                                             |

### 1-5. Actionability 척도 정의 (D1-D 신규)

**OK 판정 기준** (4 조건 중 **3개 이상 충족**):

1. **구체성**: 종목 ticker 또는 정량 지표(수치/비율) 인용
2. **측정 가능성**: 목표 수치 또는 기한 명시 (예: "비중 20% → 15%")
3. **우선순위 정합**: priority 필드 (high/medium/low)가 description 강도와 일치
4. **category 적합성**: category 필드(rebalance/monitor/research/review)가 description 의미와 일치

**NG 판정**: 위 4 조건 중 **2개 이하 충족** 또는 다음 패턴 발견:

- "모니터링 필요" / "검토하세요" / "주시하세요" 단독 (구체성 0)
- 종목/지표 인용 없는 일반론
- "장기적으로" / "중기적으로" 외 시간 표현 없음
- priority "high"인데 description은 모니터링 수준

**N/A 판정**: schema에 action_items 필드 없음 (E2/E4/E6).

### 1-6. 평가 진행 가이드 (병진용)

- 24 케이스 **무순** (D2-A blind 적용). entry/model 라벨 후공개.
- 1 케이스당 ~100초 표준 (naturalness 30초 + insight 40초 + actionability 30초)
- 24 케이스 총 ~40분
- 평가 중 **점수 분포 폭 의식적 사용**: 1~5 양극단 적극 활용 (Slice 9 #26 분포 폭 2 학습 → Slice 11 폭 ≥3 목표)

### 1-7. 산출물 dump 작업

`docs/portfolio/coach/slice11/manual_eval_rubric.md` 파일을 위 §1-2 ~ §1-6 내용 그대로 한국어 markdown으로 dump한다.

**구조**:

```markdown
# Slice 11 Part 5 — Manual Eval Rubric (D1-D 3축 하이브리드)

## §1. 3축 구조

[§1-2 표]

## §2. Naturalness 척도 정의

[§1-3 표]

## §3. Insight 척도 정의

[§1-4 표]

## §4. Actionability 척도 정의

[§1-5 본문 + OK/NG/N/A 조건]

## §5. 평가 진행 가이드

[§1-6 본문]

## §6. 출력 형식 (병진 입력)

- naturalness: \_\_/5
- insight: \_\_/5
- actionability: [OK/NG/N/A]
- note: (선택, 특이 사항만)
```

---

## §2. Step 2 — Blind Shuffle 스크립트 + Shuffled View 생성 (D2-A 채택)

### 2-1. 산출물 2건

1. `scripts/manual_eval_shuffle.py` (Slice 12+ 재활용 스크립트)
2. `docs/portfolio/coach/slice11/part5_shuffled_view.md` (병진 평가용 view)
3. `docs/portfolio/coach/slice11/part5_label_mapping.json` (평가 후 라벨 재공개용)

### 2-2. `scripts/manual_eval_shuffle.py` 명세

**입력**: `docs/portfolio/coach/slice11/part4_matrix.json`
**출력**:

- shuffled view markdown (`part5_shuffled_view.md`)
- label mapping JSON (`part5_label_mapping.json`)

**seed**: 고정 (42) — Slice 12+ 재현성 보장

**전체 코드**:

````python
"""
Slice 11+ Manual Eval Shuffle Script (D2-A blind)
- 입력: part{N}_matrix.json
- 출력: part{N}_shuffled_view.md + part{N}_label_mapping.json
- seed=42 고정 (재현성)
- Slice 12+ 매트릭스 슬라이스 manual eval 자연 재활용
"""
import json
import random
from pathlib import Path
import argparse

def shuffle_matrix(matrix_json_path: Path, output_dir: Path, seed: int = 42, prefix: str = "part5"):
    """24 케이스를 무순으로 셔플하여 blind view 생성."""
    with open(matrix_json_path, encoding="utf-8") as f:
        data = json.load(f)

    cases = data["cases"]
    indices = list(range(len(cases)))
    rng = random.Random(seed)
    rng.shuffle(indices)

    # blind view 생성 (entry/model 마스킹)
    view_lines = [f"# Slice 11 {prefix.capitalize()} — Manual Eval Blind View (D2-A)", ""]
    view_lines.append(f"**Total cases**: {len(cases)}, **Seed**: {seed}")
    view_lines.append("")
    view_lines.append("> **평가 가이드**: `manual_eval_rubric.md` 참조 (3축 하이브리드: nat 1~5 / ins 1~5 / actionability OK·NG·N/A)")
    view_lines.append(">")
    view_lines.append("> **blind 유지**: 평가 완료까지 `label_mapping.json` 열지 말 것")
    view_lines.append(">")
    view_lines.append("> **분포 폭 의식**: 1~5 양극단 적극 활용 (Slice 9 폭 2 → Slice 11 폭 ≥3 목표)")
    view_lines.append("")
    view_lines.append("---")
    view_lines.append("")

    # label mapping (병진 평가 완료 후 재공개용)
    label_mapping = {}

    for view_idx, original_idx in enumerate(indices, start=1):
        case = cases[original_idx]
        label_mapping[view_idx] = {
            "entry": case["entry"],
            "model": case["model"],
            "repeat": case["repeat"],
            "original_index": original_idx,
            "schema_fitting_pass": case["schema_fitting_pass"]
        }

        view_lines.append(f"## Case #{view_idx}")
        view_lines.append("")
        view_lines.append(f"- output_tokens: {case['output_tokens']}")
        view_lines.append(f"- latency_ms: {case['latency_ms']}")
        view_lines.append(f"- schema_fitting: {'PASS' if case['schema_fitting_pass'] else 'FAIL'}")
        view_lines.append("")
        view_lines.append("### Response")
        view_lines.append("")
        view_lines.append("```")
        view_lines.append(case["response_text"])
        view_lines.append("```")
        view_lines.append("")
        view_lines.append("### Manual Eval (병진 입력)")
        view_lines.append("")
        view_lines.append("- naturalness: ___/5")
        view_lines.append("- insight: ___/5")
        view_lines.append("- actionability: [OK/NG/N/A]")
        view_lines.append("- note: ")
        view_lines.append("")
        view_lines.append("---")
        view_lines.append("")

    view_path = output_dir / f"{prefix}_shuffled_view.md"
    view_path.write_text("\n".join(view_lines), encoding="utf-8")

    mapping_path = output_dir / f"{prefix}_label_mapping.json"
    mapping_path.write_text(json.dumps(label_mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Shuffled view: {view_path}")
    print(f"Label mapping: {mapping_path}")
    print(f"N cases: {len(cases)}, Seed: {seed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slice 11+ Manual Eval Shuffle (D2-A blind)")
    parser.add_argument("--matrix", required=True, type=Path, help="Path to part{N}_matrix.json")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--prefix", type=str, default="part5", help="Output filename prefix (default: part5)")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    shuffle_matrix(args.matrix, args.output_dir, args.seed, args.prefix)
````

### 2-3. 실행 명령

```bash
python scripts/manual_eval_shuffle.py \
  --matrix docs/portfolio/coach/slice11/part4_matrix.json \
  --output-dir docs/portfolio/coach/slice11 \
  --seed 42 \
  --prefix part5
```

### 2-4. 검증 명령

```bash
# 1. 24 케이스 dump 확인
echo "[Check 1] Case # count:"
grep -c "^## Case #" docs/portfolio/coach/slice11/part5_shuffled_view.md
# 기대: 24

# 2. label_mapping.json 24 항목 확인
echo "[Check 2] label_mapping count:"
python -c "import json; d=json.load(open('docs/portfolio/coach/slice11/part5_label_mapping.json')); print(len(d))"
# 기대: 24

# 3. seed 재현성 확인 (동일 명령 재실행하여 동일 결과 나오는지)
echo "[Check 3] Seed reproducibility:"
md5sum docs/portfolio/coach/slice11/part5_shuffled_view.md
python scripts/manual_eval_shuffle.py \
  --matrix docs/portfolio/coach/slice11/part4_matrix.json \
  --output-dir /tmp/shuffle_test \
  --seed 42 \
  --prefix part5
md5sum /tmp/shuffle_test/part5_shuffled_view.md
# 기대: 두 md5sum 동일
rm -rf /tmp/shuffle_test

# 4. blind 마스킹 확인 (view 파일에 entry/model 단어 없어야 함)
echo "[Check 4] Blind masking:"
grep -E "(haiku|sonnet|e1|e2|e3|e4|e5|e6)" docs/portfolio/coach/slice11/part5_shuffled_view.md | grep -vE "(response_text|JSON|response|e1_|e2_|e3_|e4_|e5_|e6_|HHI|Healthcare)" | head -5
# 기대: 응답 본문 안의 단어만 매칭 (Case 헤더에는 라벨 없음)
```

---

## §3. Phase A 종료 — 회귀 + IDENTICAL 확인

### 3-1. 회귀 측정

```bash
pytest portfolio/tests tests/coach -q 2>&1 | tail -3
```

**기대값**:

- Phase A는 docs/scripts 추가만 (production 코드 무변경)
- 회귀: **571 → 571** (변화 0) 또는 +α (shuffle 스크립트 단위 테스트 없음 → 0 예상)

> ※ shuffle 스크립트는 production import 경로 외부(`scripts/`)이므로 회귀 카운트 영향 없음.

### 3-2. IDENTICAL 확인

```bash
# 9슬라이스 누적 IDENTICAL (Slice 1·3·6·7·8·9·10·11 baseline hash 동일성)
pytest portfolio/tests/test_identical_hash.py -q 2>&1 | tail -3
```

**기대값**: 8/8 PASS (Slice 11 baseline 그대로)

---

## §4. Phase A 회신 형식 (Claude Code → 병진)

Phase A 완료 후 다음 형식으로 회신:

```
## Phase A 완료 보고

### baseline 확인
- [O/X] 브랜치: slice11
- [O/X] 회귀 baseline: 571 passed
- [O/X] matrix.json 존재
- [O/X] 부채 상태 확인

### Step 1: Manual Eval Rubric (D1-D)
- [O/X] manual_eval_rubric.md 생성
  - 라인 수: N
  - 3축 구조 (nat 1~5 / ins 1~5 / actionability OK·NG·N/A) 포함 확인

### Step 2: Blind Shuffle (D2-A)
- [O/X] scripts/manual_eval_shuffle.py 생성 (seed=42)
- [O/X] part5_shuffled_view.md 생성 (Case #1~#24 24개 확인)
- [O/X] part5_label_mapping.json 생성 (24 항목 확인)

### 검증
- [O/X] Check 1 — Case # count: 24
- [O/X] Check 2 — label_mapping count: 24
- [O/X] Check 3 — seed 재현성: 두 md5sum 동일
- [O/X] Check 4 — blind 마스킹: Case 헤더에 entry/model 라벨 없음

### 회귀 + IDENTICAL
- 회귀: 571 → N (변화 ±?)
- IDENTICAL: 8/8 PASS

### 산출물 dump (4건)
1. docs/portfolio/coach/slice11/manual_eval_rubric.md
2. scripts/manual_eval_shuffle.py
3. docs/portfolio/coach/slice11/part5_shuffled_view.md
4. docs/portfolio/coach/slice11/part5_label_mapping.json

### 다음 단계
병진이 Step 3 (manual eval 24 케이스 점수 입력 ~40분) 진행
→ 완료 후 "Phase B 진행" 메시지로 Phase B 트리거
```

---

## §5. Step 3 안내 (병진 직접 작업, Claude Code 대기)

**이 단계는 병진(사용자)이 직접 진행**합니다. Claude Code는 Phase A 종료 후 대기.

### 5-1. 작업 방법

1. `docs/portfolio/coach/slice11/part5_shuffled_view.md` 열기
2. 24 케이스 순서대로 평가 (Case #1 → #24):
   - naturalness: \_\_/5
   - insight: \_\_/5
   - actionability: [OK / NG / N/A]
   - note: (선택, 특이 사항만)
3. 점수 입력은 `part5_shuffled_view.md` 안에 직접 작성 (각 Case 하단 \_\_\_ 자리)

### 5-2. 평가 가이드 재확인

- **rubric**: `docs/portfolio/coach/slice11/manual_eval_rubric.md` 참조
- **분포 폭 의식**: 1~5 양극단 적극 활용 (Slice 9 폭 2 → Slice 11 폭 ≥3 목표)
- **blind 유지**: 평가 완료까지 `part5_label_mapping.json` **열지 말 것**
- **시간 기준**: 1 케이스 ~100초 / 24 케이스 ~40분

### 5-3. 완료 후 Phase B 트리거

병진이 평가 완료 후 다음 메시지로 알림:

```
Phase B 진행
```

---

## §6. Fallback 가이드 (Phase A 도중 이상 발견 시)

| 상황                                                          | 대응                                                                                            |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| baseline 회귀 ≠ 571                                           | 즉시 중단, 보고. 사용자 확인 후 재시작                                                          |
| matrix.json 손상 또는 미존재                                  | Part 4 종결 commit에서 복구 (`git log --all -- docs/portfolio/coach/slice11/part4_matrix.json`) |
| shuffle seed 42 재현 실패                                     | `random.Random(42)` 명시적 사용 확인 (글로벌 `random` 미사용)                                   |
| Check 4 blind 마스킹 실패 (Case 헤더에 entry/model 라벨 노출) | view 생성 코드의 view_lines.append() 부분 점검 — case 객체 그대로 dump 시 라벨 노출 가능        |
| 회귀 ≠ 571 (Phase A 후)                                       | scripts/ 디렉토리는 회귀 카운트 영향 없음 — 다른 변경 있는지 확인                               |
| IDENTICAL ≠ 8/8                                               | 즉시 중단. 어떤 hash 변경됐는지 보고                                                            |

---

## §7. KPI 후보 (Phase A 자체 PASS 기준, Phase B에서 본 KPI 통합)

| #   | KPI                                   | 측정값 | 기대값        | PASS/FAIL |
| --- | ------------------------------------- | ------ | ------------- | --------- |
| A1  | manual_eval_rubric.md 생성            | 존재   | 존재          | PASS      |
| A2  | 3축 구조 (nat/ins/actionability) 명시 | O      | O             | PASS      |
| A3  | shuffle 스크립트 생성 (seed=42)       | 존재   | 존재          | PASS      |
| A4  | part5_shuffled_view.md Case # count   | 24     | 24            | PASS      |
| A5  | label_mapping.json 항목 수            | 24     | 24            | PASS      |
| A6  | seed 재현성 (md5sum 동일)             | 동일   | 동일          | PASS      |
| A7  | blind 마스킹 (Case 헤더 라벨 없음)    | O      | O             | PASS      |
| A8  | 회귀 baseline 유지                    | 571    | 571 (또는 ±0) | PASS      |
| A9  | IDENTICAL                             | 8/8    | 8/8           | PASS      |

Phase B에서 위 A1~A9를 흡수하여 Part 5 전체 KPI matrix로 통합.

---

## 📋 Phase A 작업 요약

**Slice 11 Part 5의 Phase A는 manual eval 진행을 위한 준비 단계**:

1. **Rubric 작성** (D1-D 3축 하이브리드): 병진이 24 케이스를 어떤 기준으로 평가할지 정의
2. **Blind Shuffle 스크립트** (D2-A): 24 케이스를 무순으로 섞어 entry/model 라벨 가림 (self-bias 통제)
3. **검증**: shuffle 재현성 + blind 마스킹 효과 확인

**Phase A 완료 후 산출물**:

- `docs/portfolio/coach/slice11/manual_eval_rubric.md` (D1-D rubric)
- `scripts/manual_eval_shuffle.py` (Slice 12+ 재활용 도구)
- `docs/portfolio/coach/slice11/part5_shuffled_view.md` (병진 평가용 blind view)
- `docs/portfolio/coach/slice11/part5_label_mapping.json` (Phase B에서 라벨 매핑)

**다음 흐름**:
Phase A 회신 → 병진 Step 3 (~40분 직접 평가) → "Phase B 진행" 메시지 → Phase B 자동 실행 (winner 계산 + 부채 처리 + Slice 11 종결)
