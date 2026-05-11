# PR-A2 고위험 — 구조 변경 (AddField + RunPython + RemoveField)
#
# MarketPulseNews:
#   추가: entities (JSONField default=dict)
#         구조: {"tickers": [...], "sectors": [], "topics": [...]}
#   제거: matched_symbols, matched_keywords
#   데이터 매핑: matched_symbols → entities['tickers']
#               matched_keywords → entities['topics']
#               entities['sectors'] → [] (기존 데이터 없음)
#
# BriefingLog:
#   추가: body (TextField), body_sections (JSONField default=list)
#   제거: content
#   데이터 매핑: content → body (전체 복사)
#               body_sections → [] (신규 필드)

from django.db import migrations, models


def forward_news_entities(apps, schema_editor):
    """matched_symbols/matched_keywords → entities dict 변환."""
    MarketPulseNews = apps.get_model('marketpulse', 'MarketPulseNews')
    batch = []
    for news in MarketPulseNews.objects.all().iterator(chunk_size=500):
        tickers = news.matched_symbols if isinstance(news.matched_symbols, list) else []
        topics = news.matched_keywords if isinstance(news.matched_keywords, list) else []
        news.entities = {'tickers': tickers, 'sectors': [], 'topics': topics}
        batch.append(news)
        if len(batch) >= 500:
            MarketPulseNews.objects.bulk_update(batch, ['entities'])
            batch = []
    if batch:
        MarketPulseNews.objects.bulk_update(batch, ['entities'])


def reverse_news_entities(apps, schema_editor):
    """entities dict → matched_symbols/matched_keywords 복원."""
    MarketPulseNews = apps.get_model('marketpulse', 'MarketPulseNews')
    batch = []
    for news in MarketPulseNews.objects.all().iterator(chunk_size=500):
        ent = news.entities if isinstance(news.entities, dict) else {}
        news.matched_symbols = ent.get('tickers', [])
        news.matched_keywords = ent.get('topics', [])
        batch.append(news)
        if len(batch) >= 500:
            MarketPulseNews.objects.bulk_update(batch, ['matched_symbols', 'matched_keywords'])
            batch = []
    if batch:
        MarketPulseNews.objects.bulk_update(batch, ['matched_symbols', 'matched_keywords'])


def forward_briefing_body(apps, schema_editor):
    """content → body 전체 복사."""
    BriefingLog = apps.get_model('marketpulse', 'BriefingLog')
    batch = []
    for log in BriefingLog.objects.all().iterator(chunk_size=500):
        log.body = log.content or ''
        log.body_sections = []
        batch.append(log)
        if len(batch) >= 500:
            BriefingLog.objects.bulk_update(batch, ['body', 'body_sections'])
            batch = []
    if batch:
        BriefingLog.objects.bulk_update(batch, ['body', 'body_sections'])


def reverse_briefing_body(apps, schema_editor):
    """body → content 복원."""
    BriefingLog = apps.get_model('marketpulse', 'BriefingLog')
    batch = []
    for log in BriefingLog.objects.all().iterator(chunk_size=500):
        log.content = log.body or ''
        batch.append(log)
        if len(batch) >= 500:
            BriefingLog.objects.bulk_update(batch, ['content'])
            batch = []
    if batch:
        BriefingLog.objects.bulk_update(batch, ['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('marketpulse', '0003_pr_a2_medium_risk_renames'),
    ]

    operations = [
        # ─── MarketPulseNews: entities 추가 → 데이터 이전 → 구 필드 제거 ───
        migrations.AddField(
            model_name='marketpulsenews',
            name='entities',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(
            forward_news_entities,
            reverse_code=reverse_news_entities,
        ),
        migrations.RemoveField(
            model_name='marketpulsenews',
            name='matched_symbols',
        ),
        migrations.RemoveField(
            model_name='marketpulsenews',
            name='matched_keywords',
        ),

        # ─── BriefingLog: body/body_sections 추가 → 데이터 이전 → content 제거 ───
        migrations.AddField(
            model_name='briefinglog',
            name='body',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='briefinglog',
            name='body_sections',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(
            forward_briefing_body,
            reverse_code=reverse_briefing_body,
        ),
        migrations.RemoveField(
            model_name='briefinglog',
            name='content',
        ),
    ]
