"""
SEC Pipeline Celery tasks.

collect_and_extract: SEC 수집 → RawDocumentStore 저장 → extract 트리거
extract_from_document: Track A + Track B (Phase 2) LLM 추출
sync_dirty_to_neo4j: dirty evidence → Neo4j edge 동기화

분리 이유: LLM 실패 시 문서는 보존. 재추출만 하면 됨.
"""

import logging
import time

from celery import shared_task
from django.utils import timezone

from .exceptions import SECFetchError, SectionExtractionError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, soft_time_limit=300, time_limit=360)
def collect_and_extract(self, symbol: str):
    """
    수집→저장→LLM 분리.

    Step 1: SEC EDGAR 메타데이터 (retry 3, 60s backoff)
    Step 2: SEC HTML 다운로드 (retry 5, 10s backoff)
    Step 3: 섹션 추출+검증 → 실패 시 fallback → skip+로그
    Step 4: RawDocumentStore 저장 (accession_no 중복 체크)
    Step 5: extract_from_document.delay(doc.id, symbol)
    """
    from .collector import SECFilingCollector
    from .models import RawDocumentStore

    symbol = symbol.upper()
    collector = SECFilingCollector()

    # ── Step 1: 메타데이터 ──
    _log_stage(symbol, "fmp_metadata", "started")
    start = time.time()
    try:
        metadata = collector.get_filing_metadata(symbol)
        if not metadata:
            _log_stage(symbol, "fmp_metadata", "failed", "No metadata found")
            return {"symbol": symbol, "status": "no_metadata"}
        _log_stage(
            symbol,
            "fmp_metadata",
            "success",
            f"accession={metadata['accession_no']}",
            time.time() - start,
        )
    except Exception as exc:
        _log_stage(symbol, "fmp_metadata", "retrying", str(exc))
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

    # ── Step 2: SEC HTML ──
    _log_stage(symbol, "sec_fetch", "started")
    start = time.time()
    try:
        html = collector.fetch_filing_html(metadata["final_link"])
        if not html:
            raise SECFetchError("Empty HTML response")
        _log_stage(
            symbol, "sec_fetch", "success", f"{len(html)} bytes", time.time() - start
        )
    except Exception as exc:
        _log_stage(symbol, "sec_fetch", "retrying", str(exc))
        raise self.retry(
            exc=exc, max_retries=5, countdown=10 * (2**self.request.retries)
        )

    # ── Step 3: 섹션 추출+검증 ──
    _log_stage(symbol, "section_extract", "started")
    start = time.time()
    try:
        sections = collector.extract_sections(html)
        from .validators import validate_extracted_sections

        full_text = collector._html_to_text(html)
        validated, warnings = validate_extracted_sections(sections, full_text)

        has_fail = any(w.startswith("FAIL:") for w in warnings)
        if has_fail:
            # fallback 시도
            fallback = collector.extract_sections_fallback(symbol)
            extraction_method = "regex"
            if fallback:
                fb_val, fb_warn = validate_extracted_sections(fallback, full_text)
                if not any(w.startswith("FAIL:") for w in fb_warn):
                    validated, warnings = fb_val, fb_warn
                    extraction_method = "edgartools_fallback"
            else:
                extraction_method = "regex"

            if any(w.startswith("FAIL:") for w in warnings):
                _log_stage(
                    symbol,
                    "section_extract",
                    "failed",
                    "; ".join(warnings),
                    time.time() - start,
                )
        else:
            extraction_method = "regex"

        non_empty = sum(1 for k in ["item_1", "item_1a", "item_7"] if validated.get(k))
        if non_empty == 0:
            status = "failed"
        elif non_empty < 3 or has_fail:
            status = "partial"
        else:
            status = "success"

        _log_stage(
            symbol,
            "section_extract",
            "success" if status != "failed" else "failed",
            f"sections={non_empty}/3, method={extraction_method}",
            time.time() - start,
        )

    except Exception as exc:
        _log_stage(symbol, "section_extract", "failed", str(exc))
        raise self.retry(
            exc=SectionExtractionError(str(exc)), max_retries=1, countdown=5
        )

    # ── Step 4: RawDocumentStore 저장 ──
    from packages.shared.stocks.models import Stock

    stock = Stock.objects.filter(symbol=symbol).first()
    if not stock:
        _log_stage(symbol, "section_extract", "failed", f"Stock {symbol} not in DB")
        return {"symbol": symbol, "status": "stock_not_found"}

    doc, created = RawDocumentStore.objects.update_or_create(
        accession_no=metadata["accession_no"],
        defaults={
            "symbol": stock,
            "filing_date": metadata["filing_date"],
            "fiscal_year": metadata["fiscal_year"],
            "final_link": metadata["final_link"],
            "item_1_text": validated.get("item_1", ""),
            "item_1a_text": validated.get("item_1a", ""),
            "item_7_text": validated.get("item_7", ""),
            "status": status,
            "extraction_method": extraction_method,
            "warnings": warnings,
        },
    )

    # ── Step 5: 추출 트리거 ──
    if status != "failed":
        extract_from_document.delay(doc.id, symbol)

    return {
        "symbol": symbol,
        "doc_id": doc.id,
        "status": status,
        "created": created,
    }


