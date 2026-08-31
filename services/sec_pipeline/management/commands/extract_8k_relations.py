"""CS-P2-8K Slice3: 8-K 상대 기업 추출 → ticker 해소 → RelationConfidence evidence 착지.

각 SEC8KFiling(status=collected)의 item 1.01/2.01 본문 → Gemini 추출+분류 →
  · 착지후보(commercial/supply/acquisition, confidence≥τ) → ticker_matcher 해소
      - 해소 성공 → SEC8KCounterpartyEvidence + RelationConfidence(serving_layer=evidence) 착지
      - 해소 실패 → UnmatchedCompanyQueue(source_form=8-K) + evidence(landed=False)
  · 금융(은행)·unclear → 원문 보존(SEC8KFiling)·미착지·카운트만(병진 단서: 강행 착지 금지)

기본 --dry-run(LLM+분류+해소 시뮬, DB 쓰기 0·status 무변경). --apply=실제 착지.
착지 규약 = seed_relations_to_chainsight IDENTICAL(update_or_create, 기존쌍 status 무접촉,
신규쌍 create_defaults status, truth_score 85/60, self-loop 가드) + serving_layer=evidence 명시.
"""

from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from services.sec_pipeline.extractor_8k import (
    CATEGORY_TO_RELATION,
    LAND_CATEGORIES,
    extract_counterparties,
    extract_item_bodies,
)

TARGET_ITEMS = {"1.01", "2.01"}


