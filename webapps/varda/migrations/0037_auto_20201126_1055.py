# Generated by Django 2.2.13 on 2020-11-26 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0036_postinumero_koodit'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='toimipaikka',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='toimipaikka',
            constraint=models.UniqueConstraint(fields=('nimi', 'vakajarjestaja'), name='nimi_vakajarjestaja_unique_constraint'),
        ),
    ]