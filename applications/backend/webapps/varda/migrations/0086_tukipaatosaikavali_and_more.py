# Generated by Django 4.2.4 on 2024-02-06 07:46

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import varda.models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0085_alter_historicalpalvelussuhde_alkamis_pvm_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TukipaatosAikavali',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alkamis_pvm', models.DateField()),
                ('paattymis_pvm', models.DateField()),
                ('tilastointi_pvm', models.DateField()),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'tukipaatos aikavalit',
            },
        ),
        migrations.AlterField(
            model_name='z4_caskayttooikeudet',
            name='kayttooikeus',
            field=models.CharField(blank=True, choices=[('VARDA-PAAKAYTTAJA', 'Varda-Pääkäyttäjä'), ('VARDA-TALLENTAJA', 'Varda-Tallentaja'), ('VARDA-KATSELIJA', 'Varda-Katselija'), ('VARDA-PALVELUKAYTTAJA', 'Varda-Palvelukäyttäjä'), ('HUOLTAJATIETO_TALLENNUS', 'Varda-Huoltajatietojen tallentaja'), ('HUOLTAJATIETO_KATSELU', 'Varda-Huoltajatietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA', 'Varda-Täydennyskoulutustietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA', 'Varda-Täydennyskoulutustietojen tallentaja'), ('HENKILOSTO_VUOKRATTU_KATSELIJA', 'Varda-Vuokratun henkilöstön katselija'), ('HENKILOSTO_VUOKRATTU_TALLENTAJA', 'Varda-Vuokratun henkilöstön tallentaja'), ('TUEN_TIEDOT_KATSELIJA', 'Varda-Tuen tiedot katselija'), ('TUEN_TIEDOT_TALLENTAJA', 'Varda-Tuen tiedot tallentaja'), ('HENKILOSTO_TYONTEKIJA_KATSELIJA', 'Varda-Työntekijätietojen katselija'), ('HENKILOSTO_TYONTEKIJA_TALLENTAJA', 'Varda-Työntekijätietojen tallentaja'), ('VARDA_TOIMIJATIEDOT_KATSELIJA', 'Varda-Toimijatietojen katselija'), ('VARDA_TOIMIJATIEDOT_TALLENTAJA', 'Varda-Toimijatietojen tallentaja'), ('VARDA_RAPORTTIEN_KATSELIJA', 'Varda-Raporttien katselija'), ('VARDA_LUOVUTUSPALVELU', 'VARDA_LUOVUTUSPALVELU'), ('VARDA-YLLAPITAJA', 'VARDA-ylläpitäjä')], max_length=50),
        ),
        migrations.CreateModel(
            name='Tukipaatos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lapsimaara', models.PositiveIntegerField(default=0)),
                ('yksityinen_jarjestaja', models.BooleanField(default=False)),
                ('ikaryhma_koodi', models.CharField(max_length=20, validators=[varda.validators.validate_ikaryhma_koodi])),
                ('tuentaso_koodi', models.CharField(max_length=10, validators=[varda.validators.validate_tuentaso_koodi])),
                ('tilastointi_pvm', models.DateField()),
                ('lahdejarjestelma', models.CharField(max_length=2, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('tunniste', models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste])),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('vakajarjestaja', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tukipaatos', to='varda.organisaatio')),
            ],
            options={
                'verbose_name_plural': 'tukipaatokset',
            },
            bases=(varda.models.UniqueLahdejarjestelmaTunnisteMixin, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalTukipaatosAikavali',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('alkamis_pvm', models.DateField()),
                ('paattymis_pvm', models.DateField()),
                ('tilastointi_pvm', models.DateField()),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical tukipaatos aikavali',
                'verbose_name_plural': 'historical tukipaatos aikavalit',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalTukipaatos',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('lapsimaara', models.PositiveIntegerField(default=0)),
                ('yksityinen_jarjestaja', models.BooleanField(default=False)),
                ('ikaryhma_koodi', models.CharField(max_length=20, validators=[varda.validators.validate_ikaryhma_koodi])),
                ('tuentaso_koodi', models.CharField(max_length=10, validators=[varda.validators.validate_tuentaso_koodi])),
                ('tilastointi_pvm', models.DateField()),
                ('lahdejarjestelma', models.CharField(max_length=2, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('tunniste', models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste])),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('vakajarjestaja', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.organisaatio')),
            ],
            options={
                'verbose_name': 'historical tukipaatos',
                'verbose_name_plural': 'historical tukipaatokset',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddConstraint(
            model_name='tukipaatos',
            constraint=models.UniqueConstraint(condition=models.Q(('tunniste__isnull', False), models.Q(('tunniste', ''), _negated=True)), fields=('lahdejarjestelma', 'tunniste'), name='tukipaatos_lahdejarjestelma_tunniste_unique_constraint'),
        ),
    ]