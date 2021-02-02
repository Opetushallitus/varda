import datetime

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q

from varda.models import (Henkilo, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Lapsi, Huoltajuussuhde, Maksutieto,
                          Tyontekija, Palvelussuhde, TaydennyskoulutusTyontekija, Tyoskentelypaikka, PidempiPoissaolo,
                          Tutkinto, Toimipaikka)
from varda.misc import decrypt_henkilotunnus
from rest_framework import serializers


class AbstractAktiivinenToimijaYhteystietoSerializer(serializers.ModelSerializer):
    """
    Serializers extending this serializer need to define vakajarjestaja_path in Meta class.
    e.g.
    class Meta:
        vakajarjestaja_path = ['lapsi', 'vakatoimija']
    or for multiple choices (parsed in order and first match is accepted)
    class Meta:
        vakajarjestaja_path = [['lapsi', 'vakatoimija'], ['lapsi', 'oma_organisaatio']]
    """
    yhteysosoite = serializers.SerializerMethodField(read_only=True)
    aktiivinen_toimija = serializers.SerializerMethodField(read_only=True)

    def _parse_vakajarjestaja_path(self, instance, vakajarjestaja_path):
        vakajarjestaja = instance
        for path_item in vakajarjestaja_path:
            if isinstance(path_item, list):
                vakajarjestaja = self._parse_vakajarjestaja_path(instance, path_item)
                if vakajarjestaja:
                    return vakajarjestaja
            else:
                vakajarjestaja = getattr(vakajarjestaja, path_item, None)
        return vakajarjestaja

    def _get_vakajarjestaja_object(self, instance):
        if not hasattr(self, 'Meta') or not hasattr(self.Meta, 'vakajarjestaja_path'):
            raise NotImplementedError('Meta.vakajarjestaja_path')
        return self._parse_vakajarjestaja_path(instance, self.Meta.vakajarjestaja_path)

    def get_yhteysosoite(self, instance):
        aktiivinen_toimija = self.get_aktiivinen_toimija(instance)
        vakajarjestaja = self._get_vakajarjestaja_object(instance)
        if vakajarjestaja and aktiivinen_toimija:
            return vakajarjestaja.sahkopostiosoite
        return None

    def get_aktiivinen_toimija(self, instance):
        now = datetime.date.today()
        vakajarjestaja = self._get_vakajarjestaja_object(instance)
        if not vakajarjestaja:
            return None
        return vakajarjestaja.paattymis_pvm is None or vakajarjestaja.paattymis_pvm >= now


class OppijaVarhaiskasvatussuhdeToimipaikkaSerializer(serializers.ModelSerializer):
    toimipaikka_nimi = serializers.ReadOnlyField(source='nimi')
    toimipaikka_kunta_koodi = serializers.ReadOnlyField(source='kunta_koodi')

    class Meta:
        model = Toimipaikka
        fields = ('toimipaikka_nimi', 'toimipaikka_kunta_koodi')


class OppijaVarhaiskasvatussuhdeSerializer(serializers.ModelSerializer):
    toimipaikka = OppijaVarhaiskasvatussuhdeToimipaikkaSerializer(read_only=True)
    yhteysosoite = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ('id', 'alkamis_pvm', 'paattymis_pvm', 'toimipaikka', 'yhteysosoite')

    def get_yhteysosoite(self, obj):
        if obj.toimipaikka.toimintamuoto_koodi in ['tm02', 'tm03']:
            return obj.toimipaikka.vakajarjestaja.sahkopostiosoite
        else:
            return obj.toimipaikka.sahkopostiosoite


class OppijaVarhaiskasvatuspaatosSerializer(serializers.ModelSerializer):
    varhaiskasvatussuhteet = OppijaVarhaiskasvatussuhdeSerializer(many=True, read_only=True)

    class Meta:
        model = Varhaiskasvatuspaatos
        fields = ('id', 'alkamis_pvm', 'hakemus_pvm', 'paattymis_pvm', 'paivittainen_vaka_kytkin',
                  'kokopaivainen_vaka_kytkin', 'tilapainen_vaka_kytkin', 'jarjestamismuoto_koodi', 'vuorohoito_kytkin',
                  'pikakasittely_kytkin', 'tuntimaara_viikossa', 'varhaiskasvatussuhteet')


class OppijaLapsiSerializer(AbstractAktiivinenToimijaYhteystietoSerializer):
    yhteysosoite = serializers.SerializerMethodField(read_only=True)
    varhaiskasvatuksen_jarjestaja = serializers.SerializerMethodField(read_only=True)
    aktiivinen_toimija = serializers.SerializerMethodField(read_only=True)
    varhaiskasvatuspaatokset = OppijaVarhaiskasvatuspaatosSerializer(many=True, read_only=True)

    class Meta:
        model = Lapsi
        fields = ('id', 'yhteysosoite', 'varhaiskasvatuksen_jarjestaja', 'aktiivinen_toimija', 'varhaiskasvatuspaatokset')
        vakajarjestaja_path = [['vakatoimija'], ['oma_organisaatio']]

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


