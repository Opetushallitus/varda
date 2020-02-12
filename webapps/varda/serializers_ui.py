from django.urls import reverse
from rest_framework import serializers

from varda.cache import caching_to_representation
from varda.models import VakaJarjestaja, Toimipaikka

"""
UI serializers
"""


class VakaJarjestajaUiSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = VakaJarjestaja
        fields = ('nimi', 'id', 'organisaatio_oid', 'kunnallinen_kytkin', 'y_tunnus')
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

    class Meta:
        model = Toimipaikka
        fields = ('lahdejarjestelma', 'nimi', 'url', 'paos_toimipaikka_kytkin', 'paos_oma_organisaatio_url',
                  'paos_organisaatio_url', 'paos_organisaatio_nimi')

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


class ToimipaikanLapsetUISerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    etunimet = serializers.ReadOnlyField()
    sukunimi = serializers.ReadOnlyField()
    henkilo_oid = serializers.ReadOnlyField()
    syntyma_pvm = serializers.ReadOnlyField()
    lapsi_id = serializers.ReadOnlyField()
    lapsi_url = serializers.SerializerMethodField()

    def get_lapsi_url(self, vakasuhde_obj):
        request = self.context.get('request')
        return request.build_absolute_uri(reverse('lapsi-detail', kwargs={'pk': vakasuhde_obj["lapsi_id"]}))
