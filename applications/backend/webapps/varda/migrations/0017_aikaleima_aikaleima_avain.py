# Generated by Django 2.2.11 on 2020-04-07 05:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0016_auto_20200305_1019'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aikaleima',
            name='avain',
            field=models.TextField(choices=[('AUDIT_LOG_AWS_LAST_UPDATE', 'AUDIT_LOG_AWS_LAST_UPDATE'), ('HENKILOMUUTOS_LAST_UPDATE', 'HENKILOMUUTOS_LAST_UPDATE'), ('HUOLTAJASUHDEMUUTOS_LAST_UPDATE', 'HUOLTAJASUHDEMUUTOS_LAST_UPDATE'), ('ORGANISAATIOS_LAST_UPDATE', 'ORGANISAATIOS_LAST_UPDATE'), ('ORGANISAATIOS_VARDA_LAST_UPDATE', 'ORGANISAATIOS_VARDA_LAST_UPDATE')], unique=True),
        ),
    ]