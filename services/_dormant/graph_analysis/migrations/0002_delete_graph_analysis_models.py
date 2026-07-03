"""graph_analysis CUT — STAGE 1: 5개 빈 테이블 DROP (D-REHOME-GRAPH).

휴면 앱(소비자 0 = INSTALLED_APPS 1곳뿐, 0 rows, 해자 무접촉)의 Postgres 테이블을
정식 drop-migration으로 제거한다. 코드/INSTALLED_APPS 제거(STAGE 2)보다 **먼저** 적용해야
Django가 앱을 잊기 전에 DROP이 실행된다(순서 제약, D-REHOME-GRAPH).

reversible: `migrate graph_analysis 0001` = 빈 테이블 5개 재생성(DeleteModel 자동 역).
삭제 순서: CorrelationAnomaly(FK→CorrelationEdge)를 먼저, 이후 참조 대상.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("graph_analysis", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="CorrelationAnomaly"),
        migrations.DeleteModel(name="CorrelationEdge"),
        migrations.DeleteModel(name="CorrelationMatrix"),
        migrations.DeleteModel(name="PriceCache"),
        migrations.DeleteModel(name="GraphMetadata"),
    ]