class Command(BaseCommand):
    help = "8-K 상대 기업 추출 → 해소 → RelationConfidence evidence 착지. 기본 dry-run."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--limit", type=int, default=0, help="filing 상한(테스트).")
        parser.add_argument("--min-confidence", type=float, default=0.5)
        parser.add_argument("--sample", type=int, default=10, help="스팟체크 발췌 건수.")

    def handle(self, *args, **opts):
        from apps.chain_sight.models import RelationConfidence
        from apps.chain_sight.services.upward_learning import HIGHSCORE_THRESHOLD
        from apps.chain_sight.services.score_scale import (
            GRADE_CONFIRMED_MIN,
            GRADE_LIKELY_MIN,
            SCORE_VERSION_CURRENT,
        )
        from apps.chain_sight.utils import normalize_pair, skip_self_loop
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            SEC8KCounterpartyEvidence,
            SEC8KFiling,
            UnmatchedCompanyQueue,
        )
        from services.sec_pipeline.ticker_matcher import TickerMatcher

        apply = opts["apply"]
        min_conf = opts["min_confidence"]
        matcher = TickerMatcher()

        qs = SEC8KFiling.objects.filter(status="collected").order_by("id")
        if opts["limit"]:
            qs = qs[: opts["limit"]]
        total_filings = qs.count()

        sectors = dict(Stock.objects.values_list("symbol", "sector"))
        univ = set(sectors.keys())

        cat_dist = Counter()
        n_cp = 0
        landed = landed_new = landed_existing = queued = self_skip = 0
        acq_withheld = 0  # acquisition: 방향/주체 결함으로 RC 착지 보류(증거만)
        below_conf = 0
        filings_with_cp = empty = errors = 0
        spot = []
        would_land = would_queue = 0  # dry-run 시뮬

        self.stdout.write(
            f"=== 8-K 추출/착지 ({'APPLY' if apply else 'DRY-RUN'}) "
            f"filings={total_filings} min_conf={min_conf} ==="
        )

        for fi, filing in enumerate(qs.iterator()):
            company = filing.symbol_id
            bodies = extract_item_bodies(filing.raw_text, TARGET_ITEMS)
            if not bodies:
                empty += 1
                if apply:
                    SEC8KFiling.objects.filter(pk=filing.pk).update(status="empty")
                continue
            res = extract_counterparties(company, company, bodies)
            if res.get("error"):
                errors += 1
            cps = res.get("counterparties", [])
            if cps:
                filings_with_cp += 1
            elif apply:
                SEC8KFiling.objects.filter(pk=filing.pk).update(status="empty")

            source_sector = sectors.get(company, "")
            landed_this = False
            for c in cps:
                n_cp += 1
                cat = c["category"]
                cat_dist[cat] += 1
                # 스팟체크 표본(균등 수집)
                if len(spot) < opts["sample"] and n_cp % 7 == 1:
                    spot.append(
                        f"[{company} {filing.filing_date} item{c.get('item') or '?'}] "
                        f"'{c['name']}' → {cat} (conf {c['confidence']:.2f}) : {c['evidence'][:140]}"
                    )
                if cat not in LAND_CATEGORIES:
                    continue  # financing/unclear: 원문 보존·미착지·카운트만
                if c["confidence"] < min_conf:
                    below_conf += 1
                    continue
                rel_type = CATEGORY_TO_RELATION[cat]
                ticker, method = matcher.match(c["name"], source_sector)
                # 신뢰 해소 = exact/alias만. fuzzy(token_sort≥80)는 오매칭 위험(실측:
                # Masimo→Masco·Synaptics→Snap-on·Comerica→Corning) → 미해소 취급, 착지 금지.
                trusted = bool(ticker) and ticker in univ and method in ("exact", "alias")

                if trusted and ticker == company:
                    self_skip += 1
                    continue

                ev = None
                if apply:
                    ev = SEC8KCounterpartyEvidence.objects.create(
                        filing=filing, source_symbol=company,
                        raw_target_name=c["name"],
                        resolved_ticker=ticker if (ticker and ticker in univ) else "",
                        match_method=method or "", relationship_type=rel_type,
                        item_code=c.get("item") or "", filing_date=filing.filing_date,
                        evidence_text=c["evidence"], landed=False,
                    )

                if not trusted:
                    # 미해소 or fuzzy → 큐(확장 2차 근거), 미착지
                    would_queue += 1
                    if apply:
                        qe, created = UnmatchedCompanyQueue.objects.get_or_create(
                            raw_company_name=c["name"],
                            defaults={
                                "source_symbol": company, "status": "pending",
                                "source_sectors": [source_sector] if source_sector else [],
                                "source_form": "8-K",
                                "fuzzy_candidates": matcher._get_fuzzy_candidates(c["name"]),
                            },
                        )
                        if not created:
                            qe.occurrence_count += 1
                            qe.save(update_fields=["occurrence_count"])
                        queued += 1
                    continue

                # ACQUIRED(acquisition): filer→상대 방향/주체가 원문에서 불안정(실측:
                # BEAM→BMY 등 방향 역·merger sub 오지목) → RC 착지 보류(증거만 보존).
                # 방향·주체 disambiguation은 TASKQUEUE(8-K ACQUIRED 정제) 후 재개.
                if cat == "acquisition":
                    acq_withheld += 1
                    continue

                # 해소 성공(commercial/supply, exact/alias) → 착지
                would_land += 1
                if not apply:
                    continue
                # D-RC-SCALE: [0,1] 단위 계단(단일 소스 score_scale).
                score = GRADE_CONFIRMED_MIN if c["confidence"] >= 0.8 else GRADE_LIKELY_MIN
                if rel_type == "COMPETES_WITH":
                    sym_a, sym_b = normalize_pair(company, ticker)
                    direction = "both"
                else:
                    sym_a, sym_b, direction = company, ticker, "a→b"
                # A-1(MIG-BUNDLE-1): a≠b 가드 — 자기루프 skip+구조화 로그(카운터 보존).
                if skip_self_loop(sym_a, sym_b, rel_type, source="sec_8k_extract"):
                    self_skip += 1
                    continue
                # evidence_sources 병합(기존쌍 8-K 소스 추가)
                existing = RelationConfidence.objects.filter(
                    symbol_a=sym_a, symbol_b=sym_b, relation_type=rel_type
                ).first()
                sources = set((existing.evidence_sources or {}).get("sources", [])) if existing else set()
                sources.add("sec_8k")
                common = {
                    "relation_category": "truth",
                    "canonical_direction": direction,
                    "truth_score": score,
                    "score_version": SCORE_VERSION_CURRENT,  # D-RC-SCALE: 신규 행 태생 [0,1]·v3.0
                    "evidence_tier_best": 1,
                    "serving_layer": "evidence",
                    "has_supply_chain_source": rel_type == "SUPPLIES_TO",
                    "evidence_sources": {"sources": sorted(sources)},
                    "relation_basis_summary": f"SEC 8-K item {c.get('item') or ''}: {c['evidence'][:90]}",
                }
                obj, is_new = RelationConfidence.objects.update_or_create(
                    symbol_a=sym_a, symbol_b=sym_b, relation_type=rel_type,
                    defaults=common,
                    create_defaults={
                        **common,
                        "relation_status": (
                            "confirmed" if score >= HIGHSCORE_THRESHOLD else "probable"
                        ),
                    },
                )
                if ev is not None:
                    ev.landed = True
                    ev.save(update_fields=["landed"])
                landed += 1
                landed_this = True
                if is_new:
                    landed_new += 1
                else:
                    landed_existing += 1

            if apply and cps:
                SEC8KFiling.objects.filter(pk=filing.pk).update(status="extracted")
            if (fi + 1) % 100 == 0:
                self.stdout.write(f"  ...추출 {fi+1}/{total_filings} 누적 착지 {landed}")

        # ── 리포트 ──
        self.stdout.write("\n=== 분류 분포(counterparty 단위) ===")
        self.stdout.write(f"  총 counterparty: {n_cp}")
        for cat in ["commercial", "supply", "acquisition", "financing", "unclear"]:
            self.stdout.write(f"    {cat}: {cat_dist.get(cat,0)}")
        land_cand = sum(cat_dist.get(c, 0) for c in LAND_CATEGORIES)
        noise = cat_dist.get("financing", 0) + cat_dist.get("unclear", 0)
        self.stdout.write(
            f"  착지후보(상업+공급+M&A): {land_cand}  미착지(금융+unclear): {noise} "
            f"({noise/n_cp*100:.1f}% of cp)" if n_cp else "  (cp 0)"
        )
        self.stdout.write("\n=== 깔때기 ===")
        self.stdout.write(f"  filings 처리: {total_filings} (상대기업 보유 {filings_with_cp} / empty {empty} / LLM err {errors})")
        self.stdout.write(f"  착지후보 신뢰도미달(<{min_conf}): {below_conf}")
        self.stdout.write(f"  ACQUIRED 착지보류(방향결함, 증거만): {acq_withheld}")
        if apply:
            self.stdout.write(f"  착지 쌍(commercial/supply·exact/alias): {landed} (신규 {landed_new} / 기존증거보강 {landed_existing})")
            self.stdout.write(f"  미해소 큐 적재(미해소+fuzzy): {queued}  self-skip: {self_skip}")
        else:
            self.stdout.write(f"  [시뮬] 착지가능: {would_land}  미해소예상: {would_queue}  self-skip: {self_skip}")

        self.stdout.write(f"\n=== 스팟체크 표본 {len(spot)}건 ===")
        for s in spot:
            self.stdout.write("  " + s)

        if not apply:
            self.stdout.write(self.style.WARNING("\ndry-run: DB 쓰기 0건 (--apply로 착지)"))
