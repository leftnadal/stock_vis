"""Agent별 일일 보고서 빌더 (Phase 1, 2026-05-22).

도메인별 4통 분리:
  - @data       06:00 KST → NewsEvent / Stock / Neo4j 데이터 양·품질 추이
  - @backend    06:15 KST → API/DB/Beat/시스템 헬스 + 백엔드 tier3 보고서
  - @qa         06:30 KST → 보안/성능/카탈로그 tier3 보고서
  - @design     06:45 KST → 모바일 UX + thesis/chainsight 디자인 gap

원칙: 기존 collect_* 재사용 + tier3 보고서 추출. 자동 코드 변경 없음.
출력은 메일 + docs/nightly_auto_system/reports/ 그대로 활용.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.shared.metrics.services.daily_report import (
    _load_previous_snapshot,
    collect_coverage_gaps,
    collect_graph_metrics,
    collect_llm_usage,
    collect_news_metrics,
    collect_system_health,
)

logger = logging.getLogger(__name__)


# ─── 도메인 → tier3 보고서 매핑 ────────────────────────────────────────
DOMAIN_REPORT_MAP: Dict[str, List[str]] = {
    "backend": [
        "api_dependency_audit",
        "data_integrity_audit",
        "beat_schedule_audit",
        "api_docs_audit",
        "api_consistency_audit",
    ],
    "qa": [
        "security_audit",
        "performance_audit",
        "indicator_catalog_audit",
    ],
    "design": [
        "mobile_ux_audit",
        "thesis_design_gap_audit",
        "chainsight_design_gap_audit",
        "remaining_design_gap_audit",
    ],
}

REPORTS_BASE = Path(
    "/Users/byeongjinjeong/Desktop/stock_vis/docs/nightly_auto_system/reports"
)


def _find_report_path(name: str, target_date: date) -> Optional[Path]:
    """tier3 보고서 파일 경로 탐색. 어제 → 오늘 → 그제 순."""
    for delta in [1, 0, 2, 3]:
        d = target_date - timedelta(days=delta)
        cand = REPORTS_BASE / f"{d.month}월" / f"{d.day}일" / f"{name}.md"
        if cand.exists():
            return cand
    return None


_SEVERITY_RE = re.compile(r"(🔴|🟡|HIGH|MED|MEDIUM|LOW)")
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")


def extract_audit_insights(path: Path, max_items: int = 5) -> Dict[str, Any]:
    """tier3 보고서에서 핵심 인사이트 추출.

    반환:
      {
        "title": str,              # 첫 # 헤딩
        "summary_line": str,       # 총평 또는 첫 문단
        "severity_hits": List[str],  # 🔴/🟡 또는 HIGH/MED 라인 (max 5)
        "section_headings": List[str],  # ## 헤딩 (max 6)
        "lines": int,
      }
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"extract_audit_insights({path}): {e}")
        return {
            "title": path.stem,
            "summary_line": "",
            "severity_hits": [],
            "section_headings": [],
            "lines": 0,
        }

    lines = text.splitlines()
    result = {
        "title": "",
        "summary_line": "",
        "severity_hits": [],
        "section_headings": [],
        "lines": len(lines),
    }

    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 제목
        if not result["title"] and stripped.startswith("# "):
            result["title"] = stripped.lstrip("# ").strip()
            continue

        # ## 헤딩
        h = _HEADING_RE.match(stripped)
        if h and len(h.group(1)) == 2 and len(result["section_headings"]) < 6:
            result["section_headings"].append(h.group(2).strip())

        # 총평/첫 문단 (제목 직후 첫 의미 있는 문장)
        if (
            not result["summary_line"]
            and result["title"]
            and not stripped.startswith("#")
        ):
            if "총평" in stripped or "요약" in stripped or stripped.startswith("**"):
                result["summary_line"] = stripped[:200]
            elif len(stripped) > 30 and not stripped.startswith("|"):
                result["summary_line"] = stripped[:200]

        # severity hits (table 스킵)
        if stripped.startswith("|"):
            in_table = True
        elif in_table and not stripped.startswith("|"):
            in_table = False

        if (
            not in_table
            and _SEVERITY_RE.search(stripped)
            and len(result["severity_hits"]) < max_items
        ):
            if stripped.startswith("|") or stripped.startswith("```"):
                continue
            # 라인 길이 제한
            result["severity_hits"].append(stripped[:180])

    return result


