import datetime

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Subquery, Sum
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from varda import validators
from varda.clients.allas_s3_client import Client as S3Client
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.change_type import ChangeType
from varda.enums.error_messages import ErrorMessages
from varda.excel_export import ExcelReportStatus, ExcelReportType, get_s3_object_name
from varda.misc import CustomServerErrorException, decrypt_excel_report_password, decrypt_henkilotunnus
from varda.misc_queries import get_related_object_changed_id_qs
from varda.models import (Henkilo, KieliPainotus, Lapsi, TilapainenHenkilosto, ToiminnallinenPainotus, Toimipaikka,
                          Tyontekija, VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z4_CasKayttoOikeudet,
                          Z6_LastRequest, Z6_RequestCount, Z6_RequestLog, Z6_RequestSummary, Z8_ExcelReport)
from varda.serializers import ToimipaikkaHLField, VakaJarjestajaPermissionCheckedHLField
from varda.serializers_common import OidRelatedField


class KelaEtuusmaksatusAloittaneetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='A', initial='A')
    vakasuhde_alkamis_pvm = serializers.DateField(source='alkamis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkamis_pvm']


class KelaEtuusmaksatusLopettaneetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='L', initial='L')
    vakasuhde_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusMaaraaikaisetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='M', initial='M')
    vakasuhde_alkamis_pvm = serializers.DateField(source='alkamis_pvm')
    vakasuhde_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkamis_pvm', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusKorjaustiedotSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='K', initial='K')
    vakasuhde_alkamis_pvm = serializers.SerializerMethodField()
    vakasuhde_paattymis_pvm = serializers.SerializerMethodField()
    vakasuhde_alkuperainen_alkamis_pvm = serializers.DateField(source='old_alkamis_pvm')
    vakasuhde_alkuperainen_paattymis_pvm = serializers.SerializerMethodField()

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    def get_vakasuhde_alkamis_pvm(self, data):
        if data['old_alkamis_pvm'].year == 1:
            return datetime.datetime(1, 1, 1).date()
        return data['alkamis_pvm']

    def get_vakasuhde_alkuperainen_paattymis_pvm(self, data):
        if data['old_paattymis_pvm'] is None:
            return datetime.datetime(1, 1, 1).date()
        return data['old_paattymis_pvm']

    def get_vakasuhde_paattymis_pvm(self, data):
        old_paattymis_pvm = self.get_vakasuhde_alkuperainen_paattymis_pvm(data)
        if old_paattymis_pvm.year == 1:
            return datetime.datetime(1, 1, 1).date()
        return data['paattymis_pvm']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkuperainen_alkamis_pvm',
                  'vakasuhde_alkamis_pvm', 'vakasuhde_alkuperainen_paattymis_pvm', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusKorjaustiedotPoistetutSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.ReadOnlyField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='K', initial='K')
    vakasuhde_alkamis_pvm = serializers.DateField(source='new_alkamis_pvm')
    vakasuhde_paattymis_pvm = serializers.DateField(source='new_paattymis_pvm')
    vakasuhde_alkuperainen_alkamis_pvm = serializers.DateField(source='alkamis_pvm')
    vakasuhde_alkuperainen_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, instance):
        return decrypt_henkilotunnus(instance.henkilotunnus)

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkuperainen_alkamis_pvm',
                  'vakasuhde_alkamis_pvm', 'vakasuhde_alkuperainen_paattymis_pvm', 'vakasuhde_paattymis_pvm']


class TiedonsiirtotilastoSerializer(serializers.Serializer):
    vakatoimijat = serializers.IntegerField()
    toimipaikat = serializers.IntegerField()
    vakasuhteet = serializers.IntegerField()
    vakapaatokset = serializers.IntegerField()
    lapset = serializers.IntegerField()
    maksutiedot = serializers.IntegerField()
    kielipainotukset = serializers.IntegerField()
    toiminnalliset_painotukset = serializers.IntegerField()
    paos_oikeudet = serializers.ReadOnlyField()


