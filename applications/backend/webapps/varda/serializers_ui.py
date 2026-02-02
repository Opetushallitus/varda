import datetime

from django.db.models import Q
from django.urls import reverse
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from varda.cache import caching_to_representation
from varda.models import (
    PaosOikeus,
    PaosToiminta,
    Toimipaikka,
    Organisaatio,
    Henkilo,
    Tyontekija,
    Tyoskentelypaikka,
    Lapsi,
    Varhaiskasvatussuhde,
    ErrorReports,
)
from varda.permissions import get_available_tehtavanimike_codes_for_user
from varda.serializers_common import OidRelatedField, OrganisaatioPermissionCheckedHLField
from varda.validators import validate_organisaatio_oid


class OrganisaatioUiSerializer(serializers.HyperlinkedModelSerializer):
    kunnallinen_kytkin = serializers.BooleanField(read_only=True)
    active = serializers.SerializerMethodField(read_only=True)
    active_errors = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Organisaatio
        fields = (
            "nimi",
            "id",
            "url",
            "organisaatio_oid",
            "kunnallinen_kytkin",
            "y_tunnus",
            "alkamis_pvm",
            "paattymis_pvm",
            "active",
            "active_errors",
        )
        read_only_fields = (
            "nimi",
            "id",
            "organisaatio_oid",
            "kunnallinen_kytkin",
            "y_tunnus",
            "alkamis_pvm",
            "paattymis_pvm",
            "active",
            "active_errors",
        )

    @caching_to_representation("organisaatio-ui")
    def to_representation(self, instance):
        return super(OrganisaatioUiSerializer, self).to_representation(instance)

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_active(self, instance):
        today = datetime.date.today()
        return (
            False
            if (instance.alkamis_pvm and instance.alkamis_pvm > today)
            or (instance.paattymis_pvm and instance.paattymis_pvm < today)
            else True
        )

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_active_errors(self, instance):
        try:
            active_errors = instance.error_reports.active_errors
        except ErrorReports.DoesNotExist:
            active_errors = False
        return active_errors


