"""
`backfill_snapshot_anchor --from <날짜> --to <날짜>` — EstimateSnapshot 앵커 라벨 교정 백필.

배경(D-DSS-W11-RESCUE): 2026-09-12(토) 수집분은 **09-11(금) 마감 컨센서스**를 담고 있으나
앵커가 실행일(09-12)로 기록됐다. G-2 증거 게이트가 이를 확증했다(개정 폭이 클린 7일 쌍 대비
변경률 0.960x·전 분위 부풀림 0). 이 명령은 **09-12 행을 09-11 앵커로 복제**한다.

복제이지 이동이 아니다 — 09-12 행은 **남긴다**(유효신호 0이라 무해하고, 사건의 흔적이
원장에 남아야 한다).

🔴 안전장치
  ① `--to` 앵커에 행이 하나라도 있으면 **거부**. EstimateSnapshot은 `update_or_create` upsert
     모델이라 조용히 덮어쓸 수 있다(DSS-LEDGER-IMMUTABLE 근거).
  ② `--dry-run`이 기본. 실집행은 `--execute` 명시.
  ③ `--from`·`--to` 외 앵커는 읽지도 쓰지도 않는다.
  ④ `SymbolDemandSignal`은 복제하지 않는다 — DSS는 `load_dss_week`가 다시 만든다.
  ⑤ 관측 시각(`created_at`)은 **원본 09-12 값을 유지**한다. 출처가 원장에 남아야 하기 때문이다.
     (`auto_now_add=True`라 bulk_create가 새 값을 박으므로 bulk_update로 되돌린다.)
"""

import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.chain_sight.models import EstimateSnapshot

COPY_FIELDS = (
    "symbol", "fiscal_year", "eps_avg", "eps_high", "eps_low",
    "num_analysts_eps", "revenue_avg",
)


def _d(s: str) -> dt.date:
    try:
        return dt.date.fromisoformat(s)
    except ValueError as e:
        raise CommandError(f"날짜 형식 오류(YYYY-MM-DD): {s}") from e


class Command(BaseCommand):
    help = "EstimateSnapshot 앵커 복제 백필 (기본 dry-run). 대상 앵커가 비어 있을 때만 허용."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="src", required=True, help="원본 앵커 YYYY-MM-DD")
        parser.add_argument("--to", dest="dst", required=True, help="대상 앵커 YYYY-MM-DD")
        parser.add_argument(
            "--execute", action="store_true",
            help="실제 INSERT 수행. 미지정 시 dry-run(기본).",
        )

    def handle(self, *args, **opts):
        src, dst = _d(opts["src"]), _d(opts["dst"])
        dry = not opts["execute"]
        w = self.stdout.write

        if src == dst:
            raise CommandError("--from 과 --to 가 같다.")

        # ① 덮어쓰기 방지 — 최우선 가드
        existing = EstimateSnapshot.objects.filter(snapshot_date=dst).count()
        if existing:
            raise CommandError(
                f"거부: 대상 앵커 {dst}에 이미 {existing}행이 있다. "
                f"EstimateSnapshot은 upsert 모델이라 덮어쓰기 위험 — 수동 확인 필요."
            )

        rows = list(EstimateSnapshot.objects.filter(snapshot_date=src).order_by("symbol", "fiscal_year"))
        if not rows:
            raise CommandError(f"원본 앵커 {src}에 행이 없다.")

        symbols = len({r.symbol for r in rows})
        w(f"백필 {src} → {dst}   ({'DRY-RUN' if dry else '★ 실집행'})")
        w(f"  대상 행수 : {len(rows)}  / 심볼 {symbols}")
        w(f"  충돌      : {existing}  (0이어야 진행)")
        w(f"  관측시각  : 원본 유지 (created_at {rows[0].created_at} ~ {rows[-1].created_at})")
        w("  샘플 3행 (before → after):")
        for r in rows[:3]:
            w(f"    {r.symbol:<6} FY{r.fiscal_year}  eps_avg={r.eps_avg}  "
              f"{src} → {dst}  (created_at {r.created_at:%Y-%m-%d %H:%M:%S%z} 유지)")
        w(f"  예상 소요 : bulk_create {len(rows)}행 + bulk_update(created_at) — 수 초")

        if dry:
            w(self.style.WARNING("  dry-run — 쓰기 없음. 실집행은 --execute."))
            return

        objs = [
            EstimateSnapshot(snapshot_date=dst, **{f: getattr(r, f) for f in COPY_FIELDS})
            for r in rows
        ]
        with transaction.atomic():
            created = EstimateSnapshot.objects.bulk_create(objs)
            # ⑤ auto_now_add가 박은 값을 원본으로 되돌린다(bulk_update는 auto_now_add 미적용).
            for new, old in zip(created, rows):
                new.created_at = old.created_at
            EstimateSnapshot.objects.bulk_update(created, ["created_at"])

        got = EstimateSnapshot.objects.filter(snapshot_date=dst).count()
        w(self.style.SUCCESS(f"  완료: {dst} 앵커 {got}행 INSERT (원본 {len(rows)}행)"))
        if got != len(rows):
            raise CommandError(f"검증 실패: 기대 {len(rows)}행 ≠ 실제 {got}행")