class AbstractErrorReportErrorsSerializer(serializers.Serializer):
    error_code = serializers.CharField()
    description = serializers.CharField()
    model_name = serializers.CharField()
    model_id_list = serializers.ListField(child=serializers.IntegerField())


class AbstractErrorReportSerializer(serializers.ModelSerializer):
    errors = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=AbstractErrorReportErrorsSerializer)
    def get_errors(self, obj):
        # This function parses the list of errors from different error attributes in the object.
        error_list = []
        for error_key, error_tuple in self.context['view'].get_error_tuples().items():
            error_attr = getattr(obj, error_key.value['error_code'], '')
            if error_attr != '':
                model_id_list = error_attr.split(',')
                error_list.append({
                    **error_key.value,
                    'model_name': error_tuple[1],
                    'model_id_list': [int(model_id) for model_id in set(model_id_list)]
                })
        return error_list


class AbstractHenkiloErrorReportSerializer(AbstractErrorReportSerializer):
    henkilo_id = serializers.IntegerField(source='henkilo.id')
    henkilo_oid = serializers.ReadOnlyField(source='henkilo.henkilo_oid')
    etunimet = serializers.ReadOnlyField(source='henkilo.etunimet')
    sukunimi = serializers.ReadOnlyField(source='henkilo.sukunimi')


class ErrorReportLapsetSerializer(AbstractHenkiloErrorReportSerializer):
    lapsi_id = serializers.IntegerField(source='id')
    oma_organisaatio_id = serializers.IntegerField(source='oma_organisaatio.id', allow_null=True)
    oma_organisaatio_oid = serializers.ReadOnlyField(source='oma_organisaatio.organisaatio_oid', allow_null=True)
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi', allow_null=True)
    paos_organisaatio_id = serializers.IntegerField(source='paos_organisaatio.id', allow_null=True)
    paos_organisaatio_oid = serializers.ReadOnlyField(source='paos_organisaatio.organisaatio_oid', allow_null=True)
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi', allow_null=True)

    class Meta:
        model = Lapsi
        fields = ('lapsi_id', 'henkilo_id', 'henkilo_oid', 'etunimet', 'sukunimi',
                  'oma_organisaatio_id', 'oma_organisaatio_oid', 'oma_organisaatio_nimi',
                  'paos_organisaatio_id', 'paos_organisaatio_oid', 'paos_organisaatio_nimi',
                  'errors')


class ErrorReportTyontekijatSerializer(AbstractHenkiloErrorReportSerializer):
    tyontekija_id = serializers.IntegerField(source='id')

    class Meta:
        model = Tyontekija
        fields = ('tyontekija_id', 'henkilo_id', 'henkilo_oid', 'etunimet', 'sukunimi', 'errors')


class ErrorReportToimipaikatSerializer(AbstractErrorReportSerializer):
    toimipaikka_id = serializers.IntegerField(source='id')

    class Meta:
        model = Toimipaikka
        fields = ('toimipaikka_id', 'nimi', 'organisaatio_oid', 'vakajarjestaja_id', 'errors')


class TiedonsiirtoListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        reverse_param = self.context['request'].query_params.get('reverse', 'False')
        if reverse_param in ('true', 'True',):
            # If reverse is activated, i.e. user has clicked to the last page (sorting by timestamp ascending),
            # reverse the list so that results in a page are ordered by timestamp descending
            data.reverse()
        return super(TiedonsiirtoListSerializer, self).to_representation(data)


