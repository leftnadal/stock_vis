"""CS-P1B Slice2/3: evidence 계층 관계 쌍의 연결 강도(초과수익 동조성) 계산·기록.

강도 = 두 종목 초과수익(일간수익 − SPY 벤치마크수익)의 90거래일 Pearson 상관.
서비스: apps.chain_sight.services.excess_return_sync (순수 계층 + 얇은 DB 어댑터).

기본 dry-run(대상·계산가능 카운트·null 사유·분포 요약). 실제 기록은 --apply
(병진 GO 게이트 뒤에만). 쓰기는 QuerySet.update()로 sync_* 3컬럼만 갱신 —
save() 미호출이라 relation_status·last_observed_at·neo4j_dirty·previous_status 무접촉
(OUT 스코프: 기존 status·데이터 변경 금지 준수). evidence 계층만 대상.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services import excess_return_sync as ers

EVIDENCE_LAYER = "evidence"


def _quantiles(vals, qs=(0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)):
    if not vals:
        return {}
    s = sorted(vals)
    out = {}
    for q in qs:
        idx = min(len(s) - 1, int(round(q * (len(s) - 1))))
        out[q] = s[idx]
    return out


class Command(BaseCommand):
    help = (
        "evidence 계층 관계 쌍 연결 강도(초과수익 동조성) 계산. "
        "기본 dry-run, --apply 로 sync_* 기록(.update, 기존 필드 무접촉)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="실제 쓰기(미지정=dry-run).")
        parser.add_argument("--window-days", type=int, default=ers.DEFAULT_WINDOW_DAYS)
        parser.add_argument("--min-obs", type=int, default=ers.DEFAULT_MIN_OBS)
        parser.add_argument(
            "--benchmark", type=str, default=ers.BENCHMARK_INDEX,
            help="macro.MarketIndexPrice 인덱스 심볼(기본 SPY).",
        )

    def handle(self, *args, **opts):
        window_days = opts["window_days"]
        min_obs = opts["min_obs"]
        bench_sym = opts["benchmark"]

        asof = timezone.now().date()
        cutoff = ers._cutoff(asof)

        bench_returns = ers.load_benchmark_returns(cutoff, index_symbol=bench_sym)
        self.stdout.write("=== CS-P1B 연결 강도 계산 ===")
        self.stdout.write(
            f"  벤치마크={bench_sym}  벤치 관측일수={len(bench_returns)}  "
            f"윈도우={window_days}거래일  최소관측={min_obs}  cutoff={cutoff}"
        )
        if len(bench_returns) < min_obs:
            self.stdout.write(self.style.ERROR(
                f"  벤치마크 관측 {len(bench_returns)} < 최소 {min_obs} — 전량 계산 불가. 중단."
            ))
            return

        ev = (
            RelationConfidence.objects.filter(serving_layer=EVIDENCE_LAYER)
            .values_list("id", "symbol_a", "symbol_b", "relation_type")
        )
        target = len(ev)

        returns_cache = {}
        results = []          # (pk, relation_type, strength)
        null_reasons = {}     # reason prefix → count
        sec_types = {"COMPETES_WITH", "SUPPLIES_TO", "PARTNER_WITH", "DEPENDS_ON"}

        for pk, a, b, rtype in ev:
            strength, n_obs, reason = ers.compute_pair_strength(
                a, b, bench_returns, returns_cache, cutoff,
                window_days=window_days, min_obs=min_obs,
            )
            if strength is None:
                key = reason.split(":")[0] if reason else "unknown"
                null_reasons[key] = null_reasons.get(key, 0) + 1
                results.append((pk, rtype, None))
            else:
                results.append((pk, rtype, strength))

        computable = [r for r in results if r[2] is not None]
        n_ok = len(computable)
        all_vals = [r[2] for r in computable]
        sec_vals = [r[2] for r in computable if r[1] in sec_types]
        cm_vals = [r[2] for r in computable if r[1] == "CO_MENTIONED"]

        self.stdout.write(f"  evidence 대상 쌍: {target}")
        self.stdout.write(f"  계산가능(strength 산출): {n_ok}  ({n_ok/target*100:.1f}%)")
        self.stdout.write(f"  null: {target - n_ok}  사유분해={null_reasons}")

        def _summ(name, vals):
            if not vals:
                self.stdout.write(f"    {name}: n=0")
                return
            mean = sum(vals) / len(vals)
            q = _quantiles(vals)
            self.stdout.write(
                f"    {name}: n={len(vals)} mean={mean:+.3f} "
                f"min={q[0.0]:+.3f} p20={q[0.2]:+.3f} p50={q[0.5]:+.3f} "
                f"p80={q[0.8]:+.3f} max={q[1.0]:+.3f}"
            )

        self.stdout.write("  -- 강도 분포 --")
        _summ("전체", all_vals)
        _summ("SEC계(4종)", sec_vals)
        _summ("CO_MENTIONED", cm_vals)
        self.stdout.write(
            "  before 참조(선행 감사 강도-주가 상관 0.45/0.25/0.22)와 정성 대조는 원장에 기록."
        )

        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("dry-run (--apply 미지정): 쓰기 0건"))
            return

        now = timezone.now()
        written = 0
        with transaction.atomic():
            for pk, rtype, strength in results:
                if strength is None:
                    continue  # 관측 부족 행은 미기록(null 유지)
                RelationConfidence.objects.filter(pk=pk).update(
                    sync_strength=strength,
                    sync_window_days=window_days,
                    sync_computed_at=now,
                )
                written += 1
        self.stdout.write(self.style.SUCCESS(f"기록 완료: sync_strength {written}행 (.update)"))
