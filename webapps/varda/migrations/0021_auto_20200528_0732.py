# Generated by Django 2.2.12 on 2020-05-28 07:32

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import simple_history.models
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0020_auto_20200428_0945'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Z2_Koodisto',
        ),
        migrations.CreateModel(
            name='Z2_Koodisto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, unique=True)),
                ('name_koodistopalvelu', models.CharField(max_length=256, unique=True)),
                ('update_datetime', models.DateTimeField()),
                ('version', models.IntegerField()),
            ],
            options={
                'verbose_name_plural': 'Varda koodistot',
            },
        ),
        migrations.CreateModel(
            name='Z2_Code',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_value', models.CharField(max_length=256)),
            ],
            options={
                'verbose_name_plural': 'Varda codes',
            },
        ),
        migrations.AddField(
            model_name='z2_code',
            name='koodisto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='codes', to='varda.Z2_Koodisto'),
        ),
        migrations.CreateModel(
            name='Z2_CodeTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(max_length=10)),
                ('name', models.CharField(blank=True, max_length=256)),
                ('description', models.CharField(blank=True, max_length=2048)),
                ('short_name', models.CharField(blank=True, max_length=256)),
                ('code', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='translations', to='varda.Z2_Code')),
            ],
            options={
                'verbose_name_plural': 'Varda code translations',
            },
        ),
        migrations.AddConstraint(
            model_name='z2_codetranslation',
            constraint=models.UniqueConstraint(fields=('code', 'language'), name='code_language_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='z2_code',
            constraint=models.UniqueConstraint(fields=('koodisto', 'code_value'), name='koodisto_code_value_unique_constraint'),
        ),
        migrations.CreateModel(
            name='Taydennyskoulutus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name_plural': 'taydennyskoulutukset',
            },
        ),
        migrations.AlterField(
            model_name='z4_caskayttooikeudet',
            name='kayttooikeus',
            field=models.CharField(blank=True, choices=[('VARDA-PAAKAYTTAJA', 'Varda-Pääkäyttäjä'), ('VARDA-TALLENTAJA', 'Varda-Tallentaja'), ('VARDA-KATSELIJA', 'Varda-Katselija'), ('VARDA-PALVELUKAYTTAJA', 'Varda-Palvelukäyttäjä'), ('HUOLTAJATIETO_TALLENNUS', 'Varda-Huoltajatietojen tallentaja'), ('HUOLTAJATIETO_KATSELU', 'Varda-Huoltajatietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA', 'Varda-Täydennyskoulutustietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA', 'Varda-Täydennyskoulutustietojen tallentaja'), ('HENKILOSTO_TILAPAISET_KATSELIJA', 'Varda-Tilapäisen henkilöstön katselija'), ('HENKILOSTO_TILAPAISET_TALLENTAJA', 'Varda-Tilapäisen henkilöstön tallentaja'), ('HENKILOSTO_TYONTEKIJA_KATSELIJA', 'Varda-Työntekijätietojen katselija'), ('HENKILOSTO_TYONTEKIJA_TALLENTAJA', 'Varda-Työntekijätietojen tallentaja')], max_length=50),
        ),
        migrations.CreateModel(
            name='Tutkinto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tutkinto_koodi', models.CharField(max_length=10, validators=[varda.validators.validate_tutkinto_koodi])),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tutkinnot', to=settings.AUTH_USER_MODEL)),
                ('henkilo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tutkinnot', to='varda.Henkilo')),
            ],
            options={
                'verbose_name_plural': 'tutkinnot',
            },
        ),
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
            name='Palvelussuhde',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tyosuhde_koodi', models.CharField(max_length=50, validators=[varda.validators.validate_tyosuhde_koodi])),
                ('tyoaika_koodi', models.CharField(max_length=50, validators=[varda.validators.validate_tyoaika_koodi])),
                ('tutkinto_koodi', models.CharField(max_length=50, validators=[varda.validators.validate_tutkinto_koodi])),
                ('tyoaika_viikossa', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(1.0)])),
                ('alkamis_pvm', models.DateField()),
                ('paattymis_pvm', models.DateField(blank=True, default=None, null=True)),
                ('lahdejarjestelma', models.CharField(max_length=2, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('tunniste', models.CharField(blank=True, max_length=120, null=True, validators=[varda.validators.validate_tunniste])),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='palvelussuhteet', to=settings.AUTH_USER_MODEL)),
                ('tyontekija', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='palvelussuhteet', to='varda.Tyontekija')),
            ],
            options={
                'verbose_name_plural': 'palvelussuhteet',
            },
        ),
        migrations.CreateModel(
            name='HistoricalTutkinto',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('tutkinto_koodi', models.CharField(max_length=10, validators=[varda.validators.validate_tutkinto_koodi])),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('changed_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('henkilo', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.Henkilo')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical tutkinto',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
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
        migrations.CreateModel(
            name='HistoricalPalvelussuhde',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('tyosuhde_koodi', models.CharField(max_length=50, validators=[varda.validators.validate_tyosuhde_koodi])),
                ('tyoaika_koodi', models.CharField(max_length=50, validators=[varda.validators.validate_tyoaika_koodi])),
                ('tutkinto_koodi', models.CharField(max_length=50, validators=[varda.validators.validate_tutkinto_koodi])),
                ('tyoaika_viikossa', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(1.0)])),
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
                ('tyontekija', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.Tyontekija')),
            ],
            options={
                'verbose_name': 'historical palvelussuhde',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