class TiedonsiirtoSerializer(serializers.ModelSerializer):
    target = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.IntegerField(read_only=True, source='user.id')
    username = serializers.CharField(read_only=True, source='user.username')
    vakajarjestaja_id = serializers.IntegerField(read_only=True, source='vakajarjestaja.id')
    vakajarjestaja_name = serializers.CharField(read_only=True, source='vakajarjestaja.nimi')

    class Meta:
        model = Z6_RequestLog
        fields = ('request_url', 'request_method', 'request_body', 'response_code', 'response_body',
                  'lahdejarjestelma', 'target', 'user_id', 'username', 'vakajarjestaja_id', 'vakajarjestaja_name',
                  'timestamp')
        list_serializer_class = TiedonsiirtoListSerializer

    def get_target(self, instance):
        target_model = instance.target_model
        target_id = instance.target_id
        target = {}
        if target_model in ['Lapsi', 'Tyontekija']:
            if target_model == 'Lapsi':
                id_name = 'lapsi_id'
            else:
                id_name = 'tyontekija_id'

            try:
                target_object = apps.get_model('varda', target_model).objects.get(id=target_id)
            except (LookupError, ObjectDoesNotExist):
                # Could not find target object
                return None

            target[id_name] = instance.target_id
            target['henkilo_oid'] = target_object.henkilo.henkilo_oid
            target['etunimet'] = target_object.henkilo.etunimet
            target['sukunimi'] = target_object.henkilo.sukunimi
            return target


class TiedonsiirtoYhteenvetoSerializer(serializers.Serializer):
    date = serializers.DateField(read_only=True)
    successful = serializers.IntegerField(read_only=True)
    unsuccessful = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True, source='user__id')
    username = serializers.CharField(read_only=True, source='user__username')

    class Meta:
        list_serializer_class = TiedonsiirtoListSerializer


class ExcelReportSerializer(serializers.ModelSerializer):
    report_type = serializers.CharField()
    language = serializers.CharField()
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                            permission_groups=[Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA])
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True)
    toimipaikka = ToimipaikkaHLField(view_name='toimipaikka-detail', required=False)
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      either_required=False)
    toimipaikka_nimi = serializers.CharField(read_only=True, source='toimipaikka.nimi', allow_null=True)
    url = serializers.SerializerMethodField()
    password = serializers.SerializerMethodField()

    class Meta:
        model = Z8_ExcelReport
        exclude = ('s3_object_path',)
        read_only_fields = ('id', 'filename', 'status', 'password', 'user', 'timestamp', 's3_object_path')

    def validate_report_type(self, value):
        if value not in [report_type.value for report_type in ExcelReportType]:
            raise ValidationError([ErrorMessages.ER002.value])
        return value

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_url(self, instance):
        kwargs = self.context['view'].kwargs
        if not kwargs.get('pk', None) or instance.status != ExcelReportStatus.FINISHED.value:
            # Not retrieve or Excel report not finished
            return None

        if settings.PRODUCTION_ENV or settings.QA_ENV:
            s3_client = S3Client()
            # Creates a temporary link to the file, which is valid for 10 seconds
            return s3_client.create_presigned_url(get_s3_object_name(instance), expiration=10)
        else:
            return reverse('excel-reports-download', kwargs=kwargs, request=self.context['request'])

    def get_password(self, instance):
        return decrypt_excel_report_password(instance.password, instance.id)


class DuplicateLapsiVarhaiskasvatuspaatosSerializer(serializers.ModelSerializer):
    varhaiskasvatussuhde_list = serializers.SerializerMethodField()

    class Meta:
        model = Varhaiskasvatuspaatos
        fields = ('id', 'varhaiskasvatussuhde_list',)

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.IntegerField()))
    def get_varhaiskasvatussuhde_list(self, instance):
        return instance.varhaiskasvatussuhteet.values_list('id', flat=True)


class DuplicateLapsiLapsiSerializer(serializers.ModelSerializer):
    varhaiskasvatuspaatos_list = DuplicateLapsiVarhaiskasvatuspaatosSerializer(many=True,
                                                                               source='varhaiskasvatuspaatokset')
    maksutieto_list = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        fields = ('id', 'varhaiskasvatuspaatos_list', 'maksutieto_list',)

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.IntegerField()))
    def get_maksutieto_list(self, instance):
        maksutieto_id_set = set(instance.huoltajuussuhteet.values_list('maksutiedot__id', flat=True).distinct('id'))
        # There may be None values if Huoltajuussuhde does not have related Maksutieto objects
        maksutieto_id_set.discard(None)
        return maksutieto_id_set


