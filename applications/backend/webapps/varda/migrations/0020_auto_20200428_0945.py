# Generated by Django 2.2.11 on 2020-04-28 06:45

from django.db import migrations, models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0019_auto_20200422_1030'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmaksutieto',
            name='alkamis_pvm',
            field=models.DateField(blank=True, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='historicalmaksutieto',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='historicalvarhaiskasvatuspaatos',
            name='alkamis_pvm',
            field=models.DateField(validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='historicalvarhaiskasvatuspaatos',
            name='hakemus_pvm',
            field=models.DateField(validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='historicalvarhaiskasvatuspaatos',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='historicalvarhaiskasvatussuhde',
            name='alkamis_pvm',
            field=models.DateField(validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='historicalvarhaiskasvatussuhde',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='maksutieto',
            name='alkamis_pvm',
            field=models.DateField(blank=True, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='maksutieto',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='varhaiskasvatuspaatos',
            name='alkamis_pvm',
            field=models.DateField(validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='varhaiskasvatuspaatos',
            name='hakemus_pvm',
            field=models.DateField(validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='varhaiskasvatuspaatos',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='varhaiskasvatussuhde',
            name='alkamis_pvm',
            field=models.DateField(validators=[varda.validators.validate_vaka_date]),
        ),
        migrations.AlterField(
            model_name='varhaiskasvatussuhde',
            name='paattymis_pvm',
            field=models.DateField(blank=True, default=None, null=True, validators=[varda.validators.validate_vaka_date]),
        ),
    ]
