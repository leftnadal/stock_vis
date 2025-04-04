# Generated by Django 5.1.7 on 2025-03-24 08:14

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('symbol', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('exchange', models.CharField(blank=True, max_length=20, null=True)),
                ('real_time_price', models.DateTimeField(default=0.0)),
                ('overview', models.TextField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
