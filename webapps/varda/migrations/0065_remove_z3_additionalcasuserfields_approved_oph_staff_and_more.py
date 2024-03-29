# Generated by Django 4.0.1 on 2022-03-09 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0064_alter_z3_additionalcasuserfields_huollettava_oid_list_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='z3_additionalcasuserfields',
            name='approved_oph_staff',
        ),
        migrations.AlterField(
            model_name='z4_caskayttooikeudet',
            name='kayttooikeus',
            field=models.CharField(blank=True, choices=[('VARDA-PAAKAYTTAJA', 'Varda-Pääkäyttäjä'), ('VARDA-TALLENTAJA', 'Varda-Tallentaja'), ('VARDA-KATSELIJA', 'Varda-Katselija'), ('VARDA-PALVELUKAYTTAJA', 'Varda-Palvelukäyttäjä'), ('HUOLTAJATIETO_TALLENNUS', 'Varda-Huoltajatietojen tallentaja'), ('HUOLTAJATIETO_KATSELU', 'Varda-Huoltajatietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA', 'Varda-Täydennyskoulutustietojen katselija'), ('HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA', 'Varda-Täydennyskoulutustietojen tallentaja'), ('HENKILOSTO_TILAPAISET_KATSELIJA', 'Varda-Tilapäisen henkilöstön katselija'), ('HENKILOSTO_TILAPAISET_TALLENTAJA', 'Varda-Tilapäisen henkilöstön tallentaja'), ('HENKILOSTO_TYONTEKIJA_KATSELIJA', 'Varda-Työntekijätietojen katselija'), ('HENKILOSTO_TYONTEKIJA_TALLENTAJA', 'Varda-Työntekijätietojen tallentaja'), ('VARDA_TOIMIJATIEDOT_KATSELIJA', 'Varda-Toimijatietojen katselija'), ('VARDA_TOIMIJATIEDOT_TALLENTAJA', 'Varda-Toimijatietojen tallentaja'), ('VARDA_RAPORTTIEN_KATSELIJA', 'Varda-Raporttien katselija'), ('VARDA_LUOVUTUSPALVELU', 'VARDA_LUOVUTUSPALVELU'), ('VARDA-YLLAPITAJA', 'VARDA-ylläpitäjä')], max_length=50),
        ),
    ]
