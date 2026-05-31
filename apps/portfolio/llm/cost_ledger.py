"""LLM 호출 비용 ledger — append-only JSONL (Slice 14 Step 0 #63).

설계 원칙 (slice 14 step_0.md §작업 2):
- 기록 전용(append-only). 호출 허용/거부 판정에 일절 관여하지 않는다.
- 차단 동작은 #64 별도 작업. 본 모듈은 무엇이 일어났는지만 기록한다.
- append 실패가 LLM 호출 흐름을 절대 깨지 않는다 (실패는 logger.warning, 예외 미전파).
- CostGuard 공개 인터페이스 무수정. 비용 집계 지점에 1줄 append 호출만 끼움.
- 슬라이스 단위 순차 실행을 가정 — 동시성/파일 락 과설계 X.

경로: `docs/portfolio/coach/cost_ledger.jsonl` (REPO_ROOT 기준)
오버라이드: 환경변수 `COST_LEDGER_PATH` (테스트용).

행 컬럼 (JSONL 1행 = LLM 호출 1건):
    timestamp(ISO8601 UTC), slice, entry_point, provider, model,
    input_tokens, output_tokens, cost_usd, fallback_from
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_PATH = REPO_ROOT / "docs" / "portfolio" / "coach" / "cost_ledger.jsonl"


def get_ledger_path() -> Path:
    """ledger 파일 경로 (환경변수 오버라이드 지원)."""
    override = os.getenv("COST_LEDGER_PATH")
    return Path(override) if override else DEFAULT_LEDGER_PATH


def append_call(
    slice_id: str,
    entry_point: Optional[str],
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    fallback_from: Optional[str] = None,
    path: Optional[Path] = None,
) -> None:
    """LLM 호출 1건을 ledger에 append (기록 전용).

    실패해도 raise하지 않음 — ledger는 보조 장치다. logger.warning만 남기고
    호출자(LLMClient.complete)는 영향받지 않는다.

    Args:
        slice_id: CostGuard.slice_id (예: "slice14").
        entry_point: caller 단계 식별자 ("e1"~"e6" 등). 미정 시 None.
        provider: "gemini" | "anthropic".
        model: 모델 ID (예: "claude-haiku-4-5").
        input_tokens, output_tokens: LLMResponse 토큰 수.
        cost_usd: LLMResponse.cost_usd (단가 환산값).
        fallback_from: 폴백 발생 시 원래 provider, 아니면 None.
        path: 테스트용 오버라이드. None이면 get_ledger_path() 사용.
    """
    target = path if path is not None else get_ledger_path()
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "slice": slice_id,
        "entry_point": entry_point,
        "provider": provider,
        "model": model,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": float(cost_usd),
        "fallback_from": fallback_from,
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 — 보조 장치, 본 호출 흐름 보호.
        logger.warning("cost_ledger append 실패 (무시): path=%s err=%s", target, exc)


def read_records(
    path: Optional[Path] = None,
    slice_id: Optional[str] = None,
) -> list[dict]:
    """ledger 전체 또는 슬라이스 단위 행을 dict 리스트로 반환.

    파일 부재 → 빈 리스트 (실패 아님). 파싱 실패 행은 skip + warning.
    """
    target = path if path is not None else get_ledger_path()
    if not target.exists():
        return []
    rows: list[dict] = []
    try:
        with open(target, encoding="utf-8") as fp:
            for lineno, line in enumerate(fp, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "cost_ledger 행 %d 파싱 실패 (skip): %s", lineno, exc
                    )
                    continue
                if slice_id is not None and row.get("slice") != slice_id:
                    continue
                rows.append(row)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cost_ledger 읽기 실패: path=%s err=%s", target, exc)
        return []
    return rows


def sum_cost_usd(
    path: Optional[Path] = None,
    slice_id: Optional[str] = None,
) -> float:
    """ledger 누적 cost_usd 합 (옵션: 슬라이스 필터)."""
    return sum(float(r.get("cost_usd", 0.0)) for r in read_records(path, slice_id))
