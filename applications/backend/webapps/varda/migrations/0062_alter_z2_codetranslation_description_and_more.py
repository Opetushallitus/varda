# Generated by Django 4.0.1 on 2022-02-17 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0061_z9_relatedobjectchanged_varda_z9_re_parent__34baf3_idx'),
    ]

    operations = [
        migrations.AlterField(
            model_name='z2_codetranslation',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='z2_codetranslation',
            name='name',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='z2_codetranslation',
            name='short_name',
            field=models.TextField(blank=True),
        ),
    ]