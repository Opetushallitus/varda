from rest_framework import serializers

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
