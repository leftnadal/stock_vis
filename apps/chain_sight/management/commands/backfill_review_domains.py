"""검수 산출 도메인 태그 → RelationConfidence 적재 (⑳-3 S3-MINDMAP S0).

REVIEW-P2 검수 배치(review_batch_v6_labeled.csv)의 태그 컬럼을 approved 관계에
적재한다. 파이프라인이 write 모드로 실행된 적 없어 태그가 DB에 0건인 갭(S3-R 실측)을
'기존 검수 산출물 보호' 방식으로 메운다 — LLM 재호출 없음, CSV가 진실의 소스(무수정).

    python manage.py backfill_review_domains --dry-run   # 기본: DB 무기록, 적재 예정 리포트
    python manage.py backfill_review_domains --apply      # 실 DB 적재(트랜잭션 원자·idempotent)

적재 규칙 (approved = OK/CHANGE/CHANGE_REV verdict 행 중 normalized_tag 보유분):
    relation_domain       ← normalized_tag  (정규화 승인본, 마인드맵 L1 카테고리 소스)
    relation_domain_draft ← draft_domain    (LLM 원시 초안, provenance)

매칭: match_forward_exact (apply_review_verdicts 재사용, 복제 금지). approved 대상은
전부 OK 행(키 불변)이라 forward-exact로 유일 매칭. 매칭 RC가 domain_review_status
='approved'가 아니면 보호 차원에서 skip(태그를 pending/rejected에 쓰지 않음).
"""

import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.chain_sight.management.commands.apply_review_verdicts import (
    match_forward_exact,
    parse_verdict,
    VerdictParseError,
)

DEFAULT_CSV = "docs/etc/review_batch_v6_labeled.csv"
TAG_COL = "normalized_tag"       # 승인본 소스(정규화 버킷)
DRAFT_COL = "draft_domain"       # 초안 소스(원시 LLM)
VERDICT_COL = "human_verdict"


def build_backfill_plan(rows):
    """CSV 행 → 적재 계획(DB 조회만). 반환 dict.

    plan       : [(rc_id, pair, rtype, tag, draft)]
    skipped    : [(pair, rtype, reason)]  — 매칭 실패·비approved·태그없음
    """
    plan, skipped = [], []
    for r in rows:
        pair, rtype = r["symbol_pair"], r["relation_type"]
        try:
            kind, _ = parse_verdict(r[VERDICT_COL])
        except VerdictParseError:
            continue
        if kind not in ("OK", "CHANGE", "CHANGE_REV"):
            continue  # DROP/HOLD는 태그 대상 아님
        tag = (r.get(TAG_COL) or "").strip()
        if not tag:
            continue  # 태그 없는 approved(71건) — 화면 유형 수납 폴백
        draft = (r.get(DRAFT_COL) or "").strip()

        qs = match_forward_exact(pair, rtype)  # approved 대상=OK행(키 불변)
        n = qs.count()
        if n != 1:
            skipped.append((pair, rtype, f"매칭 {n}건"))
            continue
        obj = qs.first()
        if obj.domain_review_status != "approved":
            skipped.append((pair, rtype, f"비approved({obj.domain_review_status})"))
            continue
        plan.append((obj.id, pair, rtype, tag, draft))
    return {"plan": plan, "skipped": skipped}


def apply_backfill(plan):
    """plan을 DB에 적재(트랜잭션·idempotent). 반환: 적재 건수."""
    with transaction.atomic():
        for rc_id, pair, rtype, tag, draft in plan:
            # 태그·초안만 갱신(neo4j_dirty는 태그가 그래프 엣지 의미를 바꾸지 않으므로 무접촉)
            from apps.chain_sight.models import RelationConfidence
            RelationConfidence.objects.filter(id=rc_id).update(
                relation_domain=tag,
                relation_domain_draft=(draft or None),
            )
    return len(plan)


class Command(BaseCommand):
    help = "검수 배치 도메인 태그 → approved RelationConfidence 적재(CSV→DB, LLM 무호출)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=DEFAULT_CSV)
        parser.add_argument("--apply", action="store_true", help="실 DB 적재(미지정=dry-run)")
        parser.add_argument("--dry-run", action="store_true", help="명시적 dry-run(--apply보다 우선)")

    def handle(self, *args, **opts):
        import collections

        dry_run = opts["dry_run"] or not opts["apply"]
        with open(opts["csv"], newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.stdout.write(f"CSV 로드: {opts['csv']} ({len(rows)}행)")

        p = build_backfill_plan(rows)
        plan, skipped = p["plan"], p["skipped"]
        buckets = collections.Counter(tag for _, _, _, tag, _ in plan)
        self.stdout.write(f"── 적재 예정: {len(plan)}건 · 버킷 {len(buckets)}종 ──")
        for tag, c in buckets.most_common(15):
            self.stdout.write(f"    {c:3}  {tag}")
        if skipped:
            self.stdout.write(f"── skip {len(skipped)}건: {skipped[:10]} ──")

        if dry_run:
            self.stdout.write("dry-run: DB 무기록. (--apply 로 실적재)")
            return
        n = apply_backfill(plan)
        self.stdout.write(f"✅ 적재 완료: {n}건 (relation_domain=normalized_tag · draft=draft_domain)")