@shared_task(bind=True, max_retries=2, soft_time_limit=180, time_limit=240)
def extract_from_document(self, doc_id: int, symbol: str):
    """
    RawDocumentStore에서 Track A + Track B 추출.

    Track A 실패해도 Track B 시도 (Phase 2에서 구현).
    """
    from packages.shared.stocks.models import Stock

    from .extractor import GeminiExtractor
    from .models import RawDocumentStore
    from .normalizer import filter_paragraphs, normalize_section_all
    from .validator_track_a import (
        save_supply_chain_evidences,
        validate_supply_chain_result,
    )

    symbol = symbol.upper()

    try:
        doc = RawDocumentStore.objects.get(id=doc_id)
    except RawDocumentStore.DoesNotExist:
        logger.error(f"Document {doc_id} not found")
        return {"symbol": symbol, "error": "doc_not_found"}

    sections = {
        "item_1": doc.item_1_text,
        "item_1a": doc.item_1a_text,
        "item_7": doc.item_7_text,
    }

    result = {"symbol": symbol, "doc_id": doc_id}
    stock = None
    extractor = None

    # ── Track A: Supply Chain ──
    _log_stage(symbol, "track_a_extract", "started")
    start = time.time()
    try:
        combined = normalize_section_all(sections)
        paragraphs = filter_paragraphs(combined, max_paragraphs=15)

        if paragraphs:
            if not stock:
                stock = Stock.objects.filter(symbol=symbol).first()
            company_name = stock.stock_name if stock else symbol

            extractor = GeminiExtractor()
            raw = extractor.extract_supply_chain(symbol, company_name, paragraphs)
            validated = validate_supply_chain_result(raw, symbol)

            if validated:
                created = save_supply_chain_evidences(validated, doc, symbol)

                # Phase 1.5: 티커 매칭
                matched_count = 0
                if created:
                    _log_stage(symbol, "ticker_match", "started")
                    try:
                        from .ticker_matcher import TickerMatcher

                        matcher = TickerMatcher()
                        for evidence in created:
                            ticker, method = matcher.match_with_queue(
                                evidence.target_company_name, evidence, doc, symbol
                            )
                            if ticker:
                                matched_count += 1
                        _log_stage(
                            symbol,
                            "ticker_match",
                            "success",
                            f"matched={matched_count}/{len(created)}",
                        )
                    except Exception as match_err:
                        _log_stage(symbol, "ticker_match", "failed", str(match_err))

            result["track_a"] = {
                "raw": len(raw.get("relationships", [])),
                "validated": len(validated),
                "matched": matched_count if validated else 0,
            }
            _log_stage(
                symbol,
                "track_a_extract",
                "success",
                f"raw={len(raw.get('relationships', []))}, "
                f"validated={len(validated)}, matched={matched_count if validated else 0}",
                time.time() - start,
            )
        else:
            result["track_a"] = {"raw": 0, "validated": 0, "note": "no_paragraphs"}
            _log_stage(
                symbol,
                "track_a_extract",
                "skipped",
                "No relevant paragraphs",
                time.time() - start,
            )

    except Exception as exc:
        logger.error(f"{symbol} Track A failed: {exc}")
        _log_stage(symbol, "track_a_extract", "failed", str(exc), time.time() - start)
        result["track_a"] = {"error": str(exc)}
        # Track A 실패해도 Track B 시도

    # ── Track B: Business Model ──
    _log_stage(symbol, "track_b_extract", "started")
    start = time.time()
    try:
        from .keywords_track_b import filter_paragraphs_track_b
        from .validator_track_b import (
            save_business_model_snapshot,
            validate_business_model_result,
        )

        # Track B는 Item 1 위주
        item1_text = sections.get("item_1", "")
        if item1_text:
            from .normalizer import _clean_text

            cleaned = _clean_text(item1_text)
            bm_paragraphs = filter_paragraphs_track_b(cleaned, max_paragraphs=15)

            if bm_paragraphs:
                if not stock:
                    stock = Stock.objects.filter(symbol=symbol).first()
                company_name = stock.stock_name if stock else symbol

                if not extractor:
                    extractor = GeminiExtractor()
                raw_bm = extractor.extract_business_model(
                    symbol, company_name, bm_paragraphs
                )
                validated_bm = validate_business_model_result(raw_bm)
                save_business_model_snapshot(validated_bm, doc, symbol)

                result["track_b"] = {f: validated_bm[f]["value"] for f in validated_bm}
                _log_stage(
                    symbol,
                    "track_b_extract",
                    "success",
                    str(result["track_b"]),
                    time.time() - start,
                )
            else:
                result["track_b"] = {"status": "no_paragraphs"}
                _log_stage(
                    symbol,
                    "track_b_extract",
                    "skipped",
                    "No relevant paragraphs",
                    time.time() - start,
                )
        else:
            result["track_b"] = {"status": "no_item1"}
            _log_stage(
                symbol,
                "track_b_extract",
                "skipped",
                "No Item 1 text",
                time.time() - start,
            )

    except Exception as exc:
        logger.error(f"{symbol} Track B failed: {exc}")
        _log_stage(symbol, "track_b_extract", "failed", str(exc), time.time() - start)
        result["track_b"] = {"error": str(exc)}

    return result


