# Generated by Django 4.0.1 on 2022-05-13 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0069_alter_historicalhenkilo_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Z10_KelaVarhaiskasvatussuhde',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('varhaiskasvatussuhde_id', models.IntegerField()),
                ('suhde_luonti_pvm', models.DateTimeField()),
                ('suhde_alkamis_pvm', models.DateField()),
                ('suhde_paattymis_pvm', models.DateField(null=True)),
                ('varhaiskasvatuspaatos_id', models.IntegerField()),
                ('paatos_luonti_pvm', models.DateTimeField()),
                ('jarjestamismuoto_koodi', models.CharField(max_length=50)),
                ('tilapainen_vaka_kytkin', models.BooleanField()),
                ('lapsi_id', models.IntegerField()),
                ('henkilo_id', models.IntegerField()),
                ('has_hetu', models.BooleanField()),
                ('history_type', models.CharField(max_length=1)),
                ('history_date', models.DateTimeField()),
            ],
            options={
                'verbose_name_plural': 'Kela varhaiskasvatussuhteet',
            },
        ),
        migrations.AddIndex(
            model_name='z10_kelavarhaiskasvatussuhde',
            index=models.Index(fields=['history_date'], name='varda_z10_k_history_e1392a_idx'),
        ),
        migrations.AddIndex(
            model_name='z10_kelavarhaiskasvatussuhde',
            index=models.Index(fields=['varhaiskasvatussuhde_id', '-history_date'], name='varda_z10_k_varhais_046a21_idx'),
        ),
    ]
