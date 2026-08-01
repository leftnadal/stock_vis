#!/usr/bin/env python3
"""SEC β G1.6 — partial_match 재분류 dry-run (read-only, 결정론, LLM 0콜, 쓰기 0).

기준(sec_beta_g16_partial_grade_directive.md §1, Gate 0 `1c41a7e5`에 사전 고정):
  partial_match = 정규화 **접두 연속 매치 ≥ 인용 길이의 70%** AND 발산 형태 = 절단/mid-word.
  70% 미달 tail 발산은 not_found 유지. partial은 접지 성공(verbatim)에 **합산 금지**.

방식:
  - G1 공식 베이스라인과 동일 basis = **raw source**(item_1+1a+7)로 `ground_evidence` 재판정
    → verified / normalized_match / not_found / missing_source (기대 1273/41/437/0).
  - not_found 각 건에 대해 raw source 대비 **최장 연속 접두 비율** r = maxk(quote[:k]⊂source)/len(quote).
    r ≥ 0.70 → partial_match(절단/tail 발산), else not_found 유지.
  - 접두 단조성(quote[:k]⊂source ⇒ quote[:k-1]⊂source) → 이진 탐색으로 maxk 결정론 산출.
  - 4분포(v/n/pm/nf) 명목(1751)·유니크(정규화 키) 병기. 잔여 순수 not_found율 산출.
  - §3 partial_match 층화 20건(인용 vs 원문·발산 지점).

불변: LLM 0(순수 문자열 계산)·DB 쓰기 0(raw SELECT만)·판정 임계 15% 및 70% 사후조정 금지.
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

PARTIAL_MIN_RATIO = 0.70  # §1 하한 (사전 고정, 사후조정 금지)


def raw_source(item_1, item_1a, item_7):
    return "\n".join(p for p in (item_1, item_1a, item_7) if p)


def max_prefix_len(nquote: str, nsource: str) -> int:
    """정규화 인용의 최장 연속 접두 길이 k (quote[:k] 가 source 부분문자열). 이진 탐색(단조)."""
    if not nquote or not nsource:
        return 0
    if nquote in nsource:
        return len(nquote)
    lo, hi = 0, len(nquote)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if nquote[:mid] in nsource:
            lo = mid
        else:
            hi = mid - 1
    return lo


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
    nsrc_cache = {}

    def nsrc_of(doc_id):
        if doc_id not in nsrc_cache:
            nsrc_cache[doc_id] = normalize(src.get(doc_id, ""))
        return nsrc_cache[doc_id]

    stat = Counter()          # G1 baseline (raw source)
    nf_rows = []              # (ev_id, text, doc_id) — not_found
    for ev_id, text, doc_id in rows:
        st = ground_evidence(text, src.get(doc_id, "")).status
        stat[st] += 1
        if st == "not_found":
            nf_rows.append((ev_id, text, doc_id))

    # ── not_found 재분류: r≥0.70 → partial_match ──
    pm_rows, nf_resid = [], []
    for ev_id, text, doc_id in nf_rows:
        nq = normalize(text)
        if not nq:
            nf_resid.append((ev_id, text, doc_id, 0.0, 0))
            continue
        k = max_prefix_len(nq, nsrc_of(doc_id))
        r = k / len(nq)
        (pm_rows if r >= PARTIAL_MIN_RATIO else nf_resid).append(
            (ev_id, text, doc_id, r, k)
        )

    n_v, n_n = stat["verified"], stat["normalized_match"]
    n_pm, n_nf = len(pm_rows), len(nf_resid)
    n_ms = stat["missing_source"]

    # ── 유니크(정규화 키) ──
    def uniq(texts):
        return len({normalize(t) for t in texts if normalize(t)})

    uniq_all = uniq([t for _, t, _ in rows])
    uniq_v = uniq([t for _, t, d in rows if ground_evidence(t, src.get(d, "")).status == "verified"])
    # v/n/pm/nf 유니크는 겹침 가능(같은 문장이 문서별로 다른 판정) → 각 집합 유니크로 보고
    uniq_pm = uniq([t for _, t, _, _, _ in pm_rows])
    uniq_nf = uniq([t for _, t, _, _, _ in nf_resid])

    def pct(n, d):
        return f"{(n/d*100 if d else 0):5.2f}%"

    print("=" * 74)
    print("SEC β G1.6 — partial_match 재분류 (read-only, 결정론, LLM 0콜, 쓰기 0)")
    print(f"  기준: raw source · partial = 접두비율 ≥ {PARTIAL_MIN_RATIO:.0%} (Gate0 1c41a7e5 고정)")
    print("=" * 74)
    print(f"total evidence(명목): {n_total}   유니크(정규화): {uniq_all}\n")

    print("── G1 베이스라인(raw source) 재현 ──")
    print(f"  verified {n_v} / normalized {n_n} / not_found {len(nf_rows)} / missing_source {n_ms}")
    assert n_v + n_n + len(nf_rows) + n_ms == n_total, "베이스라인 합 불일치"

    print("\n── §2 재분류 후 4분포 (상호배타·전수합 명목) ──")
    print(f"  {'등급':16s}{'명목':>10s}{'(명목%)':>10s}{'유니크':>10s}")
    print(f"  {'verified':16s}{n_v:>10d}{pct(n_v,n_total):>10s}{uniq_v:>10d}")
    print(f"  {'normalized_match':16s}{n_n:>10d}{pct(n_n,n_total):>10s}{'-':>10s}")
    print(f"  {'partial_match':16s}{n_pm:>10d}{pct(n_pm,n_total):>10s}{uniq_pm:>10d}")
    print(f"  {'not_found(잔여)':16s}{n_nf:>10d}{pct(n_nf,n_total):>10s}{uniq_nf:>10d}")
    print(f"  {'missing_source':16s}{n_ms:>10d}{pct(n_ms,n_total):>10s}{'-':>10s}")
    print(f"  {'합계':16s}{n_v+n_n+n_pm+n_nf+n_ms:>10d}")
    assert n_v + n_n + n_pm + n_nf + n_ms == n_total, "4분포 전수합 ≠ 명목"

    print("\n── 잔여 순수 not_found율 (partial 제외, missing_source=0 → 분모=명목) ──")
    grounded_nom = n_v + n_n + n_pm + n_nf  # = n_total (ms=0)
    print(f"  명목 = {n_nf}/{grounded_nom} = {pct(n_nf, grounded_nom)}")
    print(f"  유니크 = {uniq_nf}/{uniq_all} = {pct(uniq_nf, uniq_all)}   [임계 15% — 판정은 감독 몫]")

    print("\n── H4 정합성 교차(G1.5 tail 발산 169 계열과 대조) ──")
    print(f"  partial_match 명목 {n_pm} · 유니크 {uniq_pm}  vs  G1.5 tail발산 유니크 169")

    print("\n── §3 partial_match 층화 20건 (인용 | 발산지점 | 원문 tail) ──")
    shown, seen = 0, set()
    # 비율 오름차순 정렬 → 70% 경계 근처부터 tail 발산 큰 것까지 층화
    for ev_id, text, doc_id, r, k in sorted(pm_rows, key=lambda x: x[3]):
        nq = normalize(text)
        if nq in seen:
            continue
        seen.add(nq)
        nsource = nsrc_of(doc_id)
        pos = nsource.find(nq[:k])
        src_tail = nsource[pos + k: pos + k + 40] if pos >= 0 else "(위치불명)"
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