@shared_task(name="sec-seed-relations-to-chainsight", max_retries=1)
def seed_relations_to_chainsight():
    """매칭된 SupplyChainEvidence → RelationConfidence 레코드 생성."""
    from apps.chain_sight.models import RelationConfidence
    from apps.chain_sight.services.upward_learning import HIGHSCORE_THRESHOLD
    from apps.chain_sight.utils import normalize_pair

    from .models import SupplyChainEvidence as SCE

    matched = SCE.objects.filter(target_company__isnull=False)
    if not matched.exists():
        logger.info("seed_relations_to_chainsight: no matched evidence")
        return {"created": 0, "updated": 0}

    created, updated = 0, 0
    for ev in matched:
        rel_type = ev.relationship_type

        # CUSTOMER_OF → SUPPLIES_TO로 정규화 (방향 반전)
        if rel_type == "CUSTOMER_OF":
            sym_a, sym_b = ev.target_company_id, ev.source_company_id
            rel_type = "SUPPLIES_TO"
            direction = "a→b"
        elif rel_type == "COMPETES_WITH":
            sym_a, sym_b = normalize_pair(ev.source_company_id, ev.target_company_id)
            direction = "both"
        elif rel_type in ("SUPPLIES_TO", "DEPENDS_ON", "PARTNER_WITH"):
            sym_a, sym_b = ev.source_company_id, ev.target_company_id
            direction = "a→b"
        else:
            continue

        score_map = {"high": 85, "medium": 60, "low": 35}
        score = score_map.get(ev.confidence_grade, 60)

        # T-3b ⓓ-2 B-1: seed의 relation_status 권위 제거 (flap 소멸).
        #   - 기존 pair(update 경로): relation_status 무접촉 — score/관측치/evidence만 갱신.
        #     (하향 권위 = decay 전담, 상향 권위 = upward 엔진. seed가 매 틱 status를 다시
        #      써서 upward가 올린 confirmed를 probable로 되돌리던 flap을 근절.)
        #   - 신규 pair(create 경로): 초기 status 설정은 생성자의 정당 권한 → create_defaults로 유지.
        #     ≥85 규칙은 upward 엔진의 HIGHSCORE_THRESHOLD 단일 출처 참조(중복 정의 금지).
        common = {
            "relation_category": "truth",
            "canonical_direction": direction,
            "truth_score": score,
            "evidence_tier_best": 1,
            "has_supply_chain_source": True,
            "relation_basis_summary": f"SEC 10-K: {ev.evidence_text[:100]}",
            # audit P0 #9: synced_to_neo4j 제거. update_or_create의 save()가 neo4j_dirty=True 자동.
        }
        obj, is_new = RelationConfidence.objects.update_or_create(
            symbol_a=sym_a,
            symbol_b=sym_b,
            relation_type=rel_type,
            defaults=common,  # 기존 pair: status 무접촉
            create_defaults={
                **common,
                "relation_status": (
                    "confirmed" if score >= HIGHSCORE_THRESHOLD else "probable"
                ),
            },
        )
        if is_new:
            created += 1
        else:
            updated += 1

    result = {"created": created, "updated": updated}
    logger.info(f"seed_relations_to_chainsight: {result}")
    return result