def _seven_day_trend(today: date, key_path: List[str]) -> List[Optional[int]]:
    """일별 스냅샷에서 7일 추이 추출. payload[key_path[0]][key_path[1]] 식 접근."""
    trend: List[Optional[int]] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        snap = _load_previous_snapshot(
            d + timedelta(days=1)
        )  # _load_previous_snapshot은 'today-1' 데이터 반환
        if snap:
            obj: Any = snap
            for k in key_path:
                obj = obj.get(k, {}) if isinstance(obj, dict) else None
                if obj is None:
                    break
            trend.append(obj if isinstance(obj, (int, float)) else None)
        else:
            trend.append(None)
    return trend


# ─── 도메인별 빌더 ───────────────────────────────────────────────────────


def build_data_report(today: date) -> Dict[str, Any]:
    """@data: NewsEvent / Stock / Neo4j 노드·관계 추이.

    포커스: 데이터 양이 늘고 있는지, 신선도, 커버리지 갭.
    """
    graph = collect_graph_metrics()
    news = collect_news_metrics(today)
    gaps = collect_coverage_gaps()
    llm = collect_llm_usage()

    # 7일 추이 (가능한 경우)
    trend_nodes = _seven_day_trend(today, ["graph", "total_nodes"])
    trend_relations = _seven_day_trend(today, ["graph", "total_relations"])
    trend_news_24h = _seven_day_trend(today, ["news", "today_new"])

    return {
        "domain": "data",
        "domain_label": "@data",
        "date": today.isoformat(),
        "graph": graph,
        "news": news,
        "gaps": gaps,
        "llm_usage": llm,
        "trends": {
            "nodes_7d": trend_nodes,
            "relations_7d": trend_relations,
            "news_24h_7d": trend_news_24h,
        },
        "tldr": _build_tldr_data(graph, news, gaps, trend_nodes, trend_news_24h),
    }


def _build_tldr_data(graph, news, gaps, trend_nodes, trend_news) -> List[str]:
    """@data TL;DR 3줄."""
    tldr = []
    valid_nodes = [n for n in trend_nodes if n is not None]
    if len(valid_nodes) >= 2:
        delta = valid_nodes[-1] - valid_nodes[0]
        emoji = "📈" if delta > 0 else ("📉" if delta < 0 else "➡️")
        tldr.append(
            f"{emoji} Neo4j 노드 7일: {valid_nodes[0]:,} → {valid_nodes[-1]:,} ({delta:+,})"
        )
    else:
        tldr.append(
            f"Neo4j 노드: {graph['total_nodes']:,} / 관계: {graph['total_relations']:,}"
        )

    tldr.append(
        f"📰 24h 뉴스: {news['today_new']}건 (LLM 분석률 {news['today_llm_analyzed_pct']}%)"
    )

    unmatched = gaps.get("unmatched_queue_count", 0)
    if unmatched > 100:
        tldr.append(f"⚠️ UnmatchedCompanyQueue 적체 {unmatched}건 — 매칭 보완 필요")
    else:
        tldr.append(f"커버리지 갭: UnmatchedQueue {unmatched}건")

    return tldr


def build_backend_report(today: date) -> Dict[str, Any]:
    """@backend: API / DB / Beat / 시스템 헬스 + 백엔드 audit."""
    health = collect_system_health()
    llm = collect_llm_usage()
    audits = _collect_domain_audits("backend", today)

    return {
        "domain": "backend",
        "domain_label": "@backend",
        "date": today.isoformat(),
        "health": health,
        "llm_usage": llm,
        "audits": audits,
        "tldr": _build_tldr_backend(health, llm, audits),
    }


