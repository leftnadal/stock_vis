"""데이터 마이그레이션: 기존 지표의 display_unit을 _infer_unit() 결과로 채우기"""

from django.db import migrations


def populate_display_unit(apps, schema_editor):
    ThesisIndicator = apps.get_model('thesis', 'ThesisIndicator')
    for ind in ThesisIndicator.objects.filter(display_unit=''):
        params = ind.data_params or {}
        series_id = params.get('series_id', '')
        unit = ''
        if series_id in ('FEDFUNDS', 'DGS10', 'DGS2'):
            unit = '%'
        elif ind.indicator_type == 'sentiment':
            unit = ''
        else:
            symbol = params.get('symbol', '').upper()
            if 'KRW' in symbol or 'USDKRW' in symbol:
                unit = '원'
            elif symbol.startswith('^'):
                unit = 'pt'
            elif ind.data_source == 'fmp':
                unit = '$'
        if unit:
            ind.display_unit = unit
            ind.save(update_fields=['display_unit'])


class Migration(migrations.Migration):

    dependencies = [
        ('thesis', '0004_add_display_unit'),
    ]

    operations = [
        migrations.RunPython(populate_display_unit, migrations.RunPython.noop),
    ]
