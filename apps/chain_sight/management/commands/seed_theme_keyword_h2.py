"""
H2 사전 박제 (TH-13, 결정19=A) — 검수표 671 → ThemeKeywordH2 원장.

docs/chain_sight/theme_heat/h2_dict_draft.json 의 review_table(배정 671, none 제외)을
정규화형 완전 일치 키로 upsert(멱등). provenance = source/applied_at/confidence 태깅.
정규화 키 충돌은 unique(term_normalized) 로 자연 병합(TH-12b 판정: 실효 손실 0).

사용: python manage.py seed_theme_keyword_h2 [--source h2_v1] [--dry-run]
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chain_sight.services.c3_narrative_service import _normalize

DRAFT_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs" / "chain_sight" / "theme_heat" / "h2_dict_draft.json"
)
GICS = {
    "Technology", "Financial Services", "Healthcare", "Energy", "Industrials",
    "Consumer Cyclical", "Consumer Defensive", "Basic Materials", "Real Estate",
    "Utilities", "Communication Services",
}
VALID_CONF = {"high", "medium", "low"}


class Command(BaseCommand):
    help = "H2 검수표 671 → ThemeKeywordH2 원장 박제 (provenance 태깅, 멱등)."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="h2_v1", help="provenance 박제 표식.")
        parser.add_argument("--dry-run", action="store_true", help="쓰기 없이 산식만.")

    def handle(self, *args, **opts):
        from apps.chain_sight.models import ThemeKeywordH2

        source = opts["source"]
        draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
        rt = draft["review_table"]

        # 검증: 배정만·GICS 정본·정규화 확신
        rows, skipped = {}, []
        for r in rt:
            sec = r["sector"]
            conf = str(r["confidence"]).strip().lower()
            if sec not in GICS or conf not in VALID_CONF:
                skipped.append((r.get("term"), sec, conf))
                continue
            key = _normalize(r["term"])
            rows[key] = {  # 충돌 시 마지막 우선(자연 병합)
                "term_original": r["term"], "sector": sec,
                "confidence": conf, "reason": r.get("reason", ""),
            }

        merged = len(rt) - len(rows)  # 정규화 충돌 병합분
        self.stdout.write(
            f"검수표 {len(rt)} → 정규화 유니크 {len(rows)} (충돌 병합 {merged}, skip {len(skipped)})"
        )
        if opts["dry_run"]:
            self.stdout.write("dry-run: 쓰기 없음.")
            return

        now = timezone.now()
        created = updated = 0
        for key, v in rows.items():
            _obj, was_created = ThemeKeywordH2.objects.update_or_create(
                term_normalized=key,
                defaults={
                    "term_original": v["term_original"], "sector": v["sector"],
                    "confidence": v["confidence"], "reason": v["reason"],
                    "source": source, "applied_at": now,
                },
            )
            created += was_created
            updated += not was_created

        total = ThemeKeywordH2.objects.filter(source=source).count()
        self.stdout.write(self.style.SUCCESS(
            f"박제 완료: created={created} updated={updated} "
            f"source={source} 원장 총 {total}행 (= 671 − 병합 {merged})"
        ))
