# Slice 7 Part 4 작업 지시서 — Manual Eval + Slice 7 종결

> **Part 4 범위**: Slice 7 종결까지의 모든 단계. manual eval 방법론 업그레이드 (A+C+D) + Slice 5/6/7 통합 평가 (38 entries) + 가설 6/6 정착 검증 + Slice 1·3·4 조건부 재검토 + Step 9 #19 처리 + 최종 종결 보고.
> **회귀 영향**: +5~10 예상 (rubric sample 회귀 + metadata 스크립트).
> **비용 예측**: ~$0.14 추가 → 누적 광의 $1.245 (임계 $1.50 마진 17%).
> **시간 예측**: 50~70분 (2 stage 적용 시 stage 1 끝나면 분기 판정 후 stage 2 또는 종결).
> **분기 사전 정의**: Slice 5/6 winner 유지 + 분포 폭 ≥ 3.0 → Slice 1·3·4 생략 (종결) / winner 변경 → Slice 1·3·4 별도 사이클 진입.

---

## §0. 사전 체크 (10초)

```bash
git status
git log --oneline -5
pytest -q  # 492 passed 확인

# Part 3 산출물 확인
ls docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json
ls docs/portfolio/coach/slice7/step8_2way_e4_conversation_scored.json

# 과거 슬라이스 raw 답변 확인 (Slice 5/6 재검토 입력)
ls docs/portfolio/coach/slice5/step8_2way_*_raw.json  # E3 preset 외삽
ls docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json

# 기존 평가 결과 확인 (winner 변경 판정 기준점)
ls docs/portfolio/coach/slice5/step9_3_scored.json  # 또는 동등 경로
ls docs/portfolio/coach/slice6/step9_3_scored.json  # 또는 동등 경로

# rubric + COST_POLICY 확인
cat docs/portfolio/coach/manual_eval_rubric.md | head -30
cat docs/portfolio/coach/COST_POLICY.md | head -20
```

- [ ] 492 passed
- [ ] Part 3 step8 raw + scored stub 존재
- [ ] Slice 5/6 step8 raw 존재 (재검토 입력)
- [ ] Slice 5/6 기존 scored.json 존재 (winner 변경 판정 reference)

---

## §1. DIMENSION_LOOKUP entry 추가 (Part 3 §J 권장 처리)

### 1.1 score_step8.py에 e4_conversation entry 추가

기존 DIMENSION_LOOKUP은 scoring config 전용. e4_conversation의 8 필드 등록:

```python
# scripts/.../score_step8.py (실제 경로는 Part 3 §J docs 참조)
DIMENSION_LOOKUP = {
    # ... 기존 entries (e1, e2, e3, e3_portfolio, e5, e6) ...
    "e4_conversation": {
        "dim1": "naturalness",        # 1번째 평가 축
        "dim2": "insight",            # 2번째 평가 축
        "weight": 0.5,                # 양축 균등 가중
        "additional_lex_check": "completeness_auto",  # schema completeness 자동
        "rationale_field": "evaluation_rationale",    # A 옵션 (rationale 입력)
        "reference_field": "rubric_sample_reference", # C 옵션 (sample 참조)
        "metadata_field": "auto_metadata",            # D 옵션 (자동 metadata)
        "tier_aware": True,                            # Tier별 보조 분석 활성화
    },
}
```

### 1.2 회귀 테스트

```python
# portfolio/tests/test_dimension_lookup.py (또는 동등 경로)
def test_e4_conversation_entry_present():
    from scripts.score_step8 import DIMENSION_LOOKUP  # 실제 경로 사용
    assert "e4_conversation" in DIMENSION_LOOKUP
    entry = DIMENSION_LOOKUP["e4_conversation"]
    assert entry["dim1"] == "naturalness"
    assert entry["dim2"] == "insight"
    assert entry["tier_aware"] is True
```

**기대**: +1~3건 회귀.

---

## §2. Rubric §B Sample 5건 영구 갱신 (#3=B 처리)

### 2.1 manual_eval_rubric.md §B에 5건 sample 추가

별첨 파일 `slice7_part4_rubric_samples.md`의 5건 sample을 `docs/portfolio/coach/manual_eval_rubric.md` §B 끝에 통합:

- Sample 1 (nat=1, ins=2) — 어색 + 기본만
- Sample 2 (nat=3, ins=1) — 무난 + 통찰 없음
- Sample 3 (nat=4, ins=3) — 자연 + 보통 통찰
- Sample 4 (nat=5, ins=4) — 자연 + 좋은 통찰
- Sample 5 (nat=5, ins=5) — 매우 자연 + 매우 통찰

### 2.2 sample 회귀 테스트 (별첨 파일 §회귀 테스트 참조)

`portfolio/tests/test_rubric_samples.py`:

- test_rubric_has_5_samples
- test_rubric_sample_score_spectrum
- test_rubric_sample_rationale_present

**기대**: +3건 회귀.

### 2.3 #25 close 검증

#25 manual eval rubric 표준화 부채는 Slice 7 Step 0에서 1차 처리됨. §B sample 추가로 완전 close.

---

## §3. Rationale 보조 호출 스크립트 (#1=A의 A 옵션, #2=C 처리)

### 3.1 스크립트 신설: `scripts/slice7/generate_rationale.py`

**대상**: Slice 5 (~12) + Slice 6 (10) + Slice 7 (28) = **약 50 entries** sonnet 호출.

> **추정 수정**: Slice 5 entries 정확 수는 Part 3에서 확인 안 됨. 실행 시 자동 카운트.

