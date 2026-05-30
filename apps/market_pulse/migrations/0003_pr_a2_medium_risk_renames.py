# PR-A2 중위험 — 필드명 변경 (RenameField only)
#
# MarketPulseNews:
#   is_exposed       → shown_on_layer0
#   first_exposed_at → shown_at
#
# BriefingLog:
#   inputs_summary   → prompt_inputs
#
# mp_news_ttl_idx 인덱스: SQL 레벨에서는 RenameField로 자동 갱신되지만, Django의
# ProjectState Meta.indexes 정의는 갱신되지 않아 makemigrations가 차이를 감지한다.
# 그래서 후속 0005에서 RemoveIndex/AddIndex로 ProjectState만 정렬한다 (동일 이름).

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketpulse", "0002_pr_a2_field_extension"),
    ]

    operations = [
        migrations.RenameField(
            model_name="marketpulsenews",
            old_name="is_exposed",
            new_name="shown_on_layer0",
        ),
        migrations.RenameField(
            model_name="marketpulsenews",
            old_name="first_exposed_at",
            new_name="shown_at",
        ),
        migrations.RenameField(
            model_name="briefinglog",
            old_name="inputs_summary",
            new_name="prompt_inputs",
        ),
    ]
