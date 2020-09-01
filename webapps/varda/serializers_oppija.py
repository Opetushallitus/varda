from varda.models import Henkilo, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Lapsi
from varda.misc import decrypt_henkilotunnus
from rest_framework import serializers


"""
Huoltajanakyma serializers
"""


class HuoltajanLapsiToimipaikkaSerializer(serializers.Serializer):
    toimipaikka_nimi = serializers.ReadOnlyField(source='nimi')
    toimipaikka_kunta_koodi = serializers.ReadOnlyField(source='kunta_koodi')


class HuoltajanLapsiVarhaiskasvatussuhdeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    alkamis_pvm = serializers.ReadOnlyField()
    paattymis_pvm = serializers.ReadOnlyField()
    toimipaikka = HuoltajanLapsiToimipaikkaSerializer()
    yhteysosoite = serializers.SerializerMethodField()

    def get_yhteysosoite(self, obj):
        if obj.toimipaikka.toimintamuoto_koodi in ['tm02', 'tm03']:
            return obj.toimipaikka.vakajarjestaja.sahkopostiosoite
        else:
            return obj.toimipaikka.sahkopostiosoite

    class Meta:
        model = Varhaiskasvatussuhde
        exclude = ('luonti_pvm', 'changed_by', 'muutos_pvm', 'varhaiskasvatuspaatos')


class HuoltajanLapsiVarhaiskasvatuspaatosSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    alkamis_pvm = serializers.ReadOnlyField()
    hakemus_pvm = serializers.ReadOnlyField()
    paattymis_pvm = serializers.ReadOnlyField()
    paivittainen_vaka_kytkin = serializers.ReadOnlyField()
    kokopaivainen_vaka_kytkin = serializers.ReadOnlyField()
    jarjestamismuoto_koodi = serializers.ReadOnlyField()
    vuorohoito_kytkin = serializers.ReadOnlyField()
    pikakasittely_kytkin = serializers.ReadOnlyField()
    tuntimaara_viikossa = serializers.ReadOnlyField()
    varhaiskasvatussuhteet = HuoltajanLapsiVarhaiskasvatussuhdeSerializer(many=True)

    class Meta:
        model = Varhaiskasvatuspaatos
        exclude = ('luonti_pvm', 'lapsi', 'changed_by', 'muutos_pvm',)


class HuoltajanLapsiLapsiSerializer(serializers.ModelSerializer):
    yhteysosoite = serializers.SerializerMethodField()
    varhaiskasvatuksen_jarjestaja = serializers.SerializerMethodField()
    varhaiskasvatuspaatokset = HuoltajanLapsiVarhaiskasvatuspaatosSerializer(many=True)

    def get_yhteysosoite(self, obj):
        if obj.vakatoimija is not None:
            return obj.vakatoimija.sahkopostiosoite
        if obj.oma_organisaatio is not None:
            return obj.oma_organisaatio.sahkopostiosoite

    def get_varhaiskasvatuksen_jarjestaja(self, obj):
        if obj.vakatoimija is not None:
            return obj.vakatoimija.nimi
        if obj.oma_organisaatio is not None:
            return obj.oma_organisaatio.nimi
        vakapaatos_first = obj.varhaiskasvatuspaatokset.first()
        if vakapaatos_first is not None:
            vakasuhde_first = vakapaatos_first.varhaiskasvatussuhteet.first()
            if vakasuhde_first is not None:
                return vakasuhde_first.toimipaikka.vakajarjestaja.nimi
        return None

    class Meta:
        model = Lapsi
        exclude = ('vakatoimija', 'paos_kytkin', 'oma_organisaatio', 'paos_organisaatio', 'henkilo', 'luonti_pvm',
                   'changed_by', 'muutos_pvm',)


class HuoltajanLapsiHenkiloSerializer(serializers.ModelSerializer):
    henkilotunnus = serializers.SerializerMethodField()

    class Meta:
        model = Henkilo
        lookup_field = 'henkilo_oid'
        fields = ('henkilo_oid', 'henkilotunnus', 'etunimet', 'kutsumanimi', 'sukunimi', 'aidinkieli_koodi',
                  'sukupuoli_koodi', 'syntyma_pvm', 'kotikunta_koodi', 'katuosoite', 'postinumero', 'postitoimipaikka')

    def get_henkilotunnus(self, obj):
        henkilotunnus = decrypt_henkilotunnus(obj.henkilotunnus)
        return henkilotunnus


class HuoltajanLapsiSerializer(serializers.Serializer):
    henkilo = HuoltajanLapsiHenkiloSerializer()
    voimassaolevia_varhaiskasvatuspaatoksia = serializers.ReadOnlyField()
    lapset = HuoltajanLapsiLapsiSerializer(many=True)
