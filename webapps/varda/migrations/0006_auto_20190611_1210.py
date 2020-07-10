# Generated by Django 2.2.2 on 2019-06-11 12:10

from django.conf import settings
import django.contrib.postgres.fields
import django.core.validators
from django.db import migrations, models
import django.utils.timezone
import simple_history.models
import varda.models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0005_auto_20190517_1449'),
    ]

    operations = [
        migrations.CreateModel(
            name='Aikaleima',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avain', models.TextField(choices=[('ORGANISAATIOS_LAST_UPDATE', 'ORGANISAATIOS_LAST_UPDATE')], unique=True)),
                ('aikaleima', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalMaksutieto',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('yksityinen_jarjestaja', models.BooleanField(default=False)),
                ('maksun_peruste_koodi', models.CharField(max_length=5, validators=[varda.validators.validate_maksun_peruste_koodi])),
                ('palveluseteli_arvo', models.DecimalField(decimal_places=2, default=0.0, max_digits=6, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('asiakasmaksu', models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('perheen_koko', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(50)])),
                ('alkamis_pvm', models.DateField(blank=True, null=True)),
                ('paattymis_pvm', models.DateField(blank=True, default=None, null=True)),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('changed_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical maksutieto',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='Maksutieto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yksityinen_jarjestaja', models.BooleanField(default=False)),
                ('maksun_peruste_koodi', models.CharField(max_length=5, validators=[varda.validators.validate_maksun_peruste_koodi])),
                ('palveluseteli_arvo', models.DecimalField(decimal_places=2, default=0.0, max_digits=6, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('asiakasmaksu', models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('perheen_koko', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(50)])),
                ('alkamis_pvm', models.DateField(blank=True, null=True)),
                ('paattymis_pvm', models.DateField(blank=True, default=None, null=True)),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='maksutiedot', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'maksutiedot',
            },
        ),
        migrations.RemoveField(
            model_name='historicalhuoltajuussuhde',
            name='maksupaatokset',
        ),
        migrations.RemoveField(
            model_name='huoltajuussuhde',
            name='maksupaatokset',
        ),
        migrations.AddField(
            model_name='historicaltoimipaikka',
            name='lahdejarjestelma',
            field=models.CharField(choices=[('VARDA', 'VARDA'), ('ORGANISAATIO', 'ORGANISAATIOPALVELU')], default='VARDA', max_length=50),
        ),
        migrations.AddField(
            model_name='toimipaikka',
            name='lahdejarjestelma',
            field=models.CharField(choices=[('VARDA', 'VARDA'), ('ORGANISAATIO', 'ORGANISAATIOPALVELU')], default='VARDA', max_length=50),
        ),
        migrations.AddField(
            model_name='z2_koodisto',
            name='maksun_peruste_koodit',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=10), default=varda.models.maksun_peruste_koodit_default, size=None),
        ),
        migrations.DeleteModel(
            name='Maksupaatos',
        ),
        migrations.AddField(
            model_name='huoltajuussuhde',
            name='maksutiedot',
            field=models.ManyToManyField(related_name='huoltajuussuhteet', to='varda.Maksutieto'),
        ),
    ]