@shared_task(bind=True, max_retries=1, soft_time_limit=300, time_limit=360)
def sync_dirty_to_neo4j(self):
    """
    SEC-PR-9: dirty evidence → Neo4j edge 동기화.

    2-Phase + select_for_update(skip_locked=True):
      Phase A: PG transaction 안에서 dirty row lock + dict 복사 (최대 500건)
      Phase B: Neo4j session으로 동기화 (DELETE + CREATE dynamic type)
      Phase C: 성공한 건 neo4j_dirty=False + neo4j_synced_at

    ⚠️ RELATED_TO 고정 type 사용 금지. dynamic type만.
    ⚠️ MERGE 사용 금지. DELETE + CREATE 패턴만.
    ⚠️ known_types에 'RELATED_TO' 포함 (레거시 정리).
    ⚠️ Phase 1에서 이 함수가 Neo4j SOLE WRITER.
    """
    from django.db import transaction

    from .models import SupplyChainEvidence

    BATCH_SIZE = 500
    KNOWN_TYPES = [
        "SUPPLIES_TO",
        "CUSTOMER_OF",
        "PARTNER_WITH",
        "DEPENDS_ON",
        "COMPETES_WITH",
        "RELATED_TO",
    ]

    # ── Phase A: PG lock + dict 복사 ──
    with transaction.atomic():
        dirty_qs = (
            SupplyChainEvidence.objects.filter(
                neo4j_dirty=True, target_company__isnull=False
            )
            .select_related("source_company", "target_company", "source_document")
            .select_for_update(skip_locked=True)[:BATCH_SIZE]
        )

        rows = []
        for ev in dirty_qs:
            rows.append(
                {
                    "id": ev.id,
                    "source_ticker": ev.source_company_id,
                    "target_ticker": ev.target_company_id,
                    "rel_type": ev.relationship_type,
                    "confidence_grade": ev.confidence_grade,
                    "evidence_text": ev.evidence_text[:200],
                    "prompt_version": ev.prompt_version,
                    "source": "sec_10k",
                    "accession_no": ev.source_document.accession_no
                    if ev.source_document
                    else "",
                }
            )

    if not rows:
        logger.info("sync_dirty_to_neo4j: no dirty rows")
        return {"synced": 0}

    # ── Phase B: Neo4j 동기화 ──
    from apps.chain_sight.graph import get_graph_repository

    try:
        repo = get_graph_repository()
        synced_ids = []

        for row in rows:
            source = row["source_ticker"]
            target = row["target_ticker"]
            rel_type = row["rel_type"]

            # DELETE 기존 SEC-origin edge (known_types 전체)
            for kt in KNOWN_TYPES:
                delete_query = f"""
                MATCH (a:Stock {{ticker: $source}})-[r:{kt}]->(b:Stock {{ticker: $target}})
                WHERE r.source = 'sec_10k'
                DELETE r
                """
                try:
                    repo.run_query(
                        delete_query,
                        {
                            "source": source,
                            "target": target,
                        },
                    )
                except Exception:
                    pass  # edge가 없으면 무시

            # CREATE 새 edge (dynamic type — f-string으로 type 삽입)
            create_query = f"""
            MATCH (a:Stock {{ticker: $source}})
            MATCH (b:Stock {{ticker: $target}})
            CREATE (a)-[r:{rel_type} {{
                confidence_grade: $grade,
                evidence_text: $evidence,
                prompt_version: $prompt_version,
                source: 'sec_10k',
                accession_no: $accession_no,
                synced_at: datetime()
            }}]->(b)
            """
            try:
                repo.run_query(
                    create_query,
                    {
                        "source": source,
                        "target": target,
                        "grade": row["confidence_grade"],
                        "evidence": row["evidence_text"],
                        "prompt_version": row["prompt_version"],
                        "accession_no": row["accession_no"],
                    },
                )
                synced_ids.append(row["id"])
            except Exception as e:
                logger.warning(
                    f"Neo4j sync failed: {source}→{target} ({rel_type}): {e}"
                )

        # ── Phase C: PG 업데이트 ──
        if synced_ids:
            SupplyChainEvidence.objects.filter(id__in=synced_ids).update(
                neo4j_dirty=False,
                neo4j_synced_at=timezone.now(),
            )

        logger.info(f"sync_dirty_to_neo4j: {len(synced_ids)}/{len(rows)} synced")
        return {"synced": len(synced_ids), "total": len(rows)}

    except Exception as e:
        logger.error(f"sync_dirty_to_neo4j error: {e}")
        raise


