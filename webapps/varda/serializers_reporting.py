import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.postgres.aggregates import StringAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import OuterRef, Q, Subquery, Sum
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from varda import validators
from varda.clients.allas_s3_client import Client as S3Client
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.change_type import ChangeType
from varda.enums.error_messages import ErrorMessages
from varda.excel_export import ReportStatus, ExcelReportType, get_s3_object_name
from varda.misc import CustomServerErrorException, decrypt_excel_report_password, decrypt_henkilotunnus
from varda.misc_queries import get_history_value_subquery, get_related_object_changed_id_qs
from varda.models import (Henkilo, Huoltajuussuhde, KieliPainotus, Lapsi, Maksutieto, MaksutietoHuoltajuussuhde,
                          Palvelussuhde, PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija, Tutkinto,
                          Tyoskentelypaikka, TilapainenHenkilosto, ToiminnallinenPainotus, Toimipaikka, Tyontekija,
                          Organisaatio, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, YearlyReportSummary,
                          Z10_KelaVarhaiskasvatussuhde, Z4_CasKayttoOikeudet, Z6_RequestCount, Z6_RequestLog,
                          Z6_RequestSummary, Z8_ExcelReport, Z9_RelatedObjectChanged)
from varda.serializers import ToimipaikkaHLField, OrganisaatioPermissionCheckedHLField
from varda.serializers_common import OidRelatedField


class KelaBaseSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.CharField(source='henkilo_instance.kotikunta_koodi')
    henkilotunnus = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'view' in self.context:
            # view is not present in context in Swagger
            self.datetime_lte = self.context['view'].datetime_lte

    def to_representation(self, instance):
        # Get henkilo data from history table or actual table (history is incomplete in test environments)
        henkilo = (Henkilo.history.filter(id=instance.henkilo_id, history_date__lte=self.datetime_lte).distinct('id')
                   .order_by('id', '-history_date').first())
        if not henkilo:
            henkilo = Henkilo.objects.filter(id=instance.henkilo_id).first()
        instance.henkilo_instance = henkilo

        return super().to_representation(instance)

    def get_henkilotunnus(self, instance):
        henkilotunnus = getattr(instance.henkilo_instance, 'henkilotunnus', None)
        henkilo_id = getattr(instance.henkilo_instance, 'id', None)
        return decrypt_henkilotunnus(henkilotunnus, henkilo_id=henkilo_id, raise_error=False)


class KelaEtuusmaksatusAloittaneetSerializer(KelaBaseSerializer, serializers.ModelSerializer):
    tietue = serializers.CharField(default='A', initial='A')
    vakasuhde_alkamis_pvm = serializers.DateField(source='suhde_alkamis_pvm')

    class Meta:
        model = Z10_KelaVarhaiskasvatussuhde
        fields = ('kotikunta_koodi', 'henkilotunnus', 'tietue', 'vakasuhde_alkamis_pvm')


class KelaEtuusmaksatusMaaraaikaisetSerializer(KelaBaseSerializer, serializers.ModelSerializer):
    tietue = serializers.CharField(default='M', initial='M')
    vakasuhde_alkamis_pvm = serializers.DateField(source='suhde_alkamis_pvm')
    vakasuhde_paattymis_pvm = serializers.DateField(source='suhde_paattymis_pvm')

    class Meta:
        model = Z10_KelaVarhaiskasvatussuhde
        fields = ('kotikunta_koodi', 'henkilotunnus', 'tietue', 'vakasuhde_alkamis_pvm', 'vakasuhde_paattymis_pvm')


class KelaEtuusmaksatusLopettaneetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.CharField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='L', initial='L')
    vakasuhde_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, instance):
        return decrypt_henkilotunnus(instance.henkilotunnus)

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusKorjaustiedotSerializer(KelaBaseSerializer, serializers.ModelSerializer):
    tietue = serializers.CharField(default='K', initial='K')
    vakasuhde_alkamis_pvm = serializers.SerializerMethodField()
    vakasuhde_paattymis_pvm = serializers.SerializerMethodField()
    vakasuhde_alkuperainen_alkamis_pvm = serializers.SerializerMethodField()
    vakasuhde_alkuperainen_paattymis_pvm = serializers.SerializerMethodField()

    class Meta:
        model = Z10_KelaVarhaiskasvatussuhde
        fields = ('kotikunta_koodi', 'henkilotunnus', 'tietue', 'vakasuhde_alkamis_pvm', 'vakasuhde_paattymis_pvm',
                  'vakasuhde_alkuperainen_alkamis_pvm', 'vakasuhde_alkuperainen_paattymis_pvm')

    def get_vakasuhde_alkamis_pvm(self, instance):
        is_different = instance.suhde_alkamis_pvm != instance.old_suhde_alkamis_pvm
        return instance.suhde_alkamis_pvm if is_different else datetime.date(1, 1, 1)

    def get_vakasuhde_paattymis_pvm(self, instance):
        # If paattymis_pvm has been set, it is reported in Lopettaneet, do not report change here
        is_different = (instance.suhde_paattymis_pvm != instance.old_suhde_paattymis_pvm and
                        instance.old_suhde_paattymis_pvm is not None)
        return instance.suhde_paattymis_pvm or datetime.date(1, 1, 1) if is_different else datetime.date(1, 1, 1)

    def get_vakasuhde_alkuperainen_alkamis_pvm(self, instance):
        is_different = instance.suhde_alkamis_pvm != instance.old_suhde_alkamis_pvm
        return instance.old_suhde_alkamis_pvm if is_different else datetime.date(1, 1, 1)

    def get_vakasuhde_alkuperainen_paattymis_pvm(self, instance):
        is_different = instance.suhde_paattymis_pvm != instance.old_suhde_paattymis_pvm
        return instance.old_suhde_paattymis_pvm or datetime.date(1, 1, 1) if is_different else datetime.date(1, 1, 1)


