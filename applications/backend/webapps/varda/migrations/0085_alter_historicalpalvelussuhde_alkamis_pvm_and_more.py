# Generated by Django 4.2.8 on 2023-12-11 08:25

from django.db import migrations, models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0084_alter_z6_lastrequest_user_alter_z6_requestlog_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalpalvelussuhde',
            name='alkamis_pvm',
            field=models.DateField(validators=[varda.validators.validate_palvelussuhde_alkamis_pvm]),
        ),
        migrations.AlterField(
            model_name='palvelussuhde',
            name='alkamis_pvm',
            field=models.DateField(validators=[varda.validators.validate_palvelussuhde_alkamis_pvm]),
        ),
    ]