"""L2-X — PEER 추측 태깅 표본 실험 (⑳-3 S3-MINDMAP 패치1).

PEER_OF는 SEC 근거가 없어 도메인 태그가 없다. LLM이 '추측'으로 얼마나 맞추는지 표본으로
측정한다(교체/하이브리드/현행 판정 재료). DB 무기록 — 비교 CSV만 산출.

층화 6구획 = 시총 3분위(상/중/하) × industry(동일/상이) × 40쌍 = 240쌍.
구획당 프롬프트 ㉮(심볼만) 20 + ㉯(+회사명·industry) 20.

    python manage.py peer_tag_experiment --sample     # 표본 CSV 생성(LLM 무호출, 결정론·시드고정)
    python manage.py peer_tag_experiment --run         # LLM sweep(240 한정) → 비교 CSV. ★게이트
    python manage.py peer_tag_experiment --aggregate    # verdict 채운 뒤 구간별 BETTER/SAME/WRONG

★ mcap 게이트: 시총 커버리지가 층화에 부족하면 --sample이 HALT(데이터 백필 선행).
★ LLM 240 한정: --run은 표본 CSV의 240행만 호출하고 호출 수를 로그로 증빙. 형식붕괴>10% HALT.
"""

import csv
import os
import random

from django.core.management.base import BaseCommand

from apps.chain_sight.models import RelationConfidence
from packages.shared.stocks.models import Stock

OUTPUT_DIR = "outputs/peer_experiment"
SAMPLE_CSV = os.path.join(OUTPUT_DIR, "peer_sample_240.csv")
RESULT_CSV = os.path.join(OUTPUT_DIR, "peer_experiment_result.csv")
SEED = 20260803  # 재현성 고정 시드
PER_CELL = 40
CELLS = 6           # 3 mcap × 2 industry
TARGET = PER_CELL * CELLS  # 240
RATE_SLEEP_S = 4.2

# 정규화 태그 어휘(53종 우선 매핑 대상) — L2-X는 신규 태그 허용하되 별도 표기.
from apps.chain_sight.services.industry_buckets import industry_to_bucket


def _mcap_map(symbols):
    """symbol → market_capitalization(있는 것만)."""
    return {
        s: mc
        for s, mc in Stock.objects.filter(symbol__in=symbols)
        .exclude(market_capitalization__isnull=True)
        .exclude(market_capitalization=0)
        .values_list("symbol", "market_capitalization")
    }


def _industry_map(symbols):
    return {
        s: ind
        for s, ind in Stock.objects.filter(symbol__in=symbols)
        .exclude(industry__isnull=True)
        .exclude(industry="")
        .values_list("symbol", "industry")
    }