class KelaEtuusmaksatusKorjaustiedotPoistetutSerializer(KelaBaseSerializer, serializers.ModelSerializer):
    tietue = serializers.CharField(default='K', initial='K')
    vakasuhde_alkamis_pvm = serializers.DateField(default='0001-01-01')
    vakasuhde_paattymis_pvm = serializers.DateField(default='0001-01-01')
    vakasuhde_alkuperainen_alkamis_pvm = serializers.DateField(source='suhde_alkamis_pvm')
    vakasuhde_alkuperainen_paattymis_pvm = serializers.SerializerMethodField()

    class Meta:
        model = Z10_KelaVarhaiskasvatussuhde
        fields = ('kotikunta_koodi', 'henkilotunnus', 'tietue', 'vakasuhde_alkamis_pvm', 'vakasuhde_paattymis_pvm',
                  'vakasuhde_alkuperainen_alkamis_pvm', 'vakasuhde_alkuperainen_paattymis_pvm')

    def get_vakasuhde_alkuperainen_paattymis_pvm(self, instance):
        return instance.suhde_paattymis_pvm or datetime.date(1, 1, 1)


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
    def get_errors(self, instance):
        # This function parses the list of errors from different error attributes in the object.
        error_list = []
        for view_error_list in self.context['view'].get_errors():
            error_dict = view_error_list[0].value
            error_attr = (getattr(instance, error_dict['error_code'].lower(), '') or
                          getattr(instance, error_dict['error_code'], ''))
            if error_attr is not None and error_attr != '':
                model_id_list = error_attr.split(',')
                error_list.append({
                    **error_dict,
                    'model_name': view_error_list[4],
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
    vakajarjestaja = OrganisaatioPermissionCheckedHLField(view_name='organisaatio-detail', required=False,
                                                          permission_groups=[Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA])
    vakajarjestaja_oid = OidRelatedField(object_type=Organisaatio,
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
        if not kwargs.get('pk', None) or instance.status != ReportStatus.FINISHED.value:
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
        instance['vakatoimija'] = Organisaatio.objects.get(id=instance['vakatoimija'])
        instance['lapsi_list'] = instance['henkilo'].lapsi.filter(vakatoimija=instance['vakatoimija'])
        return super().to_representation(instance)

    def get_henkilotunnus(self, instance):
        try:
            decrypted_hetu = decrypt_henkilotunnus(instance['henkilo'].henkilotunnus, henkilo_id=instance['henkilo'].id)
            return decrypted_hetu
        except CustomServerErrorException:
            return None


class TransferOutageReportSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source='user__id', allow_null=True)
    username = serializers.CharField(source='user__username', allow_null=True)
    vakajarjestaja_id = serializers.IntegerField(source='vakajarjestaja__id', allow_null=True)
    vakajarjestaja_nimi = serializers.CharField(source='vakajarjestaja__nimi', allow_null=True)
    vakajarjestaja_oid = serializers.CharField(source='vakajarjestaja__organisaatio_oid', allow_null=True)
    lahdejarjestelma = serializers.CharField(allow_null=True)
    last_successful_max = serializers.DateTimeField(allow_null=True)
    last_unsuccessful_max = serializers.DateTimeField(allow_null=True)


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
        if (getattr(instance, 'last_parent_id', None) is not None and
                getattr(instance, 'previous_parent_id', None) is not None and
                instance.last_parent_id != instance.previous_parent_id):
            return ChangeType.MOVED.value
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
        model = Organisaatio
        fields = ('id', 'action', 'nimi', 'organisaatio_oid', 'y_tunnus', 'kunta_koodi', 'sahkopostiosoite',
                  'kayntiosoite', 'kayntiosoite_postinumero', 'kayntiosoite_postitoimipaikka', 'postiosoite',
                  'postinumero', 'postitoimipaikka', 'puhelinnumero', 'ytjkieli', 'yritysmuoto', 'organisaatiotyyppi',
                  'alkamis_pvm', 'paattymis_pvm', 'toimipaikat', 'tilapainen_henkilosto')

    @swagger_serializer_method(serializer_or_field=TkToimipaikkaSerializer)
    def get_toimipaikat(self, instance):
        id_qs = get_related_object_changed_id_qs(Toimipaikka.get_name(), self.datetime_gt, self.datetime_lte,
                                                 additional_filters={'parent_instance_id': instance.id})

        last_parent_subquery = get_history_value_subquery(Toimipaikka, 'vakajarjestaja_id', self.datetime_lte)
        previous_parent_subquery = get_history_value_subquery(Toimipaikka, 'vakajarjestaja_id', self.datetime_gt)
        toimipaikka_qs = (Toimipaikka.history.filter(id__in=Subquery(id_qs), vakajarjestaja_id=instance.id,
                                                     history_date__lte=self.datetime_lte)
                          .annotate(last_parent_id=last_parent_subquery, previous_parent_id=previous_parent_subquery)
                          .filter(last_parent_id=instance.id)
                          .distinct('id').order_by('id', '-history_date'))
        return TkToimipaikkaSerializer(toimipaikka_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkTilapainenHenkilostoSerializer)
    def get_tilapainen_henkilosto(self, instance):
        last_parent_subquery = get_history_value_subquery(TilapainenHenkilosto, 'vakajarjestaja_id', self.datetime_lte)
        previous_parent_subquery = get_history_value_subquery(TilapainenHenkilosto, 'vakajarjestaja_id', self.datetime_gt)
        tilapainen_henkilosto_qs = (TilapainenHenkilosto.history
                                    .filter(vakajarjestaja_id=instance.id, history_date__gt=self.datetime_gt,
                                            history_date__lte=self.datetime_lte)
                                    .annotate(last_parent_id=last_parent_subquery,
                                              previous_parent_id=previous_parent_subquery)
                                    .filter(last_parent_id=instance.id)
                                    .distinct('id').order_by('id', '-history_date'))
        return TkTilapainenHenkilostoSerializer(tilapainen_henkilosto_qs, many=True, context=self.context).data


class TkVakasuhdeSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = Varhaiskasvatussuhde
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'toimipaikka_id', 'alkamis_pvm', 'paattymis_pvm',)


class TkVakapaatosSerializer(TkBaseSerializer, serializers.ModelSerializer):
    varhaiskasvatussuhteet = serializers.SerializerMethodField()

    class Meta:
        model = Varhaiskasvatuspaatos
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'pikakasittely_kytkin', 'vuorohoito_kytkin', 'paivittainen_vaka_kytkin',
                  'kokopaivainen_vaka_kytkin', 'tilapainen_vaka_kytkin', 'jarjestamismuoto_koodi',
                  'tuntimaara_viikossa', 'hakemus_pvm', 'alkamis_pvm', 'paattymis_pvm', 'varhaiskasvatussuhteet',)

    @swagger_serializer_method(serializer_or_field=TkVakasuhdeSerializer)
    def get_varhaiskasvatussuhteet(self, instance):
        vakasuhde_qs = (Varhaiskasvatussuhde.history
                        .filter(varhaiskasvatuspaatos_id=instance.id, history_date__gt=self.datetime_gt,
                                history_date__lte=self.datetime_lte).distinct('id').order_by('id', '-history_date'))
        return TkVakasuhdeSerializer(vakasuhde_qs, many=True, context=self.context).data


