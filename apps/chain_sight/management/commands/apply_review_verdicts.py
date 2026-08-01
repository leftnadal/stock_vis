"""검수 verdict → RelationConfidence 반영 (⑳-3 REVIEW-P2 S1).

동결 CSV(review_batch_v6_labeled.csv)의 human_verdict 컬럼을 domain_review_status로 반영한다.
CSV가 진실의 소스 — 이 명령은 CSV를 읽기만 하고 절대 수정하지 않는다.

    python manage.py apply_review_verdicts --dry-run   # 기본: DB 무기록, 반영 예정 리포트만
    python manage.py apply_review_verdicts --apply      # 실 DB 반영(트랜잭션 원자·idempotent)

verdict 어휘(접두사 파싱):
    OK               → domain_review_status='approved'      (검수 승인)
    DROP             → domain_review_status='rejected'      (soft-drop, serving 제외·레코드 보존)
    HOLD             → domain_review_status='pending'       (재분류 대기)
    CHANGE:<TYPE>    → relation_type=<TYPE> + status='approved'
    CHANGE_REV:<TYPE>→ S1에서 미처리(S2 방향 스왑으로 위임) — 리포트에만 표기

매칭 키: (symbol_a, symbol_b, relation_type). CSV symbol_pair를 '↔'로 split한 순서가
DB 방향(symbol_a→symbol_b)을 보존한다. forward-exact 유일 매칭 강제(0건/2건+ → HALT).

HALT(반영 중단·보고):
    H-A: 미인지 verdict 어휘 존재
    H-C: 매칭 0건 또는 2건+ (부분 반영 금지)
    H-D: verdict 분포가 동결 기대 분포와 불일치
"""

import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.chain_sight.models import RelationConfidence

DEFAULT_CSV = "docs/etc/review_batch_v6_labeled.csv"
VERDICT_COL = "human_verdict"

# 동결 기대 분포 (지시서 §0 입력, 수정 금지)
EXPECTED = {"OK": 202, "DROP": 43, "HOLD": 23, "CHANGE": 1, "CHANGE_REV": 1}

# 단순 verdict → domain_review_status 매핑
STATUS_MAP = {"OK": "approved", "DROP": "rejected", "HOLD": "pending"}

VALID_TYPES = {c[0] for c in RelationConfidence.RELATION_TYPE_CHOICES}


class VerdictParseError(Exception):
    """미인지 verdict 어휘."""


def parse_verdict(raw):
    """verdict 문자열 → (kind, arg). kind ∈ {OK,DROP,HOLD,CHANGE,CHANGE_REV}.

    CHANGE_REV: 접두사를 CHANGE: 보다 먼저 검사한다(전자가 후자를 문자열로 포함하므로).
    미인지 어휘는 VerdictParseError.
    """
    v = (raw or "").strip()
    if v in ("OK", "DROP", "HOLD"):
        return v, None
    if v.startswith("CHANGE_REV:"):
        return "CHANGE_REV", v.split(":", 1)[1].strip()
    if v.startswith("CHANGE:"):
        return "CHANGE", v.split(":", 1)[1].strip()
    raise VerdictParseError(v)


def build_plan(rows):
    """CSV 행 리스트 → 반영 계획(DB 조회만, 무변경).

    반환 dict:
        plan          : [(kind, arg, rc_id, old_type, pair, rtype), ...] (CHANGE_REV 포함)
        unrecognized  : [(pair, rtype, raw)]  — H-A
        unmatched     : [(pair, rtype, n)]    — H-C (n != 1)
        verdict_counts: {kind: n}
    """
    plan, unrecognized, unmatched = [], [], []
    verdict_counts = {k: 0 for k in EXPECTED}

    for r in rows:
        pair = r["symbol_pair"]
        rtype = r["relation_type"]
        raw = r[VERDICT_COL]
        try:
            kind, arg = parse_verdict(raw)
        except VerdictParseError:
            unrecognized.append((pair, rtype, raw))
            continue
        verdict_counts[kind] = verdict_counts.get(kind, 0) + 1

        # CHANGE 계열 타입 유효성 (choices 밖이면 미인지)
        if kind in ("CHANGE", "CHANGE_REV") and arg not in VALID_TYPES:
            unrecognized.append((pair, rtype, raw))
            continue

        x, y = pair.split("↔")
        qs = RelationConfidence.objects.filter(
            symbol_a=x, symbol_b=y, relation_type=rtype
        )
        n = qs.count()
        if n != 1:
            unmatched.append((pair, rtype, n))
            continue
        obj = qs.first()
        plan.append((kind, arg, obj.id, obj.relation_type, pair, rtype))

    return {
        "plan": plan,
        "unrecognized": unrecognized,
        "unmatched": unmatched,
        "verdict_counts": verdict_counts,
    }


def status_targets(plan):
    """plan → domain_review_status별 쓰기 예정 카운트. CHANGE_REV는 S1 제외."""
    tgt = {"approved": 0, "rejected": 0, "pending": 0}
    for kind, arg, rc_id, old_type, pair, rtype in plan:
        if kind in STATUS_MAP:
            tgt[STATUS_MAP[kind]] += 1
        elif kind == "CHANGE":
            tgt["approved"] += 1
    return tgt


