# Generated by Django 3.1.4 on 2021-02-25 09:14

from django.db import migrations, models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0043_auto_20210205_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalkielipainotus',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicalkielipainotus',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='historicallapsi',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicallapsi',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='historicalmaksutieto',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicalmaksutieto',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='historicaltoiminnallinenpainotus',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicaltoiminnallinenpainotus',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='historicaltoimipaikka',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicaltoimipaikka',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='historicalvarhaiskasvatuspaatos',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicalvarhaiskasvatuspaatos',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='historicalvarhaiskasvatussuhde',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='historicalvarhaiskasvatussuhde',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='kielipainotus',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='kielipainotus',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='lapsi',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='lapsi',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='maksutieto',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='maksutieto',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='toiminnallinenpainotus',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='toiminnallinenpainotus',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='toimipaikka',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='toimipaikka',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='varhaiskasvatuspaatos',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='varhaiskasvatuspaatos',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
        migrations.AddField(
            model_name='varhaiskasvatussuhde',
            name='lahdejarjestelma',
            field=models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi]),
        ),
        migrations.AddField(
            model_name='varhaiskasvatussuhde',
            name='tunniste',
            field=models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste]),
        ),
    ]
