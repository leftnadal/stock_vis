"""
앵커 as_of 계약 전수검사 (read-only) — D-ASOF-POPULATION.

모집단 = 동결 목록(`packages.shared.market_week.ANCHOR_EXEMPTIONS`)에 없는 모든 앵커.
판정 = `as_of_week(그 앵커의 최초 관측시각) == 앵커`.

실행: python manage.py shell < scripts/asof_anchor_sweep.py
"""
from zoneinfo import ZoneInfo

from django.db.models import Min

from apps.chain_sight.models.heat import EstimateSnapshot, SymbolDemandSignal
from packages.shared.market_week import (
    ANCHOR_EXEMPTIONS,
    as_of_week,
    exemption_reason,
    find_anchor_violations,
    is_anchor_exempt,
)

ET = ZoneInfo("America/New_York")
TARGETS = [
    ("EstimateSnapshot", EstimateSnapshot, "snapshot_date"),
    ("SymbolDemandSignal", SymbolDemandSignal, "anchor_date"),
]


def _rows(model, field):
    return [
        (r[field], r["c"].astimezone(ET))
        for r in model.objects.values(field).annotate(c=Min("created_at")).order_by(field)
    ]


total = 0
print(f"동결 목록 {len(ANCHOR_EXEMPTIONS)}건 — 제외 후 전수검사\n")
for label, model, field in TARGETS:
    rows = _rows(model, field)
    viol = find_anchor_violations(label, rows)
    total += len(viol)
    print(f"=== {label} ({field}) — 앵커 {len(rows)}건 ===")
    print(f"{'앵커':<12}{'dow':<5}{'관측시각(ET)':<21}{'as_of':<12}판정")
    for anchor, obs, in_rows in [(a, o, None) for a, o in rows]:
        if is_anchor_exempt(label, anchor):
            verdict = f"동결:{exemption_reason(label, anchor)[0]}"
        else:
            got = as_of_week(obs)
            verdict = "OK" if got == anchor else "*** VIOLATION"
        got = as_of_week(obs)
        print(f"{str(anchor):<12}{anchor.strftime('%a'):<5}"
              f"{obs.strftime('%Y-%m-%d %H:%M:%S'):<21}{str(got):<12}{verdict}")
    print(f"  → 위반 {len(viol)}건"
          + (f": {[(str(a), str(g)) for a, _, g in viol]}" if viol else "") + "\n")

print(f"### 총 위반 {total}건 (계약: 0건)")