class TkHuoltajuussuhdeSerializer(TkBaseSerializer, serializers.ModelSerializer):
    etunimet = serializers.CharField(source='henkilo_instance.etunimet', allow_null=True)
    sukunimi = serializers.CharField(source='henkilo_instance.sukunimi', allow_null=True)
    henkilo_oid = serializers.CharField(source='henkilo_instance.henkilo_oid', allow_null=True)
    henkilotunnus = serializers.SerializerMethodField()
    katuosoite = serializers.CharField(source='henkilo_instance.katuosoite', allow_null=True)
    postinumero = serializers.CharField(source='henkilo_instance.postinumero', allow_null=True)
    postitoimipaikka = serializers.CharField(source='henkilo_instance.postitoimipaikka', allow_null=True)

    class Meta:
        model = Huoltajuussuhde
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'etunimet', 'sukunimi', 'henkilo_oid', 'henkilotunnus', 'katuosoite',
                  'postinumero', 'postitoimipaikka',)

    def to_representation(self, instance):
        # Get henkilo data from history table or actual table (history is incomplete in test environments)
        henkilo = (Henkilo.history.filter(id=instance.henkilo_id, history_date__lte=self.datetime_lte).distinct('id')
                   .order_by('id', '-history_date').first())
        if not henkilo:
            henkilo = Henkilo.objects.filter(id=instance.henkilo_id).first()
        self.secondary_muutos_pvm = getattr(henkilo, 'muutos_pvm', None)
        instance.henkilo_instance = henkilo

        return super().to_representation(instance)

    def get_henkilotunnus(self, instance):
        henkilotunnus = getattr(instance.henkilo_instance, 'henkilotunnus', None)
        henkilo_id = getattr(instance.henkilo_instance, 'id', None)
        return decrypt_henkilotunnus(henkilotunnus, henkilo_id=henkilo_id, raise_error=False)


class TkMaksutietoHuoltajaSerializer(serializers.Serializer):
    henkilo_oid = serializers.CharField()
    henkilotunnus = serializers.CharField()


