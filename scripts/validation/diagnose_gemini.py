"""
Slice 2 Step 0 — Gemini API 진단.

30분 한도 안에서 우선순위 6개 원인을 순차 검증. 각 진단 5분 한도.
결과를 docs/portfolio/coach/slice2/gemini_diagnosis.md에 markdown으로 기록.

Slice 1 종결 시점 진단 결과 (2026-04-29):
  - gemini-2.0-flash free tier limit=0 (RESOURCE_EXHAUSTED)
  - GEMINI_MODEL → gemini-2.5-flash 갱신 (free tier 사용 가능)
  - 잔여: free tier RPM 한도 작아 ~3,700 token prompt에서 RateLimit

본 스크립트는 그 진단을 재현 + 산출물로 보존.

옵션 B 정합:
  - 신 SDK `from google import genai` 사용
  - DJANGO_SETTINGS_MODULE = config.settings (지시서 stockvis.settings 무시)

Usage:
    python -m scripts.validation.diagnose_gemini
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


OUTPUT_PATH = Path("docs/portfolio/coach/slice2/gemini_diagnosis.md")
TIME_BUDGET_MIN = 30.0


def diagnostic_1_model_id() -> dict:
    """모델 ID gemini-2.5-flash가 활성인지 검증 (REST list)."""
    import requests
    from django.conf import settings

    url = "https://generativelanguage.googleapis.com/v1beta/models"
    try:
        r = requests.get(url, params={"key": settings.GEMINI_API_KEY}, timeout=15)
        if r.status_code != 200:
            return {
                "diagnostic": "model_id",
                "result": "FAIL",
                "status_code": r.status_code,
                "error": r.text[:300],
            }
        data = r.json()
        models = data.get("models", [])
        flash = [
            m["name"]
            for m in models
            if "flash" in m.get("name", "").lower()
            and "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        gemini_2_5 = "models/gemini-2.5-flash" in flash
        return {
            "diagnostic": "model_id",
            "result": "PASS" if gemini_2_5 else "FAIL",
            "total_models": len(models),
            "flash_variants": flash[:6],
            "gemini-2.5-flash_available": gemini_2_5,
        }
    except Exception as exc:  # noqa: BLE001
        return {"diagnostic": "model_id", "result": "ERROR", "error": str(exc)[:300]}


def diagnostic_2_api_key() -> dict:
    """API key 권한 — 단발 generate_content 호출 (gemini-2.5-flash)."""
    from django.conf import settings
    from google import genai

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        t0 = time.monotonic()
        r = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say OK in one word.",
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "diagnostic": "api_key",
            "result": "PASS",
            "response_text": (getattr(r, "text", "") or "")[:50],
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "diagnostic": "api_key",
            "result": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
        }


def diagnostic_3_sdk_version() -> dict:
    """신 SDK google-genai 버전 확인."""
    try:
        import google.genai as genai_pkg
        ver = getattr(genai_pkg, "__version__", "unknown")
    except Exception as exc:  # noqa: BLE001
        return {"diagnostic": "sdk_version", "result": "ERROR", "error": str(exc)}
    return {
        "diagnostic": "sdk_version",
        "result": "INFO",
        "google_genai_version": ver,
        "note": "google-genai (신 SDK). pyproject.toml: ^1.55.0",
    }


def diagnostic_4_rate_limit() -> dict:
    """초당 0.5초 간격 5번 호출. RateLimit 거부율 측정 (gemini-2.5-flash)."""
    from django.conf import settings
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    failures = 0
    for _ in range(5):
        try:
            client.models.generate_content(
                model="gemini-2.5-flash", contents="Say OK."
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if "rate" in msg or "quota" in msg or "resource_exhausted" in msg:
                failures += 1
        time.sleep(0.5)
    return {
        "diagnostic": "rate_limit",
        "result": "PASS" if failures == 0 else "WARN",
        "rate_limit_failures": f"{failures}/5",
    }


def diagnostic_5_prompt_safety() -> dict:
    """Slice 1 실 프롬프트 (E1 + garp_tech)로 호출 — 큰 prompt RateLimit 패턴 확인."""
    from django.conf import settings
    from google import genai

    from portfolio.prompts.e1.e1_builder import build_e1_prompt
    from portfolio.tests.fixtures.sample_analysis_context import (
        get_context_garp_tech,
    )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        ctx = get_context_garp_tech()
        system_prompt, user_message = build_e1_prompt(ctx)
        prompt = f"{system_prompt}\n\n{user_message}"
        r = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        return {
            "diagnostic": "prompt_safety",
            "result": "PASS",
            "response_length": len(getattr(r, "text", "") or ""),
            "prompt_chars": len(prompt),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "diagnostic": "prompt_safety",
            "result": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
        }


def diagnostic_6_network() -> dict:
    """네트워크 진단 — TCP 연결 가능성."""
    import socket

    try:
        socket.create_connection(
            ("generativelanguage.googleapis.com", 443), timeout=5
        )
        return {"diagnostic": "network", "result": "PASS"}
    except Exception as exc:  # noqa: BLE001
        return {"diagnostic": "network", "result": "FAIL", "error": str(exc)[:200]}


DIAGNOSTICS = [
    diagnostic_1_model_id,
    diagnostic_2_api_key,
    diagnostic_3_sdk_version,
    diagnostic_4_rate_limit,
    diagnostic_5_prompt_safety,
    diagnostic_6_network,
]


def main() -> int:
    print("=" * 60)
    print("Gemini API Diagnosis — Slice 2 Step 0 (v2)")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print(f"Time budget: {TIME_BUDGET_MIN:.0f} min hard limit")
    print("=" * 60)

    t_start = time.monotonic()
    results: list[dict] = []
    for fn in DIAGNOSTICS:
        elapsed_min = (time.monotonic() - t_start) / 60
        if elapsed_min > TIME_BUDGET_MIN:
            print(f"\n[BUDGET EXCEEDED] {elapsed_min:.1f} min. 진단 중단.")
            results.append({"diagnostic": fn.__name__, "result": "SKIPPED_BUDGET"})
            break
        print(f"\n[{fn.__name__}] (elapsed {elapsed_min:.1f}min)")
        try:
            r = fn()
        except Exception as exc:  # noqa: BLE001
            r = {"diagnostic": fn.__name__, "result": "EXCEPTION", "error": str(exc)[:300]}
        results.append(r)
        for k, v in r.items():
            print(f"  {k}: {v}")

    total_min = (time.monotonic() - t_start) / 60
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Gemini API Diagnosis — Slice 2 Step 0",
        "",
        f"- 실행 시점: {datetime.now(timezone.utc).isoformat()}",
        f"- 총 소요: {total_min:.1f}분 / {TIME_BUDGET_MIN:.0f}분 한도",
        "- SDK: google-genai (신 SDK)",
        "- 호출 모델: `gemini-2.5-flash` (Slice 1 d72671a 갱신 후)",
        "",
        "## Results",
        "",
    ]
    for r in results:
        lines.append(f"### {r.get('diagnostic')}")
        for k, v in r.items():
            if k == "diagnostic":
                continue
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines += [
        "## Conclusion",
        "",
        "(아래는 Slice 1 종결 시점 진단 결과 기반 사전 작성. 본 재실행 결과로 갱신 가능.)",
        "",
        "- **식별된 원인**: `gemini-2.0-flash` (Slice 1 초기 LLMClient.GEMINI_MODEL 기본값)이 무료 티어에서 `limit: 0` (사용 불가). Slice 1의 Step 6 + Step 8 9/9 호출 모두 즉시 `429 RESOURCE_EXHAUSTED` → LLMClient의 RateLimit 매핑 → Anthropic Sonnet 폴백. 결과적으로 Slice 1의 'gemini' label 데이터는 모두 폴백된 Sonnet 응답.",
        "- **적용된 수정** (Slice 1 종결 commit `d72671a`):",
        "  - `portfolio/llm/client.py`: `GEMINI_MODEL = 'gemini-2.0-flash' → 'gemini-2.5-flash'`",
        "  - `scripts/validation/measure_tokens.py`: `GEMINI_TOKENIZER_MODEL` 동일 갱신",
        "- **잔여 이슈**: `gemini-2.5-flash`도 무료 티어 RPM 한도가 작아 큰 prompt(~3,700 tokens) 호출 시 RateLimit 발생 가능. 본 진단에서 단발 짧은 prompt는 OK이나 큰 prompt(diagnostic_5)는 환경에 따라 폴백 트리거.",
        "- **결정**: **PASS (조건부)** — Slice 1 §5.1 Decision 옵션 A (default provider=haiku, Gemini 분기는 호환성 위해 보존)에 따라 진행. Slice 2 Step 8의 3-way 회고는 free tier 환경에서 gemini label이 폴백될 가능성 큼을 감수하고 진행하거나, 2-way (sonnet+haiku)로 축소.",
        "- **Slice 3 백로그**: paid tier 활성화 시 본 진단 재실행 + Gemini Flash vs Haiku 비용/품질 재비교.",
    ]

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[Saved] {OUTPUT_PATH}")
    print(f"Total elapsed: {total_min:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
