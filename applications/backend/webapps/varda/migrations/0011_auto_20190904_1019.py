# Generated by Django 2.2.4 on 2019-09-04 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0010_auto_20190807_1055'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='henkilo',
            constraint=models.UniqueConstraint(fields=('henkilo_oid', 'henkilotunnus_unique_hash'), name='henkilo_oid_henkilotunnus_unique_hash_unique_constraint'),
        ),
    ]
