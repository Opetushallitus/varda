# Generated by Django 4.1.2 on 2022-10-19 14:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0074_autovacuum_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='batcherror',
            name='henkilo_duplicate',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='batcherrors_duplicate', to='varda.henkilo'),
        ),
    ]