```python
"""
Slice 7 Part 4 §3: rationale 보조 호출.

각 entry (Slice 5/6/7의 LLM 답변)에 대해 sonnet이 비평가 관점에서
naturalness/insight rationale 200자씩 분석.

본 매트릭스(Part 3 28건)는 보존, rationale은 별도 자산.

비용 예측: ~$0.14 (50건 × sonnet rationale, output 짧음 ~$0.003/건)
"""

import json
from pathlib import Path
from portfolio.llm.client import LLMClient
from portfolio.llm.cost_guard import CostGuard

INPUT_PATHS = {
    "slice5": Path("docs/portfolio/coach/slice5/step8_2way_e3_raw.json"),
    "slice6": Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json"),
    "slice7": Path("docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"),
}
OUT_PATH = Path("docs/portfolio/coach/slice7/step9_1_rationales.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step9_1_rationales_report.md")

RATIONALE_SYSTEM = """당신은 한국어 portfolio 코멘트의 비평가입니다.
주어진 답변에 대해 객관적·비판적 관점에서 다음 두 축을 분석하세요:

1. naturalness (자연스러움): 한국어 표현이 자연스러운가? 어떤 표현이 어색하거나
   기계 번역체인가? 어떤 표현이 사람이 쓴 듯한 자연스러움을 보이는가?
2. insight (통찰력): 포트폴리오 지표를 의미 있게 해석했는가? preset 의도를
   반영했는가? 행동 시사점이 구체적인가?

**중요**: 자기 변호 X, 비판적 분석 O. 약점과 강점 모두 명시.
JSON으로 출력 (각 rationale 200자 이내):
{
  "naturalness_rationale": "...",
  "insight_rationale": "..."
}
"""


def build_rationale_prompt(entry: dict) -> str:
    answer = entry.get("commentary") or entry.get("raw_content") or entry.get("answer", "")
    preset = entry.get("preset_id", "unknown")
    return f"""
## Preset
{preset}

## 답변
{answer}

위 답변의 naturalness/insight를 비평적으로 분석하세요.
"""


def main():
    CostGuard.reset_for_slice("slice7_part4_rationale")
    client = LLMClient(provider="anthropic_sonnet")

    all_entries = []
    for slice_name, path in INPUT_PATHS.items():
        if not path.exists():
            print(f"⚠ {path} not found — skipping {slice_name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["entries"] if isinstance(data, dict) else data
        for e in entries:
            e["__source_slice"] = slice_name
            all_entries.append(e)

    print(f"총 entries: {len(all_entries)}")

    rationales = []
    total_cost = 0
    for i, entry in enumerate(all_entries, 1):
        prompt = build_rationale_prompt(entry)
        try:
            response = client.call(
                messages=[{"role": "user", "content": prompt}],
                system=RATIONALE_SYSTEM,
                max_tokens=500,
            )
        except Exception as e:
            rationales.append({"idx": i - 1, "error": str(e)})
            continue
        meta = response.metadata_dict()
        cost = meta.get("cost_usd", 0)
        total_cost += cost
        try:
            parsed = json.loads(response.content)
        except Exception:
            parsed = {"naturalness_rationale": "[parse error]", "insight_rationale": "[parse error]"}
        rationales.append({
            "idx": i - 1,
            "source_slice": entry["__source_slice"],
            "scenario_id": entry.get("scenario_id"),
            "preset_id": entry.get("preset_id"),
            "provider": entry.get("provider"),
            "naturalness_rationale": parsed.get("naturalness_rationale"),
            "insight_rationale": parsed.get("insight_rationale"),
            "rationale_cost_usd": cost,
        })
        if i % 10 == 0:
            print(f"  진행: {i}/{len(all_entries)}, 누적 cost: ${total_cost:.4f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rationales, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 4 §3 — Rationale 생성 보고\n",
        f"- 총 entries: {len(all_entries)}",
        f"- 성공: {sum(1 for r in rationales if 'naturalness_rationale' in r)}",
        f"- 실패: {sum(1 for r in rationales if 'error' in r)}",
        f"- 총 비용: ${total_cost:.5f}",
    ]
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"\n✓ rationales: {OUT_PATH}")
    print(f"  총 비용: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
```

### 3.2 실행

```bash
python scripts/slice7/generate_rationale.py
```

**기대**: ~50건 sonnet 호출, 비용 ~$0.14.

---

## §4. Metadata 자동 계산 (#1=A의 D 옵션)

### 4.1 스크립트: `scripts/slice7/calc_auto_metadata.py`

각 entry의 자동 metadata 계산:

- **metric_citation_accuracy**: referenced_metrics가 portfolio_metrics에 실제 존재하는 key인가? (I4 분기 사전 진단)
- **preset_intent_match**: 답변에 preset 관련 키워드가 포함되어 있는가? (간단한 키워드 매칭)
- **answer_length_zscore**: 답변 길이의 z-score (분포 내 위치)
- **referenced_metrics_count**: 인용 지표 수

```python
"""
Slice 7 Part 4 §4: 자동 metadata 계산.

평가자가 정량 신호로 cross-check할 수 있도록 metadata 계산.
"""

import json
import re
from pathlib import Path
from statistics import mean, stdev

INPUT_PATH = Path("docs/portfolio/coach/slice7/step9_1_rationales.json")
RAW_PATHS = {
    "slice5": Path("docs/portfolio/coach/slice5/step8_2way_e3_raw.json"),
    "slice6": Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json"),
    "slice7": Path("docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"),
}
OUT_PATH = Path("docs/portfolio/coach/slice7/step9_2_auto_metadata.json")


# preset 키워드 매핑 (간단한 1차 휴리스틱)
PRESET_KEYWORDS = {
    "garp": ["garp", "균형", "합리적 가격", "성장과 가치"],
    "buffett_quality_value": ["buffett", "가치", "고품질", "moat", "ROIC", "FCF"],
    "dividend_growth": ["배당", "dividend", "안정", "방어", "현금흐름"],
    "quality_factor": ["quality", "ROIC", "수익성", "안정 이익"],
    "concentrated_value": ["집중", "high conviction", "확신", "buffett"],
    "concentrated_portfolio": ["집중", "concentration"],
}


def count_preset_keywords(text: str, preset_id: str) -> int:
    """preset 키워드 매칭 카운트."""
    text_lower = text.lower()
    keywords = []
    for k, v in PRESET_KEYWORDS.items():
        if k in preset_id.lower():
            keywords = v
            break
    if not keywords:
        return 0
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def main():
    rationales = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    # raw 답변 다시 로드 (length z-score 계산용)
    all_raw = {}
    for slice_name, path in RAW_PATHS.items():
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["entries"] if isinstance(data, dict) else data
        for e in entries:
            scenario = e.get("scenario_id", "")
            provider = e.get("provider", "")
            key = (slice_name, scenario, provider)
            all_raw[key] = e

    # 답변 길이 분포
    lengths = []
    for r in rationales:
        key = (r["source_slice"], r.get("scenario_id"), r.get("provider"))
        raw = all_raw.get(key)
        if raw:
            answer = raw.get("commentary") or raw.get("raw_content") or raw.get("answer", "")
            lengths.append(len(answer))

    avg_len = mean(lengths) if lengths else 0
    std_len = stdev(lengths) if len(lengths) > 1 else 1

    # 각 entry metadata 계산
    metadatas = []
    for r in rationales:
        key = (r["source_slice"], r.get("scenario_id"), r.get("provider"))
        raw = all_raw.get(key, {})
        answer = raw.get("commentary") or raw.get("raw_content") or raw.get("answer", "")
        portfolio_metrics_keys = set(raw.get("portfolio_metrics", {}).keys()) if isinstance(raw.get("portfolio_metrics"), dict) else set()
        referenced = raw.get("referenced_metrics", [])

        # metric citation accuracy
        if referenced and portfolio_metrics_keys:
            valid = sum(1 for m in referenced if m in portfolio_metrics_keys)
            citation_accuracy = round(valid / len(referenced), 2)
        else:
            citation_accuracy = None  # 측정 불가

        # preset intent match
        preset_match = count_preset_keywords(answer, r.get("preset_id", ""))

        # length z-score
        z = round((len(answer) - avg_len) / std_len, 2) if std_len else 0

        metadatas.append({
            "idx": r["idx"],
            "source_slice": r["source_slice"],
            "scenario_id": r.get("scenario_id"),
            "preset_id": r.get("preset_id"),
            "provider": r.get("provider"),
            "metric_citation_accuracy": citation_accuracy,
            "preset_intent_keyword_count": preset_match,
            "answer_length": len(answer),
            "answer_length_zscore": z,
            "referenced_metrics_count": len(referenced),
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(metadatas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ auto metadata: {OUT_PATH}")
    print(f"  분포: avg_length={avg_len:.0f}, std_length={std_len:.0f}")


if __name__ == "__main__":
    main()
```

