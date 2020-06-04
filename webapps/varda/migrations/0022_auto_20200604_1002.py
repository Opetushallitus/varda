# Generated by Django 2.2.12 on 2020-06-04 07:02

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0021_auto_20200528_0732'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmaksutieto',
            name='perheen_koko',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(50)]),
        ),
        migrations.AlterField(
            model_name='maksutieto',
            name='perheen_koko',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(50)]),
        ),
        migrations.CreateModel(
            name='Tyoskentelypaikka',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tehtavanimike_koodi', models.CharField(max_length=120, validators=[varda.validators.validate_tehtavanimike_koodi])),
                ('kelpoisuus_kytkin', models.BooleanField()),
                ('kiertava_tyontekija_kytkin', models.BooleanField()),
                ('alkamis_pvm', models.DateField()),
                ('paattymis_pvm', models.DateField(blank=True, default=None, null=True)),
                ('lahdejarjestelma', models.CharField(max_length=2, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('tunniste', models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste])),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tyoskentelypaikat', to=settings.AUTH_USER_MODEL)),
                ('palvelussuhde', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tyoskentelypaikat', to='varda.Palvelussuhde')),
                ('toimipaikka', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tyoskentelypaikat', to='varda.Toimipaikka')),
            ],
            options={
                'verbose_name_plural': 'tyoskentelypaikat',
            },
        ),
        migrations.CreateModel(
            name='HistoricalTyoskentelypaikka',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('tehtavanimike_koodi', models.CharField(max_length=120, validators=[varda.validators.validate_tehtavanimike_koodi])),
                ('kelpoisuus_kytkin', models.BooleanField()),
                ('kiertava_tyontekija_kytkin', models.BooleanField()),
                ('alkamis_pvm', models.DateField()),
                ('paattymis_pvm', models.DateField(blank=True, default=None, null=True)),
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
                ('palvelussuhde', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.Palvelussuhde')),
                ('toimipaikka', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.Toimipaikka')),
            ],
            options={
                'verbose_name': 'historical tyoskentelypaikka',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
