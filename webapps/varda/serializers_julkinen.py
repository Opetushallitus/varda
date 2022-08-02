from rest_framework import serializers

from varda.custom_swagger import DynamicDictField
from varda.models import Z2_Code, Z2_Koodisto


class KoodistotCodeSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    description = serializers.CharField()
    active = serializers.BooleanField()

    class Meta:
        model = Z2_Code
        fields = ('code_value', 'alkamis_pvm', 'paattymis_pvm', 'name', 'description', 'active')


class KoodistotSerializer(serializers.ModelSerializer):
    codes = KoodistotCodeSerializer(many=True)

    class Meta:
        model = Z2_Koodisto
        fields = ('name', 'version', 'update_datetime', 'codes')


class LocalisationSerializer(serializers.Serializer):
    accesscount = serializers.IntegerField()
    id = serializers.IntegerField()
    category = serializers.CharField()
    key = serializers.CharField()
    accessed = serializers.IntegerField()
    created = serializers.IntegerField()
    createdBy = serializers.CharField()
    modified = serializers.IntegerField()
    modifiedBy = serializers.CharField()
    force = serializers.BooleanField()
    locale = serializers.CharField()
    value = serializers.CharField()


class PulssiSerializer(serializers.Serializer):
    organisaatio_count = serializers.IntegerField()
    kunta_count = serializers.IntegerField()
    yksityinen_count = serializers.IntegerField()
    toimipaikka_count = serializers.IntegerField()
    toimipaikka_by_tm = DynamicDictField()
    toimipaikka_by_jm = DynamicDictField()
    toimipaikka_by_kj = DynamicDictField()
    toimipaikka_with_kp = serializers.IntegerField()
    toimipaikka_with_tp = serializers.IntegerField()
    lapsi_count = serializers.IntegerField()
    vakapaatos_count = serializers.IntegerField()
    paivittainen_count = serializers.IntegerField()
    kokopaivainen_count = serializers.IntegerField()
    vuorohoito_count = serializers.IntegerField()
    huoltaja_count = serializers.IntegerField()
    asiakasmaksu_avg = serializers.DecimalField(0, 0)
    tyontekija_count = serializers.IntegerField()
    tyoskentelypaikka_by_tn = DynamicDictField()
    tyontekija_multi_count = serializers.IntegerField()
    koulutuspaiva_count = serializers.DecimalField(0, 0)
    tilapainen_henkilosto_tyontekijamaara = serializers.IntegerField()
    tilapainen_henkilosto_tuntimaara = serializers.DecimalField(0, 0)
    ui_login_count = serializers.IntegerField()
    oppija_login_count = serializers.IntegerField()
    valtuudet_login_count = serializers.IntegerField()
    ui_new_paatos_count = serializers.IntegerField()
    ui_new_tyontekija_count = serializers.IntegerField()
    ui_new_maksutieto_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
