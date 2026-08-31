"""MIG-BUNDLE-1 A-2: 자기루프 잔존 행 정제(아카이브 후 삭제) — 병진 실행용.

배경(STEP 0 실측·2026-08-31):
  RelationConfidence 에 symbol_a==symbol_b 자기루프 13행(전부 confirmed·
  serving_layer='excluded' → 카드 미서빙)이 레거시로 잔존. 이들이 주간
  pair_aggregation 으로 RelationPairSnapshot(canonical_a==canonical_b)에
  period 마다 파생 적립(측정 시 649행, 이후 주간 증가). A-1 가드로 신규 생성은
  차단됐으나 **기존 행은 소급 삭제 아님** → 이 커맨드로 정제해야 A-4의
  CheckConstraint(symbol_a≠symbol_b) 마이그레이션이 통과한다.

정제 대상(런타임 전수 — 하드코딩 아님):
  - RelationConfidence: symbol_a == symbol_b
  - RelationPairSnapshot: canonical_a == canonical_b
  - (best-effort) Neo4j: self-loop 엣지 (a)-[r]->(a)

⚠ dev=prod 공유 DB — --apply 는 prod-write(자율 금지). **병진 배포 단계에서만 --apply.**
  기본은 dry-run(카운트만). --archive-dir 는 read-only(덤프 파일 생성).

사용:
  # 1) 아카이브 생성(read-only) + dry-run 카운트 + Neo4j 프로브
  python manage.py normalize_self_loops --archive-dir /ops/archive/selfloops_YYYYMMDD
  # 2) (병진) 실삭제 — 아카이브 존재 필수
  python manage.py normalize_self_loops --archive-dir <위 폴더> --apply

복원: 각 jsonl 줄 = 한 행 전 컬럼.
  RC:  for line in file: RelationConfidence.objects.create(**json.loads(line))  # pk 제외 재생성
  RPS: for line in file: RelationPairSnapshot.objects.create(**json.loads(line))
  또는 pg 백업 복원(권장).

랜딩 순서상 이 커맨드(--apply) 실행 → migrate(0034 CheckConstraint) 순서 엄수.
자기루프 잔존 상태로 migrate 하면 제약 추가가 IntegrityError 로 실패한다.
"""

import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import F


