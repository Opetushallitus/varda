from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from varda.misc import hash_string
from varda.models import (VakaJarjestaja, Toimipaikka, Maksutieto, Henkilo, Varhaiskasvatussuhde, Tyontekija,
                          Tyoskentelypaikka)


class AnonymisointiYhteenvetoHenkiloSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    henkilotunnus_unique_hash = serializers.CharField()
    syntyma_pvm = serializers.CharField()
    etunimet = serializers.CharField()
    kutsumanimi = serializers.CharField()
    sukunimi = serializers.CharField()
    katuosoite = serializers.CharField()


class AnonymisointiYhteenvetoSerializer(serializers.Serializer):
    no_of_henkilot = serializers.SerializerMethodField()
    no_of_vakajarjestajat = serializers.SerializerMethodField()
    no_of_toimipaikat = serializers.SerializerMethodField()
    no_of_varhaiskasvatussuhteet = serializers.SerializerMethodField()
    no_of_tyontekijat = serializers.SerializerMethodField()
    no_of_tyoskentelypaikat = serializers.SerializerMethodField()
    no_of_maksutiedot = serializers.SerializerMethodField()
    first_henkilo = serializers.SerializerMethodField()
    middle_henkilo = serializers.SerializerMethodField()
    last_henkilo = serializers.SerializerMethodField()

    def get_no_of_henkilot(self, request):
        return Henkilo.objects.count()

    def get_no_of_vakajarjestajat(self, request):
        return VakaJarjestaja.objects.count()

    def get_no_of_toimipaikat(self, request):
        return Toimipaikka.objects.count()

    def get_no_of_varhaiskasvatussuhteet(self, request):
        return Varhaiskasvatussuhde.objects.count()

    def get_no_of_tyontekijat(self, request):
        return Tyontekija.objects.count()

    def get_no_of_tyoskentelypaikat(self, request):
        return Tyoskentelypaikka.objects.count()

    def get_no_of_maksutiedot(self, request):
        return Maksutieto.objects.count()

    def get_henkilo_data(self, henkilo_id):
        henkilo_obj = Henkilo.objects.get(id=henkilo_id)
        syntyma_pvm = '' if henkilo_obj.syntyma_pvm is None else hash_string(henkilo_obj.syntyma_pvm.strftime('%m/%d/%Y'))
        return {
            'id': henkilo_obj.id,
            'henkilotunnus_unique_hash': henkilo_obj.henkilotunnus_unique_hash,
            'syntyma_pvm': syntyma_pvm,
            'etunimet': hash_string(henkilo_obj.etunimet),
            'kutsumanimi': hash_string(henkilo_obj.kutsumanimi),
            'sukunimi': hash_string(henkilo_obj.sukunimi),
            'katuosoite': hash_string(henkilo_obj.katuosoite)
        }

    def get_first_henkilo_id(self, request):
        """
        Query-param has been validated already in viewset.
        """
        first_henkilo_id_query_param = request.query_params.get('first_henkilo_id', None)
        if first_henkilo_id_query_param:
            return int(first_henkilo_id_query_param)
        return Henkilo.objects.order_by('id').first().id

    def get_middle_henkilo_id(self, request):
        """
        Query-param has been validated already in viewset.
        """
        middle_henkilo_id_query_param = request.query_params.get('middle_henkilo_id', None)
        if middle_henkilo_id_query_param:
            return int(middle_henkilo_id_query_param)
        number_of_henkilot = Henkilo.objects.all().count()
        return Henkilo.objects.order_by('id')[round(number_of_henkilot / 2)].id

    def get_last_henkilo_id(self, request):
        """
        Query-param has been validated already in viewset.
        """
        last_henkilo_id_query_param = request.query_params.get('last_henkilo_id', None)
        if last_henkilo_id_query_param:
            return int(last_henkilo_id_query_param)
        return Henkilo.objects.order_by('id').last().id

    @swagger_serializer_method(serializer_or_field=AnonymisointiYhteenvetoHenkiloSerializer)
    def get_first_henkilo(self, request):
        first_henkilo_id = self.get_first_henkilo_id(request)
        return self.get_henkilo_data(first_henkilo_id)

    @swagger_serializer_method(serializer_or_field=AnonymisointiYhteenvetoHenkiloSerializer)
    def get_middle_henkilo(self, request):
        middle_henkilo_id = self.get_middle_henkilo_id(request)
        return self.get_henkilo_data(middle_henkilo_id)

    @swagger_serializer_method(serializer_or_field=AnonymisointiYhteenvetoHenkiloSerializer)
    def get_last_henkilo(self, request):
        last_henkilo_id = self.get_last_henkilo_id(request)
        return self.get_henkilo_data(last_henkilo_id)
