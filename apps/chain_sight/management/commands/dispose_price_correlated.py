"""D-RC-PC-DISPOSE (RC-A-1 PART 3): PRICE_CORRELATED 관계 처분(아카이브 후 삭제).

PC는 D2에서 "관계 종류"에서 은퇴(신규생성 중단)됐고 전량 relation_category="market",
serving_layer="context"(비-서빙). 3,784쌍 전부 PEER_OF 중복(구조적 잉여). 확인된 연결의
강도는 P1B sync_strength가 담당. 본 커맨드는 아카이브(복원경로) 후 PG 행을 삭제한다.

⚠ dev=prod 공유 DB — --apply 는 prod-write(자율 금지). 병진 배포 단계에서만 --apply.
  기본은 dry-run(카운트만). --archive PATH 는 read-only(덤프 파일 생성).

사용:
  # 1) 아카이브 생성(read-only) + dry-run 카운트
  python manage.py dispose_price_correlated --archive /ops/archive/price_correlated_YYYYMMDD.jsonl
  # 2) (병진) 실삭제 — 아카이브 존재 필수
  python manage.py dispose_price_correlated --archive <위 파일> --apply

복원: jsonl 각 줄 = RelationConfidence 한 행 전 컬럼. 복원은
  for line in file: RelationConfidence.objects.create(**json.loads(line))  (pk 제외/재생성)
  또는 pg 백업 복원(권장).
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder

REL_TYPE = "PRICE_CORRELATED"


class Command(BaseCommand):
    help = "PRICE_CORRELATED 관계를 아카이브 후 삭제 (기본 dry-run; --apply 시 실삭제=prod-write)"

    def add_arguments(self, parser):
        parser.add_argument("--archive", type=str, default=None,
                            help="PC 전행 jsonl 덤프 경로(복원용). --apply 전 필수.")
        parser.add_argument("--apply", action="store_true",
                            help="실삭제 실행(prod-write). 미지정=dry-run.")

    def handle(self, *args, **opts):
        from apps.chain_sight.models import RelationConfidence, RelationPairSnapshot

        pc_qs = RelationConfidence.objects.filter(relation_type=REL_TYPE)
        pc_count = pc_qs.count()
        total_before = RelationConfidence.objects.count()
        peer_before = RelationConfidence.objects.filter(relation_type="PEER_OF").count()
        rps_before = RelationPairSnapshot.objects.count()

        self.stdout.write(f"[dispose PC] PRICE_CORRELATED={pc_count} / 총={total_before} "
                          f"/ PEER_OF={peer_before} / RPS={rps_before}")

        # 아카이브(read-only): 전 컬럼 덤프
        archived = 0
        if opts["archive"]:
            fields = [f.name for f in RelationConfidence._meta.fields]
            with open(opts["archive"], "w") as fh:
                for row in pc_qs.values(*fields).iterator():
                    fh.write(json.dumps(row, cls=DjangoJSONEncoder, ensure_ascii=False) + "\n")
                    archived += 1
            self.stdout.write(self.style.SUCCESS(
                f"  아카이브 {archived}행 → {opts['archive']}"))

        # Neo4j PC 엣지 잔존 확인(read-only, best-effort). 잔존 시 별도 정리 필요 경고.
        self._probe_neo4j_pc_edges()

        if not opts["apply"]:
            self.stdout.write(self.style.WARNING(
                f"  DRY-RUN: 삭제 안 함. --apply 시 {pc_count}행 삭제 예정 "
                f"(총 {total_before}→{total_before - pc_count})."))
            return

        # --apply: 실삭제 (prod-write). 아카이브 강제.
        if not opts["archive"] or archived != pc_count:
            raise CommandError(
                "--apply 전 --archive로 전행 아카이브 필수 "
                f"(아카이브 {archived} != PC {pc_count}).")

        deleted, _ = pc_qs.delete()
        total_after = RelationConfidence.objects.count()
        peer_after = RelationConfidence.objects.filter(relation_type="PEER_OF").count()
        pc_after = RelationConfidence.objects.filter(relation_type=REL_TYPE).count()
        rps_after = RelationPairSnapshot.objects.count()

        # 검증
        assert pc_after == 0, f"PC 잔존 {pc_after}"
        assert total_after == total_before - pc_count, "총행 검증 실패"
        assert peer_after == peer_before, "PEER_OF 변동(무접촉 위반)"
        assert rps_after == rps_before, "RPS 고아/변동(독립 스냅샷이어야 함)"

        self.stdout.write(self.style.SUCCESS(
            f"  삭제 완료: PC {deleted}행. PC후={pc_after} 총={total_after} "
            f"PEER_OF={peer_after}(불변) RPS={rps_after}(불변)."))
        self.stdout.write(
            "  ★ 사후: pair_aggregation 재실행 시 PC-유일 market 쌍의 market_max 소멸 반영. "
            "strip θ 상향. after-snapshot 측정 권장.")

    def _probe_neo4j_pc_edges(self):
        """Neo4j에 PRICE_CORRELATED 엣지가 잔존하는지 read-only 확인."""
        try:
            from apps.chain_sight.graph import get_graph_repository
            repo = get_graph_repository()
            rows = repo.run_query(
                "MATCH ()-[r:PRICE_CORRELATED]->() RETURN count(r) AS n")
            n = rows[0]["n"] if rows else 0
            if n:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Neo4j PRICE_CORRELATED 엣지 {n}개 잔존 — PG 삭제로 자동 소거 안 됨. "
                    "별도 Cypher 정리 필요: MATCH ()-[r:PRICE_CORRELATED]->() DELETE r"))
            else:
                self.stdout.write("  Neo4j PC 엣지 0(또는 미동기화) — 정리 불요.")
        except Exception as exc:  # noqa: BLE001 — Neo4j 미가동(06-20~) 등 흡수
            self.stdout.write(f"  Neo4j 확인 skip(미가동/오류): {exc}")
