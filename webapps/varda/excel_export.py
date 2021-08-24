import datetime
import enum
import logging
import math
import os
import shutil
import uuid
from pathlib import Path

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Q, F
from django.utils import timezone
from rest_framework import status
from xlsxwriter import Workbook
from xlsxwriter.exceptions import XlsxFileError
from xlsxwriter.worksheet import Worksheet, convert_cell_args

from varda.clients.allas_s3_client import Client as S3Client
from varda.enums.koodistot import Koodistot
from varda.enums.supported_language import SupportedLanguage
from varda.misc import decrypt_henkilotunnus, CustomServerErrorException, decrypt_excel_report_password
from varda.models import Varhaiskasvatussuhde, Z8_ExcelReport, Maksutieto, Z2_Code, Z8_ExcelReportLog

logger = logging.getLogger(__name__)


class ExcelReportStatus(enum.Enum):
    PENDING = 'PENDING'
    CREATING = 'CREATING'
    FINISHED = 'FINISHED'
    FAILED = 'FAILED'


class ExcelReportType(enum.Enum):
    VAKATIEDOT_VOIMASSA = 'VAKATIEDOT_VOIMASSA'


if 'VARDA_ENVIRONMENT_TYPE' in os.environ:
    # Backend is in a container
    EXCEL_PATH = '/tmp/excel_reports/'
else:
    # Backend is run locally
    EXCEL_PATH = f'{settings.BASE_DIR}/excel_reports/'

VAKASUHDE_SHEET_NAME = 'VAKASUHDE_SHEET_NAME'
VAKASUHDE_HEADERS = 'VAKASUHDE_HEADERS'
MAKSUTIETO_SHEET_NAME = 'MAKSUTIETO_SHEET_NAME'
MAKSUTIETO_HEADERS = 'MAKSUTIETO_HEADERS'
YES = 'YES'
NO = 'NO'
TRANSLATIONS = {
    SupportedLanguage.FI.value: {
        VAKASUHDE_SHEET_NAME: 'Varhaiskasvatus',
        VAKASUHDE_HEADERS: ('Oppijanumero', 'Etunimet', 'Sukunimi', 'Hetu', 'Turvakielto', 'Lapsen ID',
                            'PAOS (kyllä/ei)', 'PAOS-toimijan nimi', 'PAOS-toimijan OID', 'Lähdejärjestelmä',
                            'Varhaiskasvatuspäätöksen ID', 'Hakemuspvm', 'Alkamispvm', 'Päättymispvm', 'Järjestämismuoto',
                            'Päivittäinen varhaiskasvatus (kyllä/ei)', 'Kokopäiväinen varhaiskasvatus (kyllä/ei)',
                            'Vuorohoito', 'Tuntimäärä viikossa', 'Tilapäinen (kyllä/ei)', 'Varhaiskasvatussuhteen ID',
                            'Alkamispvm', 'Päättymispvm', 'Toimipaikan nimi', 'Toimipaikan OID', 'Toimipaikan ID',),
        MAKSUTIETO_SHEET_NAME: 'Maksutieto',
        MAKSUTIETO_HEADERS: ('Oppijanumero', 'Etunimet', 'Sukunimi', 'Hetu', 'Turvakielto', 'Lapsen ID', 'Maksutiedon ID',
                             'Alkamispvm', 'Päättymispvm', 'Perheen koko', 'Maksun perustekoodi', 'Asiakasmaksu',
                             'Palvelusetelin arvo', 'Huoltajan oppijanumero', 'Huoltajan etunimet',
                             'Huoltajan sukunimi',),
        YES: 'Kyllä',
        NO: 'Ei',
        ExcelReportType.VAKATIEDOT_VOIMASSA.value: 'Varhaiskasvatustiedot_voimassa'
    },
    SupportedLanguage.SV.value: {
        VAKASUHDE_SHEET_NAME: 'Småbarnspedagogik',
        VAKASUHDE_HEADERS: ('Studentnummer', 'Förnamn', 'Efternamn', 'Personbeteckning', 'Spärrmarkering', 'Barnets ID',
                            'Köptjänst-/servicesedelverksamhet (ja/nej)', 'Köptjänst-/servicesedelaktörens namn',
                            'Köptjänst-/servicesedelaktörens OID', 'Källsystem', 'ID för beslut om småbarnspedagogik',
                            'Ansökningsdatum', 'Begynnelsedatum', 'Slutdatum', 'Form för anordnande',
                            'Småbarnspedagogik varje dag (ja/nej)', 'Heldagsverksamhet inom småbarnspedagogik (ja/nej)',
                            'Skiftomsorg', 'Timantal per vecka', 'Tillfällig (ja/nej)',
                            'ID för deltagande i småbarnspedagogik', 'Begynnelsedatum', 'Slutdatum',
                            'Verksamhetsställets namn', 'Verksamhetsställets OID', 'Verksamhetsställets ID',),
        MAKSUTIETO_SHEET_NAME: 'Avgiftsuppgift',
        MAKSUTIETO_HEADERS: ('Studentnummer', 'Förnamn', 'Efternamn', 'Personbeteckning', 'Spärrmarkering',
                             'Barnets ID', 'ID för avgiftsuppgiften', 'Begynnelsedatum', 'Slutdatum',
                             'Familjens storlek', 'Kod för avgiftsgrunden', 'Klientavgift', 'Servicesedelns värde',
                             'Vårdnadshavarens studentnummer', 'Vårdnadshavarens förnamn', 'Vårdnadshavarens efternamn',),
        YES: 'Ja',
        NO: 'Nej',
        ExcelReportType.VAKATIEDOT_VOIMASSA.value: 'Uppgifterna_om_småbarnspedagogik_i_kraft'
    }
}


