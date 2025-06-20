# Generated by Django 5.2.1 on 2025-05-18 01:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0006_userprofile_initial_investment_amount_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyProfitLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('profit_amount', models.DecimalField(decimal_places=2, default=0.0, help_text='Simulated profit for this day', max_digits=12)),
                ('closing_balance', models.DecimalField(decimal_places=2, help_text='Simulated portfolio balance at end of this day', max_digits=12)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user', 'date'],
                'unique_together': {('user', 'date')},
            },
        ),
    ]
