# PR-A2 인덱스 ProjectState 정렬 — RenameField가 인덱스 필드 ref를 자동 갱신하지 않는 문제 보정
#
# 0003에서 is_exposed → shown_on_layer0 RenameField를 수행했고, Django는 SQL 레벨에서
# 인덱스의 컬럼 참조를 자동 갱신했다. 그러나 ProjectState의 Meta.indexes 정의는
# 갱신되지 않아 makemigrations --check가 차이를 감지한다.
#
# DB SQL은 이미 정확하므로 SeparateDatabaseAndState로 ProjectState만 정렬한다.
# database_operations는 비워서 forward/reverse 모두 SQL 변경 없이 동작.
# 인덱스 이름은 'mp_news_ttl_idx'로 동일하게 유지.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketpulse', '0004_pr_a2_high_risk_restructure'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveIndex(
                    model_name='marketpulsenews',
                    name='mp_news_ttl_idx',
                ),
                migrations.AddIndex(
                    model_name='marketpulsenews',
                    index=models.Index(
                        fields=['published_at', 'shown_on_layer0'],
                        name='mp_news_ttl_idx',
                    ),
                ),
            ],
        ),
    ]
