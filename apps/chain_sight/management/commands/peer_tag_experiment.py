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
JUDGED_CSV = os.path.join(OUTPUT_DIR, "peer_experiment_judged.csv")
AUDIT_CSV = os.path.join(OUTPUT_DIR, "peer_experiment_audit.csv")
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
    "반드시 JSON만 출력(설명·마크다운 금지):\n"
    '{"domain_tag": "명사구", "confidence": 0.0, '
    '"rationale": {"claim": "판단 근거 1문장", "claim_type": "known_fact", '
    '"basis_hint": "근거 힌트", "counter_signal": "반대 신호(없으면 빈 문자열)"}}\n'
    "- claim_type: known_fact(확실히 아는 사실)|inference(추론)|uncertain(불확실) 중 하나.\n"
    "- rationale는 감사용 자기보고 — 왜 그 태그인지, 무엇이 판단을 뒤집을 수 있는지."
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


def _wrong_rate(counter):
    """WRONG / 판정 합. 판정 0이면 None."""
    total = sum(counter.values())
    return round(counter.get("WRONG", 0) / total, 3) if total else None


def aggregate(rows):
    """verdict 채운 결과 → 구간·claim_type·basis_hint·counter_signal 매트릭스. 순수 함수.

    verdict 어휘: BETTER/SAME/WRONG/'' (미채움). "왜 틀리는가" 매트릭스(패치2):
      - by_claim_type: claim_type별 WRONG율(known_fact가 틀리면 위험 신호).
      - by_basis_hint_present: 근거 힌트 유무별 WRONG율.
      - by_counter_signal: counter_signal 존재군 vs 부재군 WRONG율 차이.
    """
    from collections import Counter, defaultdict

    by_cell = defaultdict(Counter)
    by_variant = defaultdict(Counter)
    by_claim_type = defaultdict(Counter)
    by_basis_hint = defaultdict(Counter)   # present|absent
    by_counter = defaultdict(Counter)      # present|absent
    for r in rows:
        v = (r.get("verdict") or "").strip().upper()
        if not v:
            continue
        by_cell[(r.get("mcap_tercile", ""), r.get("industry_same", ""))][v] += 1
        by_variant[r.get("prompt_variant", "")][v] += 1
        by_claim_type[(r.get("claim_type") or "none").strip().lower()][v] += 1
        by_basis_hint["present" if (r.get("basis_hint") or "").strip() else "absent"][v] += 1
        by_counter["present" if (r.get("counter_signal") or "").strip() else "absent"][v] += 1

    return {
        "by_cell": {k: dict(v) for k, v in by_cell.items()},
        "by_variant": {k: dict(v) for k, v in by_variant.items()},
        "by_claim_type": {k: dict(v) for k, v in by_claim_type.items()},
        "by_claim_type_wrong_rate": {k: _wrong_rate(v) for k, v in by_claim_type.items()},
        "by_basis_hint_wrong_rate": {k: _wrong_rate(v) for k, v in by_basis_hint.items()},
        "counter_signal_wrong_rate": {k: _wrong_rate(v) for k, v in by_counter.items()},
    }


LOW_GROUNDING = 0.5  # 저접지 플래그 임계(해석용)


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def aggregate_v2(rows):
    """판정 병합 rows → 구간별 결정론 지표(채점 LLM 0). 순수 함수.

    구간(6구획: mcap_tercile × industry_same)별:
      avg_grounded · low_grounding_rate · market_mismatch_rate · overconfident_rate · n
    + by_variant 접지 격차(㉮ vs ㉯) + dict_gap 빈출(사전 보강 감사).
    """
    import collections

    def _true(v):
        return str(v).strip().lower() == "true"

    by_cell = collections.defaultdict(list)
    by_variant = collections.defaultdict(list)
    gap_freq = collections.Counter()
    for r in rows:
        gr = _fnum(r.get("grounded_ratio"))
        cell = (r.get("mcap_tercile", ""), r.get("industry_same", ""))
        rec = {
            "gr": gr,
            "low": (gr is not None and gr < LOW_GROUNDING),
            "mm": _true(r.get("market_mismatch")),
            "oc": _true(r.get("overconfident")),
        }
        by_cell[cell].append(rec)
        by_variant[r.get("prompt_variant", "")].append(rec)
        for t in (r.get("dict_gap_terms", "") or "").split(" | "):
            if t.strip():
                gap_freq[t.strip()] += 1

    def _summ(recs):
        grs = [x["gr"] for x in recs if x["gr"] is not None]
        n = len(recs)
        return {
            "n": n,
            "avg_grounded": round(sum(grs) / len(grs), 3) if grs else None,
            "low_grounding_rate": round(sum(x["low"] for x in recs) / n, 3) if n else None,
            "market_mismatch_rate": round(sum(x["mm"] for x in recs) / n, 3) if n else None,
            "overconfident_rate": round(sum(x["oc"] for x in recs) / n, 3) if n else None,
        }

    return {
        "by_cell": {f"{k[0]}·{k[1]}": _summ(v) for k, v in by_cell.items()},
        "by_variant": {k: _summ(v) for k, v in by_variant.items()},
        "dict_gap_top": gap_freq.most_common(20),
    }