def apply_plan(plan):
    """plan을 DB에 반영(트랜잭션 원자·idempotent). CHANGE_REV는 S1에서 제외.

    반환: {"approved": n, "rejected": n, "pending": n, "change": n}
    """
    ok_ids = [p[2] for p in plan if p[0] == "OK"]
    drop_ids = [p[2] for p in plan if p[0] == "DROP"]
    hold_ids = [p[2] for p in plan if p[0] == "HOLD"]
    change_rows = [p for p in plan if p[0] == "CHANGE"]

    with transaction.atomic():
        RelationConfidence.objects.filter(id__in=ok_ids).update(
            domain_review_status="approved"
        )
        RelationConfidence.objects.filter(id__in=drop_ids).update(
            domain_review_status="rejected"
        )
        RelationConfidence.objects.filter(id__in=hold_ids).update(
            domain_review_status="pending"
        )
        for kind, arg, rc_id, old_type, pair, rtype in change_rows:
            # 타입 변경 = Neo4j 엣지 의미 변경 → 재동기화 표식
            RelationConfidence.objects.filter(id=rc_id).update(
                relation_type=arg,
                domain_review_status="approved",
                neo4j_dirty=True,
            )
    return {
        "approved": len(ok_ids) + len(change_rows),
        "rejected": len(drop_ids),
        "pending": len(hold_ids),
        "change": len(change_rows),
    }


class Command(BaseCommand):
    help = "검수 verdict(human_verdict) → RelationConfidence.domain_review_status 반영"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=DEFAULT_CSV, help="입력 CSV(동결)")
        parser.add_argument(
            "--apply", action="store_true",
            help="실 DB 반영. 미지정 시 dry-run(DB 무기록).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="명시적 dry-run(기본과 동일). --apply와 함께 줘도 dry-run 우선(안전).",
        )

    def handle(self, *args, **opts):
        csv_path = opts["csv"]
        # dry-run이 기본. --dry-run은 --apply보다 우선(오발 방지).
        dry_run = opts["dry_run"] or not opts["apply"]

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.stdout.write(f"CSV 로드: {csv_path} ({len(rows)}행)")

        p = build_plan(rows)
        plan = p["plan"]
        vc = p["verdict_counts"]
        change_rows = [x for x in plan if x[0] == "CHANGE"]
        change_rev_rows = [x for x in plan if x[0] == "CHANGE_REV"]
        tgt = status_targets(plan)

        # ── HALT 판정 ──
        halted = False
        if p["unrecognized"]:
            halted = True
            self.stderr.write(f"HALT H-A: 미인지 verdict {len(p['unrecognized'])}건")
            for pair, t, v in p["unrecognized"][:20]:
                self.stderr.write(f"    {pair} {t} verdict={v!r}")
        if p["unmatched"]:
            halted = True
            self.stderr.write(f"HALT H-C: 매칭 실패 {len(p['unmatched'])}건 (0건 또는 2건+)")
            for pair, t, n in p["unmatched"][:20]:
                self.stderr.write(f"    {pair} {t} matched={n}")
        if vc != EXPECTED:
            halted = True
            self.stderr.write(f"HALT H-D: verdict 분포 불일치. 실측={vc} 기대={EXPECTED}")

        # ── 반영 계획 리포트 ──
        self.stdout.write("── 반영 계획(verdict 분류) ──")
        for k in ("OK", "DROP", "HOLD", "CHANGE", "CHANGE_REV"):
            mark = "" if vc.get(k, 0) == EXPECTED[k] else "  ⚠️불일치"
            note = " (S2 위임·S1 skip)" if k == "CHANGE_REV" else ""
            self.stdout.write(f"    {k:12} {vc.get(k, 0):3d} / 기대 {EXPECTED[k]}{note}{mark}")
        self.stdout.write(
            f"── domain_review_status 쓰기 예정: approved={tgt['approved']} "
            f"rejected={tgt['rejected']} pending={tgt['pending']} "
            f"(CHANGE_REV {len(change_rev_rows)}건 S1 제외) ──"
        )
        for kind, arg, rc_id, old_type, pair, rtype in change_rows:
            self.stdout.write(f"    CHANGE: {pair} relation_type {old_type} → {arg} + approved")
        for kind, arg, rc_id, old_type, pair, rtype in change_rev_rows:
            self.stdout.write(f"    CHANGE_REV(S2 위임): {pair} {old_type} → 방향스왑+{arg}")

        if halted:
            self.stderr.write("반영 중단 — HALT 조건 발동. DB 무변경.")
            return
        if dry_run:
            self.stdout.write("dry-run: DB 무기록. (--apply 로 실반영)")
            return

        res = apply_plan(plan)
        self.stdout.write(
            f"✅ 반영 완료: approved={res['approved']} rejected={res['rejected']} "
            f"pending={res['pending']} CHANGE={res['change']}. "
            f"CHANGE_REV {len(change_rev_rows)}건은 S2 처리."
        )
