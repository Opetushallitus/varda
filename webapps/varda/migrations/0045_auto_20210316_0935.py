# Generated by Django 3.1.4 on 2021-03-16 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0044_auto_20210225_1114'),
    ]

    operations = [
        migrations.AlterField(
            model_name='z6_requestlog',
            name='timestamp',
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
    ]