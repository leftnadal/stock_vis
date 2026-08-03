"""SEC β G-e — v2 프롬프트 재추출 표본 측정 커맨드.

계약(SECB-GE-EXEC-1 · 정의서 개정 2026-08-03):
  - **prod 읽기전용**: RawDocumentStore / SupplyChainEvidence 를 read 만. 어떤 .save/.create/.update 도 없음.
  - **DB 쓰기 전면 0 (prod/dev)**: 결과는 var/secb_ge_v2_sample/ JSON 으로만 출력 (물리 격리 (b)).
  - **표본 5 고정**: --accessions 로 명시된 filing 만. 확장 금지.
  - **grounding = ground_evidence_g16 재사용** (순수 함수·LLM 0). LLM 은 추출에만 (filing당 1콜).
  - dry-run(기본): 프롬프트 조립·문자/토큰 추정만 (LLM 0). --execute 시에만 complete() 호출.
  - 재시도: 5xx 전송오류만 filing당 ≤1, 총 절대 상한 10콜.
"""

import json
import time
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from services.sec_pipeline.grounding import ground_evidence_g16
from services.sec_pipeline.grounding_backfill import build_source_text
from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence
from services.sec_pipeline.normalizer import filter_paragraphs, normalize_section_all
from services.sec_pipeline.prompts import (
    PROMPT_VERSION_V2,
    SUPPLY_CHAIN_EXTRACTION_PROMPT_V2,
)

MAX_EVIDENCE_CHARS = 300  # v1 프롬프트 "max 300 chars" 역산 (보고서 명기용)
MODEL = "gemini-2.5-flash"
GLOBAL_CALL_CAP = 10  # 절대 상한 (5 filings × (1 + 5xx재시도 1))
TAIL_STATUSES = ("partial_match", "not_found")


def _is_5xx(exc) -> bool:
    """전송오류(5xx) 판별 — 5xx 만 재시도 허용."""
    for attr in ("status_code", "code"):
        v = getattr(exc, attr, None)
        if isinstance(v, int) and 500 <= v < 600:
            return True
    s = str(exc).lower()
    return any(t in s for t in ("500", "502", "503", "504", "unavailable", "internal"))


def _v1_baseline(doc) -> dict:
    """해당 filing 의 v1 grounded(deterministic_v1) 등급 분포 — prod 읽기전용."""
    rows = SupplyChainEvidence.objects.filter(
        source_document=doc, grounding_method="deterministic_v1"
    ).values_list("grounding_status", flat=True)
    dist = Counter(rows)
    cites = sum(dist.values())
    tail = sum(dist.get(s, 0) for s in TAIL_STATUSES)
    return {
        "cites": cites,
        "tail": tail,
        "tail_rate": round(tail / cites, 4) if cites else None,
        "grade_dist": dict(dist),
    }


