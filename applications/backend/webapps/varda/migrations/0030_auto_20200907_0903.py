# Generated by Django 2.2.13 on 2020-09-07 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0029_auto_20200813_1005'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='tyontekija',
            constraint=models.UniqueConstraint(fields=('henkilo', 'vakajarjestaja'), name='unique_tyontekija'),
        ),
    ]