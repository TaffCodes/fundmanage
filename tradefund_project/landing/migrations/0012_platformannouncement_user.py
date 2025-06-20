# Generated by Django 5.2.1 on 2025-05-27 11:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0011_platformannouncement_is_read'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='platformannouncement',
            name='user',
            field=models.ForeignKey(blank=True, help_text='If set, announcement is targeted to this user only. Leave blank for all users.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='platform_announcements', to=settings.AUTH_USER_MODEL),
        ),
    ]
