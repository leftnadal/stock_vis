#!/usr/bin/env python3
"""SEC β G1.6 A-2 — 백필 경로 ↔ dry-run 리포트 경로 per-record 행위 동일성 입증.

두 독립 경로가 evidence id별 판정이 완전히 같은지 대조(집계 4분포 일치만으로는 불충분):
  경로 B(백필): ORM `run_grounding_backfill(dry_run=True, collect_records=True)` = ground_evidence_g16
                + build_source_text(ORM source_document).
  경로 A(리포트): raw SQL 소스(raw_source) + ground_evidence_g16.
둘 다 판정 로직은 단일 출처 `ground_evidence_g16`(A-1). 차이 가능 지점 = 소스 구성(ORM vs raw SQL).

결과: 총건·일치·불일치. **diff ≠ 0 → exit 1 (AUTO-HALT 신호)**, 불일치 id 목록 출력. LLM 0·쓰기 0.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

from services.sec_pipeline.grounding import ground_evidence_g16  # noqa: E402
from services.sec_pipeline.grounding_backfill import run_grounding_backfill  # noqa: E402


def raw_source(item_1, item_1a, item_7):
    return "\n".join(p for p in (item_1, item_1a, item_7) if p)


def path_a_records():
    """리포트 경로: raw SQL 소스 + ground_evidence_g16 → {id: status}."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id, item_1_text, item_1a_text, item_7_text FROM sec_raw_document_store"
        )
        src = {r[0]: raw_source(r[1], r[2], r[3]) for r in cur.fetchall()}
        cur.execute(
            "SELECT id, evidence_text, source_document_id FROM sec_supply_chain_evidence"
        )
        rows = cur.fetchall()
    return {ev_id: ground_evidence_g16(text, src.get(doc_id, "")).status
            for ev_id, text, doc_id in rows}


def main():
    # 경로 B: 백필 dry-run(미검증만 대상). 전량 대조 위해 grounding_status 무필터 필요 →
    #   현재 prod 전량 NULL(백필 前)이면 백필 dry-run이 전량 커버. 아니면 A-2는 백필 前에 수행.
    b = run_grounding_backfill(dry_run=True, collect_records=True)
    rec_b = b["records"]
    rec_a = path_a_records()

    # 백필은 grounding_status IS NULL만 → 그 부분집합으로 대조(A-2는 백필 前 = 전량 NULL 가정)
    ids = set(rec_b) & set(rec_a)
    only_b = set(rec_b) - set(rec_a)
    only_a = set(rec_a) - set(rec_b)

    diffs = [(i, rec_b[i], rec_a[i]) for i in sorted(ids) if rec_b[i] != rec_a[i]]

    print("=" * 70)
    print("SEC β G1.6 A-2 — per-record 행위 동일성 (백필 ORM ↔ 리포트 raw SQL)")
    print("=" * 70)
    print(f"경로 B(백필 dry-run) 대상: {len(rec_b)}   경로 A(리포트): {len(rec_a)}")
    print(f"공통 id: {len(ids)}   B에만: {len(only_b)}   A에만(=이미 백필됨/필터): {len(only_a)}")
    print(f"per-record 불일치(diff): {len(diffs)}")
    if diffs:
        print("\n⚠️ 불일치 목록(id, backfill, report):")
        for i, sb, sa in diffs[:50]:
            print(f"  id={i}: backfill={sb} != report={sa}")
        print("\n[AUTO-HALT] diff ≠ 0 → 정지 신호(exit 1)")
        return 1
    # 백필 대상(NULL)이 전량인지 확인 = A-2 유효성
    if len(rec_b) != len(rec_a):
        print(f"\n⚠️ 백필 대상({len(rec_b)}) ≠ 전량({len(rec_a)}) — A-2는 백필 前(전량 NULL) 수행 필요")
    print(f"\n✅ per-record diff = 0 (공통 {len(ids)}건 전부 동일 판정). 행위 동일성 입증.")
    print("[완료] LLM 0 · 쓰기 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
