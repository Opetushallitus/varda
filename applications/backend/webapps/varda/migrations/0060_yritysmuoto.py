import django.contrib.postgres.fields
from django.db import connection, migrations, models
import varda.validators


table_names = ('varda_vakajarjestaja', 'varda_historicalvakajarjestaja',)


def forwards_func(apps, schema_editor):
    with connection.cursor() as cursor:
        for table_name in table_names:
            cursor.execute(f'''
                UPDATE {table_name}
                SET yritysmuoto = CASE
                    WHEN yritysmuoto = 'EI_YRITYSMUOTOA' THEN '0' WHEN yritysmuoto = 'ASUNTOOSAKEYHTIO' THEN '2'
                    WHEN yritysmuoto = 'ASUKASHALLINTOALUA' THEN '3' WHEN yritysmuoto = 'ASUMISOIKEUSYHDISTYS' THEN '4'
                    WHEN yritysmuoto = 'AVOIN_YHTIO' THEN '5' WHEN yritysmuoto = 'AATTEELLINEN_YHDISTYS' THEN '6'
                    WHEN yritysmuoto = 'EU_TALOUDELLINEN_ETUYHT_SIVUTOIMIPAIKKA' THEN '7' WHEN yritysmuoto = 'EU_TALOUDELLINE_ETURYHMA' THEN '8'
                    WHEN yritysmuoto = 'HYPOTEEKKIYHDISTYS' THEN '9' WHEN yritysmuoto = 'KESKINAINEN_KIINTEISTOOSAKEYTIO' THEN '10'
                    WHEN yritysmuoto = 'JULKINEN_KESKINEN_VAKUUTUSYHTIO' THEN '11' WHEN yritysmuoto = 'KESKINAINEN_VAKUUTUSYHTIO' THEN '12'
                    WHEN yritysmuoto = 'KOMMANDIITTIYHTIO' THEN '13' WHEN yritysmuoto = 'OSUUSKUNTA' THEN '14'
                    WHEN yritysmuoto = 'OSUUSPANKKI' THEN '15' WHEN yritysmuoto = 'OSAKEYHTIO' THEN '16'
                    WHEN yritysmuoto = 'JULKINEN_OSAKEYHTIO' THEN '17' WHEN yritysmuoto = 'SAATIO' THEN '18'
                    WHEN yritysmuoto = 'SIVULIIKE' THEN '19' WHEN yritysmuoto = 'SAASTOPANKKI' THEN '20'
                    WHEN yritysmuoto = 'TALOUDELLINEN_YHDISTYS' THEN '21' WHEN yritysmuoto = 'VALTION_LIIKELAITOS' THEN '22'
                    WHEN yritysmuoto = 'JULKINEN_VAKUUTUSOSAKEYTIO' THEN '23' WHEN yritysmuoto = 'VAKUUTUSOSAKEYHTIO' THEN '24'
                    WHEN yritysmuoto = 'VAKUUTUSYHDISTYS' THEN '25' WHEN yritysmuoto = 'YKSITYINEN_ELINKEINONHARJOITTAJA' THEN '26'
                    WHEN yritysmuoto = 'LAIVANISANNISTOYHTIO' THEN '28' WHEN yritysmuoto = 'MUU_YHDISTYS' THEN '29'
                    WHEN yritysmuoto = 'MUU_YHTIO' THEN '30' WHEN yritysmuoto = 'ERITYISLAINSAADANTOON_PERUSTUVA_YHDISTYS' THEN '31'
                    WHEN yritysmuoto = 'ELAKESAATIO' THEN '32' WHEN yritysmuoto = 'TYOELAKEKASSA' THEN '33'
                    WHEN yritysmuoto = 'METSANHOITOYHDISTYS' THEN '35' WHEN yritysmuoto = 'VAKUUTUSKASSA' THEN '36'
                    WHEN yritysmuoto = 'TYOTTOMYYSKASSA' THEN '37' WHEN yritysmuoto = 'MUU_TALOUDELLINEN_YHDISTYS' THEN '38'
                    WHEN yritysmuoto = 'MUU_SAATIO' THEN '39' WHEN yritysmuoto = 'VALTIO_JA_SEN_LAITOKSET' THEN '40'
                    WHEN yritysmuoto = 'KUNTA' THEN '41' WHEN yritysmuoto = 'KUNTAYHTYMA' THEN '42'
                    WHEN yritysmuoto = 'AHVENANMAAN_MAAKUNTA_TAI_VIRASTO' THEN '43' WHEN yritysmuoto = 'EV_LUT_KIRKKO' THEN '44'
                    WHEN yritysmuoto = 'ORTODOKSINEN_KIRKKO' THEN '45' WHEN yritysmuoto = 'USKONNOLLINEN_YHDYSKUNTA' THEN '46'
                    WHEN yritysmuoto = 'YLIOPPILASKUNTA_TAI_OSAKUNTA' THEN '47' WHEN yritysmuoto = 'ERILLISHALLINNOLLINEN_VALTION_ALUE' THEN '48'
                    WHEN yritysmuoto = 'MUU_JULKISOIKEUDELLINE_OIKEUSHENKILO' THEN '49' WHEN yritysmuoto = 'YHTEISETUUDET' THEN '50'
                    WHEN yritysmuoto = 'VEROTUSYHTYMA' THEN '51' WHEN yritysmuoto = 'MUU_YHTEISVAST_PIDATYSVELVOLLINEN' THEN '52'
                    WHEN yritysmuoto = 'KUOLINPESA' THEN '53' WHEN yritysmuoto = 'KONKURSSIPESA' THEN '54'
                    WHEN yritysmuoto = 'YHTEISMETSA' THEN '55' WHEN yritysmuoto = 'MUU_KIINTEISTOOSAKEYHTIO' THEN '56'
                    WHEN yritysmuoto = 'ELINKEINOYHTYMA' THEN '57' WHEN yritysmuoto = 'KESKINAINEN_VAHINKOVAK_YHDISTYS' THEN '58'
                    WHEN yritysmuoto = 'MUU_VEROTUKSEN_YKSIKKO' THEN '59' WHEN yritysmuoto = 'ULKOMAINEN_YHTEISO' THEN '60'
                    WHEN yritysmuoto = 'KUNNALLINEN_LIIKELAITOS' THEN '61' WHEN yritysmuoto = 'KUNTAINLIITON_LIIKELAITOS' THEN '62'
                    WHEN yritysmuoto = 'MUUT_OIKEUSHENKILOT' THEN '63' WHEN yritysmuoto = 'AHVENANMAAN_LIIKELAITOS' THEN '64'
                    WHEN yritysmuoto = 'KAUPPAKAMARI' THEN '70' WHEN yritysmuoto = 'PAIKALLISYHTEISO' THEN '71'
                    WHEN yritysmuoto = 'EU_YHTIO' THEN '80' WHEN yritysmuoto = 'EU_OSUUSKUNTA' THEN '83'
                    WHEN yritysmuoto = 'EU_OSUUSPANKKI' THEN '84' WHEN yritysmuoto = 'EU_OSUUSKUNNAN_KIINTEA_TOIMIPAIKKA' THEN '85'
                    WHEN yritysmuoto = 'PALISKUNTA' THEN '90' WHEN yritysmuoto = 'SEURAKUNTA_PAIKALLISYHTEISO' THEN '91'
                    ELSE '0'
                END;
            ''')