class Command(BaseCommand):
    help = (
        "자기루프(symbol_a==symbol_b / canonical_a==canonical_b) 행을 아카이브 후 "
        "삭제 (기본 dry-run; --apply 시 실삭제=prod-write). A-4 제약 선행 정제."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archive-dir",
            type=str,
            default=None,
            help="RC/RPS 자기루프 전행 jsonl 덤프 폴더(복원용). --apply 전 필수. 사전 존재 필요.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실삭제 실행(prod-write). 미지정=dry-run.",
        )

    def handle(self, *args, **opts):
        from apps.chain_sight.models import RelationConfidence, RelationPairSnapshot

        rc_self = RelationConfidence.objects.filter(symbol_a=F("symbol_b"))
        rps_self = RelationPairSnapshot.objects.filter(canonical_a=F("canonical_b"))

        rc_total = RelationConfidence.objects.count()
        rps_total = RelationPairSnapshot.objects.count()
        rc_self_n = rc_self.count()
        rps_self_n = rps_self.count()

        self.stdout.write(
            f"[normalize self-loops] RC self={rc_self_n}/{rc_total} · "
            f"RPS self={rps_self_n}/{rps_total}"
        )
        rc_syms = sorted(set(rc_self.values_list("symbol_a", flat=True)))
        self.stdout.write(f"  RC 자기루프 심볼({len(rc_syms)}): {rc_syms}")

        if rc_self_n == 0 and rps_self_n == 0:
            self.stdout.write(self.style.SUCCESS("  자기루프 0 — 정제 불요(멱등)."))
            return

        # ── 아카이브(read-only): 전 컬럼 덤프 ──
        rc_archived = rps_archived = 0
        rc_path = rps_path = None
        if opts["archive_dir"]:
            d = opts["archive_dir"]
            if not os.path.isdir(d):
                raise CommandError(f"--archive-dir 폴더 미존재: {d} (사전 생성 필요).")
            rc_path = os.path.join(d, "rc_self_loops.jsonl")
            rps_path = os.path.join(d, "rps_self_loops.jsonl")
            rc_archived = self._dump(RelationConfidence, rc_self, rc_path)
            rps_archived = self._dump(RelationPairSnapshot, rps_self, rps_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  아카이브: RC {rc_archived}행→{rc_path} · RPS {rps_archived}행→{rps_path}"
                )
            )

        # ── Neo4j 자기루프 엣지 프로브(read-only) ──
        self._probe_neo4j_self_loops()

        if not opts["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    f"  DRY-RUN: 삭제 안 함. --apply 시 RC {rc_self_n}행 + RPS {rps_self_n}행 삭제 예정 "
                    f"(RC {rc_total}→{rc_total - rc_self_n}, RPS {rps_total}→{rps_total - rps_self_n})."
                )
            )
            return

        # ── --apply: 실삭제(prod-write). 아카이브 강제(카운트 일치). ──
        if not opts["archive_dir"]:
            raise CommandError("--apply 전 --archive-dir 로 전행 아카이브 필수.")
        if rc_archived != rc_self_n or rps_archived != rps_self_n:
            raise CommandError(
                f"아카이브 카운트 불일치 (RC {rc_archived}!={rc_self_n} 또는 "
                f"RPS {rps_archived}!={rps_self_n}) — 삭제 중단."
            )

        # Neo4j 자기루프 엣지 전량 삭제(best-effort). 자기루프는 a≠b 불변식 위반이라 전부 무효.
        self._delete_neo4j_self_loops()

        # PG 삭제 — 트랜잭션 가드(RPS→RC 순, 부분삭제 방지).
        with transaction.atomic():
            rps_deleted, _ = rps_self.delete()
            rc_deleted, _ = rc_self.delete()

        # ── 사후 검증 ──
        rc_self_after = RelationConfidence.objects.filter(symbol_a=F("symbol_b")).count()
        rps_self_after = RelationPairSnapshot.objects.filter(
            canonical_a=F("canonical_b")
        ).count()
        rc_total_after = RelationConfidence.objects.count()
        rps_total_after = RelationPairSnapshot.objects.count()

        assert rc_self_after == 0, f"RC 자기루프 잔존 {rc_self_after}"
        assert rps_self_after == 0, f"RPS 자기루프 잔존 {rps_self_after}"
        assert rc_total_after == rc_total - rc_self_n, "RC 총행 검증 실패(과다 삭제?)"
        assert rps_total_after == rps_total - rps_self_n, "RPS 총행 검증 실패(과다 삭제?)"

        self.stdout.write(
            self.style.SUCCESS(
                f"  삭제 완료: RC {rc_deleted}행 · RPS {rps_deleted}행. "
                f"자기루프 RC={rc_self_after} RPS={rps_self_after}(0 확인). "
                f"총 RC {rc_total}→{rc_total_after} · RPS {rps_total}→{rps_total_after}."
            )
        )
        self.stdout.write(
            "  ★ 다음: migrate(0034 CheckConstraint) 실행 가능. "
            "제약이 자기루프 0 상태를 영구 강제한다."
        )

    def _dump(self, model, qs, path):
        fields = [f.name for f in model._meta.fields]
        n = 0
        with open(path, "w") as fh:
            for row in qs.values(*fields).iterator():
                fh.write(json.dumps(row, cls=DjangoJSONEncoder, ensure_ascii=False) + "\n")
                n += 1
        return n

    def _probe_neo4j_self_loops(self):
        """Neo4j self-loop 엣지 (a)-[r]->(a) 잔존 read-only 확인."""
        try:
            from apps.chain_sight.graph import get_graph_repository

            repo = get_graph_repository()
            rows = repo.run_query(
                "MATCH (a:Stock)-[r]->(a) RETURN count(r) AS n"
            )
            n = rows[0]["n"] if rows else 0
            if n:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Neo4j self-loop 엣지 {n}개 잔존 — --apply 시 best-effort 삭제. "
                        "미가동 시 수동 Cypher: MATCH (a:Stock)-[r]->(a) DELETE r"
                    )
                )
            else:
                self.stdout.write("  Neo4j self-loop 엣지 0(또는 미동기화) — 정리 불요.")
        except Exception as exc:  # noqa: BLE001 — Neo4j 미가동 등 흡수
            self.stdout.write(f"  Neo4j 확인 skip(미가동/오류): {exc}")

    def _delete_neo4j_self_loops(self):
        """Neo4j self-loop 엣지 (a)-[r]->(a) 전량 삭제(best-effort).

        RC 13행 대응 엣지뿐 아니라 orphan 자기루프 엣지까지 포함 전수 제거
        (프로브에서 16개 실측 — RC 13 + orphan 3). 자기루프는 a≠b 불변식 위반이라 전부 무효.
        """
        try:
            from apps.chain_sight.graph import get_graph_repository

            repo = get_graph_repository()
            before = repo.run_query("MATCH (a:Stock)-[r]->(a) RETURN count(r) AS n")
            n_before = before[0]["n"] if before else 0
            if n_before == 0:
                self.stdout.write("  Neo4j self-loop 엣지 0 — 정리 불요.")
                return
            repo.run_query("MATCH (a:Stock)-[r]->(a) DELETE r")
            after = repo.run_query("MATCH (a:Stock)-[r]->(a) RETURN count(r) AS n")
            n_after = after[0]["n"] if after else 0
            self.stdout.write(
                self.style.SUCCESS(f"  Neo4j self-loop 엣지 삭제: {n_before}→{n_after}.")
            )
        except Exception as exc:  # noqa: BLE001 — Neo4j 미가동 등 흡수
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ Neo4j 삭제 skip(미가동/오류): {exc}. "
                    "가동 후 수동 Cypher: MATCH (a:Stock)-[r]->(a) DELETE r"
                )
            )
