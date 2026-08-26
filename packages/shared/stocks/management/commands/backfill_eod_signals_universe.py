"""
EOD Signal 유니버스 확장 백필 명령 (A-3, EODUNIV-P15-V01) — stocks 도메인 소유 쓰기.

배경: A-2에서 EOD 시그널 계산 유니버스가 "SP500 active only" →
"SP500 ∪ 감시등록(Monitor scope='stock')"으로 확장됐다. 하지만 신규 편입된
감시등록 종목(예: IONQ/IREN/TLN)은 과거 EODSignal 행이 전혀 없어
Monitor advisor의 EODSignal 파생 지표 3종(eod_composite/change_percent/
dollar_volume, min_n=1)이 계속 불충분(source_n=0) 상태로 남는다. 이 명령은
그 갭을 메우기 위해 감시등록 종목(비SP500)의 EODSignal 행을 소급 생성한다.

★ 실행 게이트: 이 명령은 dev=prod 공유 DB에 직접 쓴다(D-DEV-PROD-SHARED-DB).
  기본값은 --dry-run(쓰기 없음)이며, 실제 실행은 병진 수동 승인 후에만 한다.
  이 세션(EODUNIV-P15-V01 PART A)에서는 절대 --commit으로 실행하지 않았다.

────────────────────────────────────────────────────────────────────────
feasibility 결정 (A-3, 리포트 참조):

EODSignalCalculator.calculate_batch(target_date, symbols=None)은 이미
임의의 as-of target_date를 받는다(오늘 전용이 아님) — 그리고 A-2에서
`symbols` 파라미터가 additive로 추가되어(기존 호출부 전부 symbols=None
기본값 그대로 무변경) 특정 심볼 집합으로 스코프를 좁혀 계산할 수 있다.
따라서 "달력을 소급해서 도는" 전체 히스토리 백필은 **계산기 재설계 없이**
가능하다 — Stage1 Ingest·Stage3 Calculate·Stage4 Tag를 그대로 재사용하고
Stage5 News Enrich(당시 뉴스 재구성은 별개 관심사·건너뜀)·Stage7 JSON
Bake(라이브 대시보드 스냅샷 전용·과거 스냅샷 굽기는 오용)·Stage8 Accuracy
Backfill(별도 기능)만 생략한다. Stage6 DB Upsert는 EODPipeline._stage_db_upsert
를 그대로 재사용한다(private 메서드지만 eod_pipeline.py 내부에서도
`calculator._load_price_data`처럼 이미 관례적으로 쓰이는 패턴).

알려진 한계(문서화 — 은근슬쩍 다른 걸로 대체하지 않음):
  - 계산 시 symbols를 [백필 대상 종목들] ∪ {"SPY"}로 좁혀서 로드한다
    (전체 유니버스 506종을 날짜마다 다시 로드하면 285일 × 506종 스캔이
    되어 공유 prod DB에 비현실적 부하 — additive 파라미터로 회피).
  - 이 스코프 축소로 인해 "relation" 카테고리 시그널 3종(S1 섹터상대강도,
    S2 섹터소외주, S4 폭락장생존자 중 S1/S2)은 진짜 섹터 피어(SP500
    전체) 없이 계산되어 사실상 항상 비활성으로 나온다(섹터 평균이
    백필 대상 자기 자신들로만 계산됨). S4는 SPY를 항상 포함시켜 회피.
    P1~P5/P7/V1/PV1/PV2/MA1/T1(11종)과 advisor가 실제로 쓰는
    composite_score/change_percent/dollar_volume 필드는 이 한계의 영향을
    받지 않는다 — EODSignal 행 자체가 존재하기만 하면 min_n=1 충분성은
    항상 만족된다.
  - "전체 히스토리"의 정확한 범위는 대상 종목의 DailyPrice 최소/최대
    date다. SP500 편입 시점 스냅샷 같은 시점별 유니버스 소급은 하지
    않는다(eod_universe_symbols()는 "현재" 유니버스 기준 — 기존 코드도
    동일한 단순화를 이미 갖고 있었음, 신규 도입 아님).

사용:
    python manage.py backfill_eod_signals_universe                       # dry-run, 기본 대상(비SP500 감시등록)
    python manage.py backfill_eod_signals_universe --symbols IONQ,IREN,TLN --dry-run
    python manage.py backfill_eod_signals_universe --symbols IONQ,IREN,TLN --commit   # 실제 쓰기(승인 후에만)
    python manage.py backfill_eod_signals_universe --start-date 2025-07-03 --end-date 2026-08-25 --commit
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max, Min


class Command(BaseCommand):
    help = (
        "감시등록(비SP500) 종목의 EODSignal 소급 백필 (A-3, EODUNIV-P15-V01). "
        "기본 dry-run — 쓰기는 --commit 명시 시에만."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols",
            type=str,
            default=None,
            help="쉼표구분 심볼 목록. 미지정 시 = eod_universe_symbols() − SP500 "
            "(감시등록 비SP500 종목 전체, 하드코딩 없음).",
        )
        parser.add_argument(
            "--start-date", type=str, default=None, help="시작일 YYYY-MM-DD (미지정=대상 종목 DailyPrice 최소일)"
        )
        parser.add_argument(
            "--end-date", type=str, default=None, help="종료일 YYYY-MM-DD (미지정=대상 종목 DailyPrice 최대일)"
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="실제 EODSignal 행을 씁니다. 미지정 시 dry-run(집계만 출력).",
        )

    def handle(self, *args, **options):
        from packages.shared.stocks.models import DailyPrice, EODSignal, SP500Constituent
        from packages.shared.stocks.services.eod_pipeline import EODPipeline
        from packages.shared.stocks.services.eod_signal_calculator import (
            EODSignalCalculator,
            eod_universe_symbols,
        )
        from packages.shared.stocks.services.eod_signal_tagger import EODSignalTagger

        # ── 대상 심볼 결정 ────────────────────────────────────────────
        if options["symbols"]:
            target_symbols = sorted(
                {s.strip().upper() for s in options["symbols"].split(",") if s.strip()}
            )
        else:
            sp500_set = set(
                SP500Constituent.objects.filter(is_active=True).values_list(
                    "symbol", flat=True
                )
            )
            target_symbols = sorted(
                s for s in eod_universe_symbols() if s not in sp500_set
            )

        if not target_symbols:
            raise CommandError(
                "백필 대상 심볼 없음 (감시등록 비SP500 종목이 없거나 --symbols 미지정)."
            )

        self.stdout.write(f"대상 심볼({len(target_symbols)}): {target_symbols}")

        # ── 날짜 범위 결정 (대상 종목 DailyPrice 실측 범위) ─────────────
        date_bounds = DailyPrice.objects.filter(
            stock__symbol__in=target_symbols
        ).aggregate(min_date=Min("date"), max_date=Max("date"))
        universe_min = date_bounds["min_date"]
        universe_max = date_bounds["max_date"]

        if universe_min is None:
            raise CommandError(f"대상 종목 DailyPrice 없음: {target_symbols}")

        start_date = (
            date.fromisoformat(options["start_date"])
            if options["start_date"]
            else universe_min
        )
        end_date = (
            date.fromisoformat(options["end_date"])
            if options["end_date"]
            else universe_max
        )
        if start_date > end_date:
            raise CommandError(f"start-date({start_date}) > end-date({end_date})")

        self.stdout.write(
            f"날짜 범위: {start_date} ~ {end_date} "
            f"(대상 종목 DailyPrice 실측 범위: {universe_min} ~ {universe_max})"
        )

        # ── (symbol, date) 쌍 중 EODSignal 미존재만 선별 (멱등) ─────────
        existing = set(
            EODSignal.objects.filter(
                stock__symbol__in=target_symbols,
                date__gte=start_date,
                date__lte=end_date,
            ).values_list("stock_id", "date")
        )

        # 심볼별 실제 거래일(DailyPrice에 존재하는 날짜)만 대상으로 함
        price_dates = list(
            DailyPrice.objects.filter(
                stock__symbol__in=target_symbols,
                date__gte=start_date,
                date__lte=end_date,
            ).values_list("stock__symbol", "date")
        )

        missing_by_date: dict[date, list[str]] = {}
        for symbol, d in price_dates:
            if (symbol, d) in existing:
                continue
            missing_by_date.setdefault(d, []).append(symbol)

        total_missing = sum(len(syms) for syms in missing_by_date.values())
        per_symbol_missing: dict[str, int] = {}
        for syms in missing_by_date.values():
            for s in syms:
                per_symbol_missing[s] = per_symbol_missing.get(s, 0) + 1

        self.stdout.write(
            self.style.WARNING(
                f"[요약] EODSignal 결측(symbol,date) 쌍: {total_missing}건, "
                f"영향 거래일: {len(missing_by_date)}일"
            )
        )
        for s in target_symbols:
            self.stdout.write(
                f"  - {s}: 기존 EODSignal 존재={sum(1 for (sym, _d) in existing if sym == s)}, "
                f"결측(생성 예정)={per_symbol_missing.get(s, 0)}"
            )

        if not options["commit"]:
            self.stdout.write(
                self.style.NOTICE(
                    "dry-run 완료 — 실제 쓰기 없음. --commit 플래그로 재실행 시 위 건수만큼 "
                    "EODSignal 행을 생성합니다 (병진 수동 승인 후에만 실행할 것)."
                )
            )
            return

        # ── 실제 백필 실행 (--commit) ────────────────────────────────
        calculator = EODSignalCalculator()
        tagger = EODSignalTagger()
        pipeline = EODPipeline()  # _stage_db_upsert 재사용(Stage6과 동일 로직)

        created_total = 0
        for d in sorted(missing_by_date.keys()):
            syms_for_date = missing_by_date[d]
            # S4(폭락장 생존자)의 SPY 비교가 정확히 동작하도록 SPY를 항상 포함.
            # relation 시그널(S1/S2)은 진짜 섹터 피어 부재로 여전히 비활성 근사(문서화된 한계).
            calc_symbols = sorted(set(syms_for_date) | {"SPY"})
            df = calculator.calculate_batch(target_date=d, symbols=calc_symbols)
            if df.empty:
                self.stdout.write(self.style.WARNING(f"  {d}: 계산 결과 없음, 스킵"))
                continue

            df = df[df["symbol"].isin(syms_for_date)]
            if df.empty:
                continue

            tagged = tagger.tag_signals(df)
            # 기존 Stage4와 달리 signal_count==0도 유지한다 — 커버리지 목적은
            # "행의 존재"(min_n=1)이지 "시그널 발생"이 아니다.
            upserted = pipeline._stage_db_upsert(tagged, d)
            created_total += upserted
            self.stdout.write(f"  {d}: {upserted}건 생성 ({syms_for_date})")

        self.stdout.write(
            self.style.SUCCESS(f"[완료] EODSignal {created_total}건 생성/갱신.")
        )
