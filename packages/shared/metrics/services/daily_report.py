"""
Daily Report Service — 매일 아침 메일 발송용 메트릭 집계

3개 도메인:
  1. Graph (Neo4j 노드/관계 양적/퀄리티)
  2. News (뉴스 수집/분석/커버리지)
  3. Improvement Suggestions (8 카테고리 개선 방향)

스냅샷은 ~/stock-vis-nightly/daily-snapshots/{date}.json 으로 저장하여
다음날 비교 기준으로 활용.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path.home() / "stock-vis-nightly" / "daily-snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _load_previous_snapshot(target_date: date) -> Optional[Dict[str, Any]]:
    """target_date 이전 가장 최근 스냅샷을 반환."""
    candidates = sorted(SNAPSHOT_DIR.glob("*.json"), reverse=True)
    for path in candidates:
        try:
            d = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < target_date:
            try:
                return json.loads(path.read_text())
            except Exception as e:
                logger.warning(f"snapshot load fail {path}: {e}")
    return None


def _save_snapshot(today: date, payload: Dict[str, Any]) -> Path:
    path = SNAPSHOT_DIR / f"{today.isoformat()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return path


def _delta(curr: int, prev: Optional[int]) -> str:
    if prev is None:
        return f"{curr} (신규)"
    diff = curr - prev
    arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "·")
    return f"{curr} ({arrow}{abs(diff)})"


# ────────────────────────────────────────────────────────────
# Graph metrics (Neo4j)
# ────────────────────────────────────────────────────────────


def _neo4j_session():
    from neo4j import GraphDatabase

    drv = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )
    return drv


def collect_graph_metrics() -> Dict[str, Any]:
    """Neo4j 라벨/관계 카운트 + 퀄리티 메트릭."""
    drv = _neo4j_session()
    try:
        with drv.session() as s:
            # 라벨별
            labels = {}
            for r in s.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt"):
                labels[r["label"]] = r["cnt"]

            # 관계 타입별
            rels = {}
            for r in s.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt"):
                rels[r["type"]] = r["cnt"]

            # Stock 속성 완전성
            attr_completeness = {}
            for prop in [
                "sector",
                "industry",
                "market_cap",
                "growth_stage",
                "capital_type",
                "business_model_type",
                "overall_grade",
                "theme_tags",
            ]:
                rec = s.run(
                    f"MATCH (n:Stock) "
                    f"RETURN count(n) AS total, "
                    f"sum(CASE WHEN n.{prop} IS NULL THEN 0 ELSE 1 END) AS filled"
                ).single()
                total = rec["total"] or 1
                attr_completeness[prop] = round(rec["filled"] * 100 / total, 1)

            # 외로운 노드 (관계 0개)
            lonely = s.run(
                "MATCH (n:Stock) WHERE NOT (n)-[]-() RETURN count(n) AS cnt"
            ).single()["cnt"]

            # 종목당 평균 관계 수
            avg_rels = s.run(
                "MATCH (n:Stock) OPTIONAL MATCH (n)-[r]-() "
                "WITH n, count(r) AS cnt RETURN avg(cnt) AS avg_rels"
            ).single()
            avg_rels_val = avg_rels["avg_rels"] if avg_rels else 0

            # 동적 관계 신뢰도 분포 (truth_score)
            ts_dist = s.run(
                "MATCH ()-[r]-() WHERE r.truth_score IS NOT NULL "
                "RETURN "
                "  sum(CASE WHEN r.truth_score >= 70 THEN 1 ELSE 0 END) AS high, "
                "  sum(CASE WHEN r.truth_score >= 40 AND r.truth_score < 70 THEN 1 ELSE 0 END) AS mid, "
                "  sum(CASE WHEN r.truth_score < 40 THEN 1 ELSE 0 END) AS low"
            ).single()

    finally:
        drv.close()

    return {
        "labels": labels,
        "relations": rels,
        "total_nodes": sum(labels.values()),
        "total_relations": sum(rels.values()),
        "stock_attr_completeness_pct": attr_completeness,
        "lonely_stocks": lonely,
        "avg_relations_per_stock": round(float(avg_rels_val or 0), 1),
        "truth_score_dist": {
            "high(70+)": ts_dist["high"] if ts_dist else 0,
            "mid(40-69)": ts_dist["mid"] if ts_dist else 0,
            "low(<40)": ts_dist["low"] if ts_dist else 0,
        },
    }


# ────────────────────────────────────────────────────────────
# News metrics (PostgreSQL)
# ────────────────────────────────────────────────────────────


def collect_news_metrics(today: date) -> Dict[str, Any]:
    """뉴스 일일 통계 + 커버리지."""
    from news.models import NewsArticle, NewsEntity
    from packages.shared.stocks.models import Stock

    cutoff_24h = timezone.now() - timedelta(hours=24)

    total = NewsArticle.objects.count()
    today_count = NewsArticle.objects.filter(created_at__gte=cutoff_24h).count()
    today_llm_analyzed = NewsArticle.objects.filter(
        created_at__gte=cutoff_24h, llm_analyzed=True
    ).count()
    today_llm_pending = today_count - today_llm_analyzed

    # 감성 분포 (24h 내) — NewsEntity.news 가 FK 명, sentiment_score 사용
    sentiment_dist = {"positive": 0, "negative": 0, "neutral": 0}
    qs = NewsEntity.objects.filter(news__created_at__gte=cutoff_24h)
    for e in qs.only("sentiment_score"):
        s = e.sentiment_score or 0
        if s > 0.2:
            sentiment_dist["positive"] += 1
        elif s < -0.2:
            sentiment_dist["negative"] += 1
        else:
            sentiment_dist["neutral"] += 1

    # 24h 내 entity 의 symbol 리스트 (NewsEntity.symbol 은 CharField)
    entity_symbols = list(
        NewsEntity.objects.filter(news__created_at__gte=cutoff_24h).values_list(
            "symbol", flat=True
        )
    )
    symbol_to_sector = dict(
        Stock.objects.filter(symbol__in=set(entity_symbols)).values_list(
            "symbol", "sector"
        )
    )

    # 섹터별 24h 뉴스 분포 (수동 집계)
    sector_news: Dict[str, int] = {}
    for sym in entity_symbols:
        sec = symbol_to_sector.get(sym) or "(unknown/non-stock)"
        sector_news[sec] = sector_news.get(sec, 0) + 1
    sector_news = dict(sorted(sector_news.items(), key=lambda kv: -kv[1]))

    # 종목 커버리지: 535 Stock 중 24h 뉴스 없는 종목
    symbols_with_news = set(entity_symbols)
    all_stocks = set(Stock.objects.values_list("symbol", flat=True))
    no_news_count = len(all_stocks - symbols_with_news)
    covered_count = len(all_stocks & symbols_with_news)

    # importance_score 분포 (24h 내)
    imp_qs = NewsArticle.objects.filter(
        created_at__gte=cutoff_24h, importance_score__isnull=False
    )
    imp_dist = {
        "high(0.7+)": imp_qs.filter(importance_score__gte=0.7).count(),
        "mid(0.4-0.7)": imp_qs.filter(
            importance_score__gte=0.4, importance_score__lt=0.7
        ).count(),
        "low(<0.4)": imp_qs.filter(importance_score__lt=0.4).count(),
    }

    return {
        "total_articles": total,
        "today_new": today_count,
        "today_llm_analyzed": today_llm_analyzed,
        "today_llm_pending": today_llm_pending,
        "today_llm_analyzed_pct": (
            round(today_llm_analyzed * 100 / today_count, 1) if today_count else 0
        ),
        "sentiment_24h": sentiment_dist,
        "sector_distribution_24h": sector_news,
        "stocks_no_news_count": no_news_count,
        "stocks_covered_count": covered_count,
        "importance_dist_24h": imp_dist,
    }


# ────────────────────────────────────────────────────────────
# Coverage gaps & New node candidates
# ────────────────────────────────────────────────────────────


def collect_coverage_gaps() -> Dict[str, Any]:
    """현재 그래프 외에 새로 추가할 수 있는 노드 후보."""
    from chainsight.models import CompanyChainProfile
    from packages.shared.stocks.models import Stock
    from sec_pipeline.models import UnmatchedCompanyQueue

    drv = _neo4j_session()
    try:
        with drv.session() as s:
            neo4j_stock_tickers = set(
                r["t"] for r in s.run("MATCH (n:Stock) RETURN n.ticker AS t")
            )
            neo4j_industries = set(
                r["n"] for r in s.run("MATCH (i:Industry) RETURN i.name AS n")
            )
            neo4j_sectors = set(
                r["n"] for r in s.run("MATCH (s:Sector) RETURN s.name AS n")
            )
    finally:
        drv.close()

    pg_stock_symbols = set(Stock.objects.values_list("symbol", flat=True))
    pg_industries = set(
        i.upper()
        for i in Stock.objects.exclude(industry__isnull=True)
        .exclude(industry="")
        .values_list("industry", flat=True)
        .distinct()
    )
    pg_sectors = set(
        sec.upper()
        for sec in Stock.objects.exclude(sector__isnull=True)
        .exclude(sector="")
        .values_list("sector", flat=True)
        .distinct()
    )

    # 미반영 Stock
    missing_stocks = sorted(pg_stock_symbols - neo4j_stock_tickers)[:30]

    # 미반영 Industry
    missing_industries = sorted(pg_industries - neo4j_industries)[:20]

    # 미반영 Sector
    missing_sectors = sorted(pg_sectors - neo4j_sectors)[:10]

    # SEC UnmatchedCompanyQueue 미매핑 추가 후보
    unmatched_pending = UnmatchedCompanyQueue.objects.filter(status="pending")
    unmatched_count = unmatched_pending.count()
    unmatched_samples = [
        {
            "raw_name": q.raw_company_name[:60],
            "occurrence": q.occurrence_count,
            "top_fuzzy": (
                q.fuzzy_candidates[0]
                if q.fuzzy_candidates and isinstance(q.fuzzy_candidates, list)
                else None
            ),
        }
        for q in unmatched_pending.order_by("-occurrence_count")[:10]
    ]

    # CompanyChainProfile 누락 종목
    profiled_symbols = set(
        CompanyChainProfile.objects.values_list("symbol_id", flat=True)
    )
    missing_profiles = sorted(pg_stock_symbols - profiled_symbols)[:20]

    return {
        "missing_stocks_count": len(pg_stock_symbols - neo4j_stock_tickers),
        "missing_stocks_sample": missing_stocks,
        "missing_industries_count": len(pg_industries - neo4j_industries),
        "missing_industries_sample": missing_industries,
        "missing_sectors_count": len(pg_sectors - neo4j_sectors),
        "missing_sectors_sample": missing_sectors,
        "unmatched_companies_pending": unmatched_count,
        "unmatched_top_candidates": unmatched_samples,
        "missing_profiles_count": len(pg_stock_symbols - profiled_symbols),
        "missing_profiles_sample": missing_profiles,
    }


# ────────────────────────────────────────────────────────────
# System health
# ────────────────────────────────────────────────────────────


def collect_nightly_summary() -> Dict[str, Any]:
    """야간 자동화 시스템(com.stockvis.nightly) 최근 실행 요약.

    참조:
      - ~/stock-vis-nightly/logs/launchd.log (전체 실행 로그)
      - ~/stock-vis-nightly/logs/tier3_audits_{ts}.log (보고서별 상세)
      - docs/nightly_auto_system/reports/{월}/{일}/*.md (생성된 보고서)
    """
    nightly_dir = Path.home() / "stock-vis-nightly"
    reports_dir = Path(
        "/Users/byeongjinjeong/Desktop/stock_vis/docs/nightly_auto_system/reports"
    )

    result: Dict[str, Any] = {
        "available": False,
        "last_run_ended_at": None,
        "duration_min": None,
        "branch": None,
        "reports": [],
        "report_count": 0,
        "total_lines": 0,
        "errors": [],
    }

    launchd_log = nightly_dir / "logs" / "launchd.log"
    if not launchd_log.exists():
        return result

    try:
        # tail 마지막 8KB만 읽기 (효율)
        with launchd_log.open("rb") as f:
            f.seek(0, 2)  # end
            size = f.tell()
            f.seek(max(0, size - 12000))
            tail = f.read().decode("utf-8", errors="replace")

        # 마지막 실행의 시작/완료 시각
        lines = tail.splitlines()
        end_match = None
        branch = None
        report_files: List[Dict[str, Any]] = []

        for line in lines:
            # 보고서 완료 라인: ✅ 완료 — /path (NNN줄)
            if "✅ 완료" in line:
                # 시간과 경로, 줄 수 파싱
                import re

                m = re.match(r"\[(\d+:\d+:\d+)\]\s+✅ 완료 — (\S+)\s+\((\d+)줄\)", line)
                if m:
                    report_files.append(
                        {
                            "time": m.group(1),
                            "path": m.group(2),
                            "lines": int(m.group(3)),
                            "name": Path(m.group(2)).stem,
                        }
                    )
                    end_match = m.group(1)
            if "현재 브랜치:" in line:
                branch = line.split("현재 브랜치:")[-1].strip()
            if "❌" in line or "FAILED" in line or "ERROR" in line:
                # 에러/실패 라인 캡처
                if len(result["errors"]) < 10:
                    result["errors"].append(line.strip()[:200])

        if report_files:
            result["available"] = True
            result["last_run_ended_at"] = end_match
            result["branch"] = branch
            result["reports"] = report_files
            result["report_count"] = len(report_files)
            result["total_lines"] = sum(r["lines"] for r in report_files)

        # 가장 최근 보고서 디렉토리 (어제 작성)에서 추가 메타
        yesterday = date.today() - timedelta(days=1)
        for d in [yesterday, date.today()]:
            cand_dir = reports_dir / f"{d.month}월" / f"{d.day}일"
            if cand_dir.exists():
                result["report_dir"] = str(cand_dir).replace(str(Path.home()), "~")
                # 보고서 첫 헤딩 미리보기
                for r in result["reports"]:
                    rp = Path(r["path"])
                    if rp.exists():
                        try:
                            first_lines = rp.read_text(
                                encoding="utf-8", errors="replace"
                            ).splitlines()[:8]
                            # 첫 # 또는 ## 라인 찾기
                            preview = next(
                                (
                                    ln.lstrip("# ").strip()
                                    for ln in first_lines
                                    if ln.startswith("#")
                                ),
                                first_lines[0][:80] if first_lines else "",
                            )
                            r["preview"] = preview[:120]
                        except Exception:
                            r["preview"] = ""
                break

    except Exception as e:
        logger.warning(f"collect_nightly_summary failed: {e}")
        result["errors"].append(f"parse_error: {e}")

    return result


def collect_llm_usage() -> Dict[str, Any]:
    """LLM (Gemini 2.5 Flash) 24h 사용량 + 비용 추정.

    Gemini 2.5 Flash paid tier (2026-05 기준):
      - input: $0.075 / M tokens
      - output: $0.30 / M tokens

    실측 토큰 카운트가 없으므로 평균치로 추정:
      - SEC track_a/track_b: input ~8K, output ~1K tokens/call
      - News LLM 분석: input ~2K, output ~500 tokens/article
    """
    from news.models import NewsArticle
    from sec_pipeline.models import FilingProcessLog

    cutoff = timezone.now() - timedelta(hours=24)

    # SEC LLM 호출 (track_a + track_b)
    sec_calls = FilingProcessLog.objects.filter(
        started_at__gte=cutoff,
        stage__in=["track_a_extract", "track_b_extract"],
        status="success",
    ).count()
    sec_input_tokens = sec_calls * 8000
    sec_output_tokens = sec_calls * 1000

    # News LLM 호출 (오늘 llm_analyzed=True된 기사)
    news_calls = (
        NewsArticle.objects.filter(
            llm_analyzed_at__gte=cutoff,
            llm_analyzed=True,
        ).count()
        if hasattr(NewsArticle, "llm_analyzed_at")
        else (
            NewsArticle.objects.filter(
                updated_at__gte=cutoff, llm_analyzed=True
            ).count()
            if hasattr(NewsArticle, "updated_at")
            else 0
        )
    )
    news_input_tokens = news_calls * 2000
    news_output_tokens = news_calls * 500

    total_input = sec_input_tokens + news_input_tokens
    total_output = sec_output_tokens + news_output_tokens

    # 비용 (USD)
    INPUT_PRICE = 0.075 / 1_000_000  # per token
    OUTPUT_PRICE = 0.30 / 1_000_000
    cost_input = total_input * INPUT_PRICE
    cost_output = total_output * OUTPUT_PRICE
    cost_total = cost_input + cost_output

    return {
        "sec_llm_calls_24h": sec_calls,
        "news_llm_calls_24h": news_calls,
        "total_calls_24h": sec_calls + news_calls,
        "est_input_tokens_24h": total_input,
        "est_output_tokens_24h": total_output,
        "est_cost_usd_24h": round(cost_total, 4),
        "est_monthly_cost_usd": round(cost_total * 30, 2),
        "breakdown_usd": {
            "input": round(cost_input, 4),
            "output": round(cost_output, 4),
        },
        "model": "gemini-2.5-flash (paid tier)",
        "note": "토큰 평균치 기반 추정 — 실측 시 정밀화 필요",
    }


def collect_system_health() -> Dict[str, Any]:
    """Celery + Neo4j + SEC 파이프라인 헬스."""
    import subprocess

    from sec_pipeline.models import (
        FilingProcessLog,
        RawDocumentStore,
        SupplyChainEvidence,
    )

    # Celery 워커 살아있는지
    try:
        out = subprocess.run(
            ["pgrep", "-f", "celery -A config worker"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        celery_worker_alive = bool(out.stdout.strip())
        celery_worker_pids = (
            out.stdout.strip().split("\n") if celery_worker_alive else []
        )
    except Exception:
        celery_worker_alive = False
        celery_worker_pids = []

    try:
        out = subprocess.run(
            ["pgrep", "-f", "celery -A config beat"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        celery_beat_alive = bool(out.stdout.strip())
    except Exception:
        celery_beat_alive = False

    # Neo4j 응답성
    try:
        drv = _neo4j_session()
        with drv.session() as s:
            s.run("RETURN 1").single()
        neo4j_alive = True
        drv.close()
    except Exception as e:
        neo4j_alive = False

    # SEC 파이프라인 최근 24h 처리량
    cutoff_24h = timezone.now() - timedelta(hours=24)
    sec_24h_processed = (
        FilingProcessLog.objects.filter(
            started_at__gte=cutoff_24h, stage="track_a_extract", status="success"
        )
        .values("symbol")
        .distinct()
        .count()
    )
    sec_total_filings = RawDocumentStore.objects.count()
    sec_total_evidence = SupplyChainEvidence.objects.count()

    return {
        "celery_worker_alive": celery_worker_alive,
        "celery_worker_count": len(celery_worker_pids),
        "celery_beat_alive": celery_beat_alive,
        "neo4j_alive": neo4j_alive,
        "sec_24h_processed_filings": sec_24h_processed,
        "sec_total_filings": sec_total_filings,
        "sec_total_evidence": sec_total_evidence,
    }


# ────────────────────────────────────────────────────────────
# Improvement suggestions (8 카테고리)
# ────────────────────────────────────────────────────────────


def collect_suggestions(
    graph: Dict, news: Dict, gaps: Dict, health: Dict
) -> List[Dict]:
    """8 카테고리 개선 제안. 각각 severity (🟢/🟡/🔴) + actionable text."""
    suggestions = []

    # 1. Coverage Gap
    if gaps["missing_stocks_count"] > 0:
        suggestions.append(
            {
                "category": "1. 커버리지 갭",
                "severity": "🟡",
                "issue": f"PostgreSQL Stock 중 Neo4j 미반영 {gaps['missing_stocks_count']}건",
                "action": "seed_neo4j_graph 재실행 또는 sync_profiles_to_neo4j 트리거",
                "samples": gaps["missing_stocks_sample"][:5],
            }
        )
    if gaps["missing_industries_count"] > 0:
        suggestions.append(
            {
                "category": "1. 커버리지 갭",
                "severity": "🟡",
                "issue": f"Industry 노드 미반영 {gaps['missing_industries_count']}건",
                "action": "BELONGS_TO_INDUSTRY Cypher 일괄 재생성 필요",
                "samples": gaps["missing_industries_sample"][:5],
            }
        )
    if gaps["missing_sectors_count"] == 0 and gaps["missing_industries_count"] == 0:
        suggestions.append(
            {
                "category": "1. 커버리지 갭",
                "severity": "🟢",
                "issue": "Stock/Sector/Industry 커버리지 정상",
                "action": "유지",
                "samples": [],
            }
        )

    # 2. Relation Quality
    ts = graph.get("truth_score_dist", {})
    high = ts.get("high(70+)", 0)
    low = ts.get("low(<40)", 0)
    total_ts = sum(ts.values()) or 1
    low_pct = round(low * 100 / total_ts, 1)
    if low_pct > 30:
        suggestions.append(
            {
                "category": "2. 관계 퀄리티",
                "severity": "🟡",
                "issue": f"truth_score < 40 관계가 {low_pct}% — stale 또는 weak 관계 다수",
                "action": "chainsight check_stale_and_decay 트리거",
                "samples": [],
            }
        )
    else:
        suggestions.append(
            {
                "category": "2. 관계 퀄리티",
                "severity": "🟢",
                "issue": f"truth_score 분포 양호 (high {high}, mid {ts.get('mid(40-69)', 0)}, low {low})",
                "action": "유지",
                "samples": [],
            }
        )

    # 3. Relation Balance
    rels = graph.get("relations", {})
    peer = rels.get("PEER_OF", 0)
    supplies = rels.get("SUPPLIES_TO", 0)
    if peer > 0 and supplies < peer * 0.05:
        suggestions.append(
            {
                "category": "3. 관계 균형",
                "severity": "🟡",
                "issue": f"SUPPLIES_TO {supplies}개 vs PEER_OF {peer}개 — 공급망 관계 부족",
                "action": "SEC 10-K backfill 진행도 확인, UnmatchedCompanyQueue 추가 alias 매핑",
                "samples": [],
            }
        )

    # 4. Attribute Completeness
    attrs = graph.get("stock_attr_completeness_pct", {})
    weak_attrs = [(k, v) for k, v in attrs.items() if v < 70]
    if weak_attrs:
        suggestions.append(
            {
                "category": "4. 노드 속성 완전성",
                "severity": "🟡",
                "issue": f"Stock 속성 채움률 70% 미만: "
                + ", ".join(f"{k}={v}%" for k, v in weak_attrs[:5]),
                "action": "calculate_all_profiles 트리거 또는 누락 속성 backfill",
                "samples": [],
            }
        )
    else:
        suggestions.append(
            {
                "category": "4. 노드 속성 완전성",
                "severity": "🟢",
                "issue": "주요 속성 모두 70% 이상 채움",
                "action": "유지",
                "samples": [],
            }
        )

    # 5. Freshness
    if health["sec_24h_processed_filings"] == 0 and gaps["missing_stocks_count"] == 0:
        suggestions.append(
            {
                "category": "5. 데이터 신선도",
                "severity": "🟢",
                "issue": "SEC 신규 filing 처리 없음 (정상 — 분기 공시 외 없음)",
                "action": "유지",
                "samples": [],
            }
        )

    # 6. LLM Quality
    if news["today_new"] > 0 and news["today_llm_analyzed_pct"] < 80:
        suggestions.append(
            {
                "category": "6. LLM 추출 품질",
                "severity": "🟡",
                "issue": f"오늘 신규 뉴스 LLM 분석률 {news['today_llm_analyzed_pct']}% (pending {news['today_llm_pending']}건)",
                "action": "Gemini paid tier quota 확인, retry batch 트리거",
                "samples": [],
            }
        )
    elif news["today_new"] > 0:
        suggestions.append(
            {
                "category": "6. LLM 추출 품질",
                "severity": "🟢",
                "issue": f"LLM 분석률 {news['today_llm_analyzed_pct']}% (오늘 {news['today_new']}건)",
                "action": "유지",
                "samples": [],
            }
        )

    # 7. Graph Structure
    lonely = graph.get("lonely_stocks", 0)
    if lonely > 0:
        suggestions.append(
            {
                "category": "7. 구조 분석",
                "severity": "🟡",
                "issue": f"고립 Stock 노드 {lonely}개 (관계 0)",
                "action": "calculate_price_co_movement + update_relation_confidence 트리거로 관계 보강",
                "samples": [],
            }
        )
    else:
        suggestions.append(
            {
                "category": "7. 구조 분석",
                "severity": "🟢",
                "issue": f"모든 Stock 노드가 1+ 관계 보유 (avg {graph.get('avg_relations_per_stock', 0)}개)",
                "action": "유지",
                "samples": [],
            }
        )

    # 8. News Coverage
    no_news = news.get("stocks_no_news_count", 0)
    covered = news.get("stocks_covered_count", 0)
    total_stocks = no_news + covered
    if total_stocks > 0:
        coverage_pct = round(covered * 100 / total_stocks, 1)
        if coverage_pct < 30:
            sev, act = (
                "🟡",
                "Finnhub/MarketAux 종목별 수집 확장 또는 sector 단위 뉴스 broadcast",
            )
        else:
            sev, act = "🟢", "유지"
        suggestions.append(
            {
                "category": "8. 뉴스 커버리지",
                "severity": sev,
                "issue": f"24h 뉴스 커버 종목 {covered}/{total_stocks} = {coverage_pct}%",
                "action": act,
                "samples": [],
            }
        )

    # 9. System Health
    if (
        not health["celery_worker_alive"]
        or not health["celery_beat_alive"]
        or not health["neo4j_alive"]
    ):
        suggestions.append(
            {
                "category": "9. 시스템 헬스",
                "severity": "🔴",
                "issue": (
                    f"worker={'OK' if health['celery_worker_alive'] else 'DOWN'}, "
                    f"beat={'OK' if health['celery_beat_alive'] else 'DOWN'}, "
                    f"neo4j={'OK' if health['neo4j_alive'] else 'DOWN'}"
                ),
                "action": "즉시 launchctl kickstart 또는 docker restart 필요",
                "samples": [],
            }
        )
    else:
        suggestions.append(
            {
                "category": "9. 시스템 헬스",
                "severity": "🟢",
                "issue": f"worker {health['celery_worker_count']}개, beat OK, neo4j OK",
                "action": "유지",
                "samples": [],
            }
        )

    return suggestions


# ────────────────────────────────────────────────────────────
# Main entry — 리포트 데이터 빌드
# ────────────────────────────────────────────────────────────


def build_report_payload(today: date) -> Dict[str, Any]:
    """리포트 전체 페이로드 생성."""
    logger.info(f"Building daily report for {today}")

    graph = collect_graph_metrics()
    news = collect_news_metrics(today)
    gaps = collect_coverage_gaps()
    health = collect_system_health()
    llm = collect_llm_usage()
    nightly = collect_nightly_summary()
    suggestions = collect_suggestions(graph, news, gaps, health)

    # LLM 비용 경고 추가
    if llm["est_monthly_cost_usd"] > 50:
        suggestions.append(
            {
                "category": "10. LLM 비용",
                "severity": "🟡",
                "issue": f"24h LLM 비용 ${llm['est_cost_usd_24h']} → 월간 추정 ${llm['est_monthly_cost_usd']}",
                "action": "Gemini console에서 실제 quota/billing 확인. backfill 빈도 조정 검토.",
                "samples": [],
            }
        )
    else:
        suggestions.append(
            {
                "category": "10. LLM 비용",
                "severity": "🟢",
                "issue": f"24h: ${llm['est_cost_usd_24h']} ({llm['total_calls_24h']} calls), 월 추정 ${llm['est_monthly_cost_usd']}",
                "action": "유지",
                "samples": [],
            }
        )

    prev_snapshot = _load_previous_snapshot(today)
    prev_graph = prev_snapshot.get("graph", {}) if prev_snapshot else {}
    prev_news = prev_snapshot.get("news", {}) if prev_snapshot else {}

    # 변화량 계산
    deltas = {
        "labels": {},
        "relations": {},
        "total_articles": _delta(
            news["total_articles"], prev_news.get("total_articles")
        ),
    }
    for label, cnt in graph["labels"].items():
        deltas["labels"][label] = _delta(cnt, prev_graph.get("labels", {}).get(label))
    for rt, cnt in graph["relations"].items():
        deltas["relations"][rt] = _delta(cnt, prev_graph.get("relations", {}).get(rt))

    payload = {
        "date": today.isoformat(),
        "previous_date": prev_snapshot["date"] if prev_snapshot else None,
        "graph": graph,
        "news": news,
        "gaps": gaps,
        "health": health,
        "llm": llm,
        "nightly": nightly,
        "suggestions": suggestions,
        "deltas": deltas,
    }
    _save_snapshot(today, payload)
    return payload
