#!/usr/bin/env python3
"""SEC β G1.6 — partial_match 재분류 dry-run 리포트 (read-only, 결정론, LLM 0콜, 쓰기 0).

기준(sec_beta_g16_partial_grade_directive.md §1, Gate 0 `1c41a7e5` 고정):
  partial_match = 정규화 접두 연속 매치 ≥ 인용 길이 70% AND 절단/tail 발산. 70% 미달=not_found 유지.

**단일 출처(A-1)**: 판정은 `services.sec_pipeline.grounding.ground_evidence_g16`(백필과 동일 함수)를
  import. 로컬 재분류 로직 없음(복제 금지, DECISIONS 규약 10장). 본 스크립트는 raw SQL 소스 경로로
  독립 산출 → 백필(ORM 경로)과 per-record 일치를 A-2 parity check가 입증.

출력: 4분포(명목·유니크 병기)·잔여 순수 not_found율·H4 정합·§3 partial 층화 20건.
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

from services.sec_pipeline.grounding import (  # noqa: E402
    PARTIAL_MIN_RATIO,
    _max_prefix_len,
    ground_evidence_g16,
    normalize,
)


def raw_source(item_1, item_1a, item_7):
    return "\n".join(p for p in (item_1, item_1a, item_7) if p)


def main():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, item_1_text, item_1a_text, item_7_text FROM sec_raw_document_store"
        )
        src = {r[0]: raw_source(r[1], r[2], r[3]) for r in cur.fetchall()}
        cur.execute(
            "SELECT id, evidence_text, source_document_id FROM sec_supply_chain_evidence"
        )
        rows = cur.fetchall()

    n_total = len(rows)
    stat = Counter()
    by_status_texts = {"verified": [], "partial_match": [], "not_found": []}
    pm_rows = []  # (ev_id, text, doc_id) — partial_match (§3용)
    for ev_id, text, doc_id in rows:
        st = ground_evidence_g16(text, src.get(doc_id, "")).status
        stat[st] += 1
        if st in by_status_texts:
            by_status_texts[st].append(text)
        if st == "partial_match":
            pm_rows.append((ev_id, text, doc_id))

    def uniq(texts):
        return len({normalize(t) for t in texts if normalize(t)})

    uniq_all = uniq([t for _, t, _ in rows])
    n_v, n_n = stat["verified"], stat["normalized_match"]
    n_pm, n_nf, n_ms = stat["partial_match"], stat["not_found"], stat["missing_source"]

    def pct(n, d):
        return f"{(n/d*100 if d else 0):5.2f}%"

    print("=" * 74)
    print("SEC β G1.6 — partial_match 재분류 (read-only, 결정론, LLM 0콜, 쓰기 0)")
    print(f"  단일 출처 ground_evidence_g16 · partial 접두비율 ≥ {PARTIAL_MIN_RATIO:.0%} (Gate0 1c41a7e5)")
    print("=" * 74)
    print(f"total evidence(명목): {n_total}   유니크(정규화): {uniq_all}\n")

    print("── §2 재분류 후 4분포 (상호배타·전수합 명목) ──")
    print(f"  {'등급':16s}{'명목':>10s}{'(명목%)':>10s}{'유니크':>10s}")
    print(f"  {'verified':16s}{n_v:>10d}{pct(n_v,n_total):>10s}{uniq(by_status_texts['verified']):>10d}")
    print(f"  {'normalized_match':16s}{n_n:>10d}{pct(n_n,n_total):>10s}{'-':>10s}")
    print(f"  {'partial_match':16s}{n_pm:>10d}{pct(n_pm,n_total):>10s}{uniq(by_status_texts['partial_match']):>10d}")
    print(f"  {'not_found(잔여)':16s}{n_nf:>10d}{pct(n_nf,n_total):>10s}{uniq(by_status_texts['not_found']):>10d}")
    print(f"  {'missing_source':16s}{n_ms:>10d}{pct(n_ms,n_total):>10s}{'-':>10s}")
    print(f"  {'합계':16s}{n_v+n_n+n_pm+n_nf+n_ms:>10d}")
    assert n_v + n_n + n_pm + n_nf + n_ms == n_total, "4분포 전수합 ≠ 명목"

    print("\n── 잔여 순수 not_found율 (partial 제외, missing_source=0 → 분모=명목) ──")
    nf_uniq = uniq(by_status_texts["not_found"])
    print(f"  명목 = {n_nf}/{n_total} = {pct(n_nf, n_total)}")
    print(f"  유니크 = {nf_uniq}/{uniq_all} = {pct(nf_uniq, uniq_all)}   [임계 15% — 판정은 감독 몫]")

    print("\n── H4 정합성 교차(G1.5 tail 발산 169 계열과 대조) ──")
    print(f"  partial_match 명목 {n_pm} · 유니크 {uniq(by_status_texts['partial_match'])}  vs  "
          f"G1.5 tail발산 유니크 169")

    print("\n── §3 partial_match 층화 20건 (인용 | 발산지점 | 원문 tail) ──")
    scored = []
    for ev_id, text, doc_id in pm_rows:
        nq = normalize(text)
        ns = normalize(src.get(doc_id, ""))
        k = _max_prefix_len(nq, ns)
        scored.append((k / len(nq) if nq else 0, ev_id, text, ns, k, nq))
    shown, seen = 0, set()
    for r, ev_id, text, ns, k, nq in sorted(scored):
        if nq in seen:
            continue
        seen.add(nq)
        pos = ns.find(nq[:k])
        src_tail = ns[pos + k: pos + k + 40] if pos >= 0 else "(위치불명)"
        print(f"  [{ev_id}] r={r:.2f} k={k}/{len(nq)}")
        print(f"    인용접두(매치): …{nq[max(0,k-45):k]}")
        print(f"    인용발산(tail): {nq[k:k+45]!r}")
        print(f"    원문 이어짐    : {src_tail!r}")
        shown += 1
        if shown >= 20:
            break

    print("\n[완료] LLM 0콜 · DB 쓰기 0 · raw SELECT만.")


if __name__ == "__main__":
    main()