### 4.2 실행

```bash
python scripts/slice7/calc_auto_metadata.py
```

**기대**: 회귀 영향 0, 비용 0.

---

## §5. Reference Example 페어 준비 (#1=A의 C 옵션)

### 5.1 reference example 추출

rubric §B sample 5건이 이미 만들어진 견본. 각 평가 entry 옆에 sample 5건 압축 버전(50자 단위) 표시.

`scripts/slice7/prepare_reference_pairs.py`:

```python
"""
Slice 7 Part 4 §5: reference example 페어 준비.

rubric §B sample 5건을 압축 인덱스로 변환 → manual eval form에 매 entry당 첨부.
"""

import json
from pathlib import Path

OUT_PATH = Path("docs/portfolio/coach/slice7/step9_3_reference_pairs.json")

REFERENCES = {
    "sample_1": {
        "score": "nat=1, ins=2",
        "summary": "어색한 한국어 + 기본 해석만 (3건 이상 기계 번역체)",
        "key_signal": "'당신의 포트폴리오 0.45 보입니다' 같은 어순 깨짐",
    },
    "sample_2": {
        "score": "nat=3, ins=1",
        "summary": "무난한 한국어 + 통찰 0 (지표 나열만)",
        "key_signal": "사용자 질문에 답하지 않음, preset 의도 반영 X",
    },
    "sample_3": {
        "score": "nat=4, ins=3",
        "summary": "자연스러움 + 보통 통찰 (기본 해석 + preset 부분 반영)",
        "key_signal": "행동 시사점 막연 ('분산 고려' 정도)",
    },
    "sample_4": {
        "score": "nat=5, ins=4",
        "summary": "사람이 쓴 듯 + 좋은 통찰 (구체 행동 시사점 2건)",
        "key_signal": "위험/기회 양면 분석 부족",
    },
    "sample_5": {
        "score": "nat=5, ins=5",
        "summary": "정교한 흐름 + 매우 통찰 (위험·기회 양면 + 구체 전술 3건+)",
        "key_signal": "분기별 5% 조정 같은 실행 전술까지",
    },
}


def main():
    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_PATH).write_text(json.dumps(REFERENCES, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ references: {OUT_PATH}")


if __name__ == "__main__":
    main()
```

---

## §6. 통합 Manual Eval Form 생성 (38 entries, blind)

### 6.1 스크립트: `scripts/slice7/prepare_manual_eval_v7.py`

````python
"""
Slice 7 Part 4 §6: 통합 manual eval form 생성.

Slice 5 + Slice 6 + Slice 7 entries → blind 평가 양식.
각 entry에 rationale + reference + metadata 첨부.

seed=42 randomize 재현 가능. provider/preset blind, source_slice는 가림.
"""

import json
import random
from pathlib import Path

RATIONALES_PATH = Path("docs/portfolio/coach/slice7/step9_1_rationales.json")
METADATA_PATH = Path("docs/portfolio/coach/slice7/step9_2_auto_metadata.json")
REFERENCES_PATH = Path("docs/portfolio/coach/slice7/step9_3_reference_pairs.json")
RAW_PATHS = {
    "slice5": Path("docs/portfolio/coach/slice5/step8_2way_e3_raw.json"),
    "slice6": Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json"),
    "slice7": Path("docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"),
}
OUT_FORM = Path("docs/portfolio/coach/slice7/step9_4_eval_form_v7.md")
OUT_KEY = Path("docs/portfolio/coach/slice7/step9_4_eval_key_v7.json")


