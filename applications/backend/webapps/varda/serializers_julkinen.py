from drf_yasg import openapi
from rest_framework import serializers

from varda.custom_swagger import CustomSchemaField
from varda.models import Z2_Code, Z2_Koodisto


class KoodistotCodeSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    description = serializers.CharField()
    active = serializers.BooleanField()

    class Meta:
        model = Z2_Code
        fields = ("code_value", "alkamis_pvm", "paattymis_pvm", "name", "description", "active")


class KoodistotSerializer(serializers.ModelSerializer):
    codes = KoodistotCodeSerializer(many=True)

    class Meta:
        model = Z2_Koodisto
        fields = ("name", "version", "update_datetime", "codes")

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance["name"] == "posti":
            # Keep only codes that follow the rules:
            # - '00099' is always allowed
            # - Third digit cannot be '0'
            # - Last digit must be '0' or '5'
            filtered_codes = []
            for code in representation["codes"]:
                val = code["code_value"]
                if val == "00099":
                    filtered_codes.append(code)
                elif val[2] != "0" and val[-1] in ("0", "5"):
                    filtered_codes.append(code)
            representation["codes"] = filtered_codes

        return representation


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
    toimipaikka_by_tm = CustomSchemaField({"type": openapi.TYPE_OBJECT, "additionalProperties": {"type": openapi.TYPE_INTEGER}})
    toimipaikka_by_jm = CustomSchemaField({"type": openapi.TYPE_OBJECT, "additionalProperties": {"type": openapi.TYPE_INTEGER}})
    toimipaikka_by_kj = CustomSchemaField({"type": openapi.TYPE_OBJECT, "additionalProperties": {"type": openapi.TYPE_INTEGER}})
    toimipaikka_by_ak = CustomSchemaField(
        {
            "type": openapi.TYPE_OBJECT,
            "properties": {"others": {"type": openapi.TYPE_INTEGER}},
            "additionalProperties": {"type": openapi.TYPE_INTEGER},
        }
    )
    toimipaikka_with_kp = serializers.IntegerField()
    toimipaikka_with_tp = serializers.IntegerField()
    lapsi_count = serializers.IntegerField()
    lapsi_kunta_count = serializers.IntegerField()
    lapsi_yksityinen_count = serializers.IntegerField()
    vakapaatos_count = serializers.IntegerField()
    paivittainen_count = serializers.IntegerField()
    kokopaivainen_count = serializers.IntegerField()
    vuorohoito_count = serializers.IntegerField()
    lapsi_by_jm = CustomSchemaField({"type": openapi.TYPE_OBJECT, "additionalProperties": {"type": openapi.TYPE_INTEGER}})
    huoltaja_count = serializers.IntegerField()
    asiakasmaksu_avg = serializers.DecimalField(0, 0)
    tyontekija_count = serializers.IntegerField()
    tyoskentelypaikka_by_tn = CustomSchemaField(
        {"type": openapi.TYPE_OBJECT, "additionalProperties": {"type": openapi.TYPE_INTEGER}}
    )
    tyontekija_multi_count = serializers.IntegerField()
    taydennyskoulutus_count = serializers.IntegerField()
    koulutuspaiva_count = serializers.DecimalField(0, 0)
    vuokrattu_henkilosto_tyontekijamaara = serializers.IntegerField()
    vuokrattu_henkilosto_tuntimaara = serializers.DecimalField(0, 0)
    ui_login_count = serializers.IntegerField()
    oppija_login_count = serializers.IntegerField()
    valtuudet_login_count = serializers.IntegerField()
    ui_new_paatos_count = serializers.IntegerField()
    ui_new_tyontekija_count = serializers.IntegerField()
    ui_new_maksutieto_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
