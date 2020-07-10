# Generated by Django 2.2.12 on 2020-07-08 08:00

from django.db import migrations, models
import varda.enums.hallinnointijarjestelma


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0026_auto_20200702_1325'),
    ]

    operations = [
        migrations.RenameField(
            model_name='historicaltoimipaikka',
            old_name='lahdejarjestelma',
            new_name='hallinnointijarjestelma',
        ),
        migrations.AlterField(
            model_name='historicaltoimipaikka',
            name='hallinnointijarjestelma',
            field=models.CharField(choices=[('VARDA', 'VARDA'), ('ORGANISAATIO', 'ORGANISAATIOPALVELU')], default=varda.enums.hallinnointijarjestelma.Hallinnointijarjestelma('VARDA'), max_length=50),
        ),
        migrations.RenameField(
            model_name='toimipaikka',
            old_name='lahdejarjestelma',
            new_name='hallinnointijarjestelma',
        ),
        migrations.AlterField(
            model_name='toimipaikka',
            name='hallinnointijarjestelma',
            field=models.CharField(choices=[('VARDA', 'VARDA'), ('ORGANISAATIO', 'ORGANISAATIOPALVELU')], default=varda.enums.hallinnointijarjestelma.Hallinnointijarjestelma('VARDA'), max_length=50),
        ),
    ]