def audit_sample(rows, n_worst=10, n_best=8):
    """사람 감사용 표본: 최악(저접지·과신·불일치 우선) n_worst + 최상 접지 n_best.

    최악은 grounded_ratio 오름차순(동률 시 overconfident·market_mismatch 우선).
    """
    def _true(v):
        return str(v).strip().lower() == "true"

    scored = [r for r in rows if _fnum(r.get("grounded_ratio")) is not None]
    worst = sorted(
        scored,
        key=lambda r: (_fnum(r.get("grounded_ratio")),
                       -(int(_true(r.get("overconfident"))) + int(_true(r.get("market_mismatch"))))),
    )[:n_worst]
    best = sorted(scored, key=lambda r: -_fnum(r.get("grounded_ratio")))[:n_best]
    # 기존 라벨 보존: 이미 verdict/audit_verdict 값이 있는 행은 항상 표본 포함(대조용).
    labeled = [r for r in rows
               if (r.get("verdict") or "").strip() or (r.get("audit_verdict") or "").strip()]
    seen, out = set(), []
    for r in labeled + worst + best:
        k = (r["symbol_a"], r["symbol_b"], r["prompt_variant"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


class Command(BaseCommand):
    help = "PEER 추측 태깅 표본 실험(LLM 240 한정, DB 무기록)"

    def add_arguments(self, parser):
        parser.add_argument("--sample", action="store_true", help="층화 표본 CSV 생성(LLM 무호출)")
        parser.add_argument("--run", action="store_true", help="LLM sweep(240 한정) — 게이트")
        parser.add_argument("--judge", action="store_true", help="결정론 판정 컬럼 병합(LLM 0)")
        parser.add_argument("--aggregate", action="store_true", help="판정 집계 v2 + 감사 표본")

    def handle(self, *args, **opts):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if opts["sample"]:
            self._sample()
        elif opts["run"]:
            self._run()
        elif opts["judge"]:
            self._judge()
        elif opts["aggregate"]:
            self._aggregate()
        else:
            self.stdout.write("옵션 필요: --sample | --run | --judge | --aggregate")

    # ── S1/S2: 결정론 판정 병합(채점 LLM 0) ──
    def _judge(self):
        import json
        from apps.chain_sight.models.relation_discovery import PriceCoMovement
        from apps.chain_sight.services.peer_adjudicator import (
            ground_claim, load_dict, market_flag, overconfident, quartiles,
        )
        src = JUDGED_CSV if False else RESULT_CSV
        if not os.path.exists(src):
            self.stderr.write("결과 CSV 없음 — 먼저 --run.")
            return
        with open(src, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        dct = load_dict()
        syms = {r["symbol_a"] for r in rows} | {r["symbol_b"] for r in rows}
        desc = dict(Stock.objects.filter(symbol__in=syms).values_list("symbol", "description"))

        def corr_of(a, b):
            pcm = PriceCoMovement.objects.filter(
                symbol_a__in=[a, b], symbol_b__in=[a, b]
            ).order_by("period").values_list("correlation", flat=True).first()
            return float(pcm) if pcm is not None else None

        # ── Pass 1: grounding + correlation + conf ──
        for r in rows:
            raw = (r.get("rationale_A") or "").strip() or (r.get("rationale_B") or "").strip()
            claim = ""
            if raw:
                try:
                    claim = json.loads(raw).get("claim", "")
                except Exception:  # noqa: BLE001
                    claim = ""
            g = ground_claim(claim, r["symbol_a"], r["symbol_b"],
                             desc.get(r["symbol_a"], ""), desc.get(r["symbol_b"], ""), dct)
            r["grounded_ratio"] = g["grounded_ratio"] if g["grounded_ratio"] is not None else ""
            r["grounded_en"] = f"{g['grounded_en']}/{g['en_total']}"
            r["grounded_syn"] = f"{g['grounded_syn']}/{g['syn_total']}"
            r["ungrounded_terms"] = " | ".join(g["ungrounded_terms"])
            r["dict_gap_terms"] = " | ".join(g["dict_gap_terms"])
            r["correlation"] = corr_of(r["symbol_a"], r["symbol_b"])
            r["_conf"] = float(r["llm_conf"]) if r.get("llm_conf") else None
            r["_gr"] = g["grounded_ratio"]

        # ── 사분위 ──
        corr_q1, _ = quartiles([r["correlation"] for r in rows])
        _, conf_q3 = quartiles([r["_conf"] for r in rows])
        gr_q1, _ = quartiles([r["_gr"] for r in rows])

        # ── Pass 2: market_mismatch + overconfident ──
        for r in rows:
            r["market_mismatch"] = market_flag(r["correlation"], r["_conf"], corr_q1, conf_q3)
            r["overconfident"] = overconfident(r.get("claim_type"), r["_gr"], gr_q1)
            r["correlation"] = "" if r["correlation"] is None else round(r["correlation"], 4)
            del r["_conf"], r["_gr"]

        cols = list(rows[0].keys())
        with open(JUDGED_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        self.stdout.write(
            f"✅ 판정 병합 {len(rows)}행 → {JUDGED_CSV} (LLM 0). "
            f"사분위: corr_q1={corr_q1} conf_q3={conf_q3} gr_q1={gr_q1}"
        )

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

        import json
        from apps.chain_sight.services.domain_tagging import extract_rationale, parse_llm_json
        from apps.market_pulse.llm.client import generate_with_circuit

        calls, fail = 0, 0
        for r in rows:
            system, contents = build_experiment_prompt(r, names, industries)
            r.setdefault("rationale_A", "")
            r.setdefault("rationale_B", "")
            try:
                resp = generate_with_circuit(system_instruction=system, contents=contents)
                calls += 1
                out = parse_llm_json(getattr(resp, "text", "") or "")
                rat = extract_rationale(out) if out else None
                # 패치2: 형식붕괴 = JSON 파싱 실패 OR rationale 누락(rationale도 측정 대상).
                if not out or rat is None:
                    fail += 1
                if out:
                    r["llm_tag"] = out.get("domain_tag", "")
                    r["llm_conf"] = out.get("confidence", "")
                    r["normalized_bucket"] = industry_to_bucket(industries.get(r["symbol_a"]))
                if rat:
                    rj = json.dumps(rat, ensure_ascii=False)
                    r[f"rationale_{r['prompt_variant']}"] = rj  # 변형별 컬럼(㉮/㉯)
                    r["claim_type"] = rat["claim_type"]
                    r["basis_hint"] = rat["basis_hint"]
                    r["counter_signal"] = rat["counter_signal"]
            except Exception as e:  # noqa: BLE001
                fail += 1
                self.stderr.write(f"  LLM 오류: {type(e).__name__}: {e}")
            r["verdict"] = ""  # 병진 검수용 빈칸
            if calls >= 10 and fail / calls > 0.10:
                self.stderr.write(f"HALT: 형식붕괴(태그·rationale) {fail}/{calls} > 10%.")
                break
            time.sleep(RATE_SLEEP_S)

        with open(RESULT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "symbol_a", "symbol_b", "mcap_tercile", "industry_same", "prompt_variant",
                "llm_tag", "llm_conf", "normalized_bucket",
                "rationale_A", "rationale_B", "claim_type", "basis_hint", "counter_signal",
                "verdict",
            ])
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})
        self.stdout.write(
            f"✅ LLM 호출 {calls}회(240쌍 한정) · 형식붕괴 {fail} → {RESULT_CSV}"
        )

    def _aggregate(self):
        import json
        src = JUDGED_CSV if os.path.exists(JUDGED_CSV) else RESULT_CSV
        if not os.path.exists(src):
            self.stderr.write("CSV 없음 — 먼저 --judge.")
            return
        with open(src, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        if src == JUDGED_CSV:
            agg = aggregate_v2(rows)
            self.stdout.write("── 구간별 결정론 판정(채점 LLM 0) ──")
            for cell, s in sorted(agg["by_cell"].items()):
                self.stdout.write(
                    f"  {cell:8} n={s['n']:3} avg_grounded={s['avg_grounded']} "
                    f"low={s['low_grounding_rate']} mismatch={s['market_mismatch_rate']} "
                    f"overconf={s['overconfident_rate']}"
                )
            va = agg["by_variant"]
            self.stdout.write(
                f"── ㉮㉯ 접지 격차: A avg={va.get('A',{}).get('avg_grounded')} "
                f"B avg={va.get('B',{}).get('avg_grounded')} ──"
            )
            self.stdout.write(f"── dict_gap 빈출(사전 보강 감사): {agg['dict_gap_top'][:12]} ──")
            # 감사 표본 추출 → 검수 도구 로드 호환(grounded_ratio 헤더=감사 모드)
            sample = audit_sample(rows)
            with open(AUDIT_CSV, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(sample)
            self.stdout.write(f"✅ 감사 표본 {len(sample)}건 → {AUDIT_CSV}")
            with open(os.path.join(OUTPUT_DIR, "aggregate_v2.json"), "w", encoding="utf-8") as f:
                json.dump(agg, f, ensure_ascii=False, indent=2)
            return

        # 판정 전(구 verdict 집계) 폴백
        agg = aggregate(rows)
        self.stdout.write(f"구간별: {agg['by_cell']}")
        self.stdout.write(f"㉮㉯: {agg['by_variant']}")