def _build_tldr_backend(health, llm, audits) -> List[str]:
    tldr = []
    # Health 요약
    workers_ok = health.get("celery_worker_count", 0) >= 1
    beat_ok = health.get("celery_beat_running", False)
    neo4j_ok = health.get("neo4j_reachable", False)
    h_emoji = "✅" if (workers_ok and beat_ok and neo4j_ok) else "⚠️"
    tldr.append(
        f"{h_emoji} System: worker={health.get('celery_worker_count', '?')} "
        f"beat={'OK' if beat_ok else 'DOWN'} neo4j={'OK' if neo4j_ok else 'DOWN'}"
    )
    # LLM 비용
    tldr.append(
        f"💰 LLM 24h: ${llm['est_cost_usd_24h']} ({llm['total_calls_24h']} calls), "
        f"월 추정 ${llm['est_monthly_cost_usd']}"
    )
    # 가장 무거운 audit issue
    total_hits = sum(len(a.get("severity_hits", [])) for a in audits)
    tldr.append(f"📋 백엔드 audit {len(audits)}개 / severity 항목 {total_hits}개")
    return tldr


def build_qa_report(today: date) -> Dict[str, Any]:
    """@qa: 보안 / 성능 / 카탈로그 audit."""
    audits = _collect_domain_audits("qa", today)
    return {
        "domain": "qa",
        "domain_label": "@qa",
        "date": today.isoformat(),
        "audits": audits,
        "tldr": _build_tldr_qa(audits),
    }


def _build_tldr_qa(audits) -> List[str]:
    tldr = []
    for a in audits:
        hits = a.get("severity_hits", [])
        red_count = sum(1 for h in hits if "🔴" in h or "HIGH" in h)
        if red_count > 0:
            tldr.append(f"🔴 {a['name']}: HIGH {red_count}건")
    if not tldr:
        tldr.append("✅ HIGH severity 항목 없음")
    while len(tldr) < 3:
        tldr.append(f"📋 audit {len(audits)}개 검토")
    return tldr[:3]


def build_design_report(today: date) -> Dict[str, Any]:
    """@frontend + @ui-ux: 모바일 UX + 디자인 gap audit."""
    audits = _collect_domain_audits("design", today)
    return {
        "domain": "design",
        "domain_label": "@frontend @ui-ux",
        "date": today.isoformat(),
        "audits": audits,
        "tldr": _build_tldr_design(audits),
    }


def _build_tldr_design(audits) -> List[str]:
    tldr = []
    for a in audits:
        hits = a.get("severity_hits", [])
        if hits:
            tldr.append(f"📐 {a['name']}: 검토 항목 {len(hits)}개")
    while len(tldr) < 3:
        tldr.append(f"디자인 gap audit {len(audits)}개")
    return tldr[:3]


def _collect_domain_audits(domain: str, today: date) -> List[Dict[str, Any]]:
    """도메인 매핑으로 tier3 보고서 추출."""
    results = []
    for name in DOMAIN_REPORT_MAP.get(domain, []):
        path = _find_report_path(name, today)
        if path is None:
            results.append(
                {
                    "name": name,
                    "available": False,
                    "path": None,
                    "title": name,
                    "summary_line": "(보고서 없음 — nightly 미실행 또는 다른 날짜)",
                    "severity_hits": [],
                    "section_headings": [],
                    "lines": 0,
                }
            )
            continue
        insights = extract_audit_insights(path)
        results.append(
            {
                "name": name,
                "available": True,
                "path": str(path).replace(str(Path.home()), "~"),
                **insights,
            }
        )
    return results


# ─── 빌더 dispatcher ────────────────────────────────────────────────────

BUILDERS = {
    "data": build_data_report,
    "backend": build_backend_report,
    "qa": build_qa_report,
    "design": build_design_report,
}