class OppijaMaksutietoSerializer(serializers.ModelSerializer):
    huoltaja_lkm = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Maksutieto
        fields = ('id', 'yksityinen_jarjestaja', 'maksun_peruste_koodi', 'palveluseteli_arvo', 'asiakasmaksu',
                  'perheen_koko', 'alkamis_pvm', 'paattymis_pvm', 'huoltaja_lkm')

    def get_huoltaja_lkm(self, maksutieto):
        return maksutieto.huoltajuussuhteet.count()


class OppijaHuoltajuussuhdeSerializer(AbstractAktiivinenToimijaYhteystietoSerializer):
    lapsi_etunimet = serializers.ReadOnlyField(source='lapsi.henkilo.etunimet')
    lapsi_kutsumanimi = serializers.ReadOnlyField(source='lapsi.henkilo.kutsumanimi')
    lapsi_sukunimi = serializers.ReadOnlyField(source='lapsi.henkilo.sukunimi')
    lapsi_henkilo_id = serializers.ReadOnlyField(source='lapsi.henkilo_id')
    lapsi_henkilo_oid = serializers.ReadOnlyField(source='lapsi.henkilo.henkilo_oid')
    vakatoimija_id = serializers.ReadOnlyField(source='lapsi.vakatoimija_id')
    vakatoimija_oid = serializers.ReadOnlyField(source='lapsi.vakatoimija.organisaatio_oid')
    vakatoimija_nimi = serializers.ReadOnlyField(source='lapsi.vakatoimija.nimi')
    oma_organisaatio_id = serializers.ReadOnlyField(source='lapsi.oma_organisaatio_id')
    oma_organisaatio_oid = serializers.ReadOnlyField(source='lapsi.oma_organisaatio.organisaatio_oid')
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='lapsi.oma_organisaatio.nimi')
    paos_organisaatio_id = serializers.ReadOnlyField(source='lapsi.paos_organisaatio_id')
    paos_organisaatio_oid = serializers.ReadOnlyField(source='lapsi.paos_organisaatio.organisaatio_oid')
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='lapsi.paos_organisaatio.nimi')
    maksutiedot = OppijaMaksutietoSerializer(many=True, read_only=True)

    class Meta:
        model = Huoltajuussuhde
        fields = ('lapsi_id', 'lapsi_etunimet', 'lapsi_kutsumanimi', 'lapsi_sukunimi', 'lapsi_henkilo_id',
                  'lapsi_henkilo_oid', 'vakatoimija_id', 'vakatoimija_oid', 'vakatoimija_nimi', 'oma_organisaatio_id',
                  'oma_organisaatio_oid', 'oma_organisaatio_nimi', 'paos_organisaatio_id', 'paos_organisaatio_oid',
                  'paos_organisaatio_nimi', 'aktiivinen_toimija', 'yhteysosoite', 'voimassa_kytkin', 'maksutiedot')
        vakajarjestaja_path = [['lapsi', 'vakatoimija'], ['lapsi', 'oma_organisaatio']]


class OppijaPidempiPoissaoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = PidempiPoissaolo
        fields = ('id', 'alkamis_pvm', 'paattymis_pvm')


class OppijaTyoskentelypaikkaSerializer(serializers.ModelSerializer):
    toimipaikka_nimi = serializers.ReadOnlyField(source='toimipaikka.nimi')
    toimipaikka_oid = serializers.ReadOnlyField(source='toimipaikka.organisaatio_oid')

    class Meta:
        model = Tyoskentelypaikka
        fields = ('id', 'toimipaikka_id', 'toimipaikka_oid', 'toimipaikka_nimi', 'tehtavanimike_koodi',
                  'kelpoisuus_kytkin', 'kiertava_tyontekija_kytkin', 'alkamis_pvm', 'paattymis_pvm')


class OppijaPalvelussuhdeSerializer(serializers.ModelSerializer):
    tyoskentelypaikat = OppijaTyoskentelypaikkaSerializer(many=True, read_only=True)
    pidemmat_poissaolot = OppijaPidempiPoissaoloSerializer(source='pidemmatpoissaolot', many=True, read_only=True)

    class Meta:
        model = Palvelussuhde
        fields = ('id', 'tyosuhde_koodi', 'tyoaika_koodi', 'tyoaika_viikossa', 'tutkinto_koodi', 'alkamis_pvm',
                  'paattymis_pvm', 'tyoskentelypaikat', 'pidemmat_poissaolot')


class OppijaTaydennyskoulutusSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='taydennyskoulutus__id')
    nimi = serializers.ReadOnlyField(source='taydennyskoulutus__nimi')
    suoritus_pvm = serializers.ReadOnlyField(source='taydennyskoulutus__suoritus_pvm')
    koulutuspaivia = serializers.ReadOnlyField(source='taydennyskoulutus__koulutuspaivia')
    tehtavanimike_koodi_list = serializers.ReadOnlyField()

    class Meta:
        model = TaydennyskoulutusTyontekija
        fields = ('id', 'tehtavanimike_koodi_list', 'nimi', 'suoritus_pvm', 'koulutuspaivia')


class OppijaTutkintoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutkinto
        fields = ('id', 'tutkinto_koodi')


class OppijaTyontekijaSerializer(AbstractAktiivinenToimijaYhteystietoSerializer):
    vakajarjestaja_nimi = serializers.ReadOnlyField(source='vakajarjestaja.nimi')
    vakajarjestaja_oid = serializers.ReadOnlyField(source='vakajarjestaja.organisaatio_oid')
    tutkinnot = serializers.SerializerMethodField(read_only=True)
    palvelussuhteet = OppijaPalvelussuhdeSerializer(many=True, read_only=True)
    taydennyskoulutukset = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tyontekija
        fields = ('id', 'vakajarjestaja_id', 'vakajarjestaja_oid', 'vakajarjestaja_nimi', 'aktiivinen_toimija',
                  'yhteysosoite', 'tutkinnot', 'palvelussuhteet', 'taydennyskoulutukset')
        vakajarjestaja_path = ['vakajarjestaja']

    def get_tutkinnot(self, tyontekija):
        tutkinnot_qs = tyontekija.henkilo.tutkinnot.filter(vakajarjestaja=tyontekija.vakajarjestaja)
        return OppijaTutkintoSerializer(instance=tutkinnot_qs, many=True).data

    def get_taydennyskoulutukset(self, tyontekija):
        qs = tyontekija.taydennyskoulutukset_tyontekijat
        qs = (qs.values('taydennyskoulutus__id', 'taydennyskoulutus__nimi',
                        'taydennyskoulutus__suoritus_pvm', 'taydennyskoulutus__koulutuspaivia')
              .annotate(tehtavanimike_koodi_list=ArrayAgg('tehtavanimike_koodi')))
        return OppijaTaydennyskoulutusSerializer(instance=qs, many=True, read_only=True).data


class HenkilotiedotSerializer(serializers.ModelSerializer):
    henkilotunnus = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Henkilo
        fields = ('id', 'henkilo_oid', 'henkilotunnus', 'etunimet', 'kutsumanimi', 'sukunimi', 'aidinkieli_koodi',
                  'sukupuoli_koodi', 'syntyma_pvm', 'kotikunta_koodi', 'katuosoite', 'postinumero', 'postitoimipaikka')

    def get_henkilotunnus(self, henkilo):
        return decrypt_henkilotunnus(henkilo.henkilotunnus)


class HuoltajatiedotSerializer(serializers.ModelSerializer):
    huoltaja_id = serializers.ReadOnlyField(source='huoltaja.id')
    huoltajuussuhteet = OppijaHuoltajuussuhdeSerializer(source='huoltaja.huoltajuussuhteet',
                                                        many=True, read_only=True)

    class Meta:
        model = Henkilo
        fields = ('huoltaja_id', 'huoltajuussuhteet')


class TyontekijatiedotSerializer(serializers.ModelSerializer):
    tyontekijat = OppijaTyontekijaSerializer(many=True, read_only=True)

    class Meta:
        model = Henkilo
        fields = ('tyontekijat',)

    def to_representation(self, henkilo):
        data = super(TyontekijatiedotSerializer, self).to_representation(henkilo)
        if not data['tyontekijat']:
            data['tyontekijat'] = None
        return data


class VarhaiskasvatustiedotSerializer(serializers.ModelSerializer):
    lapset = OppijaLapsiSerializer(many=True, source='lapsi', read_only=True)
    voimassaolevia_varhaiskasvatuspaatoksia = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Henkilo
        fields = ('lapset', 'voimassaolevia_varhaiskasvatuspaatoksia')

    def to_representation(self, henkilo):
        data = super(VarhaiskasvatustiedotSerializer, self).to_representation(henkilo)
        if not data['lapset']:
            data['lapset'] = None
        return data

    def get_voimassaolevia_varhaiskasvatuspaatoksia(self, henkilo):
        today = datetime.date.today()
        voimassa_filter = Q(alkamis_pvm__lte=today) & (Q(paattymis_pvm__gte=today) | Q(paattymis_pvm=None))

        return Varhaiskasvatuspaatos.objects.filter(voimassa_filter & Q(lapsi__henkilo=henkilo)).distinct('id').count()
