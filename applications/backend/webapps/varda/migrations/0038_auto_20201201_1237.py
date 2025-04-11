# Generated by Django 2.2.13 on 2020-12-01 10:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import varda.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0037_auto_20201126_1055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='z4_caskayttooikeudet',
            name='kayttooikeus',
            field=models.CharField(blank=True, choices=[('VARDA-PAAKAYTTAJA', 'Varda-Pääkäyttäjä'), ('VARDA-TALLENTAJA', 'Varda-Tallentaja'), ('VARDA-KATSELIJA', 'Varda-Katselija'), ('VARDA-PALVELUKAYTTAJA', 'Varda-Palvelukäyttäjä'), ('HUOLTAJATIETO_TALLENNUS', 'Varda-Huoltajatietojen tallentaja'), ('HUOLTAJATIETO_KATSELU', 'Varda-Huoltajatietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA', 'Varda-Täydennyskoulutustietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA', 'Varda-Täydennyskoulutustietojen tallentaja'), ('HENKILOSTO_TILAPAISET_KATSELIJA', 'Varda-Tilapäisen henkilöstön katselija'), ('HENKILOSTO_TILAPAISET_TALLENTAJA', 'Varda-Tilapäisen henkilöstön tallentaja'), ('HENKILOSTO_TYONTEKIJA_KATSELIJA', 'Varda-Työntekijätietojen katselija'), ('HENKILOSTO_TYONTEKIJA_TALLENTAJA', 'Varda-Työntekijätietojen tallentaja'), ('VARDA_TOIMIJATIEDOT_KATSELIJA', 'Varda-Toimijatietojen katselija'), ('VARDA_TOIMIJATIEDOT_TALLENTAJA', 'Varda-Toimijatietojen tallentaja'), ('VARDA_RAPORTTIEN_KATSELIJA', 'Varda-Raporttien katselija')], max_length=50),
        ),
        migrations.CreateModel(
            name='Z6_RequestLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_url', models.CharField(max_length=200)),
                ('request_method', models.CharField(max_length=10)),
                ('request_body', models.TextField(blank=True)),
                ('response_code', models.IntegerField()),
                ('response_body', models.TextField(blank=True)),
                ('target_model', models.CharField(max_length=100, null=True)),
                ('target_id', models.IntegerField(null=True)),
                ('lahdejarjestelma', models.CharField(max_length=2, null=True, validators=[varda.validators.validate_lahdejarjestelma_koodi])),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='request_log', to=settings.AUTH_USER_MODEL)),
                ('vakajarjestaja', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_log', to='varda.VakaJarjestaja')),
            ],
            options={
                'verbose_name_plural': 'Request log',
            },
        ),
    ]
