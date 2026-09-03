"""점검 대상 정의 — 화면 목록의 단일 출처는 `frontend/lib/guide/`다.

가이드 데이터(GuideScreen)는 유저 가이드이자 야간 에이전트의 채점 루브릭 단일
출처다(D-GUIDE-TRACK). 1단계 정량 체크도 **같은 파일**에서 대상 화면을 읽는다.
별도 화면 목록을 두면 루브릭과 점검 대상이 어긋나기 때문이다(복제 = drift).

TS를 파싱하지만 형식이 바뀌면 조용히 0건이 되는 것을 막으려고, 추출 결과가
비면 예외를 던지고 테스트가 화면 수를 고정한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE_DIR = REPO_ROOT / "frontend" / "lib" / "guide"

# 가이드 데이터가 없는(=루브릭 대상이 아닌) 부가 점검 라우트.
EXTRA_ROUTES = [
    ("guide.hub", "/guide", "사용 가이드 허브"),
    ("auth.login", "/login", "로그인"),
]

# 라우트별 SSR 셸 마커(있어야 정상) — 데이터는 클라이언트 렌더라 셸만 검사한다.
SHELL_MARKERS = {
    "/": ["Stock-Vis"],
    "/market-pulse-v2": ["Market Pulse v2"],
    "/chainsight": ["Stock-Vis"],
    "/monitor": ["Stock-Vis"],
    "/portfolio": ["Stock-Vis"],
    "/guide": ["사용 가이드", "서비스 플로우"],
    "/login": ["Stock-Vis 로그인"],
}

# 어느 화면에서든 SSR HTML에 나오면 안 되는 실패 문구.
#
# ⚠️ 마커는 **반드시 화면 문구 전체**여야 한다. "500" 같은 짧은 토큰은 tailwind 클래스
#    (text-gray-500)·티커명(SP500)·인라인 CSS(font-weight:500)에 전부 걸려 전 라우트를
#    거짓 fail로 만든다(첫 실행에서 7/7 오탐으로 실증). 부분 토큰 금지.
ERROR_MARKERS = [
    "데이터를 불러오지 못했습니다",
    "데이터를 불러올 수 없습니다",
    "목록을 불러오지 못했어요",
    "아직 시그널 데이터가 생성되지 않았거나 네트워크 오류입니다",
    "Application error: a client-side exception has occurred",
    "Internal Server Error",
    "This page could not be found",
]

# 화면이 의존하는 핵심 API. 대부분 인증 게이트라 토큰 없이는 401이 정상 신호다.
API_TARGETS = [
    # (키, 경로, 인증필요, 비고)
    ("health", "/api/v1/health/", False, "무인증 헬스"),
    ("marketPulseV2.overview", "/api/v2/market-pulse/overview", True, "MP v2 히어로·카드"),
    ("marketPulseV2.stress", "/api/v2/market-pulse/regime/stress", True, "스트레스 밴드"),
    ("chainsight.events", "/api/v1/chainsight/events/", True, "이벤트 보드"),
    ("monitor.monitors", "/api/v1/monitor/monitors/", True, "모니터 목록"),
    ("portfolio.list", "/api/v1/users/portfolio/", True, "보유 종목"),
]

# 대시보드는 API가 아니라 baked static JSON을 읽는다(JSON Baking).
DASHBOARD_JSON_PATH = "/static/signals/dashboard.json"


@dataclass
class GuideTarget:
    id: str
    route: str
    title: str
    review_status: str
    anchors: list[str] = field(default_factory=list)
    # ── 2단계(AGENT-S2) 루브릭 입력 ──
    # coreQuestion = "정병진의 질문"의 단일 출처. 이것을 바꾸면 채점 기준이 바뀐다.
    core_question: str = ""
    learnings: list[str] = field(default_factory=list)
    flow_stage: int = 0

    @property
    def is_confirmed(self) -> bool:
        """병진 검수 승인분만 루브릭 대상(draft는 문안이 확정되지 않았다)."""
        return self.review_status == "confirmed"


_ID = re.compile(r"id:\s*'([^']+)'")
_FIELD = re.compile(r"(\w+):\s*'((?:[^'\\]|\\.)*)'")
_ANCHOR = re.compile(r"anchor:\s*'([^']+)'")
# learnings: [ '...', '...' ] — 배열 리터럴이라 _FIELD(단일 문자열)로는 안 잡힌다.
_LEARNINGS_BLOCK = re.compile(r"learnings:\s*\[(.*?)\]", re.DOTALL)
_QUOTED = re.compile(r"'((?:[^'\\]|\\.)*)'")
_FLOW_STAGE = re.compile(r"flowStage:\s*(\d+)")


def load_guide_targets(guide_dir: Path | None = None) -> list[GuideTarget]:
    """`frontend/lib/guide/*.ts`에서 화면 목록을 읽는다. index/types는 제외."""
    d = guide_dir or GUIDE_DIR
    out: list[GuideTarget] = []
    for path in sorted(d.glob("*.ts")):
        if path.stem in {"index", "types"}:
            continue
        src = path.read_text(encoding="utf-8")
        # 한 파일에 여러 화면이 올 수 있으므로 id 등장 위치로 블록을 자른다.
        starts = [m.start() for m in _ID.finditer(src)]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(src)
            block = src[start:end]
            # first-wins: nextAction 안의 `route:`가 화면 자신의 `route:`를 덮어쓰지 않게.
            fields: dict[str, str] = {}
            for key, value in _FIELD.findall(block):
                fields.setdefault(key, value)
            route = fields.get("route")
            if not route:
                continue
            learnings: list[str] = []
            lm = _LEARNINGS_BLOCK.search(block)
            if lm:
                learnings = [x.replace("\\'", "'") for x in _QUOTED.findall(lm.group(1))]
            fm = _FLOW_STAGE.search(block)
            out.append(
                GuideTarget(
                    id=fields.get("id", ""),
                    route=route,
                    title=fields.get("title", ""),
                    review_status=fields.get("reviewStatus", "unknown"),
                    anchors=_ANCHOR.findall(block),
                    core_question=fields.get("coreQuestion", ""),
                    learnings=learnings,
                    flow_stage=int(fm.group(1)) if fm else 0,
                )
            )
    if not out:
        raise RuntimeError(
            f"가이드 화면을 하나도 읽지 못했습니다: {d} — "
            "frontend/lib/guide 의 데이터 형식이 바뀌었는지 확인하세요."
        )
    return out


def all_route_targets(guide_dir: Path | None = None) -> list[tuple[str, str, str]]:
    """(키, 라우트, 표시명) — 가이드 화면 + 부가 라우트."""
    rows = [(g.id, g.route, g.title) for g in load_guide_targets(guide_dir)]
    return rows + list(EXTRA_ROUTES)


def rubric_targets(guide_dir: Path | None = None) -> list[GuideTarget]:
    """2단계 채점 대상 = confirmed + coreQuestion 보유 화면, flowStage 순.

    draft는 문안이 확정되지 않아 채점 기준으로 쓰지 않는다(D-AGENT-S2).
    """
    rows = [g for g in load_guide_targets(guide_dir) if g.is_confirmed and g.core_question]
    return sorted(rows, key=lambda g: (g.flow_stage, g.route))
