# Generated by Django 5.1.7 on 2025-03-26 06:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='economicindicator',
            old_name='name',
            new_name='indicator_name',
        ),
    ]
