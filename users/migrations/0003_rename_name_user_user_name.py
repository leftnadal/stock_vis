# Generated by Django 5.1.7 on 2025-04-03 09:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_favorite_stock'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='name',
            new_name='user_name',
        ),
    ]
