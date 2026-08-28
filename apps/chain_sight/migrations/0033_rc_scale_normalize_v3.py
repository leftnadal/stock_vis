"""D-RC-SCALE (RC-A-1 PART 2): 점수 눈금 [0,100]→[0,1] 통일 + score_version "3.0".

truth_score·market_score 의 구 계단 {0,35,60,85} 를 {0,0.35,0.60,0.85} 로 정규화하고
score_version 을 "3.0" 으로 승격한다. 변환은 단일 소스 score_scale.apply_scale_normalization
(멱등·>1.0 인 값만 /100·이미 [0,1]인 0/0.5/0.6 무접촉)을 재사용한다.

⚠ dev=prod 공유 DB — 이 마이그레이션 실행은 prod-write. 배포(병진) 단계에서만 적용.
   reverse 는 *100 근사이며 "PEER" 2행(0.5/0.6)은 완전 복원 불가 → 진짜 롤백은 pg 백업.
"""

from django.db import migrations, models
from django.db.models import F


def forward(apps, schema_editor):
    RC = apps.get_model("chainsight", "RelationConfidence")
    # 단일 소스 재사용(런타임 함수). historical 모델도 objects/update 동일 동작.
    from apps.chain_sight.services.score_scale import apply_scale_normalization

    result = apply_scale_normalization(RC)
    print(f"  [0033 forward] RC scale 정규화: {result}")


def reverse(apps, schema_editor):
    """근사 역변환(*100) + version "2.1". outlier 2행(0.5/0.6)은 50/60로 부정확 →
    비상 롤백은 pg 백업 사용."""
    RC = apps.get_model("chainsight", "RelationConfidence")
    RC.objects.filter(truth_score__gt=0.0, truth_score__lte=1.0).update(
        truth_score=F("truth_score") * 100.0
    )
    RC.objects.filter(market_score__gt=0.0, market_score__lte=1.0).update(
        market_score=F("market_score") * 100.0
    )
    RC.objects.update(score_version="2.1")


class Migration(migrations.Migration):

    dependencies = [
        ("chainsight", "0032_symboldemandsignal"),
    ]

    operations = [
        # 모델 default "2.1"→"3.0" (DB DDL 무변경 — Django state only).
        migrations.AlterField(
            model_name="relationconfidence",
            name="score_version",
            field=models.CharField(default="3.0", max_length=10),
        ),
        migrations.RunPython(forward, reverse),
    ]
