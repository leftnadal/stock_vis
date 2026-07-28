"""backfill_v2_regime_vectors — B1-S2 소급 국면 벡터 합성 management command.

소속: apps/market_pulse/management/commands (app 레이어 운영 커맨드).
역할: 과거 영업일(SPY 가격 존재일) 각각에 대해 현행 intraday regime 생성 로직을
  **as_of 매개변수화**로 소급 실행해 RegimeSnapshot 행을 idempotent 합성한다.
  벡터 의미론 단일소스: load_inputs(as_of=D) → coverage.evaluate → classifier →
  apply_hysteresis(시계열 순차 chaining). 별도 forward-fill/독자 합성 규칙 없음.

규약(B1-S2):
  - 대상 창 = --from(기본 2023-07-10) ~ 라이브 최초일 전날(하드 상한).
  - 기존 라이브 행 불가침: 창 필터 + get_or_create(신규만 생성) 이중 방어.
  - coverage 실측 저장(운영 동일 — leading gap은 저 coverage로 정직 기록).
  - is_finalized=True(확정 과거), snapshot_time/finalized_at 결정론적.
  - 소급 값 = 현재 vintage(D-B1-VINTAGE) — 개정 이력 미보존.

사용:
    python manage.py backfill_v2_regime_vectors --dry-run     # 후보 리포트(무쓰기)
    python manage.py backfill_v2_regime_vectors               # 전 영업일 합성
    python manage.py backfill_v2_regime_vectors --from 2023-07-10 --to 2026-04-26
    python manage.py backfill_v2_regime_vectors --limit 5     # 앞에서 N일만(테스트)

⚠️ migration 안에서 호출 금지. 운영자가 머지 후 수동 실행(병진).
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import date as date_cls
from datetime import datetime
from datetime import timezone as dt_timezone
from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Min

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime import classifier as classifier_mod
from apps.market_pulse.regime import coverage as coverage_mod
from apps.market_pulse.regime import inputs as inputs_mod

logger = logging.getLogger(__name__)

DEFAULT_FROM = date_cls(2023, 7, 10)
# 결정론적 스냅샷 시각: 각 영업일 D의 US 마감(≈16:00 ET = 20:00 UTC).
SNAPSHOT_HOUR_UTC = 20
# 합성행 provenance 마커(summary는 어떤 API에도 미노출 — 불가시·안전).
# 라이브 경계 탐지에서 합성행을 제외해 멱등 재실행 시 경계 붕괴를 방지한다.
BACKFILL_MARK = "[BACKFILL_V2]"


class Command(BaseCommand):
    help = "Backfill(소급 합성) intraday RegimeSnapshot 벡터 (B1-S2, idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from", dest="from_date", type=str, default=None,
            help="YYYY-MM-DD (기본 2023-07-10)",
        )
        parser.add_argument(
            "--to", dest="to_date", type=str, default=None,
            help="YYYY-MM-DD (기본: 라이브 최초일 전날). 라이브 구간은 하드 차단.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="쓰기 없이 대상·합성/스킵·국면 분포·완전벡터 수만 산출",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="대상 영업일 앞에서 N일만(테스트용)",
        )

    def handle(self, *args, **options):
        from_date = self._parse_date(options["from_date"]) or DEFAULT_FROM

        # ── 라이브 경계(하드 상한): 기존 행 불가침 ──
        # 합성행(BACKFILL_MARK)은 제외 — 멱등 재실행 시 경계가 끌려내려가지 않도록.
        live_min = (
            RegimeSnapshot.objects.exclude(summary=BACKFILL_MARK)
            .aggregate(m=Min("date"))["m"]
        )
        if live_min is None:
            # 라이브 행이 하나도 없으면 상한이 없음 → 안전상 명시 --to 요구.
            hard_upper = self._parse_date(options["to_date"])
            if hard_upper is None:
                raise CommandError(
                    "라이브 RegimeSnapshot 0건 — 상한 미확정. --to YYYY-MM-DD 명시 필요."
                )
        else:
            hard_upper = live_min - _one_day()
            req_to = self._parse_date(options["to_date"])
            if req_to is not None and req_to < hard_upper:
                hard_upper = req_to  # 요청이 더 좁으면 존중(넓히기는 불가)

        to_date = hard_upper
        if to_date < from_date:
            raise CommandError(f"빈 창: from={from_date} > to={to_date}")

        # ── 대상 영업일 = SPY 가격 존재일(창 내, 오름차순) ──
        business_days = self._spy_business_days(from_date, to_date, live_min)
        if options["limit"]:
            business_days = business_days[: options["limit"]]

        rules = classifier_mod.load_rules()

        if options["dry_run"]:
            self._run(business_days, rules, live_min, dry_run=True)
            return
        self._run(business_days, rules, live_min, dry_run=False)

    # ── core ──

    def _run(self, business_days, rules, live_min, *, dry_run: bool):
        synthesized = 0
        skipped = 0
        protected = 0
        complete = 0  # coverage >= 1.0 (완전벡터)
        stage_counter: Counter = Counter()
        prev = None  # 시계열 chaining(직전 영업일 스냅샷/네임스페이스)

        for d in business_days:
            # 이중 방어: 라이브 구간이면 절대 건드리지 않음(읽지도 쓰지도).
            if live_min is not None and d >= live_min:
                protected += 1
                continue

            result = self._synthesize_one(d, prev, rules)
            stage_counter[result["regime"]] += 1
            if result["coverage"] >= 1.0:
                complete += 1

            if dry_run:
                # 이미 존재하면 스킵으로 카운트(재실행 시 리포트 정직).
                if RegimeSnapshot.objects.filter(date=d).exists():
                    skipped += 1
                else:
                    synthesized += 1
                prev = SimpleNamespace(
                    regime=result["regime"],
                    previous_regime=result["previous_regime"],
                    hysteresis_streak=result["streak"],
                )
                continue

            snap, created = RegimeSnapshot.objects.get_or_create(
                date=d,
                defaults=self._defaults(d, result),
            )
            if created:
                synthesized += 1
            else:
                skipped += 1
            # chain은 실제 저장된 값 기준(부분 재실행 정합)
            prev = SimpleNamespace(
                regime=snap.regime,
                previous_regime=snap.previous_regime,
                hysteresis_streak=snap.hysteresis_streak,
            )

        self._report(
            business_days, synthesized, skipped, protected, complete,
            stage_counter, dry_run=dry_run,
        )

    def _synthesize_one(self, d: date_cls, prev, rules) -> dict:
        """as_of=d 로 현행 생성 로직 재실행 → 저장 필드 dict 반환(무쓰기)."""
        inputs = inputs_mod.load_inputs(as_of=d)
        cov = coverage_mod.evaluate(inputs, rules=rules)
        candidate, fired = classifier_mod.classify_inputs(inputs, rules=rules)

        if cov.status == RegimeSnapshot.Status.INSUFFICIENT_DATA:
            # 라이브 INSUFFICIENT 분기 그대로: 이전 regime 유지(캐리), 전환 보류.
            final = prev.regime if prev is not None else candidate
            previous_regime = prev.regime if prev is not None else ""
            streak = int(getattr(prev, "hysteresis_streak", 0) or 1) if prev else 1
            status = RegimeSnapshot.Status.INSUFFICIENT_DATA
        else:
            decision = classifier_mod.apply_hysteresis(
                candidate_regime=candidate, previous_snapshot=prev, rules=rules,
            )
            final = decision.final_regime
            previous_regime = decision.previous_regime
            streak = decision.streak
            status = RegimeSnapshot.Status.OK

        return {
            "regime": final,
            "previous_regime": previous_regime,
            "streak": streak,
            "status": status,
            "coverage": cov.ratio,
            "fired": fired,
            "inputs": inputs.as_dict(),
        }

    def _defaults(self, d: date_cls, result: dict) -> dict:
        snap_time = datetime(
            d.year, d.month, d.day, SNAPSHOT_HOUR_UTC, 0, tzinfo=dt_timezone.utc
        )
        headline = classifier_mod.build_headline(result["regime"], result["fired"])
        return {
            "snapshot_time": snap_time,
            "regime": result["regime"],
            "status": result["status"],
            "inputs": result["inputs"],
            "coverage": result["coverage"],
            "fired_rules": result["fired"],
            "previous_regime": result["previous_regime"],
            "hysteresis_streak": result["streak"],
            "headline": headline[:300],
            "summary": BACKFILL_MARK,  # provenance(미노출) — 라이브 경계 탐지용
            "is_finalized": True,  # 확정 과거
            "finalized_at": snap_time,
        }

    # ── helpers ──

    def _parse_date(self, s):
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None

    def _spy_business_days(self, from_date, to_date, live_min) -> list[date_cls]:
        from macro.models.indicators import MarketIndex, MarketIndexPrice

        spy = MarketIndex.objects.filter(symbol="SPY").first()
        if spy is None:
            raise CommandError("SPY MarketIndex 없음 — 영업일 산정 불가.")
        qs = MarketIndexPrice.objects.filter(
            index=spy, date__gte=from_date, date__lte=to_date
        )
        if live_min is not None:
            qs = qs.filter(date__lt=live_min)  # 창 필터(불가침 1차)
        return list(qs.order_by("date").values_list("date", flat=True))

    def _report(self, business_days, synthesized, skipped, protected,
                complete, stage_counter, *, dry_run: bool):
        tag = "[DRY-RUN] " if dry_run else ""
        first = business_days[0] if business_days else None
        last = business_days[-1] if business_days else None
        self.stdout.write(
            f"{tag}대상 영업일 {len(business_days)}건 ({first} ~ {last})"
        )
        self.stdout.write(
            f"{tag}synthesized={synthesized} skipped={skipped} "
            f"protected(라이브)={protected}"
        )
        self.stdout.write(f"{tag}완전벡터(coverage>=1.0)={complete}")
        dist = ", ".join(
            f"{k}={v}" for k, v in sorted(stage_counter.items(), key=lambda kv: -kv[1])
        )
        self.stdout.write(f"{tag}국면 분포: {dist or '(없음)'}")
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"합성 완료: {synthesized} 신규 / {skipped} 스킵(기존)"
                )
            )


def _one_day():
    from datetime import timedelta

    return timedelta(days=1)
