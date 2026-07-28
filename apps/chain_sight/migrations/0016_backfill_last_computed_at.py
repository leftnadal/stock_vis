"""T-3b ① 콜드스타트 백필: last_computed_at ← last_observed_at (NULL 행 전체).

배경: 신 선별식(apply_upward_learning_task)이
    Q(last_computed_at__isnull=True) | Q(last_observed_at__gt=F("last_computed_at"))
로 바뀌면서, last_computed_at IS NULL 분기를 "진짜 신규 pair" 전용으로 만들어야 한다.
백필 전에는 기존 13,427행(last_computed_at NULL)이 전부 isnull 분기에 걸려 첫 틱에
수천 단위 콜드스타트 폭주가 발생한다(실측: 비-market 9,635행 매칭).

이 마이그레이션은 기존 행의 last_computed_at을 last_observed_at으로 채워, isnull 분기를
진짜 신규 pair(향후 생성분) 전용화한다. 채운 뒤에는 last_observed_at == last_computed_at
이므로 gt 조건도 미충족 → 다음 seed 재관측(last_observed_at 갱신) 전까지 재선별 안 됨.

가역성: 순수 가산(기존 값 변경 아님 — NULL만 채움). reverse는 문서화된 no-op
(어느 행이 원래 NULL이었는지 복원 불가하나, last_computed_at은 감사/멱등 마커일 뿐
비즈니스 데이터가 아니므로 남겨도 무해). QuerySet.update() 사용 = auto_now 미발동.
"""

from django.db import migrations
from django.db.models import F


def backfill_last_computed_at(apps, schema_editor):
    RelationConfidence = apps.get_model("chainsight", "RelationConfidence")
    RelationConfidence.objects.filter(last_computed_at__isnull=True).update(
        last_computed_at=F("last_observed_at")
    )


def noop_reverse(apps, schema_editor):
    # 가역 문서화: 원래 NULL이던 행 집합을 복원할 수 없으므로 의도적 no-op.
    # last_computed_at은 멱등/감사 마커라 값이 남아도 하향/상향 로직에 무해.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("chainsight", "0015_relationconfidence_evidence_streak_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_last_computed_at, noop_reverse),
    ]
