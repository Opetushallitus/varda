import datetime
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.reverse import reverse

from varda import validators
from varda.clients.allas_s3_client import Client as S3Client
from varda.excel_export import ExcelReportStatus, get_s3_object_name
from varda.models import (Varhaiskasvatussuhde, Lapsi, Tyontekija, Z6_RequestLog, Z8_ExcelReport, Toimipaikka,
                          Z4_CasKayttoOikeudet, VakaJarjestaja, Henkilo, Varhaiskasvatuspaatos, Z6_LastRequest)
from varda.misc import decrypt_henkilotunnus, decrypt_excel_report_password, CustomServerErrorException
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


class AbstractErrorReportSerializer(serializers.ModelSerializer):
    errors = serializers.SerializerMethodField()

    def get_errors(self, obj):
        """
        This function parses the list of errors from different error attributes in the object.
        :param obj: object with annotated errors
        :return: list of errors
        """
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
    henkilo_id = serializers.ReadOnlyField(source='henkilo.id')
    henkilo_oid = serializers.ReadOnlyField(source='henkilo.henkilo_oid')
    etunimet = serializers.ReadOnlyField(source='henkilo.etunimet')
    sukunimi = serializers.ReadOnlyField(source='henkilo.sukunimi')


class ErrorReportLapsetSerializer(AbstractHenkiloErrorReportSerializer):
    lapsi_id = serializers.ReadOnlyField(source='id')
    oma_organisaatio_id = serializers.ReadOnlyField(source='oma_organisaatio.id')
    oma_organisaatio_oid = serializers.ReadOnlyField(source='oma_organisaatio.organisaatio_oid')
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi')
    paos_organisaatio_id = serializers.ReadOnlyField(source='paos_organisaatio.id')
    paos_organisaatio_oid = serializers.ReadOnlyField(source='paos_organisaatio.organisaatio_oid')
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')

    class Meta:
        model = Lapsi
        fields = ('lapsi_id', 'henkilo_id', 'henkilo_oid', 'etunimet', 'sukunimi',
                  'oma_organisaatio_id', 'oma_organisaatio_oid', 'oma_organisaatio_nimi',
                  'paos_organisaatio_id', 'paos_organisaatio_oid', 'paos_organisaatio_nimi',
                  'errors')


class ErrorReportTyontekijatSerializer(AbstractHenkiloErrorReportSerializer):
    tyontekija_id = serializers.ReadOnlyField(source='id')

    class Meta:
        model = Tyontekija
        fields = ('tyontekija_id', 'henkilo_id', 'henkilo_oid', 'etunimet', 'sukunimi', 'errors')


class ErrorReportToimipaikatSerializer(AbstractErrorReportSerializer):
    toimipaikka_id = serializers.ReadOnlyField(source='id')

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
    toimipaikka_nimi = serializers.CharField(read_only=True, source='toimipaikka.nimi')
    url = serializers.SerializerMethodField()

    class Meta:
        model = Z8_ExcelReport
        exclude = ('password', 's3_object_path',)
        read_only_fields = ('id', 'filename', 'status', 'password', 'user', 'timestamp', 's3_object_path')

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
        # TODO: If encryption support is added (https://jira.eduuni.fi/browse/OPHVARDA-2221), use this function to
        #       send password with the report data
        return decrypt_excel_report_password(instance.password, instance.id)


class DuplicateLapsiVarhaiskasvatuspaatosSerializer(serializers.ModelSerializer):
    varhaiskasvatussuhde_list = serializers.SerializerMethodField()

    class Meta:
        model = Varhaiskasvatuspaatos
        fields = ('id', 'varhaiskasvatussuhde_list',)

    def get_varhaiskasvatussuhde_list(self, instance):
        return instance.varhaiskasvatussuhteet.values_list('id', flat=True)


class DuplicateLapsiLapsiSerializer(serializers.ModelSerializer):
    varhaiskasvatuspaatos_list = DuplicateLapsiVarhaiskasvatuspaatosSerializer(many=True,
                                                                               source='varhaiskasvatuspaatokset')
    maksutieto_list = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        fields = ('id', 'varhaiskasvatuspaatos_list', 'maksutieto_list',)

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
