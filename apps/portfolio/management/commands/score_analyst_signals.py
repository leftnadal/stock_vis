"""SFI-I3 Part 4 — 애널리스트 신호 채점 판정 리포트 (관리 커맨드, read-only).

`python manage.py score_analyst_signals [--as-of YYYY-MM-DD]` → markdown.
Tier 1(shared analyst_scoring) + Tier 2 ④(shared analyst_revision) + ⑤(portfolio
advisory_postmortem)을 묶어 고정 템플릿으로 출력. DB 쓰기 0(순수 관측).

재현 좌표 헤더의 AdvisoryRun 행수는 이 apps 계층에서 주입한다(규칙 6 — shared는 apps 무의존).
표본 미도달 과목은 '표본 미도달 — 최초 만기 YYYY-MM-DD'로 명시(빈 값 은폐 금지).
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone


def _fmt(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


class Command(BaseCommand):
    help = "애널리스트 신호 채점 판정 리포트 (Tier 1/2, read-only markdown)"

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=str, default=None, help="YYYY-MM-DD (기본: 오늘)")

    def handle(self, *args, **options):
        from apps.portfolio.models_my import AdvisoryRun
        from apps.portfolio.services.advisory_postmortem import advisory_postmortem_v0
        from packages.shared.stocks.services.analyst_revision import revision_tracking
        from packages.shared.stocks.services import analyst_scoring as sc

        if options["as_of"]:
            as_of = datetime.strptime(options["as_of"], "%Y-%m-%d").date()
        else:
            as_of = timezone.localdate()

        tier1 = sc.score_tier1(as_of)
        revision = revision_tracking(as_of)
        postmortem = advisory_postmortem_v0(as_of)
        advisory_rows = AdvisoryRun.objects.filter(run_at__date__lte=as_of).count()

        L = []
        # ── 재현 좌표 블록 ──
        h = tier1["header"]
        ir = dict(h["input_rows"])
        ir["advisory_run_rows"] = advisory_rows
        L.append("# 애널리스트 신호 채점 판정 리포트")
        L.append("")
        L.append("## 재현 좌표")
        L.append(f"- as_of: `{h['as_of']}`")
        L.append(f"- SCORING_VERSION: `{h['scoring_version']}`")
        L.append(f"- git HEAD: `{h['git_head']}`")
        L.append(
            f"- 입력 행수: ASS={ir['ass_rows']} · DailyPrice={ir['daily_price_rows']} · "
            f"AdvisoryRun={ir['advisory_run_rows']}"
        )
        L.append("")

        pinned = tier1["cohorts"]["pinned"]
        derived = tier1["cohorts"]["derived"]

        # ── Tier 1 ──
        L.append("## 【Tier 1 — 판정 과목】 (정본 = post-pinning 코호트)")
        L.append(f"post-pinning 예측 {pinned['prediction_count']}건 · "
                 f"pre-pinning(파생 spot) {derived['prediction_count']}건")
        L.append("")
        L.append("### ① 방향 적중률  sign(target − spot)")
        for h_ in (21, 63):
            r = pinned["direction_hit_rate"][h_]
            if r["sample"] == 0:
                L.append(f"- h={h_}d: **표본 미도달 — 최초 만기 {r['earliest_maturity_est'] or '—'}**"
                         + (f" · unscoreable {len(r['unscoreable'])}건" if r["unscoreable"] else ""))
            else:
                L.append(
                    f"- h={h_}d: 적중 {r['hits']}/{r['sample']} = {_fmt(r['hit_rate'])} · "
                    f"이항 p(양측)={_fmt(r['p_value'])} · p(상방)={_fmt(r['p_greater'])}"
                    + (f" · unscoreable {len(r['unscoreable'])}건" if r["unscoreable"] else "")
                )
        L.append("")
        L.append("### ② 목표가 진행률  실현폭 / 예측폭")
        for h_ in (63, 126, 252):
            r = pinned["target_progress"][h_]
            if r["sample"] == 0:
                L.append(f"- h={h_}d: **표본 미도달 — 최초 만기 {r['earliest_maturity_est'] or '—'}**")
            else:
                iqr = r["iqr"]
                iqr_s = f"[{_fmt(iqr[0])}, {_fmt(iqr[1])}]" if iqr else "—"
                L.append(f"- h={h_}d: 표본 {r['sample']} · 중앙값 {_fmt(r['median_ratio'])} · IQR {iqr_s}")
        L.append("")
        L.append("### ③ 횡단면 IC  주간 코호트 upside% 순위 vs 실현수익 순위 (Spearman)")
        for h_ in (21, 63):
            r = pinned["cross_sectional_ic"][h_]
            if r["cohorts_scored"] == 0:
                L.append(f"- h={h_}d: **표본 미도달 — 최초 만기 {r['earliest_maturity_est'] or '—'}** ({r['caveat']})")
            else:
                L.append(f"- h={h_}d: 코호트 {r['cohorts_scored']}주 · 평균 IC {_fmt(r['mean_ic'])} ({r['caveat']})")
                for w in r["weeks"]:
                    L.append(f"    - {w['week']}: n={w['n']} IC={_fmt(w['ic'])}")
        L.append("")

        # ── Tier 2 ──
        L.append("## 【Tier 2 — 관측 과목】")
        L.append("### ④ 개정 추적  target consensus delta · 의견 변화")
        ag = revision["aggregate"]
        L.append(
            f"- 심볼 {ag['symbols']} · 총 개정 {ag['total_revisions']} · 합의변화 {ag['total_consensus_changes']} · "
            f"|delta| 중앙값 {_fmt(ag['median_abs_delta'], 2)} · 최대 {_fmt(ag['max_abs_delta'], 2)}"
        )
        for sym, d in sorted(revision["per_symbol"].items()):
            if d["revision_count"] or d["consensus_changes"]:
                L.append(f"    - {sym}: 스냅 {d['snapshots']} · 개정 {d['revision_count']} · "
                         f"합의변화 {len(d['consensus_changes'])} · 최근합의 {d['last_consensus'] or '—'}")
        L.append("")
        L.append("### ⑤ advisory 사후분석 v0")
        L.append(f"- auto run {postmortem['auto_run_count']} · manual {postmortem['manual_run_count']} · "
                 f"범위 {postmortem['auto_run_at_range'][0] or '—'} ~ {postmortem['auto_run_at_range'][1] or '—'}")
        kv = ", ".join(f"{k}(distinct={v['distinct']})" for k, v in postmortem["knob_variation"].items())
        L.append(f"- knobs 변동: {kv}")
        for uname, nav in postmortem["nav_trajectory"].items():
            r = nav["h21_realized"]
            if r and "status" in r:
                L.append(f"    - {uname} NAV h21: 표본 미도달 — 최초 만기 {r['earliest_maturity_est']} · {nav['caveat']}")
            elif r:
                L.append(f"    - {uname} NAV h21: {r['from'][0]}→{r['to'][0]} delta={r['delta_krw']} "
                         f"pct={_fmt(r['pct'])} · {nav['caveat']}")
        L.append("")

        # ── 코호트·예외 ──
        L.append("## 코호트·예외")
        es = pinned.get("epoch_split")
        if es:
            L.append(
                f"- pinned epoch 태깅(D-I3-5, CONVENTION_EPOCH={es['convention_epoch']}): "
                f"epoch 前 {es['pre_mixed']}건(**혼합 관례** — T/T−1 혼재, spot-day 수리 前 캐비앗) · "
                f"epoch 後 {es['post_t']}건(T 관례)"
            )
        L.append(f"- pre-pinning 행수(파생 spot 별도 산출): {derived['prediction_count']}")
        unsc = []
        for h_ in (21, 63):
            unsc += pinned["direction_hit_rate"][h_]["unscoreable"]
        seen, uniq = set(), []
        for u in unsc:
            key = (u[0], u[1], u[2])
            if key not in seen:
                seen.add(key)
                uniq.append(u)
        if uniq:
            L.append(f"- unscoreable {len(uniq)}건:")
            for sym, d, reason in uniq:
                L.append(f"    - {sym} @ {d} — {reason}")
        else:
            L.append("- unscoreable: 없음")

        self.stdout.write("\n".join(L))
