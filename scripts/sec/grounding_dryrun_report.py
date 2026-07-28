#!/usr/bin/env python3
"""SEC β G1 — grounding 백필 dry-run 분포 리포트 (read-only, 공유 DB 스키마 무변경).

미머지 마이그(0002)를 공유 stock_vis에 적용하지 않고도 실 1,751건의 판정 분포를
산출하기 위한 read-only 스크립트. 신규 컬럼(grounding_status 등)을 참조하지 않고
raw SQL로 evidence·원문만 읽어 결정론 매처(ground_evidence)로 집계한다. **쓰기 0건.**

판정 4종(개정문1): verified / normalized_match / not_found / missing_source.
임계(개정문2, dry-run 전 고정): not_found(순수)/(v+n+nf) > 15% → V-B 회부 · missing_source > 0 → 목록 보고.

사용: python scripts/sec/grounding_dryrun_report.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

from services.sec_pipeline.grounding import ground_evidence  # noqa: E402


def _source_text(item_1, item_1a, item_7) -> str:
    return "\n".join(p for p in (item_1, item_1a, item_7) if p)


def main():
    # 511 문서 원문을 doc_id → source_text 로 선적재(evidence가 공유 참조).
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, item_1_text, item_1a_text, item_7_text FROM sec_raw_document_store"
        )
        docs = {r[0]: _source_text(r[1], r[2], r[3]) for r in cur.fetchall()}

        cur.execute(
            "SELECT id, evidence_text, source_document_id FROM sec_supply_chain_evidence"
        )
        rows = cur.fetchall()

    tally = {"verified": 0, "normalized_match": 0, "not_found": 0, "missing_source": 0}
    not_found_samples = []
    missing_source_docs = set()
    for ev_id, evidence_text, doc_id in rows:
        source = docs.get(doc_id, "")
        status = ground_evidence(evidence_text, source).status
        tally[status] += 1
        if status == "not_found" and len(not_found_samples) < 20:
            not_found_samples.append((ev_id, (evidence_text or "")[:120]))
        if status == "missing_source":
            missing_source_docs.add(doc_id)

    total = sum(tally.values())
    grounded = tally["verified"] + tally["normalized_match"] + tally["not_found"]
    nf_ratio = (tally["not_found"] / grounded) if grounded else 0.0

    print("=" * 64)
    print("SEC β G1 — grounding dry-run 분포 (read-only, 쓰기 0건)")
    print("=" * 64)
    print(f"total evidence      : {total}")
    for k in ("verified", "normalized_match", "not_found", "missing_source"):
        pct = (tally[k] / total * 100) if total else 0
        print(f"  {k:16s}: {tally[k]:5d}  ({pct:5.1f}%)")
    print("-" * 64)
    print(f"not_found 비율(순수, missing_source 제외) = {nf_ratio*100:.2f}%  "
          f"[임계 15% → {'⚠ V-B 회부' if nf_ratio > 0.15 else 'OK'}]")
    print(f"missing_source = {tally['missing_source']}  "
          f"[>0 → 목록 보고: {'⚠ ' + str(sorted(missing_source_docs)) if tally['missing_source'] else '없음'}]")
    if not_found_samples:
        print("-" * 64)
        print(f"not_found 샘플 {len(not_found_samples)}건(≤20):")
        for ev_id, snippet in not_found_samples:
            print(f"  [{ev_id}] {snippet}")


if __name__ == "__main__":
    main()