class AutofitWorksheet(Worksheet):
    """
    Extends xlsxwriter.worksheet.Worksheet to support column autofit width
    https://xlsxwriter.readthedocs.io/example_inheritance2.html

    Also keeps track of number of rows
    """
    def __init__(self):
        super().__init__()
        self.min_width = 0
        self.last_row = 0
        self.max_column_widths = {}

    @convert_cell_args
    def write(self, row, col, *args):
        result = super(AutofitWorksheet, self).write(row, col, *args)

        if not result < 0:
            # No errors
            value_len = len(str(args[0]))
            # Set width relative to number of characters to better keep the width consistent across columns
            # In Excel the column width depends on the font etc.
            value_width = value_len * (0.9 ** value_len + 1)
            max_width = self.max_column_widths.get(col, self.min_width)
            if value_width > max_width:
                self.max_column_widths[col] = value_width

        if row > self.last_row:
            self.last_row = row

        return result


class AutofitWorkbook(Workbook):
    """
    Extends xlsxwriter.Workbook to support column autofit width
    https://xlsxwriter.readthedocs.io/example_inheritance2.html

    Also keeps track of number of rows per worksheet
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number_of_rows_per_worksheet = []

    def add_worksheet(self, *args, **kwargs):
        worksheet = super(AutofitWorkbook, self).add_worksheet(*args, **kwargs, worksheet_class=AutofitWorksheet)
        return worksheet

    def close(self):
        for worksheet in self.worksheets():
            for column, width in worksheet.max_column_widths.items():
                worksheet.set_column(column, column, width)
            self.number_of_rows_per_worksheet.append(worksheet.last_row)
        return super(AutofitWorkbook, self).close()


@shared_task(acks_late=True)
def create_excel_report_task(report_id):
    report = Z8_ExcelReport.objects.filter(id=report_id).first()
    if not report or report.status != ExcelReportStatus.PENDING.value:
        logger.error(f'Error starting Excel report creation with id {report_id}')
        return

    report.status = ExcelReportStatus.CREATING.value
    report.save()

    excel_log = Z8_ExcelReportLog(report_type=report.report_type, target_date=report.target_date,
                                  vakajarjestaja=report.vakajarjestaja, toimipaikka=report.toimipaikka,
                                  user=report.user, started_timestamp=timezone.now())

    file_path = get_excel_local_file_path(report)
    workbook = AutofitWorkbook(file_path, {'default_date_format': 'd.m.yyyy'})

    if report.report_type == ExcelReportType.VAKATIEDOT_VOIMASSA.value:
        _create_vakatiedot_voimassa_report(workbook, report.language, report.vakajarjestaja_id,
                                           toimipaikka_id=report.toimipaikka_id,
                                           target_date=report.target_date)

    # Make sure excel folder exists
    try:
        Path(EXCEL_PATH).mkdir(parents=True, exist_ok=True)
    except OSError as os_error:
        logger.error(f'Error creating temporary Excel folder: {os_error}')
        report.status = ExcelReportStatus.FAILED.value
        report.save()
        return

    try:
        workbook.close()
    except XlsxFileError as excel_error:
        logger.error(f'Error closing Excel file with id {report.id}: {excel_error}')
        report.status = ExcelReportStatus.FAILED.value
        report.save()
        return

    report.status = ExcelReportStatus.FINISHED.value

    excel_log.file_size = os.stat(file_path).st_size
    excel_log.number_of_rows = workbook.number_of_rows_per_worksheet

    password = decrypt_excel_report_password(report.password, report.id)
    encryption_start_timestamp = timezone.now()
    encryption_result = _encrypt_excel_file(file_path, password)
    if not encryption_result:
        logger.error(f'Error encrypting Excel file with id {report.id}')
        report.status = ExcelReportStatus.FAILED.value
        report.save()
        return
    excel_log.encryption_duration = math.ceil((timezone.now() - encryption_start_timestamp).total_seconds())

    if settings.PRODUCTION_ENV or settings.QA_ENV:
        s3_object_path = _get_s3_object_path(report.vakajarjestaja_id, toimipaikka_id=report.toimipaikka_id)
        report.s3_object_path = s3_object_path
        upload_result = _upload_excel_to_s3(file_path, f'{s3_object_path}{report.filename}')

        if not upload_result:
            report.status = ExcelReportStatus.FAILED.value
        # Remove file from pod
        os.remove(file_path)

    report.save()

    excel_log.finished_timestamp = timezone.now()
    excel_log.duration = math.ceil((excel_log.finished_timestamp - excel_log.started_timestamp).total_seconds())
    excel_log.save()


def _create_vakatiedot_voimassa_report(workbook, language, vakajarjestaja_id, toimipaikka_id=None, target_date=None):
    if not target_date:
        target_date = datetime.date.today()

    vakasuhde_filter = Q(alkamis_pvm__lte=target_date) & (Q(paattymis_pvm__gte=target_date) | Q(paattymis_pvm__isnull=True))
    maksutieto_filter = (Q(alkamis_pvm__lte=target_date) & (Q(paattymis_pvm__gte=target_date) | Q(paattymis_pvm__isnull=True)) &
                         Q(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=target_date) &
                         (Q(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=target_date) |
                          Q(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True)))

    _create_vakatiedot_report(workbook, language, vakajarjestaja_id, toimipaikka_id=toimipaikka_id,
                              vakasuhde_filter=vakasuhde_filter, maksutieto_filter=maksutieto_filter)


def _create_vakatiedot_report(workbook, language, vakajarjestaja_id, toimipaikka_id=None,
                              vakasuhde_filter=Q(), maksutieto_filter=Q()):
    translations = TRANSLATIONS.get(language, TRANSLATIONS.get(SupportedLanguage.FI.value))

    vakajarjestaja_filter = (Q(varhaiskasvatuspaatos__lapsi__vakatoimija=vakajarjestaja_id) |
                             Q(varhaiskasvatuspaatos__lapsi__oma_organisaatio=vakajarjestaja_id) |
                             Q(varhaiskasvatuspaatos__lapsi__paos_organisaatio=vakajarjestaja_id))
    if toimipaikka_id:
        vakajarjestaja_filter &= Q(toimipaikka=toimipaikka_id)

    vakasuhde_qs = (Varhaiskasvatussuhde.objects
                    .filter(vakajarjestaja_filter & vakasuhde_filter)
                    .select_related('toimipaikka', 'toimipaikka__vakajarjestaja', 'varhaiskasvatuspaatos',
                                    'varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo',
                                    'varhaiskasvatuspaatos__lapsi__oma_organisaatio',
                                    'varhaiskasvatuspaatos__lapsi__paos_organisaatio')
                    .distinct()
                    .order_by('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi',
                              'varhaiskasvatuspaatos__lapsi__henkilo__etunimet'))

    jarjestamismuoto_codes = _get_koodisto_with_translations(Koodistot.jarjestamismuoto_koodit.value, language)
    lahdejarjestelma_codes = _get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value, language)

    vakasuhde_sheet = workbook.add_worksheet(translations.get(VAKASUHDE_SHEET_NAME))
    _write_headers(vakasuhde_sheet, translations, VAKASUHDE_HEADERS)

    for index, vakasuhde in enumerate(vakasuhde_qs, 1):
        vakapaatos = vakasuhde.varhaiskasvatuspaatos
        lapsi = vakapaatos.lapsi
        henkilo = lapsi.henkilo

        # Lapsi information
        vakasuhde_values = [henkilo.henkilo_oid, henkilo.etunimet, henkilo.sukunimi,
                            _decrypt_hetu(henkilo.henkilotunnus),
                            _get_boolean_translation(translations, henkilo.turvakielto), lapsi.id,
                            _get_boolean_translation(translations, lapsi.paos_kytkin)]

        if lapsi.paos_kytkin:
            paos_organisaatio = lapsi.paos_organisaatio if vakajarjestaja_id != lapsi.paos_organisaatio else lapsi.oma_organisaatio
            vakasuhde_values.extend([paos_organisaatio.nimi, paos_organisaatio.organisaatio_oid])
        else:
            vakasuhde_values.extend([None, None])

        vakasuhde_values.extend([_get_code_translation(lahdejarjestelma_codes, lapsi.lahdejarjestelma)])

        # Vakapaatos information
        vakasuhde_values.extend([vakapaatos.id, vakapaatos.hakemus_pvm, vakapaatos.alkamis_pvm,
                                 vakapaatos.paattymis_pvm,
                                 _get_code_translation(jarjestamismuoto_codes, vakapaatos.jarjestamismuoto_koodi),
                                 _get_boolean_translation(translations, vakapaatos.paivittainen_vaka_kytkin),
                                 _get_boolean_translation(translations, vakapaatos.kokopaivainen_vaka_kytkin),
                                 _get_boolean_translation(translations, vakapaatos.vuorohoito_kytkin),
                                 vakapaatos.tuntimaara_viikossa,
                                 _get_boolean_translation(translations, vakapaatos.tilapainen_vaka_kytkin)])

        # Vakasuhde information
        vakasuhde_values.extend([vakasuhde.id, vakasuhde.alkamis_pvm, vakasuhde.paattymis_pvm,
                                 vakasuhde.toimipaikka.nimi, vakasuhde.toimipaikka.organisaatio_oid,
                                 vakasuhde.toimipaikka.id])

        _write_row(vakasuhde_sheet, index, vakasuhde_values)

    if not toimipaikka_id:
        # Get maksutiedot only on Vakajarjestaja-level
        # Get maksutieto only if Lapsi belongs to Vakajarjestaja, or if Vakajarjestaja is oma_organisaatio
        vakajarjestaja_filter = (Q(huoltajuussuhteet__lapsi__vakatoimija=vakajarjestaja_id) |
                                 Q(huoltajuussuhteet__lapsi__oma_organisaatio=vakajarjestaja_id))
        maksutieto_qs = (Maksutieto.objects
                         .filter(vakajarjestaja_filter & maksutieto_filter)
                         .prefetch_related('huoltajuussuhteet__lapsi__henkilo', 'huoltajuussuhteet__huoltaja__henkilo')
                         .annotate(huoltaja_henkilo_oid=F('huoltajuussuhteet__huoltaja__henkilo__henkilo_oid'),
                                   huoltaja_etunimet=F('huoltajuussuhteet__huoltaja__henkilo__etunimet'),
                                   huoltaja_sukunimi=F('huoltajuussuhteet__huoltaja__henkilo__sukunimi'),
                                   lapsi_id=F('huoltajuussuhteet__lapsi__id'),
                                   henkilo_oid=F('huoltajuussuhteet__lapsi__henkilo__henkilo_oid'),
                                   etunimet=F('huoltajuussuhteet__lapsi__henkilo__etunimet'),
                                   sukunimi=F('huoltajuussuhteet__lapsi__henkilo__sukunimi'),
                                   henkilotunnus=F('huoltajuussuhteet__lapsi__henkilo__henkilotunnus'),
                                   turvakielto=F('huoltajuussuhteet__lapsi__henkilo__turvakielto'))
                         .distinct()
                         .order_by('huoltajuussuhteet__lapsi__henkilo__sukunimi',
                                   'huoltajuussuhteet__lapsi__henkilo__etunimet'))

        maksun_peruste_codes = _get_koodisto_with_translations(Koodistot.maksun_peruste_koodit.value, language)

        maksutieto_sheet = workbook.add_worksheet(translations.get(MAKSUTIETO_SHEET_NAME))
        _write_headers(maksutieto_sheet, translations, MAKSUTIETO_HEADERS)

        for index, maksutieto in enumerate(maksutieto_qs, 1):
            # Lapsi information
            maksutieto_values = [maksutieto.henkilo_oid, maksutieto.etunimet, maksutieto.sukunimi,
                                 _decrypt_hetu(maksutieto.henkilotunnus),
                                 _get_boolean_translation(translations, maksutieto.turvakielto), maksutieto.lapsi_id]

            # Maksutieto information
            maksutieto_values.extend([maksutieto.id, maksutieto.alkamis_pvm, maksutieto.paattymis_pvm,
                                      maksutieto.perheen_koko,
                                      _get_code_translation(maksun_peruste_codes, maksutieto.maksun_peruste_koodi),
                                      maksutieto.asiakasmaksu, maksutieto.palveluseteli_arvo])

            # Huoltaja information
            maksutieto_values.extend([maksutieto.huoltaja_henkilo_oid, maksutieto.huoltaja_etunimet,
                                      maksutieto.huoltaja_sukunimi])

            _write_row(maksutieto_sheet, index, maksutieto_values)


def _write_headers(worksheet, translations, headers_name):
    headers = translations.get(headers_name)
    for index, headers in enumerate(headers):
        worksheet.write(0, index, headers)


def _get_boolean_translation(translations, boolean_value):
    return translations.get(YES) if boolean_value else translations.get(NO)


def _get_koodisto_with_translations(koodisto, language):
    return list(Z2_Code.objects.filter(Q(koodisto__name=koodisto) & Q(translations__language__iexact=language))
                .annotate(name=F('translations__name')).values('code_value', 'name',))


def _get_code_translation(code_list, code):
    if not code:
        return None
    for code_list_item in code_list:
        if code_list_item.get('code_value').lower() == code.lower():
            return f'{code_list_item.get("name")} ({code.lower()})'
    return code


def _write_row(worksheet, row, values):
    for index, value in enumerate(values):
        if not value and (value is None or value == ''):
            # If value is None or empty string, do not write it, however write numbers that equal 0
            continue
        if isinstance(value, datetime.date):
            worksheet.write_datetime(row, index, value)
        else:
            worksheet.write(row, index, value)


def _upload_excel_to_s3(file_path, filename):
    s3_client = S3Client()
    for index in range(0, 5):
        # Try to upload five times
        result = s3_client.upload_file(file_path, filename)
        if result:
            return True
    return False


def generate_filename(report_type, language):
    translations = TRANSLATIONS.get(language, TRANSLATIONS.get(SupportedLanguage.FI.value))
    type_string = translations.get(report_type, report_type)
    datetime_string = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_identifier = str(uuid.uuid4())[:8]

    return f'{type_string}_{datetime_string}_{unique_identifier}.xlsx'


def _get_s3_object_path(vakajarjestaja_id, toimipaikka_id=None):
    if toimipaikka_id:
        return f'vakajarjestajat/{vakajarjestaja_id}/toimipaikat/{toimipaikka_id}/'
    return f'vakajarjestajat/{vakajarjestaja_id}/'


def get_s3_object_name(report_instance):
    return f'{report_instance.s3_object_path}{report_instance.filename}'


def get_excel_local_file_path(report_instance):
    return f'{EXCEL_PATH}{report_instance.filename}'


def delete_excel_reports_earlier_than(timestamp):
    report_qs = Z8_ExcelReport.objects.filter(timestamp__lt=timestamp)

    s3_client = None
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        s3_client = S3Client()

    for report in report_qs:
        if s3_client:
            # In production and QA environments delete the file from S3
            for index in range(0, 5):
                # Try to deletion five times
                result = s3_client.delete_file(get_s3_object_name(report))
                if result:
                    # Deleted from S3 so delete instance from database
                    report.delete()
                    break
        else:
            # In other environments delete the local file
            try:
                os.remove(get_excel_local_file_path(report))
                # Deleted locally so delete instance from database
                report.delete()
            except OSError as os_error:
                logger.error(f'Error deleting Excel file: {os_error}')


def _decrypt_hetu(encrypted_hetu):
    try:
        decrypted_hetu = decrypt_henkilotunnus(encrypted_hetu)
        return decrypted_hetu
    except CustomServerErrorException:
        # Error decrypting hetu, return None
        return None


def _encrypt_excel_file(file_path, password):
    with open(file_path, 'rb') as excel_file:
        resp = requests.post(f'{settings.JAVA_URL}/upload', files={'excel': excel_file, 'password': (None, password,)},
                             stream=True)

    if resp and resp.status_code == status.HTTP_200_OK:
        with open(file_path, 'wb') as file:
            shutil.copyfileobj(resp.raw, file)
        return True

    # Remove local file if encryption was unsuccessful
    os.remove(file_path)
    return False
