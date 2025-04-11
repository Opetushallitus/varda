# Generated by Django 4.0.5 on 2022-08-23 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0071_z10_kelavarhaiskasvatussuhde_varda_z10_k_henkilo_5c6cba_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalyearlyreportsummary',
            name='toimipaikka_by_toimintamuoto_count',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='historicalyearlyreportsummary',
            name='varhaiskasvatuspaikat_sum',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='yearlyreportsummary',
            name='toimipaikka_by_toimintamuoto_count',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='yearlyreportsummary',
            name='varhaiskasvatuspaikat_sum',
            field=models.IntegerField(null=True),
        ),
    ]