class ToimipaikkaUiSerializer(serializers.HyperlinkedModelSerializer):
    nimi_original = serializers.ReadOnlyField(source="nimi")
    nimi = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    paos_toimipaikka_kytkin = serializers.SerializerMethodField()
    paos_oma_organisaatio_url = serializers.SerializerMethodField()
    paos_organisaatio_url = serializers.SerializerMethodField()
    paos_organisaatio_nimi = serializers.SerializerMethodField()
    paos_organisaatio_oid = serializers.SerializerMethodField()
    paos_tallentaja_organisaatio_id_list = serializers.SerializerMethodField()

    class Meta:
        model = Toimipaikka
        fields = (
            "hallinnointijarjestelma",
            "id",
            "nimi_original",
            "nimi",
            "url",
            "organisaatio_oid",
            "paos_toimipaikka_kytkin",
            "paos_oma_organisaatio_url",
            "paos_organisaatio_url",
            "paos_organisaatio_nimi",
            "paos_organisaatio_oid",
            "paos_tallentaja_organisaatio_id_list",
        )

    def get_nimi(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj["nimi"] + ", " + toimipaikka_obj["vakajarjestaja__nimi"].upper()
        else:
            return toimipaikka_obj["nimi"]

    def get_url(self, toimipaikka_obj):
        request = self.context.get("request")
        return request.build_absolute_uri(reverse("toimipaikka-detail", kwargs={"pk": toimipaikka_obj["id"]}))

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_paos_toimipaikka_kytkin(self, toimipaikka_obj):
        return not int(self.context.get("organisaatio_pk")) == toimipaikka_obj["vakajarjestaja__id"]

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_oma_organisaatio_url(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            request = self.context.get("request")
            return request.build_absolute_uri(
                reverse("organisaatio-detail", kwargs={"pk": int(self.context.get("organisaatio_pk"))})
            )
        else:
            return ""

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_organisaatio_url(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            request = self.context.get("request")
            return request.build_absolute_uri(
                reverse("organisaatio-detail", kwargs={"pk": toimipaikka_obj["vakajarjestaja__id"]})
            )
        else:
            return ""

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_organisaatio_nimi(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj["vakajarjestaja__nimi"]
        else:
            return ""

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_organisaatio_oid(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj["vakajarjestaja__organisaatio_oid"]
        else:
            return ""

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.IntegerField()))
    def get_paos_tallentaja_organisaatio_id_list(self, toimipaikka_obj):
        # Haetaan kaikki vakajärjestäjät joilla tähän toimipaikkaan tallennusoikeus
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            oma_organisaatio_id_list = PaosToiminta.objects.filter(
                Q(voimassa_kytkin=True) & Q(paos_toimipaikka=toimipaikka_obj["id"])
            ).values_list("oma_organisaatio__id", flat=True)

            return PaosOikeus.objects.filter(
                Q(voimassa_kytkin=True)
                & Q(jarjestaja_kunta_organisaatio__in=oma_organisaatio_id_list)
                & Q(tuottaja_organisaatio=toimipaikka_obj["vakajarjestaja__id"])
            ).values_list("tallentaja_organisaatio__id", flat=True)
        else:
            return []


class UiLapsiSerializer(serializers.HyperlinkedModelSerializer):
    etunimet = serializers.ReadOnlyField(source="henkilo.etunimet")
    sukunimi = serializers.ReadOnlyField(source="henkilo.sukunimi")
    henkilo_oid = serializers.ReadOnlyField(source="henkilo.henkilo_oid")
    syntyma_pvm = serializers.ReadOnlyField(source="henkilo.syntyma_pvm")
    oma_organisaatio_nimi = serializers.ReadOnlyField(source="oma_organisaatio.nimi")
    paos_organisaatio_nimi = serializers.ReadOnlyField(source="paos_organisaatio.nimi")
    lapsi_id = serializers.IntegerField(read_only=True, source="id")
    lapsi_url = serializers.HyperlinkedRelatedField(view_name="lapsi-detail", source="id", read_only=True)

    class Meta:
        model = Lapsi
        fields = (
            "etunimet",
            "sukunimi",
            "henkilo_oid",
            "syntyma_pvm",
            "oma_organisaatio_nimi",
            "paos_organisaatio_nimi",
            "lapsi_id",
            "lapsi_url",
        )


class TyontekijaUiSerializer(serializers.HyperlinkedModelSerializer):
    tehtavanimikkeet = serializers.SerializerMethodField()
    is_missing_data = serializers.SerializerMethodField()

    class Meta:
        model = Tyontekija
        fields = ("id", "url", "tehtavanimikkeet", "is_missing_data")

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_tehtavanimikkeet(self, instance):
        user = self.context["request"].user
        return get_available_tehtavanimike_codes_for_user(
            user,
            instance,
            has_permissions=self.context["has_organisaatio_level_permissions"],
            organisaatio_oid_list=self.context["organisaatio_oid_list"],
        )

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_is_missing_data(self, instance):
        return not Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=instance).exists()


class TyontekijaHenkiloUiSerializer(serializers.HyperlinkedModelSerializer):
    tyontekijat = TyontekijaUiSerializer(many=True)

    class Meta:
        model = Henkilo
        fields = ("id", "url", "henkilo_oid", "etunimet", "sukunimi", "tyontekijat")


class LapsihakuLapsetUiSerializer(serializers.HyperlinkedModelSerializer):
    vakatoimija_oid = serializers.CharField(source="vakatoimija.organisaatio_oid", allow_null=True)
    vakatoimija_nimi = serializers.CharField(source="vakatoimija.nimi", allow_null=True)
    oma_organisaatio_oid = serializers.CharField(source="oma_organisaatio.organisaatio_oid", allow_null=True)
    oma_organisaatio_nimi = serializers.CharField(source="oma_organisaatio.nimi", allow_null=True)
    paos_organisaatio_oid = serializers.CharField(source="paos_organisaatio.organisaatio_oid", allow_null=True)
    paos_organisaatio_nimi = serializers.CharField(source="paos_organisaatio.nimi", allow_null=True)
    tallentaja_organisaatio_oid = serializers.SerializerMethodField(allow_null=True)
    is_missing_data = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        fields = (
            "id",
            "url",
            "vakatoimija_oid",
            "vakatoimija_nimi",
            "oma_organisaatio_oid",
            "oma_organisaatio_nimi",
            "paos_organisaatio_oid",
            "paos_organisaatio_nimi",
            "tallentaja_organisaatio_oid",
            "is_missing_data",
        )

    def get_tallentaja_organisaatio_oid(self, lapsi):
        if lapsi.oma_organisaatio and lapsi.paos_organisaatio:
            paos_oikeus = PaosOikeus.objects.filter(
                jarjestaja_kunta_organisaatio=lapsi.oma_organisaatio,
                tuottaja_organisaatio=lapsi.paos_organisaatio,
                voimassa_kytkin=True,
            ).first()
            if paos_oikeus:
                return paos_oikeus.tallentaja_organisaatio.organisaatio_oid
        return None

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_is_missing_data(self, instance):
        return not Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=instance).exists()


class LapsihakuHenkiloUiSerializer(serializers.HyperlinkedModelSerializer):
    lapset = LapsihakuLapsetUiSerializer(many=True, source="lapsi")

    class Meta:
        model = Henkilo
        fields = ("id", "url", "henkilo_oid", "etunimet", "sukunimi", "lapset")


class UiTyontekijaSerializer(serializers.HyperlinkedModelSerializer):
    etunimet = serializers.ReadOnlyField(source="henkilo.etunimet")
    sukunimi = serializers.ReadOnlyField(source="henkilo.sukunimi")
    henkilo_oid = serializers.ReadOnlyField(source="henkilo.henkilo_oid")
    vakajarjestaja_nimi = serializers.ReadOnlyField(source="vakajarjestaja.nimi")
    tyontekija_id = serializers.IntegerField(read_only=True, source="id")
    tyontekija_url = serializers.HyperlinkedRelatedField(view_name="tyontekija-detail", source="id", read_only=True)

    class Meta:
        model = Tyontekija
        fields = ("etunimet", "sukunimi", "henkilo_oid", "vakajarjestaja_nimi", "tyontekija_id", "tyontekija_url")


class ActiveOrganisaatioSerializer(serializers.Serializer):
    organisaatio = OrganisaatioPermissionCheckedHLField(view_name="organisaatio-detail", required=False, write_only=True)
    organisaatio_oid = OidRelatedField(
        object_type=Organisaatio,
        parent_field="organisaatio",
        parent_attribute="organisaatio_oid",
        prevalidator=validate_organisaatio_oid,
        either_required=True,
        write_only=True,
    )
