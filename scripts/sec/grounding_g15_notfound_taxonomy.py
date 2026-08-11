#!/usr/bin/env python3
"""SEC β G1.5 — not_found 배타적 근본원인 분류 (SECB-G15-DECOMP-0811).

read-only · 결정론(재실행 동일) · LLM 0콜 · DB 쓰기 0.

기존 `grounding_g15_decompose.py`(4d0ed3b5, 07-28)는 raw↔LLM-basis 정규화갭 +
dedup + prefix64/24 비-verbatim 렌즈로 분해했다. 본 스크립트는 그 위에서
디렉터 지시(SECB-G15-DECOMP-0811)의 **배타적 우선순위 분류**(한 건 = 한 태그)를
계산한다. 목적 = V-B(LLM 재추출) 판정의 분모를 code-fixable(NORM-MISS)와
진성 비-verbatim(TRUE-NONVERBATIM)으로 순수 분리.

grounding source = 프로덕션 `build_source_text` 미러 = "\n".join(item_1, item_1a, item_7).
strict 판정 = `ground_evidence`(NFKC+ASCII따옴표/대시+공백압축, **소문자화 없음**).

분류 (우선순위 ①→⑤, 배타):
  ① DUP-EXTRACT     : (filing=source_document_id, 정규화문장) 쌍 중복 계상분.
                      dedup 후 대표 1건만 남기고 나머지(N-1)를 DUP-EXTRACT로 계상.
                      대표는 ②~⑤로 흐른다(중복이 근본원인을 은폐하지 않게).
  ② ITEM-MISSING    : 대조 원문 섹션 자체가 저장 파이프라인에 부재 → not_found 필연.
                      판정: 해당 filing 저장 item(1/1a/7) 실측. 전부 공백이면 ITEM-MISSING.
                      (섹션 메타 부재로 item 3/8 개별 귀속은 불가 = 추측 분류 금지.)
  ③ NORM-MISS       : 원문 실존하나 정규화 차이로 exact match 실패.
                      판정: strict normalize에 **소문자화** 추가한 완화 재대조 시 매치 성공.
                      (strict normalize가 이미 NFKC+공백 처리 → 완화의 순수 델타 = 대소문자.)
  ④ TRUE-NONVERBATIM: 위 셋 전부 아님 = LLM 패러프레이즈 추정 잔여 (V-B 실분모).
  ⑤ OTHER           : 넷으로 설명 안 되는 건 (빈 인용문 등). 유형 서술 필수.

집계 분모 = STEP 0-4 실측 not_found 모수 (명목) + dedup 후 유니크.
"""
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

from services.sec_pipeline.grounding import ground_evidence, normalize  # noqa: E402


def build_source_text(item_1, item_1a, item_7):
    """프로덕션 grounding_backfill.build_source_text 미러 (동일 결합 규칙)."""
    parts = [item_1, item_1a, item_7]
    return "\n".join(p for p in parts if p)


def relaxed_normalize(text):
    """strict normalize + 소문자화. 완화의 순수 델타 = 대소문자(NFKC·공백은 이미 strict가 처리)."""
    return normalize(text).lower()


