"""Slice 11 Step 0 §2 — LLM raw messages 보존 정책 hook (#52).

모든 LLM 호출 직후 `messages + system + model + token + cost`를 슬라이스별 JSONL에
보존한다. 이후 estimator/router/cost 모델 fitting 시 자동으로 누적 데이터 확보.

**Slice 10 Fallback A 트리거 부채(#52)** 해결 인프라.

핵심 동작:
- 저장 위치: `docs/portfolio/coach/slice<N>/llm_messages.jsonl` (slice별 격리)
- 멱등성: SHA256(`messages + system + model`) hash로 중복 제거 (1회만 저장)
- toggle: 환경 변수 `STOCKVIS_LLM_MESSAGE_DUMP=0` → no-op
- redact: 민감 키워드(API_KEY, password, token=) 자동 마스킹

본 모듈은 hook 함수만 제공. 실제 호출 위치는 Slice 11 Part 1+에서
`portfolio/llm/client.py` 측에 통합 예정.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
COACH_ROOT = REPO_ROOT / "docs" / "portfolio" / "coach"

ENV_TOGGLE = "STOCKVIS_LLM_MESSAGE_DUMP"

logger = logging.getLogger(__name__)


# ============================================================
# Redact (민감정보 마스킹)
# ============================================================

_REDACT_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\s,'\"]+)"),
    re.compile(r"(?i)(password\s*[:=]\s*)([^\s,'\"]+)"),
    re.compile(r"(?i)(secret\s*[:=]\s*)([^\s,'\"]+)"),
    re.compile(r"(?i)(token\s*[:=]\s*)([^\s,'\"]+)"),
    re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"),  # Anthropic key prefix
]


def redact(text: str) -> str:
    """민감 패턴을 `<REDACTED>`로 마스킹."""
    if not isinstance(text, str):
        return text
    out = text
    for pat in _REDACT_PATTERNS[:4]:
        out = pat.sub(r"\1<REDACTED>", out)
    out = _REDACT_PATTERNS[4].sub("<REDACTED>", out)
    return out


def _redact_messages(messages: list[dict]) -> list[dict]:
    """messages list 안의 content 문자열에 redact 적용."""
    cleaned: list[dict] = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            cleaned.append({**m, "content": redact(content)})
        elif isinstance(content, list):
            blocks = []
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    blocks.append({**block, "text": redact(block["text"])})
                else:
                    blocks.append(block)
            cleaned.append({**m, "content": blocks})
        else:
            cleaned.append(m)
    return cleaned


# ============================================================
# Hash + path
# ============================================================


def compute_call_hash(messages: list[dict], system: str | None, model: str) -> str:
    """동일 (messages, system, model)이면 같은 hash → 중복 dump 차단."""
    payload = json.dumps(
        {"messages": messages, "system": system or "", "model": model},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def messages_jsonl_path(slice_n: int) -> Path:
    return COACH_ROOT / f"slice{slice_n}" / "llm_messages.jsonl"


# ============================================================
# Dedupe + write
# ============================================================


def _load_existing_hashes(path: Path) -> set[str]:
    """기존 파일의 hash 집합 (멱등성 검사)."""
    if not path.exists():
        return set()
    hashes: set[str] = set()
    with open(path, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                h = rec.get("hash")
                if h:
                    hashes.add(h)
            except json.JSONDecodeError:
                continue
    return hashes


def dump_llm_call(
    messages: list[dict],
    system: str | None,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    slice_n: int,
    *,
    extra: dict | None = None,
    out_path: Path | None = None,
) -> bool:
    """LLM 호출 1건을 slice별 JSONL에 append.

    Args:
        messages: Anthropic messages 형식 list.
        system: system prompt (없으면 None).
        model: 모델 ID.
        input_tokens / output_tokens / cost_usd: 응답 메타.
        slice_n: 슬라이스 번호.
        extra: 추가 필드 (scenario_id, preset_id 등 호출 컨텍스트).
        out_path: 저장 경로 override (테스트용).

    Returns:
        True if appended, False if no-op (toggle off OR 중복 hash).
    """
    if os.getenv(ENV_TOGGLE, "1") == "0":
        logger.debug("STOCKVIS_LLM_MESSAGE_DUMP=0 → skip")
        return False

    h = compute_call_hash(messages, system, model)
    target = out_path or messages_jsonl_path(slice_n)
    existing = _load_existing_hashes(target)
    if h in existing:
        logger.debug("dedupe hit: %s (slice %d)", h[:8], slice_n)
        return False

    record = {
        "hash": h,
        "slice": slice_n,
        "messages": _redact_messages(messages),
        "system": redact(system) if system else None,
        "model": model,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": float(cost_usd),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        record["extra"] = extra

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
        fp.write("\n")
    return True
