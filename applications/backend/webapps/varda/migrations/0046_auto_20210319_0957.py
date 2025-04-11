# Generated by Django 3.1.4 on 2021-03-19 07:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0045_auto_20210318_0953'),
    ]

    operations = [
        migrations.AlterField(
            model_name='z6_requestlog',
            name='timestamp',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['timestamp'], name='varda_z6_re_timesta_92f854_idx'),
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['-timestamp'], name='varda_z6_re_timesta_96cf31_idx'),
        ),
    ]
