from django.db.models import Q
from django.urls import reverse
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from varda.cache import caching_to_representation
from varda.models import PaosOikeus, PaosToiminta, Toimipaikka, VakaJarjestaja, Henkilo, Tyontekija, Tyoskentelypaikka
from varda.permissions import get_taydennyskoulutus_tyontekija_group_organisaatio_oids, is_toimipaikka_access_for_group

"""
UI serializers
"""


class VakaJarjestajaUiSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = VakaJarjestaja
        fields = ('nimi', 'id', 'url', 'organisaatio_oid', 'kunnallinen_kytkin', 'y_tunnus')
        read_only_fields = ('nimi', 'id', 'organisaatio_oid', 'kunnallinen_kytkin', 'y_tunnus')

    @caching_to_representation('vakajarjestaja-ui')
    def to_representation(self, instance):
        return super(VakaJarjestajaUiSerializer, self).to_representation(instance)


class ToimipaikkaUiSerializer(serializers.HyperlinkedModelSerializer):
    nimi = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    paos_toimipaikka_kytkin = serializers.SerializerMethodField()
    paos_oma_organisaatio_url = serializers.SerializerMethodField()
    paos_organisaatio_url = serializers.SerializerMethodField()
    paos_organisaatio_nimi = serializers.SerializerMethodField()
    paos_tallentaja_organisaatio_id_list = serializers.SerializerMethodField()

    class Meta:
        model = Toimipaikka
        fields = ('hallinnointijarjestelma', 'id', 'nimi', 'url', 'organisaatio_oid', 'paos_toimipaikka_kytkin', 'paos_oma_organisaatio_url',
                  'paos_organisaatio_url', 'paos_organisaatio_nimi', 'paos_tallentaja_organisaatio_id_list')

    def get_nimi(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj['nimi'] + ', ' + toimipaikka_obj['vakajarjestaja__nimi'].upper()
        else:
            return toimipaikka_obj['nimi']

    def get_url(self, toimipaikka_obj):
        request = self.context.get('request')
        return request.build_absolute_uri(reverse('toimipaikka-detail', kwargs={'pk': toimipaikka_obj['id']}))

    def get_paos_toimipaikka_kytkin(self, toimipaikka_obj):
        return not int(self.context.get('vakajarjestaja_pk')) == toimipaikka_obj['vakajarjestaja__id']

    def get_paos_oma_organisaatio_url(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            request = self.context.get('request')
            return request.build_absolute_uri(reverse('vakajarjestaja-detail',
                                                      kwargs={'pk': int(self.context.get('vakajarjestaja_pk'))}))
        else:
            return ''

    def get_paos_organisaatio_url(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            request = self.context.get('request')
            return request.build_absolute_uri(reverse('vakajarjestaja-detail',
                                                      kwargs={'pk': toimipaikka_obj['vakajarjestaja__id']}))
        else:
            return ''

    def get_paos_organisaatio_nimi(self, toimipaikka_obj):
        if self.get_paos_toimipaikka_kytkin(toimipaikka_obj):
            return toimipaikka_obj['vakajarjestaja__nimi']
        else:
            return ''

    # Haetaan kaikki vakajärjestäjät joilla tähän toimipaikkaan tallennusoikeus
    def get_paos_tallentaja_organisaatio_id_list(self, toimipaikka_obj):
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


class ToimipaikanLapsetUISerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    etunimet = serializers.ReadOnlyField()
    sukunimi = serializers.ReadOnlyField()
    henkilo_oid = serializers.ReadOnlyField()
    syntyma_pvm = serializers.ReadOnlyField()
    oma_organisaatio_nimi = serializers.ReadOnlyField()
    paos_organisaatio_nimi = serializers.ReadOnlyField()
    lapsi_id = serializers.ReadOnlyField()
    lapsi_url = serializers.SerializerMethodField()

    def get_lapsi_url(self, vakasuhde_obj):
        request = self.context.get('request')
        return request.build_absolute_uri(reverse('lapsi-detail', kwargs={'pk': vakasuhde_obj["lapsi_id"]}))


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
        filter_condition = (Q(toimipaikka__vakajarjestaja__organisaatio_oid__in=organisaatio_oids) |
                            Q(toimipaikka__organisaatio_oid__in=organisaatio_oids))
        # user with tyontekija toimipaikka permissions might have object level permissions to tyontekijat without tyoskentelypaikka
        if is_toimipaikka_access_for_group(user, vakajarjestaja_pk, 'HENKILOSTO_TYONTEKIJA_'):
            tyontekijat_object_level_permission = get_objects_for_user(user, 'view_tyontekija', klass=Tyontekija, accept_global_perms=False)
            filter_condition = filter_condition | Q(palvelussuhde__tyontekija__in=tyontekijat_object_level_permission)
        tyoskentelypaikat = tyoskentelypaikat.filter(filter_condition).order_by('-alkamis_pvm')
        return super(PermissionCheckedTyoskentelypaikkaUiListSerializer, self).to_representation(tyoskentelypaikat)


class TyoskentelypaikatUiSerializer(serializers.HyperlinkedModelSerializer):
    toimipaikka_oid = serializers.CharField(source='toimipaikka.organisaatio_oid')
    toimipaikka_nimi = serializers.CharField(source='toimipaikka.nimi')

    class Meta:
        model = Tyoskentelypaikka
        fields = ('id', 'url', 'toimipaikka_oid', 'toimipaikka_nimi', 'tehtavanimike_koodi', 'alkamis_pvm')
        list_serializer_class = PermissionCheckedTyoskentelypaikkaUiListSerializer


class TyontekijatUiSerializer(serializers.HyperlinkedModelSerializer):
    tyoskentelypaikat = serializers.SerializerMethodField()

    class Meta:
        model = Tyontekija
        fields = ('id', 'url', 'tyoskentelypaikat')

    def get_tyoskentelypaikat(self, tyontekija):
        tyoskentelypaikat = Tyoskentelypaikka.objects.filter(palvelussuhde__in=tyontekija.palvelussuhteet.all())
        return TyoskentelypaikatUiSerializer(instance=tyoskentelypaikat, many=True, context=self.context).data


class TyontekijaUiSerializer(serializers.HyperlinkedModelSerializer):
    tyontekijat = TyontekijatUiSerializer(many=True)

    class Meta:
        model = Henkilo
        fields = ('id', 'url', 'henkilo_oid', 'etunimet', 'sukunimi', 'tyontekijat')