class DuplicateLapsiSerializer(serializers.Serializer):
    henkilo_id = serializers.CharField(source='henkilo.id')
    etunimet = serializers.CharField(source='henkilo.etunimet')
    kutsumanimi = serializers.CharField(source='henkilo.kutsumanimi')
    sukunimi = serializers.CharField(source='henkilo.sukunimi')
    henkilo_oid = serializers.CharField(source='henkilo.henkilo_oid')
    henkilotunnus = serializers.SerializerMethodField()
    vakatoimija_id = serializers.CharField(source='vakatoimija.id')
    vakatoimija_nimi = serializers.CharField(source='vakatoimija.nimi')
    vakatoimija_oid = serializers.CharField(source='vakatoimija.organisaatio_oid')
    lapsi_list = DuplicateLapsiLapsiSerializer(many=True)

    class Meta:
        fields = ('henkilo_id', 'etunimet', 'kutsumanimi', 'sukunimi', 'henkilo_oid', 'henkilotunnus',
                  'vakatoimija_id', 'vakatoimija_nimi', 'vakatoimija_oid',)

    def to_representation(self, instance):
        instance['henkilo'] = Henkilo.objects.get(id=instance['henkilo'])
        instance['vakatoimija'] = VakaJarjestaja.objects.get(id=instance['vakatoimija'])
        instance['lapsi_list'] = instance['henkilo'].lapsi.filter(vakatoimija=instance['vakatoimija'])
        return super().to_representation(instance)

    def get_henkilotunnus(self, instance):
        try:
            decrypted_hetu = decrypt_henkilotunnus(instance['henkilo'].henkilotunnus)
            return decrypted_hetu
        except CustomServerErrorException:
            return None


class LahdejarjestelmaTransferOutageReportSerializer(serializers.Serializer):
    lahdejarjestelma = serializers.SerializerMethodField()
    last_successful = serializers.SerializerMethodField()
    last_unsuccessful = serializers.SerializerMethodField()

    def get_lahdejarjestelma(self, instance):
        return instance

    def get_last_successful(self, instance):
        return getattr(Z6_LastRequest.objects.filter(lahdejarjestelma=instance, last_successful__isnull=False)
                       .order_by('-last_successful').first(), 'last_successful', None)

    def get_last_unsuccessful(self, instance):
        return getattr(Z6_LastRequest.objects.filter(lahdejarjestelma=instance, last_unsuccessful__isnull=False)
                       .order_by('-last_unsuccessful').first(), 'last_unsuccessful', None)


class UserTransferOutageReportSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    vakajarjestaja_id = serializers.IntegerField(source='vakajarjestaja.id', allow_null=True)
    vakajarjestaja_nimi = serializers.CharField(source='vakajarjestaja.nimi', allow_null=True)
    vakajarjestaja_oid = serializers.CharField(source='vakajarjestaja.organisaatio_oid', allow_null=True)

    class Meta:
        model = Z6_LastRequest
        fields = ('user_id', 'username', 'vakajarjestaja_id', 'vakajarjestaja_nimi', 'vakajarjestaja_oid',
                  'lahdejarjestelma', 'last_successful', 'last_unsuccessful')


class RequestCountSerializer(serializers.ModelSerializer):
    successful = serializers.SerializerMethodField()

    class Meta:
        model = Z6_RequestCount
        fields = ('request_url_simple', 'request_method', 'response_code', 'count', 'successful')

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_successful(self, instance):
        return instance.response_code in SUCCESSFUL_STATUS_CODE_LIST


class RequestSummarySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', allow_null=True)
    username = serializers.CharField(source='user.username', allow_null=True)
    vakajarjestaja_id = serializers.IntegerField(source='vakajarjestaja.id', allow_null=True)
    vakajarjestaja_nimi = serializers.CharField(source='vakajarjestaja.nimi', allow_null=True)
    vakajarjestaja_oid = serializers.CharField(source='vakajarjestaja.organisaatio_oid', allow_null=True)
    ratio = serializers.FloatField()
    request_counts = serializers.SerializerMethodField()

    class Meta:
        model = Z6_RequestSummary
        fields = ('user_id', 'username', 'vakajarjestaja_id', 'vakajarjestaja_nimi', 'vakajarjestaja_oid',
                  'lahdejarjestelma', 'request_url_simple', 'summary_date', 'successful_count', 'unsuccessful_count',
                  'ratio', 'request_counts',)

    @swagger_serializer_method(serializer_or_field=RequestCountSerializer)
    def get_request_counts(self, instance):
        request_count_qs = instance.request_counts.all().order_by('-count')
        return RequestCountSerializer(request_count_qs, many=True).data


class RequestCountGroupSerializer(serializers.Serializer):
    request_url_simple = serializers.CharField()
    request_method = serializers.CharField()
    response_code = serializers.IntegerField()
    count = serializers.IntegerField(source='sum')
    successful = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=serializers.BooleanField)
    def get_successful(self, instance):
        return instance['response_code'] in SUCCESSFUL_STATUS_CODE_LIST


class RequestSummaryGroupSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source='user__id', allow_null=True)
    username = serializers.CharField(source='user__username', allow_null=True)
    vakajarjestaja_id = serializers.IntegerField(source='vakajarjestaja__id', allow_null=True)
    vakajarjestaja_nimi = serializers.CharField(source='vakajarjestaja__nimi', allow_null=True)
    vakajarjestaja_oid = serializers.CharField(source='vakajarjestaja__organisaatio_oid', allow_null=True)
    lahdejarjestelma = serializers.CharField(allow_null=True)
    request_url_simple = serializers.CharField(allow_null=True)
    ratio = serializers.FloatField()
    successful_count = serializers.IntegerField(source='successful_sum')
    unsuccessful_count = serializers.IntegerField(source='unsuccessful_sum')
    request_counts = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=RequestCountGroupSerializer)
    def get_request_counts(self, instance):
        request_count_qs = (Z6_RequestCount.objects
                            .filter(request_summary__id__in=instance['id_list'])
                            .values('request_url_simple', 'request_method', 'response_code')
                            .annotate(sum=Sum('count'))
                            .values('request_url_simple', 'request_method', 'response_code', 'sum')
                            .order_by('-sum'))
        return RequestCountGroupSerializer(request_count_qs, many=True).data


class TkBaseSerializer(serializers.Serializer):
    action = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'view' in self.context:
            # view is not present in context in Swagger
            self.datetime_gt = self.context['view'].datetime_gt
            self.datetime_lte = self.context['view'].datetime_lte
        self.secondary_muutos_pvm = None

    def get_action(self, instance):
        if instance.history_type == '-':
            return ChangeType.DELETED.value
        if self.datetime_gt < instance.luonti_pvm <= self.datetime_lte:
            return ChangeType.CREATED.value
        if self.datetime_gt < instance.muutos_pvm <= self.datetime_lte:
            return ChangeType.MODIFIED.value

        # Also verify secondary muutos_pvm (Henkilo.muutos_pvm for Lapsi, Huoltaja and Tyontekija objects)
        if self.secondary_muutos_pvm and self.datetime_gt < self.secondary_muutos_pvm <= self.datetime_lte:
            return ChangeType.MODIFIED.value

        return ChangeType.UNCHANGED.value


class TkBaseListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        # Remove instances that have been added and deleted during the time range
        datetime_gt = self.context['view'].datetime_gt
        data = [instance for instance in data
                if instance.history_type != '-' or (instance.history_type == '-' and instance.luonti_pvm < datetime_gt)]

        return super().to_representation(data)


class TkToiminnallinenPainotusSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = ToiminnallinenPainotus
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'toimintapainotus_koodi', 'alkamis_pvm', 'paattymis_pvm')


class TkKielipainotusSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = KieliPainotus
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'kielipainotus_koodi', 'alkamis_pvm', 'paattymis_pvm')


class TkToimipaikkaSerializer(TkBaseSerializer, serializers.ModelSerializer):
    toiminnalliset_painotukset = serializers.SerializerMethodField()
    kielipainotukset = serializers.SerializerMethodField()

    class Meta:
        model = Toimipaikka
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'nimi', 'organisaatio_oid', 'kunta_koodi', 'sahkopostiosoite', 'kayntiosoite',
                  'kayntiosoite_postinumero', 'kayntiosoite_postitoimipaikka', 'postiosoite', 'postinumero',
                  'postitoimipaikka', 'puhelinnumero', 'kasvatusopillinen_jarjestelma_koodi', 'toimintamuoto_koodi',
                  'asiointikieli_koodi', 'jarjestamismuoto_koodi', 'varhaiskasvatuspaikat', 'alkamis_pvm',
                  'paattymis_pvm', 'toiminnalliset_painotukset', 'kielipainotukset')

    @swagger_serializer_method(serializer_or_field=TkToiminnallinenPainotusSerializer)
    def get_toiminnalliset_painotukset(self, instance):
        painotus_qs = (ToiminnallinenPainotus.history
                       .filter(toimipaikka_id=instance.id, history_date__gt=self.datetime_gt,
                               history_date__lte=self.datetime_lte).distinct('id').order_by('id', '-history_date'))
        return TkToiminnallinenPainotusSerializer(painotus_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkKielipainotusSerializer)
    def get_kielipainotukset(self, instance):
        painotus_qs = (KieliPainotus.history
                       .filter(toimipaikka_id=instance.id, history_date__gt=self.datetime_gt,
                               history_date__lte=self.datetime_lte).distinct('id').order_by('id', '-history_date'))
        return TkKielipainotusSerializer(painotus_qs, many=True, context=self.context).data


class TkTilapainenHenkilostoSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = TilapainenHenkilosto
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'kuukausi', 'tuntimaara', 'tyontekijamaara')


class TkOrganisaatiotSerializer(TkBaseSerializer, serializers.ModelSerializer):
    toimipaikat = serializers.SerializerMethodField()
    tilapainen_henkilosto = serializers.SerializerMethodField()

    class Meta:
        model = VakaJarjestaja
        fields = ('id', 'action', 'nimi', 'organisaatio_oid', 'y_tunnus', 'kunta_koodi', 'sahkopostiosoite',
                  'kayntiosoite', 'kayntiosoite_postinumero', 'kayntiosoite_postitoimipaikka', 'postiosoite',
                  'postinumero', 'postitoimipaikka', 'puhelinnumero', 'ytjkieli', 'yritysmuoto', 'alkamis_pvm',
                  'paattymis_pvm', 'toimipaikat', 'tilapainen_henkilosto')

    @swagger_serializer_method(serializer_or_field=TkToimipaikkaSerializer)
    def get_toimipaikat(self, instance):
        id_qs = get_related_object_changed_id_qs(Toimipaikka.get_name(), self.datetime_gt, self.datetime_lte,
                                                 additional_filters={'parent_instance_id': instance.id})
        toimipaikka_qs = (Toimipaikka.history.filter(id__in=Subquery(id_qs), vakajarjestaja_id=instance.id,
                                                     history_date__lte=self.datetime_lte)
                          .distinct('id').order_by('id', '-history_date'))
        return TkToimipaikkaSerializer(toimipaikka_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkTilapainenHenkilostoSerializer)
    def get_tilapainen_henkilosto(self, instance):
        tilapainen_henkilosto_qs = (TilapainenHenkilosto.history
                                    .filter(vakajarjestaja_id=instance.id, history_date__gt=self.datetime_gt,
                                            history_date__lte=self.datetime_lte)
                                    .distinct('id').order_by('id', '-history_date'))
        return TkTilapainenHenkilostoSerializer(tilapainen_henkilosto_qs, many=True, context=self.context).data