class TkMaksutietoSerializer(TkBaseSerializer, serializers.ModelSerializer):
    huoltajat = serializers.SerializerMethodField()

    class Meta:
        model = Maksutieto
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'maksun_peruste_koodi', 'perheen_koko', 'asiakasmaksu', 'palveluseteli_arvo',
                  'alkamis_pvm', 'paattymis_pvm', 'huoltajat',)

    @swagger_serializer_method(serializer_or_field=TkMaksutietoHuoltajaSerializer)
    def get_huoltajat(self, instance):
        # Get data of Henkilo objects that are related to the Maksutieto object during the time window
        # Get henkilo data from history table or actual table (history is incomplete in test environments)
        # We need to join historical tables so raw SQL query is simpler
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT DISTINCT ON(hhu.henkilo_id) hhu.henkilo_id, hhe.henkilo_oid, he.henkilo_oid, hhe.henkilotunnus, he.henkilotunnus
                FROM varda_historicalmaksutietohuoltajuussuhde hmhs
                LEFT JOIN varda_historicalhuoltajuussuhde hhs ON hmhs.huoltajuussuhde_id = hhs.id
                LEFT JOIN varda_historicalhuoltaja hhu ON hhs.huoltaja_id = hhu.id
                LEFT JOIN varda_historicalhenkilo hhe ON hhe.id = hhu.henkilo_id
                LEFT JOIN varda_henkilo he ON he.id = hhu.henkilo_id
                WHERE hmhs.maksutieto_id = %s AND hmhs.history_date <= %s
                ORDER BY hhu.henkilo_id, hhe.history_date DESC;
            ''', [instance.id, self.datetime_lte])

            huoltaja_list = [{'henkilo_oid': result[1] or result[2],
                              'henkilotunnus': (decrypt_henkilotunnus(result[3], henkilo_id=result[0], raise_error=False) or
                                                decrypt_henkilotunnus(result[4], henkilo_id=result[0], raise_error=False))}
                             for result in cursor.fetchall()]
            return TkMaksutietoHuoltajaSerializer(huoltaja_list, many=True).data


class TkVakatiedotSerializer(TkBaseSerializer, serializers.ModelSerializer):
    etunimet = serializers.CharField(source='henkilo_instance.etunimet', allow_null=True)
    sukunimi = serializers.CharField(source='henkilo_instance.sukunimi', allow_null=True)
    henkilo_oid = serializers.CharField(source='henkilo_instance.henkilo_oid', allow_null=True)
    henkilotunnus = serializers.SerializerMethodField()
    syntyma_pvm = serializers.DateField(source='henkilo_instance.syntyma_pvm', allow_null=True)
    sukupuoli_koodi = serializers.CharField(source='henkilo_instance.sukupuoli_koodi', allow_null=True)
    aidinkieli_koodi = serializers.CharField(source='henkilo_instance.aidinkieli_koodi', allow_null=True)
    kotikunta_koodi = serializers.CharField(source='henkilo_instance.kotikunta_koodi', allow_null=True)
    katuosoite = serializers.CharField(source='henkilo_instance.katuosoite', allow_null=True)
    postinumero = serializers.CharField(source='henkilo_instance.postinumero', allow_null=True)
    postitoimipaikka = serializers.CharField(source='henkilo_instance.postitoimipaikka', allow_null=True)
    varhaiskasvatuspaatokset = serializers.SerializerMethodField()
    huoltajat = serializers.SerializerMethodField()
    maksutiedot = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'etunimet', 'sukunimi', 'henkilo_oid', 'henkilotunnus', 'syntyma_pvm',
                  'sukupuoli_koodi', 'aidinkieli_koodi', 'kotikunta_koodi', 'katuosoite', 'postinumero',
                  'postitoimipaikka', 'vakatoimija_id', 'paos_kytkin', 'oma_organisaatio_id', 'paos_organisaatio_id',
                  'varhaiskasvatuspaatokset', 'huoltajat', 'maksutiedot',)

    def to_representation(self, instance):
        # Get henkilo data from history table or actual table (history is incomplete in test environments)
        henkilo = (Henkilo.history.filter(id=instance.henkilo_id, history_date__lte=self.datetime_lte)
                   .distinct('id').order_by('id', '-history_date').first())
        if not henkilo:
            henkilo = Henkilo.objects.filter(id=instance.henkilo_id).first()
        self.secondary_muutos_pvm = getattr(henkilo, 'muutos_pvm', None)
        instance.henkilo_instance = henkilo

        # varda_historicallapsi does not contain all vakatoimija_id changes because the field has been updated
        # directly in db, so try to get it from varda_lapsi table
        if not instance.paos_kytkin and not instance.vakatoimija_id:
            instance.vakatoimija_id = getattr(Lapsi.objects.filter(id=instance.id).first(), 'vakatoimija_id', None)

        lapsi = super().to_representation(instance)
        return lapsi

    def get_henkilotunnus(self, instance):
        henkilotunnus = getattr(instance.henkilo_instance, 'henkilotunnus', None)
        henkilo_id = getattr(instance.henkilo_instance, 'id', None)
        return decrypt_henkilotunnus(henkilotunnus, henkilo_id=henkilo_id, raise_error=False)

    @swagger_serializer_method(serializer_or_field=TkVakapaatosSerializer)
    def get_varhaiskasvatuspaatokset(self, instance):
        id_qs = get_related_object_changed_id_qs(Varhaiskasvatuspaatos.get_name(), self.datetime_gt,
                                                 self.datetime_lte, additional_filters={'parent_instance_id': instance.id})

        last_parent_subquery = get_history_value_subquery(Varhaiskasvatuspaatos, 'lapsi_id', self.datetime_lte)
        previous_parent_subquery = get_history_value_subquery(Varhaiskasvatuspaatos, 'lapsi_id', self.datetime_gt)
        vakapaatos_qs = (Varhaiskasvatuspaatos.history
                         .filter(id__in=Subquery(id_qs), lapsi_id=instance.id, history_date__lte=self.datetime_lte)
                         .annotate(last_parent_id=last_parent_subquery, previous_parent_id=previous_parent_subquery)
                         .filter(last_parent_id=instance.id)
                         .distinct('id').order_by('id', '-history_date'))
        return TkVakapaatosSerializer(vakapaatos_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkHuoltajuussuhdeSerializer)
    def get_huoltajat(self, instance):
        id_tuple = tuple(get_related_object_changed_id_qs(
            Lapsi.get_name(), self.datetime_gt, self.datetime_lte, return_value='trigger_instance_id',
            additional_filters={'instance_id': instance.id, 'trigger_model_name': Huoltajuussuhde.get_name()}
        )) or (-1,)

        # Get a list of Huoltajuussuhde objects that have been modified, or a related Henkilo object has been modified
        # during the time window
        # We need to join historical tables so raw SQL query is simpler (to get henkilo_id)
        huoltajuussuhde_qs = Huoltajuussuhde.history.raw('''
            SELECT DISTINCT ON (hhs.id) hhs.*, hh.henkilo_id as henkilo_id
            FROM varda_historicalhuoltajuussuhde hhs
            LEFT JOIN varda_historicalhuoltaja hh ON hh.id = hhs.huoltaja_id
            WHERE hhs.lapsi_id = %s AND hhs.id IN %s AND hhs.history_date <= %s
            ORDER BY hhs.id, hhs.history_date DESC;
        ''', [instance.id, id_tuple, self.datetime_lte])
        return TkHuoltajuussuhdeSerializer(huoltajuussuhde_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkMaksutietoSerializer)
    def get_maksutiedot(self, instance):
        id_qs = get_related_object_changed_id_qs(
            Lapsi.get_name(), self.datetime_gt, self.datetime_lte, return_value='parent_instance_id',
            additional_filters={'instance_id': instance.id,
                                'trigger_model_name': MaksutietoHuoltajuussuhde.get_name()}
        )

        last_parent_subquery = Subquery(
            Z9_RelatedObjectChanged.objects
            .filter(parent_instance_id=OuterRef('id'), parent_model_name=Maksutieto.get_name(),
                    history_type='+', changed_timestamp__lte=self.datetime_lte)
            .distinct('parent_instance_id').order_by('parent_instance_id', '-changed_timestamp')
            .values('instance_id')
        )
        previous_parent_subquery = Subquery(
            Z9_RelatedObjectChanged.objects
            .filter(parent_instance_id=OuterRef('id'), parent_model_name=Maksutieto.get_name(),
                    history_type='+', changed_timestamp__lte=self.datetime_gt)
            .distinct('parent_instance_id').order_by('parent_instance_id', '-changed_timestamp')
            .values('instance_id')
        )
        maksutieto_qs = (Maksutieto.history.filter(id__in=Subquery(id_qs), history_date__lte=self.datetime_lte)
                         .annotate(last_parent_id=last_parent_subquery, previous_parent_id=previous_parent_subquery)
                         .filter(last_parent_id=instance.id)
                         .distinct('id').order_by('id', '-history_date'))
        return TkMaksutietoSerializer(maksutieto_qs, many=True, context=self.context).data


class TkPidempiPoissaoloSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = PidempiPoissaolo
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'alkamis_pvm', 'paattymis_pvm',)


class TkTyoskentelypaikkaSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = Tyoskentelypaikka
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'toimipaikka_id', 'tehtavanimike_koodi', 'kelpoisuus_kytkin',
                  'kiertava_tyontekija_kytkin', 'alkamis_pvm', 'paattymis_pvm',)


class TkPalvelussuhdeSerializer(TkBaseSerializer, serializers.ModelSerializer):
    tyoskentelypaikat = serializers.SerializerMethodField()
    pidemmat_poissaolot = serializers.SerializerMethodField()

    class Meta:
        model = Palvelussuhde
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'tyosuhde_koodi', 'tyoaika_koodi', 'tutkinto_koodi', 'tyoaika_viikossa',
                  'alkamis_pvm', 'paattymis_pvm', 'tyoskentelypaikat', 'pidemmat_poissaolot',)

    @swagger_serializer_method(serializer_or_field=TkTyoskentelypaikkaSerializer)
    def get_tyoskentelypaikat(self, instance):
        tyoskentelypaikka_qs = (Tyoskentelypaikka.history
                                .filter(palvelussuhde_id=instance.id, history_date__gt=self.datetime_gt,
                                        history_date__lte=self.datetime_lte)
                                .distinct('id').order_by('id', '-history_date'))
        return TkTyoskentelypaikkaSerializer(tyoskentelypaikka_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkPidempiPoissaoloSerializer)
    def get_pidemmat_poissaolot(self, instance):
        pidempi_poissaolo_qs = (PidempiPoissaolo.history
                                .filter(palvelussuhde_id=instance.id, history_date__gt=self.datetime_gt,
                                        history_date__lte=self.datetime_lte)
                                .distinct('id').order_by('id', '-history_date'))
        return TkPidempiPoissaoloSerializer(pidempi_poissaolo_qs, many=True, context=self.context).data


class TkTutkintoSerializer(TkBaseSerializer, serializers.ModelSerializer):
    class Meta:
        model = Tutkinto
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'tutkinto_koodi',)


class TkTaydennyskoulutusSerializer(TkBaseSerializer, serializers.ModelSerializer):
    tehtavanimikkeet = serializers.SerializerMethodField()

    class Meta:
        model = Taydennyskoulutus
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'nimi', 'suoritus_pvm', 'koulutuspaivia', 'tehtavanimikkeet',)

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_tehtavanimikkeet(self, instance):
        # Get list of tehtavanimikkeet that are active during the time window
        # QuerySet may contain duplicates and distinct + annotate is not supported so use set
        return set(TaydennyskoulutusTyontekija.history.values('id')
                   .filter(taydennyskoulutus_id=instance.id, tyontekija_id=self.context['tyontekija_id'],
                           history_date__lte=self.datetime_lte)
                   .annotate(history_type_list=StringAgg('history_type', ','))
                   .filter(~(Q(history_type_list__contains='+') & Q(history_type_list__contains='-')))
                   .order_by('id').values_list('tehtavanimike_koodi', flat=True))


class TkHenkilostotiedotSerializer(TkBaseSerializer, serializers.ModelSerializer):
    etunimet = serializers.CharField(source='henkilo_instance.etunimet', allow_null=True)
    sukunimi = serializers.CharField(source='henkilo_instance.sukunimi', allow_null=True)
    henkilo_oid = serializers.CharField(source='henkilo_instance.henkilo_oid', allow_null=True)
    henkilotunnus = serializers.SerializerMethodField()
    syntyma_pvm = serializers.DateField(source='henkilo_instance.syntyma_pvm', allow_null=True)
    aidinkieli_koodi = serializers.CharField(source='henkilo_instance.aidinkieli_koodi', allow_null=True)
    sukupuoli_koodi = serializers.CharField(source='henkilo_instance.sukupuoli_koodi', allow_null=True)
    tutkinnot = serializers.SerializerMethodField()
    palvelussuhteet = serializers.SerializerMethodField()
    taydennyskoulutukset = serializers.SerializerMethodField()

    class Meta:
        model = Tyontekija
        list_serializer_class = TkBaseListSerializer
        fields = ('id', 'action', 'etunimet', 'sukunimi', 'henkilo_oid', 'henkilotunnus', 'syntyma_pvm',
                  'aidinkieli_koodi', 'sukupuoli_koodi', 'vakajarjestaja_id', 'tutkinnot', 'palvelussuhteet',
                  'taydennyskoulutukset',)

    def to_representation(self, instance):
        # Get henkilo data from history table or actual table (history is incomplete in test environments)
        henkilo = (Henkilo.history.filter(id=instance.henkilo_id, history_date__lte=self.datetime_lte)
                   .distinct('id').order_by('id', '-history_date').first())
        if not henkilo:
            henkilo = Henkilo.objects.filter(id=instance.henkilo_id).first()
        instance.henkilo_instance = henkilo
        self.secondary_muutos_pvm = getattr(henkilo, 'muutos_pvm', None)
        self.context['tyontekija_id'] = instance.id

        return super().to_representation(instance)

    def get_henkilotunnus(self, instance):
        henkilotunnus = getattr(instance.henkilo_instance, 'henkilotunnus', None)
        henkilo_id = getattr(instance.henkilo_instance, 'id', None)
        return decrypt_henkilotunnus(henkilotunnus, henkilo_id=henkilo_id, raise_error=False)

    @swagger_serializer_method(serializer_or_field=TkTutkintoSerializer)
    def get_tutkinnot(self, instance):
        last_parent_subquery = get_history_value_subquery(Tutkinto, 'vakajarjestaja_id', self.datetime_lte)
        previous_parent_subquery = get_history_value_subquery(Tutkinto, 'vakajarjestaja_id', self.datetime_gt)
        tutkinto_qs = (Tutkinto.history
                       .filter(henkilo_id=instance.henkilo_id, vakajarjestaja_id=instance.vakajarjestaja_id,
                               history_date__gt=self.datetime_gt, history_date__lte=self.datetime_lte)
                       .annotate(last_parent_id=last_parent_subquery, previous_parent_id=previous_parent_subquery)
                       .filter(last_parent_id=instance.vakajarjestaja_id)
                       .distinct('id').order_by('id', '-history_date'))
        return TkTutkintoSerializer(tutkinto_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkPalvelussuhdeSerializer)
    def get_palvelussuhteet(self, instance):
        id_qs = get_related_object_changed_id_qs(Palvelussuhde.get_name(), self.datetime_gt,
                                                 self.datetime_lte, additional_filters={'parent_instance_id': instance.id})

        last_parent_subquery = get_history_value_subquery(Palvelussuhde, 'tyontekija_id', self.datetime_lte)
        previous_parent_subquery = get_history_value_subquery(Palvelussuhde, 'tyontekija_id', self.datetime_gt)
        palvelussuhde_qs = (Palvelussuhde.history
                            .filter(id__in=Subquery(id_qs), tyontekija_id=instance.id,
                                    history_date__lte=self.datetime_lte)
                            .annotate(last_parent_id=last_parent_subquery, previous_parent_id=previous_parent_subquery)
                            .filter(last_parent_id=instance.id)
                            .distinct('id').order_by('id', '-history_date'))
        return TkPalvelussuhdeSerializer(palvelussuhde_qs, many=True, context=self.context).data

    @swagger_serializer_method(serializer_or_field=TkTaydennyskoulutusSerializer)
    def get_taydennyskoulutukset(self, instance):
        id_qs = get_related_object_changed_id_qs(
            Tyontekija.get_name(), self.datetime_gt, self.datetime_lte, return_value='parent_instance_id',
            additional_filters={'instance_id': instance.id,
                                'trigger_model_name': TaydennyskoulutusTyontekija.get_name()}
        )
        taydennyskoulutus_qs = (Taydennyskoulutus.history
                                .filter(id__in=Subquery(id_qs), history_date__lte=self.datetime_lte)
                                .distinct('id').order_by('id', '-history_date'))
        return TkTaydennyskoulutusSerializer(taydennyskoulutus_qs, many=True, context=self.context).data


class YearlyReportingDataSummarySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    vakajarjestaja = serializers.ReadOnlyField()
    vakajarjestaja_input = serializers.CharField(required=True, write_only=True)
    status = serializers.CharField(read_only=True)
    tilasto_pvm = serializers.DateField(read_only=True)
    tilastovuosi = serializers.IntegerField(write_only=True, required=False, allow_null=False)

    class Meta:
        model = YearlyReportSummary
        read_only_fields = ('vakajarjestaja_count', 'vakajarjestaja_is_active', 'toimipaikka_count', 'toimintapainotus_count',
                            'kielipainotus_count', 'yhteensa_henkilo_count', 'yhteensa_lapsi_count', 'yhteensa_varhaiskasvatussuhde_count',
                            'yhteensa_varhaiskasvatuspaatos_count', 'yhteensa_vuorohoito_count', 'oma_henkilo_count',
                            'oma_lapsi_count', 'oma_varhaiskasvatussuhde_count', 'oma_varhaiskasvatuspaatos_count',
                            'oma_vuorohoito_count', 'paos_henkilo_count', 'paos_lapsi_count', 'paos_varhaiskasvatussuhde_count',
                            'paos_varhaiskasvatuspaatos_count', 'paos_vuorohoito_count', 'yhteensa_maksutieto_count',
                            'yhteensa_maksutieto_mp01_count', 'yhteensa_maksutieto_mp02_count', 'yhteensa_maksutieto_mp03_count',
                            'oma_maksutieto_count', 'oma_maksutieto_mp01_count', 'oma_maksutieto_mp02_count', 'oma_maksutieto_mp03_count',
                            'paos_maksutieto_count', 'paos_maksutieto_mp01_count', 'paos_maksutieto_mp02_count', 'paos_maksutieto_mp03_count')
        exclude = ('luonti_pvm', 'muutos_pvm')
