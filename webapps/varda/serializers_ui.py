from operator import itemgetter

from django.db.models import Q
from django.urls import reverse
from drf_yasg.utils import swagger_serializer_method
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from varda.cache import caching_to_representation
from varda.models import (PaosOikeus, PaosToiminta, Toimipaikka, VakaJarjestaja, Henkilo, Tyontekija, Tyoskentelypaikka,
                          Lapsi, Varhaiskasvatussuhde)
from varda.permissions import get_taydennyskoulutus_tyontekija_group_organisaatio_oids, get_toimipaikat_group_has_access

"""
UI serializers
"""


class VakaJarjestajaUiSerializer(serializers.HyperlinkedModelSerializer):
    kunnallinen_kytkin = serializers.BooleanField(read_only=True)

    class Meta:
        model = VakaJarjestaja
        fields = ('nimi', 'id', 'url', 'organisaatio_oid', 'kunnallinen_kytkin', 'y_tunnus')
        read_only_fields = ('nimi', 'id', 'organisaatio_oid', 'kunnallinen_kytkin', 'y_tunnus')

    @caching_to_representation('vakajarjestaja-ui')
    def to_representation(self, instance):
        return super(VakaJarjestajaUiSerializer, self).to_representation(instance)


class ToimipaikkaUiSerializer(serializers.HyperlinkedModelSerializer):
    nimi_original = serializers.ReadOnlyField(source='nimi')
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
        fields = ('hallinnointijarjestelma', 'id', 'nimi_original', 'nimi', 'url', 'organisaatio_oid',
                  'paos_toimipaikka_kytkin', 'paos_oma_organisaatio_url', 'paos_organisaatio_url',
                  'paos_organisaatio_nimi', 'paos_organisaatio_oid', 'paos_tallentaja_organisaatio_id_list',)

    def get_nimi(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj['nimi'] + ', ' + toimipaikka_obj['vakajarjestaja__nimi'].upper()
        else:
            return toimipaikka_obj['nimi']

    def get_url(self, toimipaikka_obj):
        request = self.context.get('request')
        return request.build_absolute_uri(reverse('toimipaikka-detail', kwargs={'pk': toimipaikka_obj['id']}))

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_paos_toimipaikka_kytkin(self, toimipaikka_obj):
        return not int(self.context.get('vakajarjestaja_pk')) == toimipaikka_obj['vakajarjestaja__id']

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_oma_organisaatio_url(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            request = self.context.get('request')
            return request.build_absolute_uri(reverse('vakajarjestaja-detail',
                                                      kwargs={'pk': int(self.context.get('vakajarjestaja_pk'))}))
        else:
            return ''

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_organisaatio_url(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            request = self.context.get('request')
            return request.build_absolute_uri(reverse('vakajarjestaja-detail',
                                                      kwargs={'pk': toimipaikka_obj['vakajarjestaja__id']}))
        else:
            return ''

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_organisaatio_nimi(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj['vakajarjestaja__nimi']
        else:
            return ''

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_paos_organisaatio_oid(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj['vakajarjestaja__organisaatio_oid']
        else:
            return ''

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.IntegerField()))
    def get_paos_tallentaja_organisaatio_id_list(self, toimipaikka_obj):
        # Haetaan kaikki vakajärjestäjät joilla tähän toimipaikkaan tallennusoikeus
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            oma_organisaatio_id_list = (PaosToiminta.objects.filter(Q(voimassa_kytkin=True) &
                                                                    Q(paos_toimipaikka=toimipaikka_obj['id']))
                                        .values_list('oma_organisaatio__id', flat=True))

            return (PaosOikeus.objects.filter(Q(voimassa_kytkin=True) &
                                              Q(jarjestaja_kunta_organisaatio__in=oma_organisaatio_id_list) &
                                              Q(tuottaja_organisaatio=toimipaikka_obj['vakajarjestaja__id']))
                    .values_list('tallentaja_organisaatio__id', flat=True))
        else:
            return []


class UiLapsiSerializer(serializers.HyperlinkedModelSerializer):
    etunimet = serializers.ReadOnlyField(source='henkilo.etunimet')
    sukunimi = serializers.ReadOnlyField(source='henkilo.sukunimi')
    henkilo_oid = serializers.ReadOnlyField(source='henkilo.henkilo_oid')
    syntyma_pvm = serializers.ReadOnlyField(source='henkilo.syntyma_pvm')
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi')
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')
    lapsi_id = serializers.IntegerField(read_only=True, source='id')
    lapsi_url = serializers.HyperlinkedRelatedField(view_name='lapsi-detail', source='id', read_only=True)

    class Meta:
        model = Lapsi
        fields = ('etunimet', 'sukunimi', 'henkilo_oid', 'syntyma_pvm', 'oma_organisaatio_nimi',
                  'paos_organisaatio_nimi', 'lapsi_id', 'lapsi_url')


class PermissionCheckedTyoskentelypaikkaUiListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        super(PermissionCheckedTyoskentelypaikkaUiListSerializer, self).update(instance, validated_data)

    def to_representation(self, tyoskentelypaikat):
        """
        Filter tyontekijat user has no permission.
        :param tyoskentelypaikat: Queryset of tyontekijat
        :return: Dict of serialized tyontekijat
        """
        user = self.context['request'].user
        vakajarjestaja_pk = self.context['view'].kwargs['pk']
        organisaatio_oids = get_taydennyskoulutus_tyontekija_group_organisaatio_oids(user)
        filter_condition = Q(palvelussuhde__tyontekija__vakajarjestaja=vakajarjestaja_pk)
        if not user.is_superuser:
            filter_condition = (Q(palvelussuhde__tyontekija__vakajarjestaja__organisaatio_oid__in=organisaatio_oids) |
                                Q(toimipaikka__organisaatio_oid__in=organisaatio_oids))
            # user with tyontekija toimipaikka permissions might have object level permissions to tyontekijat without tyoskentelypaikka
            if get_toimipaikat_group_has_access(user, vakajarjestaja_pk, 'HENKILOSTO_TYONTEKIJA_').exists():
                tyontekijat_object_level_permission = get_objects_for_user(user, 'view_tyontekija', klass=Tyontekija, accept_global_perms=False)
                filter_condition = filter_condition | Q(palvelussuhde__tyontekija__in=tyontekijat_object_level_permission)
        tyoskentelypaikat = tyoskentelypaikat.filter(filter_condition).order_by('-alkamis_pvm')
        return super(PermissionCheckedTyoskentelypaikkaUiListSerializer, self).to_representation(tyoskentelypaikat)


class TyoskentelypaikatUiSerializer(serializers.HyperlinkedModelSerializer):
    toimipaikka_oid = serializers.CharField(source='toimipaikka.organisaatio_oid', allow_null=True)
    toimipaikka_nimi = serializers.CharField(source='toimipaikka.nimi', allow_null=True)

    class Meta:
        model = Tyoskentelypaikka
        fields = ('id', 'url', 'toimipaikka_oid', 'toimipaikka_nimi', 'kiertava_tyontekija_kytkin', 'tehtavanimike_koodi', 'alkamis_pvm')
        list_serializer_class = PermissionCheckedTyoskentelypaikkaUiListSerializer


class TyontekijatUiListSerializer(serializers.ListSerializer):
    def to_representation(self, tyontekijat):
        vakajarjestaja_pk = self.context['view'].kwargs['pk']
        return super(TyontekijatUiListSerializer, self).to_representation(tyontekijat.filter(vakajarjestaja=vakajarjestaja_pk))


class TyontekijatUiSerializer(serializers.HyperlinkedModelSerializer):
    tyoskentelypaikat = serializers.SerializerMethodField()

    class Meta:
        model = Tyontekija
        fields = ('id', 'url', 'tyoskentelypaikat')
        list_serializer_class = TyontekijatUiListSerializer

    @swagger_serializer_method(serializer_or_field=TyoskentelypaikatUiSerializer)
    def get_tyoskentelypaikat(self, tyontekija):
        tyoskentelypaikat = Tyoskentelypaikka.objects.filter(palvelussuhde__in=tyontekija.palvelussuhteet.all())
        return TyoskentelypaikatUiSerializer(instance=tyoskentelypaikat, many=True, context=self.context).data


class TyontekijaHenkiloUiSerializer(serializers.HyperlinkedModelSerializer):
    tyontekijat = TyontekijatUiSerializer(many=True)

    class Meta:
        model = Henkilo
        fields = ('id', 'url', 'henkilo_oid', 'etunimet', 'sukunimi', 'tyontekijat')


class LapsihakuToimipaikkaUiSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Toimipaikka
        fields = ('id', 'url', 'organisaatio_oid', 'nimi', )


class LapsihakuLapsetUiListSerializer(serializers.ListSerializer):

    def update(self, instance, validated_data):
        return super(LapsihakuLapsetUiListSerializer, self).update(instance, validated_data)

    def to_representation(self, lapsi_list_data):
        view = self.context['view']
        vakajarjestaja_pk = view.kwargs['pk']
        query_params = view.request.query_params

        # We use same conditions as when doing the initial henkilo filtering.
        filter_condition = view.get_lapsi_list_filter_conditions(vakajarjestaja_pk, query_params, permission_context=self.context)
        filtered_lapsi_list_data = lapsi_list_data.filter(filter_condition).distinct()
        return super(LapsihakuLapsetUiListSerializer, self).to_representation(filtered_lapsi_list_data)


class LapsihakuLapsetUiSerializer(serializers.HyperlinkedModelSerializer):
    vakatoimija_oid = serializers.CharField(source='vakatoimija.organisaatio_oid', allow_null=True)
    vakatoimija_nimi = serializers.CharField(source='vakatoimija.nimi', allow_null=True)
    oma_organisaatio_oid = serializers.CharField(source='oma_organisaatio.organisaatio_oid', allow_null=True)
    oma_organisaatio_nimi = serializers.CharField(source='oma_organisaatio.nimi', allow_null=True)
    paos_organisaatio_oid = serializers.CharField(source='paos_organisaatio.organisaatio_oid', allow_null=True)
    paos_organisaatio_nimi = serializers.CharField(source='paos_organisaatio.nimi', allow_null=True)
    tallentaja_organisaatio_oid = serializers.SerializerMethodField(allow_null=True)
    toimipaikat = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        fields = ('id', 'url', 'vakatoimija_oid', 'vakatoimija_nimi', 'oma_organisaatio_oid', 'oma_organisaatio_nimi',
                  'paos_organisaatio_oid', 'paos_organisaatio_nimi', 'tallentaja_organisaatio_oid', 'toimipaikat')
        list_serializer_class = LapsihakuLapsetUiListSerializer

    @swagger_serializer_method(serializer_or_field=LapsihakuToimipaikkaUiSerializer)
    def get_toimipaikat(self, lapsi):
        permission_context = self.context
        vakasuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__in=lapsi.varhaiskasvatuspaatokset.all())
        toimipaikat_condition = Q(varhaiskasvatussuhteet__in=vakasuhteet)
        # Since we are flattening these here manually it breaks nested filtering possibility in LapsihakuUiFilter
        toimipaikka_oid = self.context['request'].query_params.get('toimipaikka_oid')
        if toimipaikka_oid:
            toimipaikat_condition = toimipaikat_condition & Q(organisaatio_oid=toimipaikka_oid)
        toimipaikka_id = self.context['request'].query_params.get('toimipaikka_id')
        if toimipaikka_id:
            toimipaikat_condition = toimipaikat_condition & Q(id=toimipaikka_id)
        toimipaikat = Toimipaikka.objects.filter(toimipaikat_condition).distinct()
        is_superuser, vakajarjestaja_oid, user_organisaatio_oids = itemgetter('is_superuser', 'vakajarjestaja_oid', 'user_organisaatio_oids')(permission_context)
        if not is_superuser and vakajarjestaja_oid not in user_organisaatio_oids:
            toimipaikka_oids = permission_context['toimipaikka_oids']
            toimipaikat = toimipaikat.filter(organisaatio_oid__in=toimipaikka_oids)
        return LapsihakuToimipaikkaUiSerializer(instance=toimipaikat, many=True, context=self.context).data

    def get_tallentaja_organisaatio_oid(self, lapsi):
        if lapsi.oma_organisaatio and lapsi.paos_organisaatio:
            paos_oikeus = PaosOikeus.objects.filter(jarjestaja_kunta_organisaatio=lapsi.oma_organisaatio,
                                                    tuottaja_organisaatio=lapsi.paos_organisaatio,
                                                    voimassa_kytkin=True).first()
            if paos_oikeus:
                return paos_oikeus.tallentaja_organisaatio.organisaatio_oid
        return None


class LapsihakuHenkiloUiSerializer(serializers.HyperlinkedModelSerializer):
    lapset = LapsihakuLapsetUiSerializer(many=True, source='lapsi')

    class Meta:
        model = Henkilo
        fields = ('id', 'url', 'henkilo_oid', 'etunimet', 'sukunimi', 'lapset')


class UiTyontekijaSerializer(serializers.HyperlinkedModelSerializer):
    etunimet = serializers.ReadOnlyField(source='henkilo.etunimet')
    sukunimi = serializers.ReadOnlyField(source='henkilo.sukunimi')
    henkilo_oid = serializers.ReadOnlyField(source='henkilo.henkilo_oid')
    vakajarjestaja_nimi = serializers.ReadOnlyField(source='vakajarjestaja.nimi')
    tyontekija_id = serializers.IntegerField(read_only=True, source='id')
    tyontekija_url = serializers.HyperlinkedRelatedField(view_name='tyontekija-detail', source='id', read_only=True)

    class Meta:
        model = Tyontekija
        fields = ('etunimet', 'sukunimi', 'henkilo_oid', 'vakajarjestaja_nimi', 'tyontekija_id', 'tyontekija_url')
