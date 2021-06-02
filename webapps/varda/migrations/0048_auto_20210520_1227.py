# Generated by Django 3.1.4 on 2021-05-20 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0047_auto_20210421_1716'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['vakajarjestaja'], name='varda_z6_re_vakajar_9ad3f4_idx'),
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['lahdejarjestelma'], name='varda_z6_re_lahdeja_5bd86a_idx'),
        ),
        migrations.AddIndex(
            model_name='z6_requestlog',
            index=models.Index(fields=['user'], name='varda_z6_re_user_id_0a04de_idx'),
        ),
    ]