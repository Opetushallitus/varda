# Generated by Django 2.2.11 on 2020-08-13 07:05

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0028_auto_20200803_1124'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaltutkinto',
            name='vakajarjestaja',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='tutkinto',
            name='vakajarjestaja',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tutkinnot', to='varda.VakaJarjestaja'),
        ),
        migrations.AlterField(
            model_name='historicalpalvelussuhde',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_palvelussuhde_paattymis_pvm]),
        ),
        migrations.AlterField(
            model_name='historicalpalvelussuhde',
            name='tyoaika_viikossa',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(50.0)]),
        ),
        migrations.AlterField(
            model_name='palvelussuhde',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_palvelussuhde_paattymis_pvm]),
        ),
        migrations.AlterField(
            model_name='palvelussuhde',
            name='tyoaika_viikossa',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(1.0), django.core.validators.MaxValueValidator(50.0)]),
        ),
    ]
