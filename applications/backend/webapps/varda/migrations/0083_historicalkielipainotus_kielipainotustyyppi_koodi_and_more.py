# Generated by Django 4.2 on 2023-06-02 09:58

from django.db import migrations, models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0082_rename_asiointikieli_koodi_historicaltoimipaikka_toimintakieli_koodi_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalkielipainotus',
            name='kielipainotustyyppi_koodi',
            field=models.CharField(max_length=4, null=True, validators=[varda.validators.validate_kielipainotustyyppi_koodi]),
        ),
        migrations.AddField(
            model_name='kielipainotus',
            name='kielipainotustyyppi_koodi',
            field=models.CharField(max_length=4, null=True, validators=[varda.validators.validate_kielipainotustyyppi_koodi]),
        ),
    ]