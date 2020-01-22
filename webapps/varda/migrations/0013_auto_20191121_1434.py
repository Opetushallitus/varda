# Generated by Django 2.2.6 on 2019-11-21 14:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('varda', '0012_auto_20191031_0926'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalPaosOikeus',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('voimassa_kytkin', models.BooleanField(default=False)),
                ('luonti_pvm', models.DateTimeField(blank=True, editable=False)),
                ('muutos_pvm', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'verbose_name': 'historical paos oikeus',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='PaosOikeus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voimassa_kytkin', models.BooleanField(default=False)),
                ('luonti_pvm', models.DateTimeField(auto_now_add=True)),
                ('muutos_pvm', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Paos-oikeudet',
            },
        ),
        migrations.RemoveField(
            model_name='historicalpaostoiminta',
            name='voimassa_kytkin',
        ),
        migrations.RemoveField(
            model_name='paostoiminta',
            name='voimassa_kytkin',
        ),
        migrations.AddField(
            model_name='historicallapsi',
            name='oma_organisaatio',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='historicallapsi',
            name='paos_kytkin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicallapsi',
            name='paos_organisaatio',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='lapsi',
            name='oma_organisaatio',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='paos_lapsi_oma_organisaatio', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='lapsi',
            name='paos_kytkin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lapsi',
            name='paos_organisaatio',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='paos_lapsi_paos_organisaatio', to='varda.VakaJarjestaja'),
        ),
        migrations.AlterField(
            model_name='historicalvakajarjestaja',
            name='yritysmuoto',
            field=models.CharField(choices=[('EI_YRITYSMUOTOA', 'Ei yritysmuotoa'), ('AATTEELLINEN_YHDISTYS', 'Aatteellinen yhdistys'), ('AHVENANMAAN_LIIKELAITOS', 'Ahvenanmaan liikelaitos'), ('AHVENANMAAN_MAAKUNTA_TAI_VIRASTO', 'Ahvenanmaan maakunta ja sen virastot'), ('ASUKASHALLINTOALUA', 'Asukashallintoalue'), ('ASUMISOIKEUSYHDISTYS', 'Asumisoikeusyhdistys'), ('ASUNTOOSAKEYHTIO', 'Asunto-osakeyhtiö'), ('AVOIN_YHTIO', 'Avoin yhtiö'), ('ELINKEINOYHTYMA', 'Elinkeinoyhtymä'), ('ELAKESAATIO', 'Eläkesäätiö'), ('ERILLISHALLINNOLLINEN_VALTION_ALUE', 'Erillishallinnollinen valtion laitos'), ('ERITYISLAINSAADANTOON_PERUSTUVA_YHDISTYS', 'Erityislainsäädäntöön perustuva yhdistys'), ('EU_TALOUDELLINEN_ETUYHT_SIVUTOIMIPAIKKA', 'Euroopp.taloudell.etuyht.sivutoimipaikka'), ('EU_TALOUDELLINE_ETURYHMA', 'Eurooppalainen taloudellinen etuyhtymä'), ('EU_OSUUSKUNNAN_KIINTEA_TOIMIPAIKKA', 'Eurooppaosuuskunnan kiinteä toimipaikka'), ('EU_OSUUSKUNTA', 'Eurooppaosuuskunta'), ('EU_OSUUSPANKKI', 'Eurooppaosuuspankki'), ('EU_YHTIO', 'Eurooppayhtiö'), ('EV_LUT_KIRKKO', 'Ev.lut.kirkko'), ('HYPOTEEKKIYHDISTYS', 'Hypoteekkiyhdistys'), ('JULKINEN_KESKINEN_VAKUUTUSYHTIO', 'Julkinen keskinäinen vakuutusyhtiö'), ('JULKINEN_OSAKEYHTIO', 'Julkinen osakeyhtiö'), ('JULKINEN_VAKUUTUSOSAKEYTIO', 'Julkinen vakuutusosakeyhtiö'), ('KAUPPAKAMARI', 'Kauppakamari'), ('KESKINAINEN_KIINTEISTOOSAKEYTIO', 'Keskinäinen kiinteistöosakeyhtiö'), ('KESKINAINEN_VAHINKOVAK_YHDISTYS', 'Keskinäinen vahinkovak.yhdistys'), ('KESKINAINEN_VAKUUTUSYHTIO', 'Keskinäinen vakuutusyhtiö'), ('KOMMANDIITTIYHTIO', 'Kommandiittiyhtiö'), ('KONKURSSIPESA', 'Konkurssipesä'), ('KUNNALLINEN_LIIKELAITOS', 'Kunnallinen liikelaitos'), ('KUNTA', 'Kunta'), ('KUNTAINLIITON_LIIKELAITOS', 'Kuntainliiton liikelaitos'), ('KUNTAYHTYMA', 'Kuntayhtymä'), ('KUOLINPESA', 'Kuolinpesä'), ('LAIVANISANNISTOYHTIO', 'Laivanisännistöyhtiö'), ('METSANHOITOYHDISTYS', 'Metsänhoitoyhdistys'), ('MUU_JULKISOIKEUDELLINE_OIKEUSHENKILO', 'Muu julkisoikeudellinen oikeushenkilö'), ('MUU_KIINTEISTOOSAKEYHTIO', 'Muu kiinteistöosakeyhtiö'), ('MUU_SAATIO', 'Muu säätiö'), ('MUU_TALOUDELLINEN_YHDISTYS', 'Muu taloudellinen yhdistys'), ('MUU_VEROTUKSEN_YKSIKKO', 'Muu verotuksen yksikkö'), ('MUU_YHDISTYS', 'Muu yhdistys'), ('MUU_YHTEISVAST_PIDATYSVELVOLLINEN', 'Muu yhteisvast.pidätysvelvollinen'), ('MUU_YHTIO', 'Muu yhtiö'), ('MUUT_OIKEUSHENKILOT', 'Muut oikeushenkilöt'), ('ORTODOKSINEN_KIRKKO', 'Ortodoksinen kirkko'), ('OSAKEYHTIO', 'Osakeyhtiö'), ('OSUUSKUNTA', 'Osuuskunta'), ('OSUUSPANKKI', 'Osuuspankki'), ('PALISKUNTA', 'Paliskunta'), ('SEURAKUNTA_PAIKALLISYHTEISO', 'Seurakunta/Paikallisyhteisö'), ('SIVULIIKE', 'Sivuliike'), ('SAASTOPANKKI', 'Säästöpankki'), ('SAATIO', 'Säätiö'), ('TALOUDELLINEN_YHDISTYS', 'Taloudellinen yhdistys'), ('TYOELAKEKASSA', 'Työeläkekassa'), ('TYOTTOMYYSKASSA', 'Työttömyyskassa'), ('ULKOMAINEN_YHTEISO', 'Ulkomainen yhteisö'), ('USKONNOLLINEN_YHDYSKUNTA', 'Uskonnollinen yhdyskunta'), ('VAKUUTUSKASSA', 'Vakuutuskassa'), ('VAKUUTUSOSAKEYHTIO', 'Vakuutusosakeyhtiö'), ('VAKUUTUSYHDISTYS', 'Vakuutusyhdistys'), ('VALTIO_JA_SEN_LAITOKSET', 'Valtio ja sen laitokset'), ('VALTION_LIIKELAITOS', 'Valtion liikelaitos'), ('VEROTUSYHTYMA', 'Verotusyhtymä'), ('YHTEISETUUDET', 'Yhteisetuudet'), ('YHTEISMETSA', 'Yhteismetsä'), ('YKSITYINEN_ELINKEINONHARJOITTAJA', 'Yksityinen elinkeinonharjoittaja'), ('YLIOPPILASKUNTA_TAI_OSAKUNTA', 'Ylioppilaskunta tai osakunta')], default='EI_YRITYSMUOTOA', max_length=50),
        ),
        migrations.AlterField(
            model_name='paostoiminta',
            name='oma_organisaatio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='paos_toiminnat_oma_organisaatio', to='varda.VakaJarjestaja'),
        ),
        migrations.AlterField(
            model_name='paostoiminta',
            name='paos_organisaatio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='paos_toiminnat_paos_organisaatio', to='varda.VakaJarjestaja'),
        ),
        migrations.AlterField(
            model_name='paostoiminta',
            name='paos_toimipaikka',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='paos_toiminnat_paos_toimipaikka', to='varda.Toimipaikka'),
        ),
        migrations.AlterField(
            model_name='vakajarjestaja',
            name='yritysmuoto',
            field=models.CharField(choices=[('EI_YRITYSMUOTOA', 'Ei yritysmuotoa'), ('AATTEELLINEN_YHDISTYS', 'Aatteellinen yhdistys'), ('AHVENANMAAN_LIIKELAITOS', 'Ahvenanmaan liikelaitos'), ('AHVENANMAAN_MAAKUNTA_TAI_VIRASTO', 'Ahvenanmaan maakunta ja sen virastot'), ('ASUKASHALLINTOALUA', 'Asukashallintoalue'), ('ASUMISOIKEUSYHDISTYS', 'Asumisoikeusyhdistys'), ('ASUNTOOSAKEYHTIO', 'Asunto-osakeyhtiö'), ('AVOIN_YHTIO', 'Avoin yhtiö'), ('ELINKEINOYHTYMA', 'Elinkeinoyhtymä'), ('ELAKESAATIO', 'Eläkesäätiö'), ('ERILLISHALLINNOLLINEN_VALTION_ALUE', 'Erillishallinnollinen valtion laitos'), ('ERITYISLAINSAADANTOON_PERUSTUVA_YHDISTYS', 'Erityislainsäädäntöön perustuva yhdistys'), ('EU_TALOUDELLINEN_ETUYHT_SIVUTOIMIPAIKKA', 'Euroopp.taloudell.etuyht.sivutoimipaikka'), ('EU_TALOUDELLINE_ETURYHMA', 'Eurooppalainen taloudellinen etuyhtymä'), ('EU_OSUUSKUNNAN_KIINTEA_TOIMIPAIKKA', 'Eurooppaosuuskunnan kiinteä toimipaikka'), ('EU_OSUUSKUNTA', 'Eurooppaosuuskunta'), ('EU_OSUUSPANKKI', 'Eurooppaosuuspankki'), ('EU_YHTIO', 'Eurooppayhtiö'), ('EV_LUT_KIRKKO', 'Ev.lut.kirkko'), ('HYPOTEEKKIYHDISTYS', 'Hypoteekkiyhdistys'), ('JULKINEN_KESKINEN_VAKUUTUSYHTIO', 'Julkinen keskinäinen vakuutusyhtiö'), ('JULKINEN_OSAKEYHTIO', 'Julkinen osakeyhtiö'), ('JULKINEN_VAKUUTUSOSAKEYTIO', 'Julkinen vakuutusosakeyhtiö'), ('KAUPPAKAMARI', 'Kauppakamari'), ('KESKINAINEN_KIINTEISTOOSAKEYTIO', 'Keskinäinen kiinteistöosakeyhtiö'), ('KESKINAINEN_VAHINKOVAK_YHDISTYS', 'Keskinäinen vahinkovak.yhdistys'), ('KESKINAINEN_VAKUUTUSYHTIO', 'Keskinäinen vakuutusyhtiö'), ('KOMMANDIITTIYHTIO', 'Kommandiittiyhtiö'), ('KONKURSSIPESA', 'Konkurssipesä'), ('KUNNALLINEN_LIIKELAITOS', 'Kunnallinen liikelaitos'), ('KUNTA', 'Kunta'), ('KUNTAINLIITON_LIIKELAITOS', 'Kuntainliiton liikelaitos'), ('KUNTAYHTYMA', 'Kuntayhtymä'), ('KUOLINPESA', 'Kuolinpesä'), ('LAIVANISANNISTOYHTIO', 'Laivanisännistöyhtiö'), ('METSANHOITOYHDISTYS', 'Metsänhoitoyhdistys'), ('MUU_JULKISOIKEUDELLINE_OIKEUSHENKILO', 'Muu julkisoikeudellinen oikeushenkilö'), ('MUU_KIINTEISTOOSAKEYHTIO', 'Muu kiinteistöosakeyhtiö'), ('MUU_SAATIO', 'Muu säätiö'), ('MUU_TALOUDELLINEN_YHDISTYS', 'Muu taloudellinen yhdistys'), ('MUU_VEROTUKSEN_YKSIKKO', 'Muu verotuksen yksikkö'), ('MUU_YHDISTYS', 'Muu yhdistys'), ('MUU_YHTEISVAST_PIDATYSVELVOLLINEN', 'Muu yhteisvast.pidätysvelvollinen'), ('MUU_YHTIO', 'Muu yhtiö'), ('MUUT_OIKEUSHENKILOT', 'Muut oikeushenkilöt'), ('ORTODOKSINEN_KIRKKO', 'Ortodoksinen kirkko'), ('OSAKEYHTIO', 'Osakeyhtiö'), ('OSUUSKUNTA', 'Osuuskunta'), ('OSUUSPANKKI', 'Osuuspankki'), ('PALISKUNTA', 'Paliskunta'), ('SEURAKUNTA_PAIKALLISYHTEISO', 'Seurakunta/Paikallisyhteisö'), ('SIVULIIKE', 'Sivuliike'), ('SAASTOPANKKI', 'Säästöpankki'), ('SAATIO', 'Säätiö'), ('TALOUDELLINEN_YHDISTYS', 'Taloudellinen yhdistys'), ('TYOELAKEKASSA', 'Työeläkekassa'), ('TYOTTOMYYSKASSA', 'Työttömyyskassa'), ('ULKOMAINEN_YHTEISO', 'Ulkomainen yhteisö'), ('USKONNOLLINEN_YHDYSKUNTA', 'Uskonnollinen yhdyskunta'), ('VAKUUTUSKASSA', 'Vakuutuskassa'), ('VAKUUTUSOSAKEYHTIO', 'Vakuutusosakeyhtiö'), ('VAKUUTUSYHDISTYS', 'Vakuutusyhdistys'), ('VALTIO_JA_SEN_LAITOKSET', 'Valtio ja sen laitokset'), ('VALTION_LIIKELAITOS', 'Valtion liikelaitos'), ('VEROTUSYHTYMA', 'Verotusyhtymä'), ('YHTEISETUUDET', 'Yhteisetuudet'), ('YHTEISMETSA', 'Yhteismetsä'), ('YKSITYINEN_ELINKEINONHARJOITTAJA', 'Yksityinen elinkeinonharjoittaja'), ('YLIOPPILASKUNTA_TAI_OSAKUNTA', 'Ylioppilaskunta tai osakunta')], default='EI_YRITYSMUOTOA', max_length=50),
        ),
        migrations.AddConstraint(
            model_name='lapsi',
            constraint=models.CheckConstraint(check=models.Q(_negated=True, oma_organisaatio=django.db.models.expressions.F('paos_organisaatio')), name='oma_organisaatio_is_not_paos_organisaatio'),
        ),
        migrations.AddField(
            model_name='paosoikeus',
            name='changed_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='paos_oikeudet', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='paosoikeus',
            name='jarjestaja_kunta_organisaatio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='paos_oikeudet_jarjestaja_kunta', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='paosoikeus',
            name='tallentaja_organisaatio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='paos_oikeudet_tallentaja_organisaatio', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='paosoikeus',
            name='tuottaja_organisaatio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='paos_oikeudet_tuottaja', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='historicalpaosoikeus',
            name='changed_by',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalpaosoikeus',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalpaosoikeus',
            name='jarjestaja_kunta_organisaatio',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='historicalpaosoikeus',
            name='tallentaja_organisaatio',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja'),
        ),
        migrations.AddField(
            model_name='historicalpaosoikeus',
            name='tuottaja_organisaatio',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='varda.VakaJarjestaja'),
        ),
        migrations.AddConstraint(
            model_name='paosoikeus',
            constraint=models.UniqueConstraint(fields=('jarjestaja_kunta_organisaatio', 'tuottaja_organisaatio'), name='jarjestaja_kunta_organisaatio_tuottaja_organisaatio_unique_constraint'),
        ),
        migrations.AddConstraint(
            model_name='paosoikeus',
            constraint=models.CheckConstraint(check=models.Q(_negated=True, jarjestaja_kunta_organisaatio=django.db.models.expressions.F('tuottaja_organisaatio')), name='jarjestaja_kunta_organisaatio_is_not_tuottaja_organisaatio_constraint'),
        ),
    ]
