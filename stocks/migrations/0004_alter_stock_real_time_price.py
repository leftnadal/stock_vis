# Generated by Django 5.1.7 on 2025-04-13 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0003_rename_name_stock_stock_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stock',
            name='real_time_price',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