def main():
    rationales = {f"{r['source_slice']}_{r['idx']}": r for r in json.loads(RATIONALES_PATH.read_text(encoding="utf-8"))}
    metadatas = {f"{m['source_slice']}_{m['idx']}": m for m in json.loads(METADATA_PATH.read_text(encoding="utf-8"))}
    references = json.loads(REFERENCES_PATH.read_text(encoding="utf-8"))

    all_entries = []
    for slice_name, path in RAW_PATHS.items():
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["entries"] if isinstance(data, dict) else data
        for i, e in enumerate(entries):
            answer = e.get("commentary") or e.get("raw_content") or e.get("answer", "")
            r_key = f"{slice_name}_{i}"
            all_entries.append({
                "source_slice": slice_name,
                "idx": i,
                "preset_id": e.get("preset_id"),
                "tier": e.get("tier"),
                "provider": e.get("provider"),
                "answer": answer,
                "rationale": rationales.get(r_key, {}),
                "metadata": metadatas.get(r_key, {}),
            })

    # seed=42 randomize
    random.Random(42).shuffle(all_entries)

    # 2 stage: provider별 분리 (stage 1 = haiku only)
    haiku_entries = [e for e in all_entries if "haiku" in (e["provider"] or "")]
    sonnet_entries = [e for e in all_entries if "sonnet" in (e["provider"] or "")]

    # blind key
    key_map = {"haiku_stage1": [], "sonnet_stage2": []}
    for i, e in enumerate(haiku_entries, 1):
        key_map["haiku_stage1"].append({"eval_id": i, "source_slice": e["source_slice"], "idx": e["idx"], "provider": e["provider"], "preset_id": e["preset_id"], "tier": e["tier"]})
    for i, e in enumerate(sonnet_entries, 1):
        key_map["sonnet_stage2"].append({"eval_id": i, "source_slice": e["source_slice"], "idx": e["idx"], "provider": e["provider"], "preset_id": e["preset_id"], "tier": e["tier"]})

    # form 생성
    lines = [
        "# Slice 7 Part 4 Manual Eval Form (v7)\n",
        "> **방법론 업그레이드 (#1=A의 A+C+D)**: rationale + reference + metadata 제공",
        "> **2 stage**: Stage 1 = haiku (이 문서) / Stage 2 = sonnet (조건부, 별도 문서)",
        "> **분포 폭 KPI**: rubric §C.6 자동 게이트 (≥ 3.0 필수)",
        "> **참조**: rubric §B sample 5건 (평가 전 반드시 검토)\n",
        "## Reference Examples (rubric §B 압축)\n",
    ]
    for name, ref in references.items():
        lines.append(f"- **{name}** ({ref['score']}): {ref['summary']} — 신호: {ref['key_signal']}")
    lines.append("\n---\n")

    # Stage 1 haiku
    lines.append("# Stage 1 — haiku 평가 (먼저 진행)\n")
    for i, e in enumerate(haiku_entries, 1):
        lines.append(f"## Eval #{i} (preset={e['preset_id']}, tier={e['tier']})")
        lines.append(f"\n**답변**:\n```\n{e['answer']}\n```")
        if e["rationale"]:
            r = e["rationale"]
            lines.append(f"\n**Rationale (sonnet 비평)**:")
            lines.append(f"- naturalness: {r.get('naturalness_rationale', '—')}")
            lines.append(f"- insight: {r.get('insight_rationale', '—')}")
        if e["metadata"]:
            m = e["metadata"]
            lines.append(f"\n**Auto Metadata**:")
            lines.append(f"- metric_citation_accuracy: {m.get('metric_citation_accuracy', '—')}")
            lines.append(f"- preset_intent_keyword_count: {m.get('preset_intent_keyword_count', '—')}")
            lines.append(f"- answer_length: {m.get('answer_length', '—')} (z={m.get('answer_length_zscore', '—')})")
            lines.append(f"- referenced_metrics_count: {m.get('referenced_metrics_count', '—')}")
        lines.append(f"\n- naturalness: [ ? ] / 5")
        lines.append(f"- insight: [ ? ] / 5")
        lines.append(f"- note (선택): \n")
        lines.append("---\n")

    OUT_FORM.write_text("\n".join(lines), encoding="utf-8")
    OUT_KEY.write_text(json.dumps(key_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ eval form: {OUT_FORM}")
    print(f"✓ eval key: {OUT_KEY}")
    print(f"  Stage 1 (haiku): {len(haiku_entries)} entries")
    print(f"  Stage 2 (sonnet): {len(sonnet_entries)} entries (조건부)")


if __name__ == "__main__":
    main()
````

### 6.2 실행

```bash
python scripts/slice7/prepare_manual_eval_v7.py
```

---

## §7. Step 9.2 Stage 1 — 병진 haiku 평가 (사람 작업)

### 7.1 평가 절차

1. `docs/portfolio/coach/manual_eval_rubric.md` §B sample 5건 검토 (~5분)
2. `docs/portfolio/coach/slice7/step9_4_eval_form_v7.md` 열기
3. Stage 1 = haiku 19~24 entries 평가 (실제 수는 카운트)
4. 각 entry에서:
   - 답변 본문 읽기 (~1분)
   - rationale 검토 (sonnet의 비평) (~30초)
   - metadata 정량 신호 확인 (~10초)
   - reference sample과 비교하여 점수 결정
   - note 작성 (자유)
5. 평가 완료 후 `step9_5_eval_filled_v7.md`로 저장

### 7.2 예상 소요

- entry당 ~2~3분
- haiku 19~24 entries × 2분 = **40~50분**

### 7.3 평가 가이드 (분포 폭 ≥ 3.0 권장)

- "이 entry가 sample 1과 비슷한가? 5와 비슷한가? 3과 비슷한가?"
- 망설이면 rationale의 강점/약점을 다시 읽기
- metadata가 정량 신호 보강 (예: citation_accuracy 0.5면 hallucination 의심)
- **1점·5점 적극 사용** (안전 평가 회피)

---

## §8. Step 9.3 — Stage 1 자동 판정 + Stage 2 진행 여부

### 8.1 스크립트: `scripts/slice7/score_stage1.py`

```python
"""
Slice 7 Part 4 §8: Stage 1 자동 판정.

Stage 1 (haiku) 평가 결과로:
1. winner 신호 (haiku 단독 평가지만 기존 sonnet 데이터와 efficiency 비교 가능)
2. 분포 폭 KPI (rubric §C.6, ≥ 3.0 필수)
3. Stage 2 (sonnet) 진행 여부 자동 판정

판정 기준:
- haiku label_mean ≥ 3.5 (Slice 6 수준 이상) + 분포 폭 ≥ 3.0
  → Stage 2 생략 가능 (haiku winner 명확)
- haiku label_mean < 3.0
  → Stage 2 진행 (sonnet 위닝 가능성 검증)
- 3.0 ~ 3.5 또는 분포 폭 < 3.0
  → Stage 2 진행 (안전 확보)
"""

import json
import re
from pathlib import Path
from portfolio.llm.eval_metrics import distribution_width_kpi

FILLED_PATH = Path("docs/portfolio/coach/slice7/step9_5_eval_filled_v7.md")
KEY_PATH = Path("docs/portfolio/coach/slice7/step9_4_eval_key_v7.json")
RAW_PATHS = {
    "slice5": Path("docs/portfolio/coach/slice5/step8_2way_e3_raw.json"),
    "slice6": Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json"),
    "slice7": Path("docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"),
}
OUT_PATH = Path("docs/portfolio/coach/slice7/step9_6_stage1_verdict.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step9_6_stage1_report.md")

EVAL_BLOCK = re.compile(
    r"##\s*Eval\s*#(\d+).*?naturalness:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?.*?insight:\s*\[?\s*(\d+(?:\.\d+)?)\s*\]?",
    re.DOTALL,
)


def parse_filled(text: str) -> dict:
    results = {}
    for match in EVAL_BLOCK.finditer(text):
        eid = int(match.group(1))
        nat = float(match.group(2))
        ins = float(match.group(3))
        results[eid] = {"naturalness": nat, "insight": ins}
    return results


def load_costs():
    """raw 데이터에서 cost_usd 추출."""
    costs = {}  # (source_slice, idx) → cost
    for slice_name, path in RAW_PATHS.items():
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["entries"] if isinstance(data, dict) else data
        for i, e in enumerate(entries):
            costs[(slice_name, i)] = e.get("cost_usd", 0)
    return costs


def main():
    parsed = parse_filled(FILLED_PATH.read_text(encoding="utf-8"))
    key_map = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    costs = load_costs()
    haiku_keys = key_map["haiku_stage1"]

    # eval_id → original metadata 매핑
    haiku_results = []
    all_scores = []
    for eid, scores in parsed.items():
        meta = next((k for k in haiku_keys if k["eval_id"] == eid), None)
        if not meta:
            continue
        cost = costs.get((meta["source_slice"], meta["idx"]), 0)
        label_mean = (scores["naturalness"] + scores["insight"]) / 2
        efficiency = label_mean / cost if cost > 0 else 0
        haiku_results.append({
            "eval_id": eid,
            "source_slice": meta["source_slice"],
            "preset_id": meta["preset_id"],
            "tier": meta["tier"],
            "provider": meta["provider"],
            "naturalness": scores["naturalness"],
            "insight": scores["insight"],
            "label_mean": label_mean,
            "cost_usd": cost,
            "efficiency": efficiency,
        })
        all_scores.extend([scores["naturalness"], scores["insight"]])

    # 분포 폭 KPI
    kpi = distribution_width_kpi(all_scores)

    # haiku label_mean 집계
    label_means = [r["label_mean"] for r in haiku_results]
    avg_label = sum(label_means) / len(label_means) if label_means else 0

    # Slice별 winner 신호
    by_slice = {}
    for r in haiku_results:
        by_slice.setdefault(r["source_slice"], []).append(r["label_mean"])
    slice_avg = {s: sum(v) / len(v) for s, v in by_slice.items()}

    # Stage 2 진행 판정
    if avg_label >= 3.5 and kpi["width"] >= 3:
        stage2_decision = "skip"
        stage2_reason = f"haiku label_mean {avg_label:.2f} ≥ 3.5 + 분포 폭 {kpi['width']} ≥ 3"
    elif avg_label < 3.0:
        stage2_decision = "proceed"
        stage2_reason = f"haiku label_mean {avg_label:.2f} < 3.0 → sonnet 위닝 가능성 검증"
    else:
        stage2_decision = "proceed"
        stage2_reason = f"haiku label_mean {avg_label:.2f} 또는 분포 폭 {kpi['width']} 애매 → 안전 확보"

    verdict = {
        "haiku_results": haiku_results,
        "avg_label_mean": round(avg_label, 4),
        "slice_avg_label_mean": {s: round(v, 4) for s, v in slice_avg.items()},
        "distribution_kpi": kpi,
        "stage2_decision": stage2_decision,
        "stage2_reason": stage2_reason,
        "rubric_c6_pass": kpi["pass"],
        "rubric_26_close_eligible": kpi["pass"],
    }
    OUT_PATH.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 4 Stage 1 Verdict\n",
        f"## 집계",
        f"- haiku entries: {len(haiku_results)}",
        f"- avg label_mean: {avg_label:.4f}",
        f"- 분포 폭 (max-min): {kpi['width']}",
        f"- 5점 비율: {kpi['five_ratio']}",
        f"- 1점 사용: {kpi['one_count']}건",
        f"- rubric §C.6 PASS: {kpi['pass']}",
        "",
        f"## Slice별 haiku label_mean",
    ]
    for s, avg in slice_avg.items():
        md.append(f"- {s}: {avg:.4f}")
    md.extend([
        "",
        f"## Stage 2 판정",
        f"- **decision: {stage2_decision}**",
        f"- 사유: {stage2_reason}",
        "",
        f"## #26 자연 close 가능 여부",
        f"- 분포 폭 KPI PASS: {kpi['pass']}",
        f"- 자연 close 적격: {verdict['rubric_26_close_eligible']}",
    ])
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ verdict: {OUT_PATH}")
    print(f"  Stage 2 decision: {stage2_decision}")


if __name__ == "__main__":
    main()
```

### 8.2 실행

```bash
python scripts/slice7/score_stage1.py
```

### 8.3 분기

- **stage2_decision = "skip"**: §9 건너뛰고 §10으로
- **stage2_decision = "proceed"**: §9 진행

---

## §9. Step 9.4 (조건부) — sonnet 평가

### 9.1 sonnet eval form 생성

`scripts/slice7/prepare_stage2_form.py` — Stage 1과 동일 로직, sonnet entries만.

### 9.2 병진 sonnet 평가

- entries 19~24건 × 2분 = ~40~50분
- `step9_7_sonnet_filled_v7.md`로 저장

---

## §10. Step 9.5 — 통합 Winner + Slice 5/6 재판정 + Slice 7 Winner

### 10.1 스크립트: `scripts/slice7/score_final.py`

```python
"""
Slice 7 Part 4 §10: 통합 efficiency winner + Slice별 재판정.

Stage 1 + Stage 2 (있다면) 데이터로:
1. 통합 efficiency winner (Slice 1·3·4·5·6 패턴 일관)
2. Slice 5 재판정 vs 기존 결과 비교
3. Slice 6 재판정 vs 기존 결과 비교
4. Slice 7 winner 확정
5. Tier별 보조 분석
6. 글쓰기 가설 5/5 vs 6/6 판정
7. Slice 1·3·4 진행 여부 자동 결정
"""

import json
from pathlib import Path

STAGE1_PATH = Path("docs/portfolio/coach/slice7/step9_6_stage1_verdict.json")
STAGE2_PATH = Path("docs/portfolio/coach/slice7/step9_8_stage2_verdict.json")  # 조건부
EXISTING_RESULTS = {
    "slice5": Path("docs/portfolio/coach/slice5/step9_3_scored.json"),
    "slice6": Path("docs/portfolio/coach/slice6/step9_3_scored.json"),
}
OUT_PATH = Path("docs/portfolio/coach/slice7/step9_9_final_verdict.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step9_9_final_report.md")


def determine_winner_by_slice(entries):
    """Slice별 + provider별 efficiency 집계."""
    by_slice_provider = {}
    for e in entries:
        key = (e["source_slice"], e["provider"])
        by_slice_provider.setdefault(key, []).append(e)
    result = {}
    for (slice_name, provider), es in by_slice_provider.items():
        label_means = [x["label_mean"] for x in es]
        costs = [x["cost_usd"] for x in es]
        avg_label = sum(label_means) / len(label_means) if label_means else 0
        avg_cost = sum(costs) / len(costs) if costs else 0
        efficiency = avg_label / avg_cost if avg_cost else 0
        result.setdefault(slice_name, {})[provider] = {
            "n": len(es),
            "avg_label_mean": round(avg_label, 4),
            "avg_cost": round(avg_cost, 6),
            "efficiency": round(efficiency, 2),
        }
    return result


def main():
    stage1 = json.loads(STAGE1_PATH.read_text(encoding="utf-8"))
    haiku_entries = stage1["haiku_results"]

    sonnet_entries = []
    stage2_present = STAGE2_PATH.exists()
    if stage2_present:
        stage2 = json.loads(STAGE2_PATH.read_text(encoding="utf-8"))
        sonnet_entries = stage2.get("sonnet_results", [])

    all_entries = haiku_entries + sonnet_entries
    slice_winners = determine_winner_by_slice(all_entries)

    # winner 판정
    winners_by_slice = {}
    for slice_name, providers in slice_winners.items():
        if "anthropic_haiku" in providers and "anthropic_sonnet" in providers:
            h_eff = providers["anthropic_haiku"]["efficiency"]
            s_eff = providers["anthropic_sonnet"]["efficiency"]
            winner = "haiku" if h_eff > s_eff else "sonnet"
            gap_pct = round((h_eff - s_eff) / s_eff * 100, 2) if s_eff else None
            winners_by_slice[slice_name] = {
                "winner": winner,
                "haiku_efficiency": h_eff,
                "sonnet_efficiency": s_eff,
                "efficiency_gap_pct": gap_pct,
            }
        else:
            winners_by_slice[slice_name] = {
                "winner": "stage1_only_haiku",
                "haiku_efficiency": providers.get("anthropic_haiku", {}).get("efficiency", 0),
            }

    # 기존 winner와 비교 (Slice 5/6)
    winner_changes = {}
    for slice_name, existing_path in EXISTING_RESULTS.items():
        if not existing_path.exists():
            continue
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        old_winner = existing.get("winner", "unknown")
        new_winner = winners_by_slice.get(slice_name, {}).get("winner", "unknown")
        winner_changes[slice_name] = {
            "old": old_winner,
            "new": new_winner,
            "changed": old_winner != new_winner,
        }

    # 글쓰기 가설 판정
    # 가설: S1·S3·S4·S5·S6·S7 모두 winner=haiku → 6/6
    s7_winner = winners_by_slice.get("slice7", {}).get("winner", "unknown")
    s5_winner = winners_by_slice.get("slice5", {}).get("winner", "unknown")
    s6_winner = winners_by_slice.get("slice6", {}).get("winner", "unknown")

    # 가설 정착 확인 (slice7 + 재검토된 slice5, 6 기준)
    haiku_count = sum(1 for w in [s5_winner, s6_winner, s7_winner] if w == "haiku")
    if haiku_count == 3:
        hypothesis_status = "6_of_6_pending_slice1_3_4_verification"
        slice134_proceed = False  # 재검토 생략 가능
    elif haiku_count < 3:
        hypothesis_status = "broken_winner_changed"
        slice134_proceed = True  # Slice 1·3·4 재검토 필수
    else:
        hypothesis_status = "indeterminate"
        slice134_proceed = True

    # Tier별 보조 분석 (Slice 7 전용)
    tier_analysis = {}
    s7_entries = [e for e in all_entries if e["source_slice"] == "slice7"]
    for tier in [1, 2, 3]:
        t_entries = [e for e in s7_entries if e["tier"] == tier]
        if not t_entries:
            continue
        haiku_t = [e for e in t_entries if e["provider"] == "anthropic_haiku"]
        sonnet_t = [e for e in t_entries if e["provider"] == "anthropic_sonnet"]
        tier_analysis[f"tier_{tier}"] = {
            "haiku_n": len(haiku_t),
            "haiku_avg_label": round(sum(e["label_mean"] for e in haiku_t) / len(haiku_t), 4) if haiku_t else None,
            "sonnet_n": len(sonnet_t),
            "sonnet_avg_label": round(sum(e["label_mean"] for e in sonnet_t) / len(sonnet_t), 4) if sonnet_t else None,
            "n_total": len(t_entries),
            "weak_signal_warning": len(t_entries) < 6,  # Tier 3 N=2 weak signal
        }

    final = {
        "stage2_executed": stage2_present,
        "winners_by_slice": winners_by_slice,
        "winner_changes": winner_changes,
        "hypothesis_status": hypothesis_status,
        "slice134_recheck_proceed": slice134_proceed,
        "tier_analysis_slice7": tier_analysis,
        "rubric_c6_distribution_pass": stage1["distribution_kpi"]["pass"],
        "rubric_26_close_action": "close" if stage1["distribution_kpi"]["pass"] else "keep_open",
    }
    OUT_PATH.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 4 Final Verdict\n",
        f"## 통합 Winner",
    ]
    for slice_name, w in winners_by_slice.items():
        md.append(f"- {slice_name}: **{w['winner']}** (haiku eff {w.get('haiku_efficiency', '—')} / sonnet eff {w.get('sonnet_efficiency', '—')}, gap {w.get('efficiency_gap_pct', '—')}%)")

    md.append("\n## Slice 5/6 Winner 변경 분석")
    for slice_name, change in winner_changes.items():
        marker = "⚠ 변경" if change["changed"] else "✓ 유지"
        md.append(f"- {slice_name}: {change['old']} → {change['new']} {marker}")

    md.append("\n## 글쓰기 가설")
    md.append(f"- 상태: **{hypothesis_status}**")
    md.append(f"- Slice 1·3·4 재검토 진행: **{slice134_proceed}**")

    md.append("\n## Tier별 분석 (Slice 7)")
    for tier, t in tier_analysis.items():
        warn = " ⚠ weak signal" if t["weak_signal_warning"] else ""
        md.append(f"- {tier} (n={t['n_total']}{warn}): haiku label {t.get('haiku_avg_label')} / sonnet label {t.get('sonnet_avg_label')}")

    md.append(f"\n## #26 자연 close")
    md.append(f"- 분포 폭 KPI PASS: {stage1['distribution_kpi']['pass']}")
    md.append(f"- #26 action: **{final['rubric_26_close_action']}**")

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ final verdict: {OUT_PATH}")
    print(f"  hypothesis: {hypothesis_status}")
    print(f"  Slice 1·3·4 proceed: {slice134_proceed}")


if __name__ == "__main__":
    main()
```

### 10.2 실행

```bash
python scripts/slice7/score_final.py
```

---

## §11. Step 9.6 — 글쓰기 가설 6/6 + #26 close + Slice 1·3·4 분기 처리

### 11.1 자동 분기 (§10의 verdict 기반)

- **hypothesis_status = "6_of_6_pending_slice1_3_4_verification" + slice134_proceed = False**: Slice 1·3·4 재검토 생략, Slice 7 종결 진행
- **hypothesis_status = "broken_winner_changed" + slice134_proceed = True**: Slice 1·3·4 재검토 별도 사이클 진입 (Slice 8 진입 전)
- **hypothesis_status = "indeterminate"**: 측정 도구 문제 의심, rubric §B sample 추가 보완 후 재시도

### 11.2 #26 close 처리

- **rubric_c6_distribution_pass = True**: #26 close, 메모리에 명시
- **False**: #26 keep_open, Slice 8 Step 0 후보 진입

### 11.3 분기 처리 메모리 갱신

- Slice 5/6 winner 변경 사실 (있다면)
- 가설 status
- Slice 1·3·4 재검토 진행 결정

---

## §12. Step 10 — #19 LLMClient System 인자 처리

### 12.1 #19 구현

Slice 7 Step 9 슬롯 확정 사항. `portfolio/llm/client.py`의 `LLMClient.call()`에 `system` 인자 분리:

```python
# 기존: user message에 system 포함 (Slice 7 Part 3 prompt builder 패턴)
# 신규: system 별도 인자 → API에 별도 전달

class LLMClient:
    def call(self, messages: list[dict], system: str = None, max_tokens: int = 1000):
        # Anthropic API의 system 인자 활용
        kwargs = {"messages": messages, "max_tokens": max_tokens}
        if system:
            kwargs["system"] = system
        # ... 기존 호출 로직
```

### 12.2 prompt builder 갱신

`portfolio/prompts/e4/builder.py`의 `build_e4_messages()`에서 system은 user message에 포함 안 함 (이미 system 별도 반환).

### 12.3 회귀 테스트

- 기존 e1~e3, e5, e6도 영향 없음 검증 (system 인자 optional)
- e4 호출 시 system이 정확히 분리되어 전달되는지 검증
- IDENTICAL hash 유지 확인 (Slice 1 e1 + Slice 3 e2)

**기대**: +3~5건 회귀.

---

## §13. Step 11 — Slice 7 최종 종결 보고

### 13.1 종결 보고서 작성

`docs/portfolio/coach/slice7/slice7_final_report.md`:

```markdown
# Slice 7 (E4 대화 Q&A) 최종 종결 보고

## KPI 종합

- 회귀: 484 → ??? (Part 4 종결 후)
- 누적 광의 비용: $???
- 호출 카운트: ?/50
- KPI: 자동 + manual 통합

## Winner & 가설

- winner (Slice 7): ???
- efficiency gap: ???%
- 글쓰기 가설: 5/5 / 6/6 / broken

## Slice 5/6 재검토 결과

- Slice 5 winner: 유지 / 변경
- Slice 6 winner: 유지 / 변경

## Slice 1·3·4 처리

- 재검토 진행 여부: YES / NO
- 사유

## #β2 처리 (Slice 8 Step 0 진입)

- estimator systematic bias 확정 (-50%)
- Slice 8 Step 0 작업

## #19 처리 (Step 9 슬롯)

- LLMClient system 인자 분리 완료
- 회귀 +? 건

## #26 처리

- 분포 폭 KPI PASS / FAIL
- close / keep_open

## Slice 8 진입점 후보

1. #β2 estimator 재설계 (PS 2.5)
2. #24 preset 외삽 일반화 (PS 2.5, H3 confirmed)
3. B (sonnet judge) 도입 (PS 1.5)
4. Slice 1·3·4 재검토 (조건부)
5. L4 임계 강화 (PS 0.5)
```

---

## §14. 분기 시나리오 (Part 4 안에서)

| 시나리오 | 트리거                                     | 조치                                                 |
| -------- | ------------------------------------------ | ---------------------------------------------------- |
| **M1**   | Slice 5/6 winner 모두 유지 + 분포 폭 ≥ 3.0 | Slice 1·3·4 생략, Slice 7 종결 가능. 가설 6/6 PASS   |
| **M2**   | Slice 5 또는 Slice 6 winner 변경           | Slice 1·3·4 재검토 필수, Slice 8 진입 전 별도 사이클 |
| **M3**   | 분포 폭 < 3.0                              | rubric §B sample 보완 (5건 → 10건) + 재시도          |
| **M4**   | Stage 1 결과 애매 (3.0 ~ 3.5)              | Stage 2 진행                                         |
| **M5**   | Stage 2 결과 sonnet 우세                   | 가설 깨짐, primary LLM 정책 재검토                   |
| **M6**   | metric_citation_accuracy < 0.7 다수        | I4 분기 다수 발동, hallucination 부채 등록           |
| **M7**   | Tier 3 N=2 weak signal 그대로              | Slice 8 mock fixture 확장 부채 등록                  |
| **M8**   | #19 회귀 깨짐 (IDENTICAL hash 영향)        | 즉시 보고 + Part 4 보류                              |

---

## §15. 회귀 영향 KPI

| 단계                      | 회귀 영향 | 비용   |
| ------------------------- | --------- | ------ |
| §1 DIMENSION_LOOKUP entry | +1~3      | $0     |
| §2 rubric sample 회귀     | +3        | $0     |
| §3 rationale 호출         | 0         | ~$0.14 |
| §4 metadata               | 0         | $0     |
| §5 reference              | 0         | $0     |
| §6 manual eval form       | 0         | $0     |
| §7~§9 평가 + 판정         | 0         | $0     |
| §10 winner 판정           | 0         | $0     |
| §11 분기 처리             | 0         | $0     |
| §12 #19 LLMClient         | +3~5      | $0     |
| §13 종결 보고             | 0         | $0     |

**총 회귀 추가**: +7~11건 (492 → 499~503)
**총 비용 추가**: ~$0.14
**누적 광의 예상**: $1.105 + $0.14 = **$1.245** (임계 $1.50 마진 17%)

---

## §16. 완료 보고 양식

```
[Slice 7 Part 4 완료 보고]

== §1 DIMENSION_LOOKUP entry ==
- e4_conversation entry 추가: ✓
- 회귀 +?

== §2 Rubric §B Sample ==
- 5건 영구 추가: ✓
- 회귀 +3
- #25 close: ✓

== §3 Rationale 보조 호출 ==
- 총 entries: ?
- 성공: ?/?
- 비용: $?

== §4 Auto Metadata ==
- 계산 완료: ?건
- citation accuracy 분포: ?

== §5 Reference Pairs ==
- sample 5건 압축 인덱스: ✓

== §6 통합 eval form ==
- 38 entries (또는 실제 수) 생성: ✓
- 2 stage 분리: haiku ? / sonnet ?

== §7 Stage 1 (haiku 평가) ==
- 사용자 평가 완료: ✓
- 분포 폭: ?
- KPI §C.6 PASS: ?

== §8 Stage 2 진행 판정 ==
- decision: skip / proceed
- 사유

== §9 Stage 2 (sonnet 평가, 조건부) ==
- 진행: YES/NO
- 결과

== §10 통합 winner ==
- Slice 5: ?
- Slice 6: ?
- Slice 7: ?
- winner 변경: 있음/없음

== §11 가설 + #26 ==
- 글쓰기 가설: 6/6 PASS / broken / indeterminate
- #26 close: ✓/✗
- Slice 1·3·4 재검토 진행: YES/NO

== §12 #19 LLMClient ==
- system 인자 분리: ✓
- 회귀 +?
- IDENTICAL hash 유지: ✓

== §13 종결 보고 ==
- slice7_final_report.md 작성: ✓

== 종합 ==
- 회귀: 492 → ? (목표 499~503)
- 누적 광의: $? (예상 $1.245)
- 분기 발동: M? 목록
- Slice 8 진입점 후보: ?

§I 산출물 (~15건)
§II 분기 발동 결과
§III Slice 8 진입 준비
§IV Commit 메시지 권장
§V 핵심 결과
```

---

## §17. Commit 메시지 권장

```
feat(slice7/part4/§1): DIMENSION_LOOKUP e4_conversation entry
docs(slice7/part4/§2): rubric §B sample 5건 영구 추가 (#25 close)
test(slice7/part4/§2): rubric sample 회귀 +3
feat(slice7/part4/§3): rationale 보조 호출 (sonnet 50건)
feat(slice7/part4/§4): auto metadata 자동 계산
feat(slice7/part4/§5): reference example pairs
feat(slice7/part4/§6): 통합 manual eval form (38 entries blind)
docs(slice7/part4/§8): Stage 1 verdict + Stage 2 판정
docs(slice7/part4/§10): 통합 winner + Slice 5/6 재판정
docs(slice7/part4/§11): 가설 ?/6 + #26 close + Slice 1·3·4 분기
feat(slice7/part4/§12): #19 LLMClient system 인자 분리
test(slice7/part4/§12): #19 회귀 +?
docs(slice7/part4/§13): Slice 7 최종 종결 보고
```

---

## §18. Slice 8 진입 사전 등록

Slice 7 종결 후 Slice 8 진입점 후보 (확정 순서):

1. **#β2 estimator 재설계** (Step 0 진입 확정, PS 2.5)
2. **#24 preset 외삽 일반화** (H3 confirmed, PS 2.5) — Slice 7 Part 4 결과에 따라 우선순위 변동
3. **Slice 1·3·4 재검토** (M2 분기 발동 시, 별도 사이클)
4. **B (sonnet judge) 도입** (Slice 7에서 효과 검증, Slice 8 후보, PS 1.5)
5. **L4 임계 강화** (50% → 30%, PS 0.5)

---

## §19. Part 4 종결 KPI

- [ ] DIMENSION_LOOKUP entry 추가
- [ ] rubric §B sample 영구 갱신 + #25 close
- [ ] rationale 50건 생성
- [ ] auto metadata 계산
- [ ] reference pairs 준비
- [ ] 통합 eval form 생성
- [ ] Stage 1 평가 + 판정 완료
- [ ] (조건부) Stage 2 평가 + 판정 완료
- [ ] Slice 5/6 winner 재판정
- [ ] 글쓰기 가설 status 확정
- [ ] #26 처리 결정
- [ ] Slice 1·3·4 진행 여부 결정
- [ ] #19 LLMClient system 인자 처리
- [ ] Slice 7 최종 종결 보고
- [ ] 회귀 +7~11건 (목표 499~503)
- [ ] 누적 광의 $1.245 (임계 마진 17%)
- [ ] commit 13~15건 완료