class Command(BaseCommand):
    help = "SEC β G-e: v2 프롬프트 재추출 표본 측정 (prod 읽기전용·파일 출력·DB 쓰기 0)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--accessions",
            nargs="+",
            required=True,
            help="대상 filing accession_no (명시 필수, 표본 5 고정)",
        )
        parser.add_argument(
            "--out-dir",
            default="var/secb_ge_v2_sample",
            help="JSON 출력 디렉토리 (gitignore)",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="LLM 호출 실행. 미지정 시 dry-run(프롬프트 조립·토큰 추정만, LLM 0).",
        )

    def handle(self, *args, **opts):
        accessions = opts["accessions"]
        out_dir = Path(opts["out_dir"])
        execute = opts["execute"]

        if len(accessions) > 5:
            raise CommandError(
                f"표본 {len(accessions)} > 5 — 확장 금지 (SECB-GE 불변). HALT."
            )

        out_dir.mkdir(parents=True, exist_ok=True)
        filings = []
        call_count = 0

        for acc in accessions:
            try:
                doc = RawDocumentStore.objects.select_related("symbol").get(
                    accession_no=acc
                )
            except RawDocumentStore.DoesNotExist:
                raise CommandError(f"filing not found: {acc} — HALT")

            symbol = doc.symbol.symbol
            company_name = getattr(doc.symbol, "stock_name", None) or symbol
            sections = {
                "item_1": doc.item_1_text,
                "item_1a": doc.item_1a_text,
                "item_7": doc.item_7_text,
            }
            # v1 파이프라인과 IDENTICAL 입력 재현 (tasks.py:205-206)
            combined = normalize_section_all(sections)
            paragraphs = filter_paragraphs(combined, max_paragraphs=15)
            paragraphs_text = "\n\n---\n\n".join(paragraphs)
            prompt = SUPPLY_CHAIN_EXTRACTION_PROMPT_V2.format(
                symbol=symbol,
                company_name=company_name,
                paragraphs=paragraphs_text,
            )

            source_text = build_source_text(doc)
            entry = {
                "accession": acc,
                "symbol": symbol,
                "fiscal_year": doc.fiscal_year,
                "paragraphs_count": len(paragraphs),
                "prompt_chars": len(prompt),
                "prompt_est_tokens": len(prompt) // 4,
                "v1": _v1_baseline(doc),
            }

            if not execute:
                entry["v2"] = None
                entry["prompt_preview_head"] = prompt[:400]
                filings.append(entry)
                self.stdout.write(
                    f"[dry-run] {symbol} {acc}: paras={len(paragraphs)} "
                    f"prompt_chars={len(prompt)} est_tok={len(prompt)//4}"
                )
                continue

            # ── --execute: LLM 호출 (filing당 1, 5xx 재시도 ≤1, 총 cap 10) ──
            citations, raw_count = self._extract_v2(
                prompt, symbol, acc, call_state=lambda: call_count
            )
            call_count = self._last_call_count

            graded = []
            gdist = Counter()
            for c in citations:
                ev = (c.get("evidence_text") or "").strip()
                res = ground_evidence_g16(ev, source_text)
                gdist[res.status] += 1
                graded.append(
                    {
                        "target_company_name": c.get("target_company_name"),
                        "relationship_type": c.get("relationship_type"),
                        "evidence_chars": len(ev),
                        "grounding_status": res.status,
                    }
                )
            v2_cites = len(graded)
            v2_tail = sum(gdist.get(s, 0) for s in TAIL_STATUSES)
            entry["v2"] = {
                "prompt_version": PROMPT_VERSION_V2,
                "cites": v2_cites,
                "tail": v2_tail,
                "tail_rate": round(v2_tail / v2_cites, 4) if v2_cites else None,
                "grade_dist": dict(gdist),
                "citations": graded,
            }
            filings.append(entry)
            self.stdout.write(
                f"[execute] {symbol} {acc}: v2 cites={v2_cites} tail={v2_tail} "
                f"dist={dict(gdist)}"
            )

        result = self._summarize(filings, execute, call_count)
        mode = "execute" if execute else "dryrun"
        out_path = out_dir / f"secb_ge_v2_sample_{mode}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        self.stdout.write(self.style.SUCCESS(f"→ {out_path}  (DB 쓰기 0)"))

    _last_call_count = 0

    def _extract_v2(self, prompt, symbol, acc, call_state):
        """complete() 1콜 (extractor.py:59-79 미러링). 5xx 만 ≤1 재시도, 총 cap 10."""
        from google.genai import types

        from packages.shared.llm import complete

        base = call_state()
        attempts = 0
        while True:
            if base + attempts + 1 > GLOBAL_CALL_CAP:
                raise CommandError(
                    f"LLM 호출 절대 상한 {GLOBAL_CALL_CAP} 도달 — HALT ({acc})"
                )
            attempts += 1
            try:
                response = complete(
                    prompt,
                    provider="gemini",
                    model=MODEL,
                    temperature=0.1,
                    response_format="json",
                    extra={
                        "thinking_config": types.ThinkingConfig(thinking_budget=0)
                    },
                )
                text = (
                    response.text
                    if hasattr(response, "text") and response.text
                    else "{}"
                )
                parsed = json.loads(text)
                rels = parsed.get("relationships", [])
                if not isinstance(rels, list):
                    rels = []
                self._last_call_count = base + attempts
                return rels, len(rels)
            except json.JSONDecodeError as e:
                raise CommandError(f"{acc}: JSON 파싱 실패 — HALT ({e})")
            except Exception as e:  # noqa: BLE001
                if _is_5xx(e) and attempts <= 1:
                    self.stderr.write(f"{acc}: 5xx 재시도 1회 ({e})")
                    time.sleep(2)
                    continue
                self._last_call_count = base + attempts
                raise CommandError(f"{acc}: 추출 실패 (5xx 아님/재시도 소진) — HALT ({e})")

    def _summarize(self, filings, execute, call_count):
        v1c = sum(f["v1"]["cites"] for f in filings)
        v1t = sum(f["v1"]["tail"] for f in filings)
        totals = {
            "v1_cites": v1c,
            "v1_tail": v1t,
            "v1_tail_rate": round(v1t / v1c, 4) if v1c else None,
        }
        if execute:
            v2c = sum(f["v2"]["cites"] for f in filings)
            v2t = sum(f["v2"]["tail"] for f in filings)
            totals.update(
                {
                    "v2_cites": v2c,
                    "v2_tail": v2t,
                    "v2_tail_rate": round(v2t / v2c, 4) if v2c else None,
                    "llm_calls": call_count,
                }
            )
        return {
            "meta": {
                "track": "SEC β G-e",
                "prompt_version_v2": PROMPT_VERSION_V2,
                "max_evidence_chars": MAX_EVIDENCE_CHARS,
                "model": MODEL,
                "mode": "execute" if execute else "dry-run",
                "db_writes": 0,
                "sample_size": len(filings),
            },
            "totals": totals,
            "filings": filings,
        }
