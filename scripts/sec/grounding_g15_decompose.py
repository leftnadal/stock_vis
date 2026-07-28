#!/usr/bin/env python3
"""SEC β G1.5 — not_found 437 분해 (read-only, 결정론, LLM 0콜, 쓰기 0).

STEP 0 확정:
- evidence에 섹션 메타 없음 → 행별 추측 귀속 금지.
- Track A 추출기(`normalize_section_all`)는 item_1 + item_7만 `_clean_text` 후 LLM 투입
  (item_1a 제외). 따라서 인용 출처 = 저장 섹션(1/7) 내부 = missing_source_section 0(결정론).
- G1 grounding source = raw item_1+1a+7(엔티티 포함). LLM 실입력 basis = _clean_text(1+7).
  → not_found 유력 동인 = normalizer 갭(엔티티/공백). 본 스크립트가 이를 정량 분리.

분해:
① 중복 접기: 정규화 문장 키 클러스터 → 유니크 수·크기 분포(437 + 1,751 분모).
② 섹션 귀속: missing_source_section=0(구조적). raw-source vs LLM-basis-source 재접지 델타.
③ 잔여 층화 샘플 20건(육안 대조용).
"""
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

from services.sec_pipeline.grounding import ground_evidence, normalize  # noqa: E402
from services.sec_pipeline.normalizer import normalize_section_all  # noqa: E402


def raw_source(item_1, item_1a, item_7):
    return "\n".join(p for p in (item_1, item_1a, item_7) if p)


def llm_basis_source(item_1, item_1a, item_7):
    # 추출 당시 LLM이 실제로 본 텍스트 = normalize_section_all(item_1+item_7, _clean_text).
    return normalize_section_all(
        {"item_1": item_1, "item_1a": item_1a, "item_7": item_7}
    )