def main():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, item_1_text, item_1a_text, item_7_text FROM sec_raw_document_store"
        )
        src = {}
        for r in cur.fetchall():
            src[r[0]] = build_source_text(r[1], r[2], r[3])
        cur.execute(
            "SELECT id, evidence_text, source_document_id FROM sec_supply_chain_evidence"
        )
        rows = cur.fetchall()

    n_total = len(rows)

    # ── STEP 1: strict 판정으로 not_found 모수 확정 ──
    nf_rows = []  # (ev_id, text, doc_id)
    strict_dist = Counter()
    for ev_id, text, doc_id in rows:
        st = ground_evidence(text, src.get(doc_id, "")).status
        strict_dist[st] += 1
        if st == "not_found":
            nf_rows.append((ev_id, text, doc_id))
    n_nf = len(nf_rows)

    # ── STEP 2: ① DUP-EXTRACT — (doc_id, 정규화문장) 쌍 dedup ──
    groups = defaultdict(list)  # key=(doc_id, norm_text) -> [ev_id...]
    for ev_id, text, doc_id in nf_rows:
        groups[(doc_id, normalize(text))].append((ev_id, text, doc_id))
    reps = [g[0] for g in groups.values()]   # 대표 1건/그룹
    n_uniq = len(reps)
    n_dup = n_nf - n_uniq                     # 중복 계상분

    # ── STEP 3: 대표 각각을 ②→⑤ 배타 분류 ──
    tags = {}            # ev_id -> tag
    norm_miss_hits = 0
    for ev_id, text, doc_id in reps:
        s = src.get(doc_id, "")
        ntext = normalize(text)
        # ⑤ 빈 인용문 (strict not_found의 자명 케이스) → OTHER
        if not ntext:
            tags[ev_id] = "OTHER:빈인용문"
            continue
        # ② ITEM-MISSING: 저장 원문(item 1/1a/7) 전부 공백 = 대조 섹션 부재
        if not s or not s.strip():
            tags[ev_id] = "ITEM-MISSING"
            continue
        # ③ NORM-MISS: 완화(소문자) 재대조 매치
        if relaxed_normalize(text) in relaxed_normalize(s):
            tags[ev_id] = "NORM-MISS"
            norm_miss_hits += 1
            continue
        # ④ 잔여
        tags[ev_id] = "TRUE-NONVERBATIM"

    tag_count = Counter(tags.values())
    # OTHER 하위유형 접기
    other_sub = Counter(t for t in tags.values() if t.startswith("OTHER"))

    def pct(n, d):
        return f"{n/d*100:5.2f}%" if d else "  n/a"

    print("=" * 74)
    print("SEC β G1.5 — not_found 배타 근본원인 분류 (SECB-G15-DECOMP-0811)")
    print("read-only · 결정론 · LLM 0콜 · 쓰기 0")
    print("=" * 74)
    print(f"total evidence            : {n_total}")
    print(f"strict 판정 분포          : "
          + "  ".join(f"{k}={strict_dist[k]}" for k in
                      ("verified", "normalized_match", "not_found", "missing_source")))
    print(f"not_found 모수(명목)      : {n_nf}")
    print(f"  └ dedup 유니크(doc,문장): {n_uniq}   중복 계상(DUP-EXTRACT): {n_dup}")
    print()

    print("── 배타 분류 집계표 (우선순위 ①→⑤, 한 건=한 태그) ──")
    print(f"{'태그':<20}{'건수':>8}{'명목%':>10}{'유니크기준%':>14}")
    # ① DUP-EXTRACT (명목에서만 계상 — 유니크 분모에는 미포함)
    print(f"{'① DUP-EXTRACT':<20}{n_dup:>8}{pct(n_dup, n_nf):>10}{'—(중복제거대상)':>14}")
    for tag in ("ITEM-MISSING", "NORM-MISS", "TRUE-NONVERBATIM"):
        c = tag_count.get(tag, 0)
        label = {"ITEM-MISSING": "② ITEM-MISSING",
                 "NORM-MISS": "③ NORM-MISS",
                 "TRUE-NONVERBATIM": "④ TRUE-NONVERBATIM"}[tag]
        print(f"{label:<20}{c:>8}{pct(c, n_nf):>10}{pct(c, n_uniq):>14}")
    n_other = sum(v for k, v in tag_count.items() if k.startswith("OTHER"))
    print(f"{'⑤ OTHER':<20}{n_other:>8}{pct(n_other, n_nf):>10}{pct(n_other, n_uniq):>14}")
    if other_sub:
        for k, v in other_sub.most_common():
            print(f"     └ {k}: {v}")
    # 검산
    accounted = n_dup + sum(tag_count.values())
    print(f"검산: DUP {n_dup} + 대표 {sum(tag_count.values())} = {accounted} (모수 {n_nf}) "
          f"{'✅' if accounted == n_nf else '❌ 불일치'}")
    print()

    print("── ③ NORM-MISS 완화(소문자) 재대조 매치율 (구제 가능성 정량 근거) ──")
    print(f"  유니크 대표 {n_uniq} 중 소문자 완화로 매치 = {norm_miss_hits} "
          f"({pct(norm_miss_hits, n_uniq)}) → 대조기 소문자 완화 시 code-fixable")
    print(f"  잔여 진성 비-verbatim(V-B 실분모) = {tag_count.get('TRUE-NONVERBATIM', 0)} "
          f"(유니크 {pct(tag_count.get('TRUE-NONVERBATIM', 0), n_uniq)})")
    print()

    # ── 태그별 대표 사례 2건 (filing id + 발췌 최소 + 근거) ──
    print("── 태그별 대표 사례 (각 2건, filing=source_document_id) ──")
    by_tag = defaultdict(list)
    for ev_id, text, doc_id in reps:
        by_tag[tags[ev_id]].append((ev_id, text, doc_id))
    # DUP-EXTRACT 사례 = 중복 그룹(size≥2) 대표
    dup_examples = [(k, v) for k, v in groups.items() if len(v) >= 2]
    dup_examples.sort(key=lambda kv: -len(kv[1]))
    print("① DUP-EXTRACT (중복 그룹 상위 2):")
    for (doc_id, nkey), members in dup_examples[:2]:
        ev0 = members[0]
        print(f"   filing={doc_id} ×{len(members)}회: [{ev0[0]}] {(ev0[1] or '')[:90]}")
    for tag_key in ("ITEM-MISSING", "NORM-MISS", "TRUE-NONVERBATIM"):
        exs = by_tag.get(tag_key, [])
        print(f"{tag_key} ({len(exs)}건) 사례:")
        for ev_id, text, doc_id in exs[:2]:
            print(f"   filing={doc_id} [{ev_id}]: {(text or '')[:90]}")
        if not exs:
            print("   (해당 건 0 — 구조적 부재)")
    for tag_key in [k for k in by_tag if k.startswith("OTHER")]:
        exs = by_tag[tag_key]
        print(f"{tag_key} ({len(exs)}건) 사례:")
        for ev_id, text, doc_id in exs[:2]:
            print(f"   filing={doc_id} [{ev_id}]: '{(text or '')[:60]}'")


if __name__ == "__main__":
    main()