def build_sample(peers, mcap_map, industry_map):
    """층화 표본 계획. 반환 (sample_rows, halt_reason|None).

    mcap 3분위 경계는 표본 모집단(양쪽 mcap+industry 보유 쌍)의 페어 최소 시총 기준.
    """
    pop = []
    for p in peers:
        a, b = p["symbol_a"], p["symbol_b"]
        if a in mcap_map and b in mcap_map and a in industry_map and b in industry_map:
            pair_mcap = min(float(mcap_map[a]), float(mcap_map[b]))
            same_ind = industry_map[a].strip().lower() == industry_map[b].strip().lower()
            pop.append((a, b, pair_mcap, same_ind))

    if len(pop) < TARGET:
        return [], (
            f"mcap 게이트 HALT: 층화 모집단 {len(pop)} < 목표 {TARGET} "
            f"(mcap 보유 심볼 부족). market_capitalization 백필 선행 필요."
        )

    mcaps = sorted(pair_mcap for _, _, pair_mcap, _ in pop)
    t1 = mcaps[len(mcaps) // 3]
    t2 = mcaps[2 * len(mcaps) // 3]

    def tercile(m):
        return "하" if m < t1 else ("중" if m < t2 else "상")

    # 6구획 버킷
    cells = {(t, si): [] for t in ("상", "중", "하") for si in (True, False)}
    for a, b, pm, si in pop:
        cells[(tercile(pm), si)].append((a, b, pm, si))

    rng = random.Random(SEED)
    sample = []
    for (t, si), rows in cells.items():
        if len(rows) < PER_CELL:
            return [], (
                f"mcap 게이트 HALT: 구획({t},{'동일' if si else '상이'}) "
                f"모집단 {len(rows)} < {PER_CELL}. 층화 불가."
            )
        rng.shuffle(rows)
        picked = rows[:PER_CELL]
        for i, (a, b, pm, s) in enumerate(picked):
            variant = "A" if i < PER_CELL // 2 else "B"  # 앞 20=㉮, 뒤 20=㉯
            sample.append({
                "symbol_a": a, "symbol_b": b,
                "mcap_tercile": t, "industry_same": "동일" if s else "상이",
                "prompt_variant": variant,
            })
    return sample, None


# ── 프롬프트 2안 (LLMClient 경유, 직접 호출 금지) ──
_SYSTEM = (
    "너는 미국 상장사 간 관계를 분류하는 금융 애널리스트다. 두 Peer 종목이 어떤 사업 "
    "도메인에서 경쟁·연결되는지 짧은 한국어 명사구 1개로 태깅한다. "
    '반드시 JSON만 출력: {"domain_tag": "명사구", "confidence": 0.0}'
)


def build_experiment_prompt(row, names, industries):
    """㉮ 심볼만 / ㉯ +회사명·industry. (system, contents) 반환."""
    a, b = row["symbol_a"], row["symbol_b"]
    if row["prompt_variant"] == "A":
        user = f"두 Peer 종목: {a} ↔ {b}"
    else:
        user = (
            f"두 Peer 종목:\n"
            f"- {a} ({names.get(a, '')}, {industries.get(a, '')})\n"
            f"- {b} ({names.get(b, '')}, {industries.get(b, '')})"
        )
    return _SYSTEM, [user]


def aggregate(rows):
    """verdict 채운 결과 → 구간별 BETTER/SAME/WRONG율 + ㉮㉯ 격차. 순수 함수.

    verdict 어휘: BETTER(㉯가 더 나음)/SAME/WRONG(둘 다 틀림)/'' (미채움).
    """
    from collections import Counter, defaultdict

    by_cell = defaultdict(Counter)
    by_variant = defaultdict(Counter)
    for r in rows:
        v = (r.get("verdict") or "").strip().upper()
        if not v:
            continue
        cell = (r.get("mcap_tercile", ""), r.get("industry_same", ""))
        by_cell[cell][v] += 1
        by_variant[r.get("prompt_variant", "")][v] += 1
    return {"by_cell": {k: dict(v) for k, v in by_cell.items()},
            "by_variant": {k: dict(v) for k, v in by_variant.items()}}


class Command(BaseCommand):
    help = "PEER 추측 태깅 표본 실험(LLM 240 한정, DB 무기록)"

    def add_arguments(self, parser):
        parser.add_argument("--sample", action="store_true", help="층화 표본 CSV 생성(LLM 무호출)")
        parser.add_argument("--run", action="store_true", help="LLM sweep(240 한정) — 게이트")
        parser.add_argument("--aggregate", action="store_true", help="verdict 채운 뒤 집계")

    def handle(self, *args, **opts):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if opts["sample"]:
            self._sample()
        elif opts["run"]:
            self._run()
        elif opts["aggregate"]:
            self._aggregate()
        else:
            self.stdout.write("옵션 필요: --sample | --run | --aggregate")

    def _sample(self):
        peers = list(
            RelationConfidence.objects.filter(relation_type="PEER_OF")
            .exclude(domain_review_status="rejected")
            .values("symbol_a", "symbol_b")
        )
        syms = {p["symbol_a"] for p in peers} | {p["symbol_b"] for p in peers}
        sample, halt = build_sample(peers, _mcap_map(syms), _industry_map(syms))
        if halt:
            self.stderr.write(halt)
            return
        with open(SAMPLE_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "symbol_a", "symbol_b", "mcap_tercile", "industry_same", "prompt_variant",
            ])
            w.writeheader()
            w.writerows(sample)
        self.stdout.write(f"✅ 표본 {len(sample)}쌍 → {SAMPLE_CSV}")

    def _run(self):
        import time
        if not os.path.exists(SAMPLE_CSV):
            self.stderr.write("표본 CSV 없음 — 먼저 --sample.")
            return
        with open(SAMPLE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        syms = {r["symbol_a"] for r in rows} | {r["symbol_b"] for r in rows}
        names = dict(Stock.objects.filter(symbol__in=syms).values_list("symbol", "stock_name"))
        industries = _industry_map(syms)

        from apps.chain_sight.services.domain_tagging import parse_llm_json
        from apps.market_pulse.llm.client import generate_with_circuit

        calls, fail = 0, 0
        for r in rows:
            system, contents = build_experiment_prompt(r, names, industries)
            try:
                resp = generate_with_circuit(system_instruction=system, contents=contents)
                calls += 1
                out = parse_llm_json(getattr(resp, "text", "") or "")
                if not out:
                    fail += 1
                    r["llm_tag"], r["llm_conf"] = "", ""
                else:
                    tag = out.get("domain_tag", "")
                    r["llm_tag"] = tag
                    r["llm_conf"] = out.get("confidence", "")
                    r["normalized_bucket"] = industry_to_bucket(industries.get(r["symbol_a"]))
            except Exception as e:  # noqa: BLE001
                fail += 1
                self.stderr.write(f"  LLM 오류: {type(e).__name__}: {e}")
            r["verdict"] = ""  # 병진 검수용 빈칸
            if calls >= 10 and fail / calls > 0.10:
                self.stderr.write(f"HALT: 형식붕괴 {fail}/{calls} > 10%.")
                break
            time.sleep(RATE_SLEEP_S)

        with open(RESULT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "symbol_a", "symbol_b", "mcap_tercile", "industry_same", "prompt_variant",
                "llm_tag", "llm_conf", "normalized_bucket", "verdict",
            ])
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})
        self.stdout.write(
            f"✅ LLM 호출 {calls}회(한정 {TARGET}) · 형식붕괴 {fail} → {RESULT_CSV}"
        )

    def _aggregate(self):
        if not os.path.exists(RESULT_CSV):
            self.stderr.write("결과 CSV 없음.")
            return
        with open(RESULT_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        agg = aggregate(rows)
        self.stdout.write(f"구간별: {agg['by_cell']}")
        self.stdout.write(f"㉮㉯: {agg['by_variant']}")
