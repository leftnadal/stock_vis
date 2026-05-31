"""
Recheck 6단계 로직 — CS-6-5
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.chain_sight.graph import get_graph_repository
from apps.chain_sight.models import PathAction, SavedPath

logger = logging.getLogger(__name__)

STATUS_ORDER = {
    "hidden": 0,
    "stale": 1,
    "weak": 2,
    "probable": 3,
    "confirmed": 4,
}
ACTIVE_TRANSITION_RECHECK_COUNT = 2
ACTIVE_TRANSITION_HOURS = 24


@dataclass
class EdgeDiff:
    from_ticker: str
    to_ticker: str
    rel_type: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]
    old_score: Optional[int]
    new_score: Optional[int]
    bucket: str


@dataclass
class RecheckResult:
    headline: str = ""
    strengthened: List[Dict] = field(default_factory=list)
    weakened: List[Dict] = field(default_factory=list)
    unchanged: List[Dict] = field(default_factory=list)
    broken_edges: List[Dict] = field(default_factory=list)
    path_intact: bool = True
    suggested_action: str = "none"
    suggested_reason: str = ""
    updated_why_now: Dict = field(default_factory=dict)
    new_edge_snapshot: List[Dict] = field(default_factory=list)


def run_recheck(saved_path: SavedPath) -> RecheckResult:
    old_snapshot = saved_path.edge_snapshot or []
    new_snapshot = _fetch_current_snapshot(saved_path.path_nodes)
    diffs = _compute_diffs(old_snapshot, new_snapshot)

    result = RecheckResult(
        new_edge_snapshot=new_snapshot,
        strengthened=[_diff_to_dict(d) for d in diffs if d.bucket == "strengthened"],
        weakened=[_diff_to_dict(d) for d in diffs if d.bucket == "weakened"],
        unchanged=[_diff_to_dict(d) for d in diffs if d.bucket == "unchanged"],
        broken_edges=[_diff_to_dict(d) for d in diffs if d.bucket == "broken"],
    )
    result.path_intact = not result.broken_edges
    result.headline = _build_headline(result)
    result.suggested_action, result.suggested_reason = _decide_suggestion(
        result, saved_path
    )
    result.updated_why_now = _build_updated_why_now(saved_path, result)

    with transaction.atomic():
        saved_path.edge_snapshot = new_snapshot
        saved_path.why_now_snapshot = result.updated_why_now
        saved_path.recheck_count += 1
        _maybe_transition_to_active(saved_path)
        saved_path.save()
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.RECHECK,
            metadata={
                "strengthened": len(result.strengthened),
                "weakened": len(result.weakened),
                "broken": len(result.broken_edges),
                "suggested_action": result.suggested_action,
            },
        )
    return result


def _fetch_current_snapshot(path_nodes: List[str]) -> List[Dict]:
    if len(path_nodes) < 2:
        return []
    repo = get_graph_repository()
    snapshot = []
    for i in range(len(path_nodes) - 1):
        a, b = path_nodes[i], path_nodes[i + 1]
        rows = repo.run_query(
            """
            MATCH (from:Stock {ticker: $a})-[r]-(to:Stock {ticker: $b})
            RETURN type(r) AS rel_type,
                   r.truth_score AS truth_score,
                   r.status AS status,
                   startNode(r).ticker AS start_ticker
            ORDER BY r.truth_score DESC NULLS LAST
            LIMIT 1
            """,
            {"a": a, "b": b},
        )
        if rows:
            row = rows[0]
            snapshot.append(
                {
                    "from": row["start_ticker"],
                    "to": b if row["start_ticker"] == a else a,
                    "type": row["rel_type"],
                    "truth_score": row["truth_score"],
                    "status": row["status"],
                }
            )
        else:
            snapshot.append(
                {
                    "from": a,
                    "to": b,
                    "type": None,
                    "truth_score": None,
                    "status": "hidden",
                }
            )
    return snapshot


def _compute_diffs(old_snapshot, new_snapshot):
    diffs = []
    if len(old_snapshot) != len(new_snapshot):
        logger.warning(
            f"edge_snapshot 길이 불일치: old={len(old_snapshot)}, new={len(new_snapshot)}"
        )
    pairs = min(len(old_snapshot), len(new_snapshot))
    for i in range(pairs):
        old, new = old_snapshot[i], new_snapshot[i]
        bucket = _classify_edge_change(old, new)
        diffs.append(
            EdgeDiff(
                from_ticker=new.get("from", old.get("from")),
                to_ticker=new.get("to", old.get("to")),
                rel_type=new.get("type") or old.get("type"),
                old_status=old.get("status"),
                new_status=new.get("status"),
                old_score=old.get("truth_score"),
                new_score=new.get("truth_score"),
                bucket=bucket,
            )
        )
    return diffs


def _classify_edge_change(old: Dict, new: Dict) -> str:
    old_status = old.get("status")
    new_status = new.get("status")
    old_score = old.get("truth_score") or 0
    new_score = new.get("truth_score") or 0

    if old_status in ("confirmed", "probable", "weak") and new_status in (
        "hidden",
        "stale",
    ):
        return "broken"
    if old_status in STATUS_ORDER and new_status in STATUS_ORDER:
        old_rank = STATUS_ORDER[old_status]
        new_rank = STATUS_ORDER[new_status]
        if new_rank > old_rank:
            return "strengthened"
        elif new_rank < old_rank:
            return "weakened" if new_rank >= STATUS_ORDER["weak"] else "broken"
    score_delta = new_score - old_score
    if abs(score_delta) < 5:
        return "unchanged"
    return "strengthened" if score_delta > 0 else "weakened"


def _build_headline(result: RecheckResult) -> str:
    s, w, b = len(result.strengthened), len(result.weakened), len(result.broken_edges)
    total = s + w + b + len(result.unchanged)

    if b > 0:
        if b == total:
            return f"전 구간({b}개) 연결 끊김"
        if s > 0:
            return f"{b}개 구간 끊김, 다른 {s}개 구간은 강화"
        if w > 0:
            return f"{b}개 구간 끊김, {w}개 구간 약화 — 경로 재검토 필요"
        return f"{b}개 구간 연결 끊김"
    if s > 0 and w == 0:
        return f"{s}개 구간 강화 — 관계 활성 ↑"
    if w > 0 and s == 0:
        return f"{w}개 구간 약화"
    if s > 0 and w > 0:
        if s > w:
            return f"전반적 강화 ({s}개 ↑ / {w}개 ↓)"
        elif w > s:
            return f"전반적 약화 ({w}개 ↓ / {s}개 ↑)"
        else:
            return f"혼재 신호 ({s}개 ↑ / {w}개 ↓)"
    return "큰 변화 없음 — 관계 유지"


def _decide_suggestion(result: RecheckResult, saved_path: SavedPath) -> tuple:
    b, s, w = len(result.broken_edges), len(result.strengthened), len(result.weakened)
    total_edges = b + s + w + len(result.unchanged)

    if b == total_edges:
        return "resolve", "전 구간이 끊어진 경로입니다. 전략 종료를 고려해보세요."
    if b > 0:
        broken_nodes = set()
        for e in result.broken_edges:
            broken_nodes.add(e["from"])
            broken_nodes.add(e["to"])
        broken_list = ", ".join(sorted(broken_nodes)[:3])
        return "alternatives", f"{broken_list} 주변에서 대체 경로를 탐색해보세요."
    if s > 0 and w == 0:
        return "expand", f"강화된 {s}개 구간의 인접 노드를 탐색해볼 가치가 있습니다."
    if s > 0 and w > 0:
        if s >= w:
            return "expand", "주 구간이 강화되는 중입니다. 확장을 고려해보세요."
        else:
            return (
                "alternatives",
                "일부 구간이 약해지고 있습니다. 대안 경로를 살펴보세요.",
            )
    if w > 0:
        if saved_path.recheck_count >= 3:
            return (
                "archive",
                "여러 차례 Recheck에서 약화 신호가 반복됩니다. 보관을 고려해보세요.",
            )
        return "none", "구간이 약해지는 중입니다. 며칠 후 다시 Recheck해보세요."
    return "none", "현재 큰 변화가 없습니다."


def _build_updated_why_now(saved_path, result):
    new_snapshot = result.new_edge_snapshot
    strong_count = sum(
        1 for e in new_snapshot if e.get("status") in ("confirmed", "probable")
    )
    return {
        "headline": result.headline,
        "signals": [
            {"type": "strengthened", "count": len(result.strengthened)},
            {"type": "weakened", "count": len(result.weakened)},
            {"type": "broken", "count": len(result.broken_edges)},
        ],
        "generated_at": timezone.now().isoformat(),
        "strong_edges": strong_count,
        "total_edges": len(new_snapshot),
        "suggested_action": result.suggested_action,
    }


def _maybe_transition_to_active(saved_path):
    if saved_path.status != SavedPath.Status.WATCHING:
        return
    if saved_path.recheck_count < ACTIVE_TRANSITION_RECHECK_COUNT:
        return
    age = timezone.now() - saved_path.created_at
    if age < timedelta(hours=ACTIVE_TRANSITION_HOURS):
        return
    saved_path.status = SavedPath.Status.ACTIVE


def _diff_to_dict(diff: EdgeDiff) -> Dict:
    return {
        "from": diff.from_ticker,
        "to": diff.to_ticker,
        "type": diff.rel_type,
        "old_status": diff.old_status,
        "new_status": diff.new_status,
        "old_score": diff.old_score,
        "new_score": diff.new_score,
    }