def main():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, item_1_text, item_1a_text, item_7_text FROM sec_raw_document_store"
        )
        raw = {}
        llm = {}
        for r in cur.fetchall():
            raw[r[0]] = raw_source(r[1], r[2], r[3])
            llm[r[0]] = llm_basis_source(r[1], r[2], r[3])
        cur.execute(
            "SELECT id, evidence_text, source_document_id FROM sec_supply_chain_evidence"
        )
        rows = cur.fetchall()

    n_total = len(rows)
    # 두 소스 기준 판정
    stat_raw = Counter()
    stat_llm = Counter()
    nf_raw_rows = []   # (id, text) — raw 기준 not_found
    nf_llm_rows = []   # (id, text) — LLM-basis 기준 not_found (잔여)
    for ev_id, text, doc_id in rows:
        s_raw = ground_evidence(text, raw.get(doc_id, "")).status
        s_llm = ground_evidence(text, llm.get(doc_id, "")).status
        stat_raw[s_raw] += 1
        stat_llm[s_llm] += 1
        if s_raw == "not_found":
            nf_raw_rows.append((ev_id, text))
        if s_llm == "not_found":
            nf_llm_rows.append((ev_id, text))

    def pct(n):
        return f"{n/n_total*100:5.1f}%"

    print("=" * 70)
    print("SEC β G1.5 — not_found 분해 (read-only, 결정론, LLM 0콜, 쓰기 0)")
    print("=" * 70)
    print(f"total evidence: {n_total}\n")

    print("── 판정 분포: raw source(G1) vs LLM-basis source(정제 item_1+7) ──")
    for k in ("verified", "normalized_match", "not_found", "missing_source"):
        print(f"  {k:16s}: raw {stat_raw[k]:5d}({pct(stat_raw[k])})   "
              f"LLM-basis {stat_llm[k]:5d}({pct(stat_llm[k])})")
    print(f"\n  [②섹션귀속] missing_source_section = 0 (구조적: LLM은 저장섹션 item_1+7만 봄)")
    print(f"  [②정규화갭] raw not_found {stat_raw['not_found']} → LLM-basis not_found "
          f"{stat_llm['not_found']} (감소 {stat_raw['not_found']-stat_llm['not_found']} = 정제갭분)")

    # ── ① 중복 접기 (정규화 문장 키) ──
    all_keys = [normalize(t) for _, t, _ in rows]
    uniq_all = len(set(k for k in all_keys if k))
    nf_llm_keys = [normalize(t) for _, t in nf_llm_rows]
    uniq_nf_llm = len(set(k for k in nf_llm_keys if k))
    nf_raw_keys = [normalize(t) for _, t in nf_raw_rows]
    uniq_nf_raw = len(set(k for k in nf_raw_keys if k))
    print("\n── ① 중복 접기(정규화 문장 키) ──")
    print(f"  전체 1,751 유니크 문장 = {uniq_all} (명목 {n_total}, 중복률 {(1-uniq_all/n_total)*100:.1f}%)")
    print(f"  raw not_found {len(nf_raw_rows)} → 유니크 {uniq_nf_raw}")
    print(f"  LLM-basis not_found(잔여) {len(nf_llm_rows)} → 유니크 {uniq_nf_llm}")
    # 잔여 클러스터 크기 분포
    csize = Counter(Counter(k for k in nf_llm_keys if k).values())
    print(f"  잔여 not_found 클러스터 크기 분포(크기:클러스터수) = {dict(sorted(csize.items()))}")

    # ── 재판정: 순수 not_found율(명목·유니크) ──
    grounded_nom = stat_llm["verified"] + stat_llm["normalized_match"] + stat_llm["not_found"]
    nf_nom = stat_llm["not_found"] / grounded_nom if grounded_nom else 0
    nf_uniq = uniq_nf_llm / uniq_all if uniq_all else 0
    print("\n── 재판정(LLM-basis 잔여 순수 not_found율) ──")
    print(f"  명목 기준 = {nf_nom*100:.2f}%   유니크 기준 = {nf_uniq*100:.2f}%   [임계 15%]")
    verdict = "≤15% → V-B 불요, Gate2 사인오프 직행" if max(nf_nom, nf_uniq) <= 0.15 \
        else ">15% → V-B 부분도입 결정 사이클 회부(범위=잔여 클러스터)"
    print(f"  판정: {verdict}")

    # ── ③-a 비-verbatim 패턴 결정론 분류(prefix 매칭, prompt v2 설계 입력) ──
    # 유니크 잔여 not_found를 원문(정규화) 대비 prefix 존재로 분류:
    #  prefix64 존재 → 문장 대체로 원문에 있음, LLM이 tail 발산(절단/소편집)
    #  prefix24만 존재 → 부분 중첩(중간 재서술)
    #  prefix24 부재 → 원문에 문두조차 없음(합성/전면 재서술)
    src_by_ev = {ev_id: normalize(llm.get(doc_id, "")) for ev_id, _, doc_id in rows}
    seen_key = set()
    buckets = Counter()
    for ev_id, text in nf_llm_rows:
        k = normalize(text)
        if not k or k in seen_key:
            continue
        seen_key.add(k)
        nsrc = src_by_ev.get(ev_id, "")
        if len(k) >= 64 and k[:64] in nsrc:
            buckets["prefix64_present(tail 발산=절단/소편집)"] += 1
        elif len(k) >= 24 and k[:24] in nsrc:
            buckets["prefix24_present(중간 재서술)"] += 1
        else:
            buckets["prefix24_absent(합성/전면 재서술)"] += 1
    print("\n── ③-a 비-verbatim 패턴 분류(유니크 182 잔여, 결정론 prefix) ──")
    for klabel, v in buckets.most_common():
        print(f"  {klabel:38s}: {v}")

    # ── ③ 잔여 층화 샘플 20(유니크 클러스터 대표) ──
    print("\n── ③ 잔여 not_found 층화 샘플 20(유니크 대표, 육안 대조용) ──")
    seen = set()
    shown = 0
    for ev_id, text in nf_llm_rows:
        k = normalize(text)
        if k in seen:
            continue
        seen.add(k)
        print(f"  [{ev_id}] {(text or '')[:150]}")
        shown += 1
        if shown >= 20:
            break


if __name__ == "__main__":
    main()