def reverse_func(apps, schema_editor):
    with connection.cursor() as cursor:
        for table_name in table_names:
            cursor.execute(f'''
                UPDATE {table_name}
                SET yritysmuoto = CASE
                    WHEN yritysmuoto = '0' THEN 'EI_YRITYSMUOTOA' WHEN yritysmuoto = '2' THEN 'ASUNTOOSAKEYHTIO'
                    WHEN yritysmuoto = '3' THEN 'ASUKASHALLINTOALUA' WHEN yritysmuoto = '4' THEN 'ASUMISOIKEUSYHDISTYS'
                    WHEN yritysmuoto = '5' THEN 'AVOIN_YHTIO' WHEN yritysmuoto = '6' THEN 'AATTEELLINEN_YHDISTYS'
                    WHEN yritysmuoto = '7' THEN 'EU_TALOUDELLINEN_ETUYHT_SIVUTOIMIPAIKKA' WHEN yritysmuoto = '8' THEN 'EU_TALOUDELLINE_ETURYHMA'
                    WHEN yritysmuoto = '9' THEN 'HYPOTEEKKIYHDISTYS' WHEN yritysmuoto = '10' THEN 'KESKINAINEN_KIINTEISTOOSAKEYTIO'
                    WHEN yritysmuoto = '11' THEN 'JULKINEN_KESKINEN_VAKUUTUSYHTIO' WHEN yritysmuoto = '12' THEN 'KESKINAINEN_VAKUUTUSYHTIO'
                    WHEN yritysmuoto = '13' THEN 'KOMMANDIITTIYHTIO' WHEN yritysmuoto = '14' THEN 'OSUUSKUNTA'
                    WHEN yritysmuoto = '15' THEN 'OSUUSPANKKI' WHEN yritysmuoto = '16' THEN 'OSAKEYHTIO'
                    WHEN yritysmuoto = '17' THEN 'JULKINEN_OSAKEYHTIO' WHEN yritysmuoto = '18' THEN 'SAATIO'
                    WHEN yritysmuoto = '19' THEN 'SIVULIIKE' WHEN yritysmuoto = '20' THEN 'SAASTOPANKKI'
                    WHEN yritysmuoto = '21' THEN 'TALOUDELLINEN_YHDISTYS' WHEN yritysmuoto = '22' THEN 'VALTION_LIIKELAITOS'
                    WHEN yritysmuoto = '23' THEN 'JULKINEN_VAKUUTUSOSAKEYTIO' WHEN yritysmuoto = '24' THEN 'VAKUUTUSOSAKEYHTIO'
                    WHEN yritysmuoto = '25' THEN 'VAKUUTUSYHDISTYS' WHEN yritysmuoto = '26' THEN 'YKSITYINEN_ELINKEINONHARJOITTAJA'
                    WHEN yritysmuoto = '28' THEN 'LAIVANISANNISTOYHTIO' WHEN yritysmuoto = '29' THEN 'MUU_YHDISTYS'
                    WHEN yritysmuoto = '30' THEN 'MUU_YHTIO' WHEN yritysmuoto = '31' THEN 'ERITYISLAINSAADANTOON_PERUSTUVA_YHDISTYS'
                    WHEN yritysmuoto = '32' THEN 'ELAKESAATIO' WHEN yritysmuoto = '33' THEN 'TYOELAKEKASSA'
                    WHEN yritysmuoto = '35' THEN 'METSANHOITOYHDISTYS' WHEN yritysmuoto = '36' THEN 'VAKUUTUSKASSA'
                    WHEN yritysmuoto = '37' THEN 'TYOTTOMYYSKASSA' WHEN yritysmuoto = '38' THEN 'MUU_TALOUDELLINEN_YHDISTYS'
                    WHEN yritysmuoto = '39' THEN 'MUU_SAATIO' WHEN yritysmuoto = '40' THEN 'VALTIO_JA_SEN_LAITOKSET'
                    WHEN yritysmuoto = '41' THEN 'KUNTA' WHEN yritysmuoto = '42' THEN 'KUNTAYHTYMA'
                    WHEN yritysmuoto = '43' THEN 'AHVENANMAAN_MAAKUNTA_TAI_VIRASTO' WHEN yritysmuoto = '44' THEN 'EV_LUT_KIRKKO'
                    WHEN yritysmuoto = '45' THEN 'ORTODOKSINEN_KIRKKO' WHEN yritysmuoto = '46' THEN 'USKONNOLLINEN_YHDYSKUNTA'
                    WHEN yritysmuoto = '47' THEN 'YLIOPPILASKUNTA_TAI_OSAKUNTA' WHEN yritysmuoto = '48' THEN 'ERILLISHALLINNOLLINEN_VALTION_ALUE'
                    WHEN yritysmuoto = '49' THEN 'MUU_JULKISOIKEUDELLINE_OIKEUSHENKILO' WHEN yritysmuoto = '50' THEN 'YHTEISETUUDET'
                    WHEN yritysmuoto = '51' THEN 'VEROTUSYHTYMA' WHEN yritysmuoto = '52' THEN 'MUU_YHTEISVAST_PIDATYSVELVOLLINEN'
                    WHEN yritysmuoto = '53' THEN 'KUOLINPESA' WHEN yritysmuoto = '54' THEN 'KONKURSSIPESA'
                    WHEN yritysmuoto = '55' THEN 'YHTEISMETSA' WHEN yritysmuoto = '56' THEN 'MUU_KIINTEISTOOSAKEYHTIO'
                    WHEN yritysmuoto = '57' THEN 'ELINKEINOYHTYMA' WHEN yritysmuoto = '58' THEN 'KESKINAINEN_VAHINKOVAK_YHDISTYS'
                    WHEN yritysmuoto = '59' THEN 'MUU_VEROTUKSEN_YKSIKKO' WHEN yritysmuoto = '60' THEN 'ULKOMAINEN_YHTEISO'
                    WHEN yritysmuoto = '61' THEN 'KUNNALLINEN_LIIKELAITOS' WHEN yritysmuoto = '62' THEN 'KUNTAINLIITON_LIIKELAITOS'
                    WHEN yritysmuoto = '63' THEN 'MUUT_OIKEUSHENKILOT' WHEN yritysmuoto = '64' THEN 'AHVENANMAAN_LIIKELAITOS'
                    WHEN yritysmuoto = '70' THEN 'KAUPPAKAMARI' WHEN yritysmuoto = '71' THEN 'PAIKALLISYHTEISO'
                    WHEN yritysmuoto = '80' THEN 'EU_YHTIO' WHEN yritysmuoto = '83' THEN 'EU_OSUUSKUNTA'
                    WHEN yritysmuoto = '84' THEN 'EU_OSUUSPANKKI' WHEN yritysmuoto = '85' THEN 'EU_OSUUSKUNNAN_KIINTEA_TOIMIPAIKKA'
                    WHEN yritysmuoto = '90' THEN 'PALISKUNTA' WHEN yritysmuoto = '91' THEN 'SEURAKUNTA_PAIKALLISYHTEISO'
                    ELSE 'EI_YRITYSMUOTOA'
                END;
            ''')


class Migration(migrations.Migration):

    dependencies = [
        ('varda', '0059_historicalyearlyreportsummary_yearlyreportsummary'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
        migrations.AlterField(
            model_name='historicalvakajarjestaja',
            name='yritysmuoto',
            field=models.CharField(default='0', max_length=4, validators=[varda.validators.validate_yritysmuoto_koodi]),
        ),
        migrations.AlterField(
            model_name='vakajarjestaja',
            name='yritysmuoto',
            field=models.CharField(default='0', max_length=4, validators=[varda.validators.validate_yritysmuoto_koodi]),
        ),
        migrations.AlterField(
            model_name='historicalvakajarjestaja',
            name='integraatio_organisaatio',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, size=None),
        ),
        migrations.AlterField(
            model_name='vakajarjestaja',
            name='integraatio_organisaatio',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, size=None),
        ),
    ]
