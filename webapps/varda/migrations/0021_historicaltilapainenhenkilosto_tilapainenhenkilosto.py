# Generated by Django 2.2.11 on 2020-05-07 09:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0020_auto_20200428_0945'),
    ]

    operations = [
        migrations.CreateModel(
            name='TilapainenHenkilosto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kuukausi', models.DateField()),
                ('tuntimaara', models.DecimalField(decimal_places=2, max_digits=6)),
                ('tyontekijamaara', models.IntegerField()),
                ('lahdejarjestelma', models.CharField(max_length=2, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('tunniste', models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste])),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tilapainen_henkilosto', to=settings.AUTH_USER_MODEL)),
                ('vakajarjestaja', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tilapainen_henkilosto', to='varda.VakaJarjestaja')),
            ],
            options={
                'verbose_name_plural': 'tilapainen henkilosto',
            },
        ),
        migrations.CreateModel(
            name='HistoricalTilapainenHenkilosto',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('kuukausi', models.DateField()),
                ('tuntimaara', models.DecimalField(decimal_places=2, max_digits=6)),
                ('tyontekijamaara', models.IntegerField()),
                ('lahdejarjestelma', models.CharField(max_length=2, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('tunniste', models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste])),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('changed_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('vakajarjestaja', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja')),
            ],
            options={
                'verbose_name': 'historical tilapainen henkilosto',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
