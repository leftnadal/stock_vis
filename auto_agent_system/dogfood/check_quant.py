"""AGENT-S1 1단계 — 야간 도그푸딩 정량 체크 (read-only).

세 축을 잰다.
  ⑴ 라우트 매트릭스 — :3000 HTTP 상태·응답시간·셸 마커 존재·에러 마커 부재
  ⑵ 데이터 신선도  — baked dashboard.json의 거래일이 대상 세션과 맞는가
  ⑶ API 헬스       — 화면이 쓰는 핵심 API 응답(대부분 인증 게이트 → 401=존재)

경계: DB 직접 조회 금지(API·정적 파일 경유). apps 코드 무접촉. 쓰기 없음.
출력: ~/stock-vis-nightly/dogfood/quant_YYYYMMDD.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .market_calendar import holiday_name, is_trading_day, target_session_date
from .targets import (
    API_TARGETS,
    DASHBOARD_JSON_PATH,
    ERROR_MARKERS,
    SHELL_MARKERS,
    all_route_targets,
)

WEB_BASE = os.getenv("DOGFOOD_WEB_BASE", "http://127.0.0.1:3000")
API_BASE = os.getenv("DOGFOOD_API_BASE", "http://127.0.0.1:18765")
OUT_DIR = Path(os.getenv("DOGFOOD_OUT_DIR", str(Path.home() / "stock-vis-nightly" / "dogfood")))

# 임계값 — 넘으면 fail/warn. 근거 없는 값은 넣지 않는다(전부 관측 가능한 것만).
ROUTE_TIMEOUT_S = 15
SLOW_ROUTE_MS = 3000          # 이보다 느리면 warn (사람이 느린 걸 알아채는 대략의 선)
MIN_HTML_BYTES = 5000         # 셸조차 안 나온 빈 응답 감지
MAX_FRESHNESS_LAG_DAYS = 1    # 대상 세션 대비 며칠까지 허용

OK, WARN, FAIL = "ok", "warn", "fail"


def _item(status: str, value: Any, threshold: Any, note: str) -> dict[str, Any]:
    return {"status": status, "value": value, "threshold": threshold, "note": note}


_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def visible_text(html: str) -> str:
    """사람이 화면에서 보는 텍스트만 남긴다.

    Next.js는 RSC 플라이트 페이로드와 404 컴포넌트 문자열을 **모든 페이지의 인라인
    스크립트**에 실어 보낸다. 원문 HTML에 문구 매칭을 하면 "This page could not be
    found"가 전 라우트에서 걸려 전건 거짓 fail이 된다(첫 실행에서 7/7 오탐으로 실증).
    따라서 마커 판정은 반드시 이 함수를 거친 텍스트에 대해서만 한다.
    """
    body = _SCRIPT_OR_STYLE.sub(" ", html)
    return _TAG.sub(" ", body)


def _fetch(url: str, timeout: int = ROUTE_TIMEOUT_S) -> tuple[int, bytes, float]:
    """(status, body, elapsed_ms). 연결 실패는 status 0."""
    req = urllib.request.Request(url, headers={"User-Agent": "stockvis-dogfood/1"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body, (time.monotonic() - start) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() or b"", (time.monotonic() - start) * 1000
    except Exception:
        return 0, b"", (time.monotonic() - start) * 1000


# ────────────────────────────── ⑴ 라우트 매트릭스


def check_routes() -> dict[str, Any]:
    results: dict[str, Any] = {}
    for key, route, title in all_route_targets():
        status_code, body, elapsed = _fetch(f"{WEB_BASE}{route}")
        html = body.decode("utf-8", errors="ignore")
        text = visible_text(html)

        if status_code != 200:
            results[key] = _item(FAIL, status_code, 200, f"{title} — HTTP {status_code or '연결 실패'}")
            continue
        if len(body) < MIN_HTML_BYTES:
            results[key] = _item(FAIL, len(body), f">={MIN_HTML_BYTES}", f"{title} — 응답이 비정상적으로 작음(빈 화면 의심)")
            continue

        missing = [m for m in SHELL_MARKERS.get(route, []) if m not in text]
        if missing:
            results[key] = _item(FAIL, missing, "셸 마커 존재", f"{title} — 셸 마커 누락: {', '.join(missing)}")
            continue

        found_errors = [m for m in ERROR_MARKERS if m in text]
        if found_errors:
            results[key] = _item(FAIL, found_errors, "에러 문구 부재", f"{title} — 화면에 실패 문구 노출: {', '.join(found_errors)}")
            continue

        ms = round(elapsed)
        if ms > SLOW_ROUTE_MS:
            results[key] = _item(WARN, ms, f"<={SLOW_ROUTE_MS}ms", f"{title} — 느림 {ms}ms")
            continue
        results[key] = _item(OK, ms, f"<={SLOW_ROUTE_MS}ms", f"{title} — 200 / {ms}ms")
    return results


# ────────────────────────────── ⑵ 데이터 신선도


def check_freshness(session: date) -> dict[str, Any]:
    status_code, body, _ = _fetch(f"{WEB_BASE}{DASHBOARD_JSON_PATH}")
    if status_code != 200 or not body:
        return {
            "dashboard.json": _item(FAIL, status_code, 200, "baked dashboard.json을 못 읽음"),
        }
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return {"dashboard.json": _item(FAIL, str(exc), "valid JSON", "dashboard.json 파싱 실패")}

    out: dict[str, Any] = {}
    raw_date = data.get("trading_date")
    try:
        trading = date.fromisoformat(raw_date) if raw_date else None
    except (TypeError, ValueError):
        trading = None

    if trading is None:
        out["eod.trading_date"] = _item(FAIL, raw_date, "YYYY-MM-DD", "trading_date 부재/형식 오류")
    else:
        lag = (session - trading).days
        status = OK if lag <= MAX_FRESHNESS_LAG_DAYS else FAIL
        out["eod.trading_date"] = _item(
            status, str(trading), f"대상 세션 {session} (지연 <= {MAX_FRESHNESS_LAG_DAYS}일)",
            f"EOD 최신 거래일 {trading} / 대상 세션 {session} — 지연 {lag}일",
        )

    out["eod.is_stale"] = _item(
        WARN if data.get("is_stale") else OK, bool(data.get("is_stale")), False,
        "베이커가 stale로 표시함" if data.get("is_stale") else "신선",
    )
    cards = data.get("signal_cards") or []
    out["eod.signal_cards"] = _item(
        OK if cards else FAIL, len(cards), ">=1",
        f"시그널 카드 {len(cards)}건" if cards else "시그널 카드 0건 — 빈 대시보드",
    )
    recs = data.get("recommendations") or []
    out["eod.recommendations"] = _item(
        OK if recs else WARN, len(recs), ">=1",
        f"추천 {len(recs)}건" if recs else "추천 0건",
    )
    return out


# ────────────────────────────── ⑶ API 헬스


def _login_token() -> str | None:
    """DOGFOOD_API_USER/PASSWORD가 있으면 JWT 획득. 없으면 None(축소 모드)."""
    user = os.getenv("DOGFOOD_API_USER")
    password = os.getenv("DOGFOOD_API_PASSWORD")
    if not user or not password:
        return None
    payload = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/users/login/", data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "stockvis-dogfood/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=ROUTE_TIMEOUT_S) as resp:
            body = json.loads(resp.read())
    except Exception:
        return None
    for key in ("access", "access_token", "token"):
        if isinstance(body, dict) and body.get(key):
            return str(body[key])
    return None


def check_apis(token: str | None) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for key, path, needs_auth, note in API_TARGETS:
        url = f"{API_BASE}{path}"
        if token and needs_auth:
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {token}", "User-Agent": "stockvis-dogfood/1"}
            )
            start = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=ROUTE_TIMEOUT_S) as resp:
                    status_code, body = resp.status, resp.read()
            except urllib.error.HTTPError as exc:
                status_code, body = exc.code, exc.read() or b""
            except Exception:
                status_code, body = 0, b""
            elapsed = (time.monotonic() - start) * 1000
        else:
            status_code, body, elapsed = _fetch(url)

        if status_code == 200:
            empty = _looks_empty(body)
            results[key] = _item(
                WARN if empty else OK, 200, 200,
                f"{note} — 200이나 결과가 비어 있음" if empty else f"{note} — 200 / {round(elapsed)}ms",
            )
        elif status_code == 401 and needs_auth:
            results[key] = _item(
                OK if not token else FAIL, 401, "200(토큰 있을 때) / 401(없을 때)",
                f"{note} — 인증 게이트 응답(엔드포인트 존재)" if not token
                else f"{note} — 토큰이 있는데도 401(인증 실패)",
            )
        else:
            results[key] = _item(FAIL, status_code, 200, f"{note} — HTTP {status_code or '연결 실패'}")
    return results


def _looks_empty(body: bytes) -> bool:
    try:
        data = json.loads(body)
    except Exception:
        return False
    if isinstance(data, list):
        return len(data) == 0
    if isinstance(data, dict):
        for key in ("results", "data", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value) == 0
        return len(data) == 0
    return False


# ────────────────────────────── 조립


def build_report(run_date: date | None = None) -> dict[str, Any]:
    run_date = run_date or datetime.now().date()
    session = target_session_date(run_date)
    token = _login_token()

    checks: dict[str, Any] = {}
    checks.update({f"route.{k}": v for k, v in check_routes().items()})
    checks.update({f"data.{k}": v for k, v in check_freshness(session).items()})
    checks.update({f"api.{k}": v for k, v in check_apis(token).items()})

    passed = sum(1 for c in checks.values() if c["status"] == OK)
    return {
        "schema_version": 1,
        "run_date": run_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_date": session.isoformat(),
        "market": {
            "run_date_is_trading_day": is_trading_day(run_date),
            "run_date_holiday": holiday_name(run_date),
        },
        "auth_mode": "token" if token else "unauthenticated",
        "summary": {
            "total": len(checks),
            "passed": passed,
            "warn": sum(1 for c in checks.values() if c["status"] == WARN),
            "failed": sum(1 for c in checks.values() if c["status"] == FAIL),
        },
        "checks": checks,
    }


def write_report(report: dict[str, Any], out_dir: Path | None = None) -> Path:
    directory = out_dir or OUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"quant_{report['run_date'].replace('-', '')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="야간 도그푸딩 정량 체크 (read-only)")
    parser.add_argument("--date", help="실행일 YYYY-MM-DD (기본: 오늘)")
    parser.add_argument("--out-dir", help="출력 디렉토리")
    args = parser.parse_args()

    run_date = date.fromisoformat(args.date) if args.date else None
    report = build_report(run_date)
    path = write_report(report, Path(args.out_dir) if args.out_dir else None)
    s = report["summary"]
    print(f"{path}  —  통과 {s['passed']}/{s['total']} (warn {s['warn']} / fail {s['failed']})")
    return 1 if s["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
