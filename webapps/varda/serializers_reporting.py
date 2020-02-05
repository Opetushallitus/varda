from rest_framework import serializers
from varda.models import Z2_Koodisto

"""
Serializers for query-results used in reports
"""


class LapsetRyhmittainSerializer(serializers.Serializer):
    ryhma_id = serializers.IntegerField()
    ryhma_tunnus = serializers.CharField()
    ryhma_lisatieto = serializers.CharField()
    ryhma_vuorohoitoryhma = serializers.BooleanField()
    ryhma_avoin_varhaiskasvatus = serializers.CharField()
    ryhma_avoin_varhaiskasvatus_lkm = serializers.IntegerField()
    ryhma_alkamispaivamaara = serializers.DateField()
    ryhma_paattymispaivamaara = serializers.DateField()
    lapsen_id = serializers.IntegerField()
    oid = serializers.CharField()
    aidinkieli = serializers.CharField()
    sukupuoli = serializers.CharField()
    syntymapaivamaara = serializers.CharField()
    kunta = serializers.CharField()


class KelaRaporttiSerializer(serializers.Serializer):
    henkilotunnus = serializers.CharField()
    etunimet = serializers.CharField()
    sukunimi = serializers.CharField()
    ika = serializers.CharField()
    postinumero = serializers.CharField()
    kotikunta_koodi = serializers.CharField()
    vaka_paatos_alkamis_pvm = serializers.DateField()
    vaka_paatos_paattymis_pvm = serializers.DateField()
    varhaiskasvatuksessa = serializers.BooleanField()
    vaka_paatos_muutos_pvm = serializers.DateTimeField()


class KoodistoSerializer(serializers.Serializer):
    class Meta:
        model = Z2_Koodisto


class TiedonsiirtotilastoSerializer(serializers.Serializer):
    vakatoimijat = serializers.IntegerField()
    toimipaikat = serializers.IntegerField()
    vakasuhteet = serializers.IntegerField()
    vakapaatokset = serializers.IntegerField()
    lapset = serializers.IntegerField()
    maksutiedot = serializers.IntegerField()
    kielipainotukset = serializers.IntegerField()
    toiminnalliset_painotukset = serializers.IntegerField()
