# audit P0 #9 (2026-04-29): Neo4j 동기화 플래그 통일
#   - RelationConfidence: synced_to_neo4j 제거 (neo4j_dirty 단일 소스)
#   - CompanyChainProfile: neo4j_synced (반전 의미) → neo4j_dirty (의미 통일)
# 데이터 마이그레이션 순서: AddField → RunPython(반전) → RemoveField

from django.db import migrations, models


def migrate_neo4j_synced_to_dirty(apps, schema_editor):
    """기존 neo4j_synced=True (동기화됨) → neo4j_dirty=False (반전)."""
    CompanyChainProfile = apps.get_model("chainsight", "CompanyChainProfile")
    # neo4j_synced=True였던 row만 neo4j_dirty=False로 변경. 나머지는 default=True 유지.
    CompanyChainProfile.objects.filter(neo4j_synced=True).update(neo4j_dirty=False)


def migrate_neo4j_dirty_to_synced(apps, schema_editor):
    """역방향: neo4j_dirty=False (반영됨) → neo4j_synced=True."""
    CompanyChainProfile = apps.get_model("chainsight", "CompanyChainProfile")
    CompanyChainProfile.objects.filter(neo4j_dirty=False).update(neo4j_synced=True)


class Migration(migrations.Migration):
    dependencies = [
        ("chainsight", "0007_seedsnapshot"),
    ]

    operations = [
        # ── RelationConfidence: synced_to_neo4j 제거 ──
        migrations.RemoveIndex(
            model_name="relationconfidence",
            name="chainsight__synced__2206c6_idx",
        ),
        migrations.RemoveField(
            model_name="relationconfidence",
            name="synced_to_neo4j",
        ),
        # ── CompanyChainProfile: neo4j_synced → neo4j_dirty (의미 반전) ──
        migrations.AddField(
            model_name="companychainprofile",
            name="neo4j_dirty",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.RunPython(
            migrate_neo4j_synced_to_dirty,
            reverse_code=migrate_neo4j_dirty_to_synced,
        ),
        migrations.RemoveField(
            model_name="companychainprofile",
            name="neo4j_synced",
        ),
    ]