def _to_grade(confidence: float) -> str:
    """confidence → grade (sync에서 사용)."""
    if confidence >= 0.8:
        return "high"
    elif confidence >= 0.6:
        return "medium"
    return "low"


@shared_task(bind=True, max_retries=1, soft_time_limit=600, time_limit=660)
def check_new_filings(self):
    """
    SEC-PR-15: SEC EDGAR에서 S&P 500 신규 10-K filing 감지.

    기존 RawDocumentStore에 없는 새 filing을 찾아 수집 트리거.
    """
    from .collector import SECFilingCollector
    from .models import RawDocumentStore
    from .sp500 import get_sp500_symbols

    collector = SECFilingCollector()
    symbols = get_sp500_symbols()
    new_count = 0

    for symbol in symbols:
        try:
            metadata = collector.get_filing_metadata(symbol)
            if not metadata:
                continue

            accession = metadata["accession_no"]
            exists = RawDocumentStore.objects.filter(accession_no=accession).exists()
            if not exists:
                collect_and_extract.delay(symbol)
                new_count += 1
                logger.info(f"New filing detected: {symbol} ({accession})")

        except Exception as e:
            logger.debug(f"check_new_filings {symbol}: {e}")
            continue

    logger.info(f"check_new_filings: {new_count} new filings triggered")
    return {"new_filings": new_count, "checked": len(symbols)}


@shared_task(bind=True, max_retries=1, soft_time_limit=120, time_limit=180)
def generate_intelligence_report(self, hours_back: int = 24):
    """SEC-PR-17: Intelligence 리포트 생성 task."""
    from .intelligence import PipelineIntelligenceReporter

    reporter = PipelineIntelligenceReporter()
    return reporter.generate_report(hours_back=hours_back)


@shared_task(bind=True, max_retries=0, soft_time_limit=7200, time_limit=7260)
def run_batch_and_report(self, symbols: list = None):
    """
    SEC-PR-17: 배치 수집 → 후처리 체인.

    symbols가 None이면 S&P 500 전체.
    chord 대신 순차 실행 (1인 개발 단순성).
    """
    from .quality_checks import run_post_batch_quality_checks
    from .sp500 import get_sp500_symbols

    if symbols is None:
        symbols = get_sp500_symbols()

    # Phase 1: 수집 + 추출
    results = []
    for symbol in symbols:
        try:
            r = collect_and_extract(symbol)
            if r.get("doc_id") and r.get("status") != "failed":
                extract_from_document(r["doc_id"], symbol)
            results.append({"symbol": symbol, "status": r.get("status", "unknown")})
        except Exception as e:
            results.append({"symbol": symbol, "status": "error", "error": str(e)})
            logger.error(f"Batch {symbol}: {e}")

    # Phase 2: 후처리
    sync_result = sync_dirty_to_neo4j()
    alerts = run_post_batch_quality_checks(hours_back=24)

    # Phase 3: Intelligence 리포트
    report_result = generate_intelligence_report(hours_back=24)

    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] in ("failed", "error"))

    logger.info(
        f"run_batch_and_report: {success} success, {failed} failed, "
        f"{len(alerts)} alerts, report={report_result}"
    )
    return {
        "total": len(symbols),
        "success": success,
        "failed": failed,
        "sync": sync_result,
        "alerts": alerts,
        "report": report_result,
    }


# ── Celery Beat 설정 (주석) ──
# 'sync-sec-dirty-neo4j': {
#     'task': 'sec_pipeline.tasks.sync_dirty_to_neo4j',
#     'schedule': crontab(minute='*/5'),
# },
# 'check-new-filings': {
#     'task': 'sec_pipeline.tasks.check_new_filings',
#     'schedule': crontab(day_of_month='1', hour='6', minute='0'),
# },


def _log_stage(
    symbol: str, stage: str, status: str, detail: str = "", duration: float = None
):
    """FilingProcessLog 기록."""
    from .models import FilingProcessLog

    FilingProcessLog.objects.create(
        symbol=symbol,
        stage=stage,
        status=status,
        detail=detail[:1000] if detail else "",
        duration_seconds=round(duration, 2) if duration else None,
    )
