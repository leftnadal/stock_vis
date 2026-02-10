# Generated migration for Screener Alert System (Phase 1)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('serverless', '0005_screener_upgrade'),
    ]

    operations = [
        # ScreenerAlert model
        migrations.CreateModel(
            name='ScreenerAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='알림 이름', max_length=100)),
                ('description', models.TextField(blank=True, help_text='알림 설명')),
                ('filters_json', models.JSONField(default=dict, help_text='커스텀 필터 조건 (프리셋 없을 때 사용)')),
                ('alert_type', models.CharField(choices=[('filter_match', '필터 조건 충족'), ('price_target', '목표가 도달'), ('volume_spike', '거래량 급증'), ('ai_signal', 'AI 신호'), ('new_high', '신고가'), ('new_low', '신저가')], default='filter_match', max_length=20)),
                ('target_count', models.IntegerField(blank=True, help_text='필터 매칭 종목 수 임계값 (예: 10개 이상이면 알림)', null=True)),
                ('target_symbols', models.JSONField(blank=True, default=list, help_text='특정 종목 모니터링 (price_target용)')),
                ('is_active', models.BooleanField(default=True, help_text='알림 활성화 여부')),
                ('cooldown_hours', models.IntegerField(default=24, help_text='동일 조건 재알림 대기 시간 (시간)')),
                ('last_triggered_at', models.DateTimeField(blank=True, help_text='마지막 알림 발송 시간', null=True)),
                ('trigger_count', models.IntegerField(default=0, help_text='총 알림 발송 횟수')),
                ('notify_in_app', models.BooleanField(default=True, help_text='인앱 알림')),
                ('notify_email', models.BooleanField(default=False, help_text='이메일 알림')),
                ('notify_push', models.BooleanField(default=False, help_text='푸시 알림 (PWA)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('preset', models.ForeignKey(blank=True, help_text='프리셋 기반 알림 (null이면 커스텀 필터)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='serverless.screenerpreset')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screener_alerts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'serverless_screener_alert',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='screeneralert',
            index=models.Index(fields=['user', 'is_active'], name='serverless__user_id_5c8e1c_idx'),
        ),
        migrations.AddIndex(
            model_name='screeneralert',
            index=models.Index(fields=['is_active', '-created_at'], name='serverless__is_acti_a7b3e4_idx'),
        ),

        # AlertHistory model
        migrations.CreateModel(
            name='AlertHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('triggered_at', models.DateTimeField(auto_now_add=True)),
                ('matched_count', models.IntegerField(help_text='매칭된 종목 수')),
                ('matched_symbols', models.JSONField(default=list, help_text='매칭된 종목 리스트 (최대 10개)')),
                ('snapshot', models.JSONField(default=dict, help_text='알림 시점 필터 조건 스냅샷')),
                ('status', models.CharField(choices=[('sent', '발송 완료'), ('failed', '발송 실패'), ('skipped', '쿨다운으로 스킵')], default='sent', max_length=10)),
                ('error_message', models.TextField(blank=True, help_text='실패 시 에러 메시지')),
                ('read_at', models.DateTimeField(blank=True, help_text='사용자 확인 시간', null=True)),
                ('dismissed', models.BooleanField(default=False, help_text='알림 해제 여부')),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='serverless.screeneralert')),
            ],
            options={
                'db_table': 'serverless_alert_history',
                'ordering': ['-triggered_at'],
            },
        ),
        migrations.AddIndex(
            model_name='alerthistory',
            index=models.Index(fields=['alert', '-triggered_at'], name='serverless__alert_i_5a8b1f_idx'),
        ),
        migrations.AddIndex(
            model_name='alerthistory',
            index=models.Index(fields=['triggered_at'], name='serverless__trigger_d2e8a1_idx'),
        ),

        # InvestmentThesis model (Phase 2 준비)
        migrations.CreateModel(
            name='InvestmentThesis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='투자 테제 제목', max_length=200)),
                ('summary', models.TextField(help_text='투자 테제 요약 (1-2문장)')),
                ('filters_snapshot', models.JSONField(default=dict, help_text='테제 생성 시 적용된 필터')),
                ('preset_ids', models.JSONField(default=list, help_text='사용된 프리셋 IDs')),
                ('key_metrics', models.JSONField(default=list, help_text="핵심 지표 (예: ['PER < 15', 'ROE > 20%'])")),
                ('top_picks', models.JSONField(default=list, help_text='추천 종목 (최대 5개)')),
                ('risks', models.JSONField(default=list, help_text='리스크 요인')),
                ('rationale', models.TextField(blank=True, help_text='투자 근거 상세')),
                ('llm_model', models.CharField(default='gemini-2.5-flash', max_length=50)),
                ('generation_time_ms', models.IntegerField(blank=True, null=True)),
                ('is_public', models.BooleanField(default=False)),
                ('share_code', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('view_count', models.IntegerField(default=0)),
                ('save_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='investment_theses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'serverless_investment_thesis',
                'ordering': ['-created_at'],
                'verbose_name_plural': 'Investment Theses',
            },
        ),
        migrations.AddIndex(
            model_name='investmentthesis',
            index=models.Index(fields=['user', '-created_at'], name='serverless__user_id_9f1b2c_idx'),
        ),
        migrations.AddIndex(
            model_name='investmentthesis',
            index=models.Index(fields=['is_public', '-view_count'], name='serverless__is_publ_3e4d5a_idx'),
        ),
        migrations.AddIndex(
            model_name='investmentthesis',
            index=models.Index(fields=['share_code'], name='serverless__share_c_7a8b9c_idx'),
        ),
    ]
