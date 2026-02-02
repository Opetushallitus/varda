import datetime
import enum
import logging
import math
import os
import shutil
import uuid
from decimal import Decimal
from pathlib import Path

import requests
from django.apps import apps
from django.conf import settings
from django.db.models import Q, F, Model, OuterRef, Exists, Count
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from xlsxwriter import Workbook
from xlsxwriter.exceptions import XlsxFileError
from xlsxwriter.worksheet import Worksheet, convert_cell_args

from varda.clients.aws_s3_client import Client as S3Client
from varda.constants import YRITYSMUOTO_KUNTA
from varda.custom_celery import custom_shared_task
from varda.enums.data_access_type import DataAccessType
from varda.enums.koodistot import Koodistot
from varda.enums.reporting import ReportStatus
from varda.enums.supported_language import SupportedLanguage
from varda.enums.translation import Translation as T
from varda.lokalisointipalvelu import get_translation
from varda.misc import (
    decrypt_henkilotunnus,
    TemporaryObject,
    decrypt_excel_report_password,
    get_latest_tilastointi_pvm_before_date,
    get_tuen_tiedot_tuen_taso_paatosmaaras,
)
from varda.misc_queries import (
    get_active_filter,
    get_koodisto_codes_lower,
    get_yearly_report_kielipainotus_data,
    get_yearly_report_lapsi_ids,
    get_yearly_report_maksutieto_data,
    get_yearly_report_organisaatio_count,
    get_yearly_report_palvelussuhde_data,
    get_yearly_report_tyontekija_ids,
    get_yearly_report_vuokrattu_henkilosto_data,
    get_yearly_report_tyoskentelypaikka_data,
    get_yearly_report_toiminnallinen_painotus_count,
    get_yearly_report_toimintakieli_data,
    get_yearly_report_toimipaikka_data,
    get_yearly_report_tyontekija_multiple_tehtavanimike_count,
    get_yearly_report_vaka_data,
    get_yearly_report_fixed_term_data,
)
from varda.models import (
    Varhaiskasvatussuhde,
    Z8_ExcelReport,
    Maksutieto,
    Z2_Code,
    Z8_ExcelReportLog,
    Lapsi,
    Tyontekija,
    Toimipaikka,
    Palvelussuhde,
    Varhaiskasvatuspaatos,
)
from varda.request_logging import save_data_access_log


logger = logging.getLogger(__name__)


class ExcelReportType(enum.Enum):
    VAKATIEDOT_VOIMASSA = "VAKATIEDOT_VOIMASSA"
    PUUTTEELLISET_TOIMIPAIKKA = "PUUTTEELLISET_TOIMIPAIKKA"
    PUUTTEELLISET_LAPSI = "PUUTTEELLISET_LAPSI"
    PUUTTEELLISET_TYONTEKIJA = "PUUTTEELLISET_TYONTEKIJA"
    TYONTEKIJATIEDOT_VOIMASSA = "TYONTEKIJATIEDOT_VOIMASSA"
    TOIMIPAIKAT_VOIMASSA = "TOIMIPAIKAT_VOIMASSA"
    VUOSIRAPORTTI = "VUOSIRAPORTTI"
    MAKSUTIETO_PUUTTUU_LAPSI = "MAKSUTIETO_PUUTTUU_LAPSI"


class ExcelReportSubtype(enum.Enum):
    ALL = "ALL"
    VARHAISKASVATUS = "VARHAISKASVATUS"
    HENKILOSTO = "HENKILOSTO"


# Custom headers used sometimes for specific customer requests, to be modified based on request
# Remember to update vakasuhde_values below as well - for row writing
VAKASUHDE_HEADERS_CUSTOM = "VAKASUHDE_HEADERS_CUSTOM"
VAKASUHDE_HEADERS = "VAKASUHDE_HEADERS"
MAKSUTIETO_HEADERS = "MAKSUTIETO_HEADERS"
PUUTTEELLISET_TOIMIPAIKKA_HEADERS = "PUUTTEELLISET_TOIMIPAIKKA_HEADERS"
PUUTTEELLISET_LAPSI_HEADERS = "PUUTTEELLISET_LAPSI_HEADERS"
PUUTTEELLISET_TYONTEKIJA_HEADERS = "PUUTTEELLISET_TYONTEKIJA_HEADERS"
TYONTEKIJA_HEADERS = "TYONTEKIJA_HEADERS"
TOIMIPAIKKA_HEADERS = "TOIMIPAIKKA_HEADERS"
VUOSIRAPORTTI_VARHAISKASVATUS_HEADERS = "VUOSIRAPORTTI_VARHAISKASVATUS_HEADERS"
MAKSUTIETO_PUUTTUU_LAPSI_HEADERS = "MAKSUTIETO_PUUTTUU_LAPSI_HEADERS"
TRANSLATIONS = {
    VAKASUHDE_HEADERS_CUSTOM: (
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_HETU,
    ),
    VAKASUHDE_HEADERS: (
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_ETUNIMET,
        T.EXCEL_SUKUNIMI,
        T.EXCEL_HETU,
        T.EXCEL_TURVAKIELTO,
        T.EXCEL_LAPSI_ID,
        T.EXCEL_PAOS_KYTKIN,
        T.EXCEL_PAOS_NIMI,
        T.EXCEL_PAOS_OID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_VARHAISKASVATUSPAATOS_ID,
        T.EXCEL_HAKEMUS_PVM,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
        T.EXCEL_JARJESTAMISMUOTO,
        T.EXCEL_PAIVITTAINEN_KYTKIN,
        T.EXCEL_KOKOPAIVAINEN_KYTKIN,
        T.EXCEL_VUOROHOITO_KYTKIN,
        T.EXCEL_TUNTIMAARA_VIIKOSSA,
        T.EXCEL_TILAPAINEN_KYTKIN,
        T.EXCEL_VARHAISKASVATUSSUHDE_ID,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
        T.EXCEL_TOIMIPAIKKA_NIMI,
        T.EXCEL_TOIMIPAIKKA_OID,
        T.EXCEL_TOIMIPAIKKA_ID,
    ),
    MAKSUTIETO_HEADERS: (
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_ETUNIMET,
        T.EXCEL_SUKUNIMI,
        T.EXCEL_HETU,
        T.EXCEL_TURVAKIELTO,
        T.EXCEL_LAPSI_ID,
        T.EXCEL_PAOS_KYTKIN,
        T.EXCEL_PAOS_NIMI,
        T.EXCEL_PAOS_OID,
        T.EXCEL_MAKSUTIETO_ID,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
        T.EXCEL_PERHEEN_KOKO,
        T.EXCEL_MAKSUN_PERUSTE,
        T.EXCEL_ASIAKASMAKSU,
        T.EXCEL_PALVELUSETELI_ARVO,
        T.EXCEL_HUOLTAJA_OPPIJANUMERO,
        T.EXCEL_HUOLTAJA_ETUNIMET,
        T.EXCEL_HUOLTAJA_SUKUNIMI,
    ),
    PUUTTEELLISET_TOIMIPAIKKA_HEADERS: (
        T.EXCEL_TOIMIPAIKKA_NIMI,
        T.EXCEL_TOIMIPAIKKA_OID,
        T.EXCEL_TOIMIPAIKKA_ID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_ERROR,
        T.EXCEL_TIETOSISALTO,
        T.EXCEL_OBJECT_ID,
        T.EXCEL_VOIMASSAOLO,
    ),
    PUUTTEELLISET_LAPSI_HEADERS: (
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_ETUNIMET,
        T.EXCEL_SUKUNIMI,
        T.EXCEL_HETU,
        T.EXCEL_TURVAKIELTO,
        T.EXCEL_LAPSI_ID,
        T.EXCEL_PAOS_KYTKIN,
        T.EXCEL_PAOS_NIMI,
        T.EXCEL_PAOS_OID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_ERROR,
        T.EXCEL_TIETOSISALTO,
        T.EXCEL_OBJECT_ID,
        T.EXCEL_VOIMASSAOLO,
    ),
    PUUTTEELLISET_TYONTEKIJA_HEADERS: (
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_ETUNIMET,
        T.EXCEL_SUKUNIMI,
        T.EXCEL_HETU,
        T.EXCEL_TURVAKIELTO,
        T.EXCEL_TYONTEKIJA_ID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_ERROR,
        T.EXCEL_TIETOSISALTO,
        T.EXCEL_OBJECT_ID,
        T.EXCEL_VOIMASSAOLO,
    ),
    TYONTEKIJA_HEADERS: (
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_ETUNIMET,
        T.EXCEL_SUKUNIMI,
        T.EXCEL_HETU,
        T.EXCEL_EMAIL,
        T.EXCEL_TURVAKIELTO,
        T.EXCEL_TYONTEKIJA_ID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_PALVELUSSUHDE_ID,
        T.EXCEL_PALVELUSSUHDE_TUNNISTE,
        T.EXCEL_PALVELUSSUHDE_TYYPPI,
        T.EXCEL_TYOAIKA,
        T.EXCEL_TUTKINTO,
        T.EXCEL_TYOAIKA_VIIKOSSA,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
        T.EXCEL_TYOSKENTELYPAIKKA_ID,
        T.EXCEL_TYOSKENTELYPAIKKA_TUNNISTE,
        T.EXCEL_KIERTAVA_KYTKIN,
        T.EXCEL_TOIMIPAIKKA_NIMI,
        T.EXCEL_TOIMIPAIKKA_OID,
        T.EXCEL_TOIMIPAIKKA_ID,
        T.EXCEL_TEHTAVANIMIKE,
        T.EXCEL_KELPOISUUS_KYTKIN,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
        T.EXCEL_PIDEMPI_POISSAOLO_ID,
        T.EXCEL_PIDEMPI_POISSAOLO_TUNNISTE,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
    ),
    TOIMIPAIKKA_HEADERS: (
        T.EXCEL_NIMI,
        T.EXCEL_OID,
        T.EXCEL_ID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_TUNNISTE,
        T.EXCEL_PALVELUNTUOTTAJA_NIMI,
        T.EXCEL_PALVELUNTUOTTAJA_OID,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
        T.EXCEL_KASVATUSOPILLINEN_JARJESTELMA,
        T.EXCEL_TOIMINTAMUOTO,
        T.EXCEL_TOIMINTAKIELI,
        T.EXCEL_JARJESTAMISMUOTO,
        T.EXCEL_VARHAISKASVATUSPAIKAT,
        T.EXCEL_KUNTA,
        T.EXCEL_KAYNTIOSOITE,
        T.EXCEL_POSTINUMERO,
        T.EXCEL_POSTITOIMIPAIKKA,
        T.EXCEL_POSTIOSOITE,
        T.EXCEL_POSTINUMERO,
        T.EXCEL_POSTITOIMIPAIKKA,
        T.EXCEL_PUHELINNUMERO,
        T.EXCEL_EMAIL,
        T.EXCEL_PAINOTUS_ID,
        T.EXCEL_LAHDEJARJESTELMA,
        T.EXCEL_TUNNISTE,
        T.EXCEL_TOIMINNALLINEN_PAINOTUS,
        T.EXCEL_KIELIPAINOTUS,
        T.EXCEL_KIELIPAINOTUS_TYYPPI,
        T.EXCEL_ALKAMIS_PVM,
        T.EXCEL_PAATTYMIS_PVM,
    ),
    VUOSIRAPORTTI_VARHAISKASVATUS_HEADERS: (
        "",
        T.EXCEL_KAIKKI_TIEDOT,
        T.EXCEL_OMAT_TIEDOT,
        T.EXCEL_PAOS_TIEDOT,
    ),
    MAKSUTIETO_PUUTTUU_LAPSI_HEADERS: (
        T.EXCEL_VAKATOIMIJA_NIMI,
        T.EXCEL_OPPIJANUMERO,
        T.EXCEL_ETUNIMET,
        T.EXCEL_SUKUNIMI,
        T.EXCEL_HETU,
        T.EXCEL_LAPSI_ID,
        T.EXCEL_HUOLTAJUUSSUHTEET_VOIMASSA,
    ),
    ExcelReportType.VAKATIEDOT_VOIMASSA.value: T.EXCEL_FILENAME_VAKATIEDOT_VOIMASSA,
    ExcelReportType.PUUTTEELLISET_TOIMIPAIKKA.value: T.EXCEL_FILENAME_PUUTTEELLISET_TOIMIPAIKKA,
    ExcelReportType.PUUTTEELLISET_LAPSI.value: T.EXCEL_FILENAME_PUUTTEELLISET_LAPSI,
    ExcelReportType.PUUTTEELLISET_TYONTEKIJA.value: T.EXCEL_FILENAME_PUUTTEELLISET_TYONTEKIJA,
    ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value: T.EXCEL_FILENAME_TYONTEKIJATIEDOT_VOIMASSA,
    ExcelReportType.TOIMIPAIKAT_VOIMASSA.value: T.EXCEL_FILENAME_TOIMIPAIKAT_VOIMASSA,
    ExcelReportType.VUOSIRAPORTTI.value: {
        ExcelReportSubtype.ALL.value: T.EXCEL_FILENAME_VUOSIRAPORTTI_ALL,
        ExcelReportSubtype.VARHAISKASVATUS.value: T.EXCEL_FILENAME_VUOSIRAPORTTI_VARHAISKASVATUS,
        ExcelReportSubtype.HENKILOSTO.value: T.EXCEL_FILENAME_VUOSIRAPORTTI_HENKILOSTO,
    },
    ExcelReportType.MAKSUTIETO_PUUTTUU_LAPSI.value: T.EXCEL_FILENAME_MAKSUTIETO_PUUTTUU_LAPSI,
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
            value_width = value_len * (0.9**value_len + 1)
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


@custom_shared_task(single_instance=True)
def create_excel_report_task(report_id):
    report = Z8_ExcelReport.objects.filter(id=report_id).first()
    if not report or report.status != ReportStatus.PENDING.value:
        logger.error(f"Error starting Excel report creation with id {report_id}")
        return

    report_generator = ExcelReportGenerator(report)
    report_generator.generate()


class ExcelReportGenerator:
    def __init__(self, report):
        self.report = report
        self.language = report.language
        self.admin_user_all_organizations = report.admin_user_all_organizations
        self.organisaatio_id = getattr(report.organisaatio, "id", None)
        self.toimipaikka_id = getattr(report.toimipaikka, "id", None)

        self.workbook = None
        self.integer_format = None
        self.float_format = None
        self.align_right_format = None
        self.date_format = "%d.%m.%Y"
        self.translations = TRANSLATIONS.get(self.language, TRANSLATIONS.get(SupportedLanguage.FI.value))
        self.error_koodisto = None
        self.lahdejarjestelma_koodisto = None

        self.henkilo_id_oid_set = set()

    def generate(self):
        report = self.report
        report.status = ReportStatus.CREATING.value
        report.filename = self._generate_filename()
        report.save()

        excel_log = Z8_ExcelReportLog(
            report_id=report.id,
            report_type=report.report_type,
            report_subtype=report.report_subtype,
            target_date=report.target_date,
            target_date_secondary=report.target_date_secondary,
            organisaatio=report.organisaatio,
            toimipaikka_id=self.toimipaikka_id,
            user=report.user,
            started_timestamp=timezone.now(),
        )

        file_path = get_excel_local_file_path(report)
        self.workbook = AutofitWorkbook(file_path, {"default_date_format": "d.m.yyyy"})
        self.integer_format = self.workbook.add_format()
        self.integer_format.set_num_format(3)
        self.float_format = self.workbook.add_format()
        self.float_format.set_num_format(4)
        self.align_right_format = self.workbook.add_format()
        self.align_right_format.set_align("right")

        self._create_excel_report()

        # Make sure excel folder exists
        try:
            Path(settings.EXCEL_PATH).mkdir(parents=True, exist_ok=True)
        except OSError as os_error:
            logger.error(f"Error creating temporary Excel folder: {os_error}")
            report.status = ReportStatus.FAILED.value
            report.save()
            return None

        try:
            self.workbook.close()
        except XlsxFileError as excel_error:
            logger.error(f"Error closing Excel file with id {report.id}: {excel_error}")
            report.status = ReportStatus.FAILED.value
            report.save()
            return None

        report.status = ReportStatus.FINISHED.value

        excel_log.file_size = os.stat(file_path).st_size
        excel_log.number_of_rows = self.workbook.number_of_rows_per_worksheet

        password = decrypt_excel_report_password(report.password, report.id)
        encryption_start_timestamp = timezone.now()
        encryption_result = _encrypt_excel_file(file_path, password)
        excel_log.encryption_duration = math.ceil((timezone.now() - encryption_start_timestamp).total_seconds())
        if not encryption_result:
            logger.error(
                f"Error encrypting Excel file with ID {report.id}, size: {excel_log.file_size}, "
                f"rows: {excel_log.number_of_rows}, encryption duration: {excel_log.encryption_duration}"
            )
            report.status = ReportStatus.FAILED.value
            report.save()
            return None

        if settings.PRODUCTION_ENV or settings.QA_ENV or settings.DEV_ENV:
            s3_object_path = self._get_s3_object_path()
            report.s3_object_path = s3_object_path
            upload_result = _upload_excel_to_s3(file_path, f"{s3_object_path}{report.filename}")

            if not upload_result:
                report.status = ReportStatus.FAILED.value
            # Remove file from pod
            os.remove(file_path)

        report.save()

        excel_log.finished_timestamp = timezone.now()
        excel_log.duration = math.ceil((excel_log.finished_timestamp - excel_log.started_timestamp).total_seconds())
        excel_log.save()

        if not self.admin_user_all_organizations:
            # Save data access logs if henkilo_id_oid_set is not empty
            save_data_access_log(self.report.user, DataAccessType.EXCEL.value, henkilo_id_oid_list=self.henkilo_id_oid_set)

    def _create_excel_report(self):
        match self.report.report_type:
            case ExcelReportType.VAKATIEDOT_VOIMASSA.value:
                self._create_vakatiedot_voimassa_report()
            case (
                ExcelReportType.PUUTTEELLISET_TOIMIPAIKKA.value
                | ExcelReportType.PUUTTEELLISET_LAPSI.value
                | ExcelReportType.PUUTTEELLISET_TYONTEKIJA.value
            ):
                self._create_puutteelliset_report()
            case ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value:
                self._create_tyontekijatiedot_voimassa_report()
            case ExcelReportType.TOIMIPAIKAT_VOIMASSA.value:
                self._create_toimipaikat_voimassa_report()
            case ExcelReportType.VUOSIRAPORTTI.value:
                self._create_vuosiraportti_report()
            case ExcelReportType.MAKSUTIETO_PUUTTUU_LAPSI.value:
                self._create_maksutieto_puuttuu_lapsi_report()

    def _create_vakatiedot_voimassa_report(self):
        target_date = self.report.target_date
        if not target_date:
            target_date = datetime.date.today()

        active_filter = get_active_filter(target_date)
        vakasuhde_filter = active_filter & get_active_filter(target_date, prefix="varhaiskasvatuspaatos")
        maksutieto_filter = (
            active_filter
            & get_active_filter(target_date, prefix="huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset")
            & get_active_filter(target_date, prefix="huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet")
        )

        self._create_vakatiedot_report(vakasuhde_filter=vakasuhde_filter, maksutieto_filter=maksutieto_filter)

    def _create_vakatiedot_report(self, vakasuhde_filter=Q(), maksutieto_filter=Q()):
        if self.admin_user_all_organizations:
            vakajarjestaja_filter = Q()
            select_related = ["varhaiskasvatuspaatos", "varhaiskasvatuspaatos__lapsi", "varhaiskasvatuspaatos__lapsi__henkilo"]
            order_by = ["varhaiskasvatuspaatos__lapsi__henkilo__id"]
        else:
            vakajarjestaja_filter = (
                Q(varhaiskasvatuspaatos__lapsi__vakatoimija=self.organisaatio_id)
                | Q(varhaiskasvatuspaatos__lapsi__oma_organisaatio=self.organisaatio_id)
                | Q(varhaiskasvatuspaatos__lapsi__paos_organisaatio=self.organisaatio_id)
            )
            select_related = [
                "toimipaikka",
                "toimipaikka__vakajarjestaja",
                "varhaiskasvatuspaatos",
                "varhaiskasvatuspaatos__lapsi",
                "varhaiskasvatuspaatos__lapsi__henkilo",
                "varhaiskasvatuspaatos__lapsi__oma_organisaatio",
                "varhaiskasvatuspaatos__lapsi__paos_organisaatio",
            ]
            order_by = ["varhaiskasvatuspaatos__lapsi__henkilo__sukunimi", "varhaiskasvatuspaatos__lapsi__henkilo__etunimet"]
        if self.toimipaikka_id:
            vakajarjestaja_filter &= Q(toimipaikka=self.toimipaikka_id)

        vakasuhde_qs = (
            Varhaiskasvatussuhde.objects.filter(vakajarjestaja_filter & vakasuhde_filter)
            .select_related(*select_related)
            .distinct()
            .order_by(*order_by)
        )

        jarjestamismuoto_codes = self._get_koodisto_with_translations(Koodistot.jarjestamismuoto_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        vakasuhde_sheet = self._add_worksheet(T.EXCEL_VARHAISKASVATUS)

        if self.admin_user_all_organizations:
            self._write_headers(vakasuhde_sheet, VAKASUHDE_HEADERS_CUSTOM)
        else:
            self._write_headers(vakasuhde_sheet, VAKASUHDE_HEADERS)

        for index, vakasuhde in enumerate(vakasuhde_qs.iterator(), 1):
            vakapaatos = vakasuhde.varhaiskasvatuspaatos
            lapsi = vakapaatos.lapsi
            henkilo = lapsi.henkilo

            if self.admin_user_all_organizations:
                """
                This is a custom selection for specific customer requests. Must match with the VAKASUHDE_HEADERS_CUSTOM
                """
                vakasuhde_values = [
                    henkilo.henkilo_oid,
                    decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                ]
            else:
                # Lapsi information
                vakasuhde_values = [
                    henkilo.henkilo_oid,
                    henkilo.etunimet,
                    henkilo.sukunimi,
                    decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                    self._get_boolean_translation(henkilo.turvakielto),
                    lapsi.id,
                    self._get_boolean_translation(lapsi.paos_kytkin),
                ]

                if lapsi.paos_kytkin:
                    paos_organisaatio = (
                        lapsi.paos_organisaatio if self.organisaatio_id != lapsi.paos_organisaatio else lapsi.oma_organisaatio
                    )
                    vakasuhde_values.extend([paos_organisaatio.nimi, paos_organisaatio.organisaatio_oid])
                else:
                    vakasuhde_values.extend([None, None])

                vakasuhde_values.extend([_get_code_translation(lahdejarjestelma_codes, lapsi.lahdejarjestelma)])

                # Vakapaatos information
                vakasuhde_values.extend(
                    [
                        vakapaatos.id,
                        vakapaatos.hakemus_pvm,
                        vakapaatos.alkamis_pvm,
                        vakapaatos.paattymis_pvm,
                        _get_code_translation(jarjestamismuoto_codes, vakapaatos.jarjestamismuoto_koodi),
                        self._get_boolean_translation(vakapaatos.paivittainen_vaka_kytkin),
                        self._get_boolean_translation(vakapaatos.kokopaivainen_vaka_kytkin),
                        self._get_boolean_translation(vakapaatos.vuorohoito_kytkin),
                        vakapaatos.tuntimaara_viikossa,
                        self._get_boolean_translation(vakapaatos.tilapainen_vaka_kytkin),
                    ]
                )

                # Vakasuhde information
                vakasuhde_values.extend(
                    [
                        vakasuhde.id,
                        vakasuhde.alkamis_pvm,
                        vakasuhde.paattymis_pvm,
                        vakasuhde.toimipaikka.nimi,
                        vakasuhde.toimipaikka.organisaatio_oid,
                        vakasuhde.toimipaikka.id,
                    ]
                )

            self.henkilo_id_oid_set.add(
                (
                    henkilo.id,
                    henkilo.henkilo_oid,
                )
            )
            self._write_row(vakasuhde_sheet, index, vakasuhde_values)

        if not self.toimipaikka_id and not self.admin_user_all_organizations:
            # Get maksutiedot only on Vakajarjestaja-level, and never for admin_user_all_organizations
            # Get maksutieto only if Lapsi belongs to Vakajarjestaja, or if Vakajarjestaja is oma_organisaatio
            vakajarjestaja_filter = Q(huoltajuussuhteet__lapsi__vakatoimija=self.organisaatio_id) | Q(
                huoltajuussuhteet__lapsi__oma_organisaatio=self.organisaatio_id
            )
            maksutieto_qs = (
                Maksutieto.objects.filter(vakajarjestaja_filter & maksutieto_filter)
                .prefetch_related("huoltajuussuhteet__lapsi__henkilo", "huoltajuussuhteet__huoltaja__henkilo")
                .annotate(
                    huoltaja_henkilo_oid=F("huoltajuussuhteet__huoltaja__henkilo__henkilo_oid"),
                    huoltaja_etunimet=F("huoltajuussuhteet__huoltaja__henkilo__etunimet"),
                    huoltaja_sukunimi=F("huoltajuussuhteet__huoltaja__henkilo__sukunimi"),
                    lapsi_id=F("huoltajuussuhteet__lapsi__id"),
                    henkilo_id=F("huoltajuussuhteet__lapsi__henkilo_id"),
                    henkilo_oid=F("huoltajuussuhteet__lapsi__henkilo__henkilo_oid"),
                    etunimet=F("huoltajuussuhteet__lapsi__henkilo__etunimet"),
                    sukunimi=F("huoltajuussuhteet__lapsi__henkilo__sukunimi"),
                    henkilotunnus=F("huoltajuussuhteet__lapsi__henkilo__henkilotunnus"),
                    turvakielto=F("huoltajuussuhteet__lapsi__henkilo__turvakielto"),
                    paos_kytkin=F("huoltajuussuhteet__lapsi__paos_kytkin"),
                    paos_organisaatio_nimi=F("huoltajuussuhteet__lapsi__paos_organisaatio__nimi"),
                    paos_organisaatio_oid=F("huoltajuussuhteet__lapsi__paos_organisaatio__organisaatio_oid"),
                )
                .distinct()
                .order_by("huoltajuussuhteet__lapsi__henkilo__sukunimi", "huoltajuussuhteet__lapsi__henkilo__etunimet")
            )

            maksun_peruste_codes = self._get_koodisto_with_translations(Koodistot.maksun_peruste_koodit.value)

            maksutieto_sheet = self._add_worksheet(T.EXCEL_MAKSUTIETO)
            self._write_headers(maksutieto_sheet, MAKSUTIETO_HEADERS)

            for index, maksutieto in enumerate(maksutieto_qs.iterator(chunk_size=1000), 1):
                # Lapsi information
                maksutieto_values = [
                    maksutieto.henkilo_oid,
                    maksutieto.etunimet,
                    maksutieto.sukunimi,
                    decrypt_henkilotunnus(maksutieto.henkilotunnus, henkilo_id=maksutieto.henkilo_id, raise_error=False),
                    self._get_boolean_translation(maksutieto.turvakielto),
                    maksutieto.lapsi_id,
                    self._get_boolean_translation(maksutieto.paos_kytkin),
                    maksutieto.paos_organisaatio_nimi,
                    maksutieto.paos_organisaatio_oid,
                ]

                # Maksutieto information
                maksutieto_values.extend(
                    [
                        maksutieto.id,
                        maksutieto.alkamis_pvm,
                        maksutieto.paattymis_pvm,
                        maksutieto.perheen_koko,
                        _get_code_translation(maksun_peruste_codes, maksutieto.maksun_peruste_koodi),
                        maksutieto.asiakasmaksu,
                        maksutieto.palveluseteli_arvo,
                    ]
                )

                # Huoltaja information
                maksutieto_values.extend(
                    [maksutieto.huoltaja_henkilo_oid, maksutieto.huoltaja_etunimet, maksutieto.huoltaja_sukunimi]
                )

                self.henkilo_id_oid_set.add(
                    (
                        maksutieto.henkilo_id,
                        maksutieto.henkilo_oid,
                    )
                )
                self._write_row(maksutieto_sheet, index, maksutieto_values)

    def _create_puutteelliset_report(self):
        # Import locally to avoid circular reference
        from varda.viewsets_reporting import (
            ErrorReportLapsetViewSet,
            ErrorReportTyontekijatViewSet,
            ErrorReportToimipaikatViewSet,
        )

        match self.report.report_type:
            case ExcelReportType.PUUTTEELLISET_TOIMIPAIKKA.value:
                viewset = ErrorReportToimipaikatViewSet()
                headers = PUUTTEELLISET_TOIMIPAIKKA_HEADERS
                data_handler_function = self._create_puutteelliset_toimipaikka_report
            case ExcelReportType.PUUTTEELLISET_LAPSI.value:
                viewset = ErrorReportLapsetViewSet()
                headers = PUUTTEELLISET_LAPSI_HEADERS
                data_handler_function = self._create_puutteelliset_lapsi_report
            case _:
                # default or PUUTTEELLISET_TYONTEKIJA
                viewset = ErrorReportTyontekijatViewSet()
                headers = PUUTTEELLISET_TYONTEKIJA_HEADERS
                data_handler_function = self._create_puutteelliset_tyontekija_report

        worksheet = self._add_worksheet(T.EXCEL_PUUTTEELLISET_TIEDOT)
        self._write_headers(worksheet, headers)

        # Initialize ViewSet by setting properties
        viewset.vakajarjestaja_id = self.organisaatio_id
        viewset.vakajarjestaja_oid = self.report.organisaatio.organisaatio_oid
        viewset.format_kwarg = None
        temp_request_object = TemporaryObject()
        temp_request_object.user = self.report.user
        temp_request_object.query_params = {}
        viewset.request = temp_request_object

        try:
            # Verify permissions and set internal properties
            viewset.verify_permissions()
        except Http404:
            # No permissions
            return None

        self.error_koodisto = self._get_koodisto_with_translations(Koodistot.virhe_koodit.value)
        self.lahdejarjestelma_koodisto = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        queryset = viewset.get_queryset()
        serializer_data = viewset.get_serializer(queryset, many=True).data
        data_handler_function(worksheet, serializer_data)

    def _create_puutteelliset_toimipaikka_report(self, worksheet, data):
        index = 1
        for instance in data:
            toimipaikka = Toimipaikka.objects.get(id=instance["toimipaikka_id"])
            for error in instance["errors"]:
                for model_id in error["model_id_list"]:
                    # Toimipaikka information
                    error_values = [
                        toimipaikka.nimi,
                        toimipaikka.organisaatio_oid,
                        toimipaikka.id,
                        _get_code_translation(self.lahdejarjestelma_koodisto, toimipaikka.lahdejarjestelma),
                    ]

                    error_values.extend(
                        [
                            _get_code_translation(self.error_koodisto, error["error_code"]),
                            error["model_name"],
                            model_id,
                            _get_dates_for_model_and_id(error["model_name"], model_id),
                        ]
                    )

                    self._write_row(worksheet, index, error_values)
                    index += 1

    def _create_puutteelliset_lapsi_report(self, worksheet, data):
        index = 1
        for instance in data:
            lapsi = Lapsi.objects.get(id=instance["lapsi_id"])
            henkilo = lapsi.henkilo
            for error in instance["errors"]:
                for model_id in error["model_id_list"]:
                    # Lapsi information
                    error_values = [
                        henkilo.henkilo_oid,
                        henkilo.etunimet,
                        henkilo.sukunimi,
                        decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                        self._get_boolean_translation(henkilo.turvakielto),
                        lapsi.id,
                        self._get_boolean_translation(lapsi.paos_kytkin),
                    ]

                    if lapsi.paos_kytkin:
                        paos_organisaatio = (
                            lapsi.paos_organisaatio if self.organisaatio_id != lapsi.paos_organisaatio else lapsi.oma_organisaatio
                        )
                        error_values.extend([paos_organisaatio.nimi, paos_organisaatio.organisaatio_oid])
                    else:
                        error_values.extend([None, None])

                    error_values.extend(
                        [
                            _get_code_translation(self.lahdejarjestelma_koodisto, lapsi.lahdejarjestelma),
                            _get_code_translation(self.error_koodisto, error["error_code"]),
                            error["model_name"],
                            model_id,
                            _get_dates_for_model_and_id(error["model_name"], model_id),
                        ]
                    )

                    self._write_row(worksheet, index, error_values)
                    index += 1

    def _create_puutteelliset_tyontekija_report(self, worksheet, data):
        index = 1
        for instance in data:
            tyontekija = Tyontekija.objects.get(id=instance["tyontekija_id"])
            henkilo = tyontekija.henkilo
            for error in instance["errors"]:
                for model_id in error["model_id_list"]:
                    # Tyontekija information
                    error_values = [
                        henkilo.henkilo_oid,
                        henkilo.etunimet,
                        henkilo.sukunimi,
                        decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                        self._get_boolean_translation(henkilo.turvakielto),
                        tyontekija.id,
                        _get_code_translation(self.lahdejarjestelma_koodisto, tyontekija.lahdejarjestelma),
                    ]

                    error_values.extend(
                        [
                            _get_code_translation(self.error_koodisto, error["error_code"]),
                            error["model_name"],
                            model_id,
                            _get_dates_for_model_and_id(error["model_name"], model_id),
                        ]
                    )

                    self._write_row(worksheet, index, error_values)
                    index += 1

    def _create_tyontekijatiedot_voimassa_report(self):
        target_date = self.report.target_date
        if not target_date:
            target_date = datetime.date.today()

        palvelussuhde_filter = get_active_filter(target_date) & get_active_filter(target_date, prefix="tyoskentelypaikat")

        self._create_tyontekijatiedot_report(palvelussuhde_filter=palvelussuhde_filter)

    def _create_tyontekijatiedot_report(self, palvelussuhde_filter=Q()):
        vakajarjestaja_filter = Q(tyontekija__vakajarjestaja=self.organisaatio_id)
        if self.toimipaikka_id:
            vakajarjestaja_filter &= Q(tyoskentelypaikat__toimipaikka=self.toimipaikka_id)

        palvelussuhde_qs = (
            Palvelussuhde.objects.filter(vakajarjestaja_filter & palvelussuhde_filter)
            .distinct()
            .select_related("tyontekija__henkilo")
            .prefetch_related("tyontekija__henkilo__tutkinnot")
            .order_by("tyontekija__henkilo__sukunimi", "tyontekija__henkilo__etunimet", "alkamis_pvm")
        )

        tutkinto_codes = self._get_koodisto_with_translations(Koodistot.tutkinto_koodit.value)
        tyosuhde_codes = self._get_koodisto_with_translations(Koodistot.tyosuhde_koodit.value)
        tyoaika_codes = self._get_koodisto_with_translations(Koodistot.tyoaika_koodit.value)
        tehtavanimike_codes = self._get_koodisto_with_translations(Koodistot.tehtavanimike_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        tyontekija_sheet = self._add_worksheet(T.EXCEL_TYONTEKIJATIEDOT)
        self._write_headers(tyontekija_sheet, TYONTEKIJA_HEADERS)

        index = 1
        for palvelussuhde in palvelussuhde_qs.iterator(chunk_size=500):
            tyoskentelypaikka_qs = (
                palvelussuhde.tyoskentelypaikat.filter(toimipaikka=self.toimipaikka_id)
                if self.toimipaikka_id
                else palvelussuhde.tyoskentelypaikat.all()
            )
            tyoskentelypaikka_qs.order_by("alkamis_pvm")
            tyontekija = palvelussuhde.tyontekija
            henkilo = tyontekija.henkilo
            for type_index, data_set in enumerate(
                (
                    tyoskentelypaikka_qs,
                    palvelussuhde.pidemmatpoissaolot.all().order_by("alkamis_pvm"),
                )
            ):
                for data_instance in data_set:
                    # Tyontekija information
                    tyontekija_values = [
                        henkilo.henkilo_oid,
                        henkilo.etunimet,
                        henkilo.sukunimi,
                        decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id, raise_error=False),
                        tyontekija.sahkopostiosoite,
                        self._get_boolean_translation(henkilo.turvakielto),
                        tyontekija.id,
                        _get_code_translation(lahdejarjestelma_codes, tyontekija.lahdejarjestelma),
                    ]

                    # Palvelussuhde information

                    # We use newest Tutkinto/tutkinto_koodi instead of tutkinto_koodi
                    # in Palvelussuhde. (Palvelussuhde/tutkinto_koodi is used as backup)

                    # Filter the prefetched tutkinnot to get latest Tutkinto with the correct vakajarjestaja_id
                    filtered_tutkinnot = [
                        tutkinto
                        for tutkinto in palvelussuhde.tyontekija.henkilo.tutkinnot.all()
                        if tutkinto.vakajarjestaja_id == self.organisaatio_id
                    ]
                    latest_tutkinto = max(filtered_tutkinnot, key=lambda t: t.luonti_pvm, default=None)
                    latest_tutkinto_koodi = latest_tutkinto.tutkinto_koodi if latest_tutkinto else None

                    tyontekija_values.extend(
                        [
                            palvelussuhde.id,
                            palvelussuhde.tunniste,
                            _get_code_translation(tyosuhde_codes, palvelussuhde.tyosuhde_koodi),
                            _get_code_translation(tyoaika_codes, palvelussuhde.tyoaika_koodi),
                            _get_code_translation(tutkinto_codes, latest_tutkinto_koodi),
                            palvelussuhde.tyoaika_viikossa,
                            palvelussuhde.alkamis_pvm,
                            palvelussuhde.paattymis_pvm,
                        ]
                    )

                    if type_index == 0:
                        # Tyoskentelypaikka
                        tyontekija_values.extend(
                            [
                                data_instance.id,
                                data_instance.tunniste,
                                self._get_boolean_translation(data_instance.kiertava_tyontekija_kytkin),
                            ]
                        )
                        if data_instance.toimipaikka:
                            tyontekija_values.extend(
                                [
                                    data_instance.toimipaikka.nimi,
                                    data_instance.toimipaikka.organisaatio_oid,
                                    data_instance.toimipaikka.id,
                                ]
                            )
                        else:
                            tyontekija_values.extend([None, None, None])
                        tyontekija_values.extend(
                            [
                                _get_code_translation(tehtavanimike_codes, data_instance.tehtavanimike_koodi),
                                self._get_boolean_translation(data_instance.kelpoisuus_kytkin),
                                data_instance.alkamis_pvm,
                                data_instance.paattymis_pvm,
                            ]
                        )
                    else:
                        # Pidempi poissaolo
                        # Because every row has Tyoskentelypaikka and Pidempi Poissaolo columns, fill Tyoskentelypaikka
                        # columns with None
                        tyontekija_values.extend([None] * 10)
                        tyontekija_values.extend(
                            [data_instance.id, data_instance.tunniste, data_instance.alkamis_pvm, data_instance.paattymis_pvm]
                        )

                    self.henkilo_id_oid_set.add(
                        (
                            henkilo.id,
                            henkilo.henkilo_oid,
                        )
                    )
                    self._write_row(tyontekija_sheet, index, tyontekija_values)
                    index += 1

    def _create_toimipaikat_voimassa_report(self):
        target_date = self.report.target_date
        if not target_date:
            target_date = datetime.date.today()

        self._create_toimipaikat_report(toimipaikka_filter=get_active_filter(target_date))

    def _create_toimipaikat_report(self, toimipaikka_filter=Q()):
        vakajarjestaja_filter = Q(vakajarjestaja=self.organisaatio_id) | (
            Q(paos_toiminnat_paos_toimipaikka__oma_organisaatio=self.organisaatio_id)
            & Q(paos_toiminnat_paos_toimipaikka__voimassa_kytkin=True)
        )
        if self.toimipaikka_id:
            vakajarjestaja_filter &= Q(id=self.toimipaikka_id)

        toimipaikka_qs = (
            Toimipaikka.objects.filter(vakajarjestaja_filter & toimipaikka_filter)
            .select_related("vakajarjestaja")
            .prefetch_related("toiminnallisetpainotukset", "kielipainotukset")
            .distinct()
            .order_by("nimi", "vakajarjestaja_id")
        )

        kunta_codes = self._get_koodisto_with_translations(Koodistot.kunta_koodit.value)
        kasvatusjarjestelma_codes = self._get_koodisto_with_translations(Koodistot.kasvatusopillinen_jarjestelma_koodit.value)
        toiminnallinen_painotus_codes = self._get_koodisto_with_translations(Koodistot.toiminnallinen_painotus_koodit.value)
        kieli_codes = self._get_koodisto_with_translations(Koodistot.kieli_koodit.value)
        kielipainotustyyppi_codes = self._get_koodisto_with_translations(Koodistot.kielipainotustyyppi_koodit.value)
        toimintamuoto_codes = self._get_koodisto_with_translations(Koodistot.toimintamuoto_koodit.value)
        jarjestamismuoto_codes = self._get_koodisto_with_translations(Koodistot.jarjestamismuoto_koodit.value)
        lahdejarjestelma_codes = self._get_koodisto_with_translations(Koodistot.lahdejarjestelma_koodit.value)

        toimipaikka_sheet = self._add_worksheet(T.EXCEL_TOIMIPAIKKA_PLURAL)
        self._write_headers(toimipaikka_sheet, TOIMIPAIKKA_HEADERS)

        index = 1
        for toimipaikka in toimipaikka_qs.iterator(chunk_size=1000):
            painotus_list = list(toimipaikka.toiminnallisetpainotukset.all()) + list(toimipaikka.kielipainotukset.all())
            if len(painotus_list) == 0:
                # We want at least one row for toimipaikka
                painotus_list = [TemporaryObject()]
            for painotus in painotus_list:
                toimipaikka_values = [
                    toimipaikka.nimi,
                    toimipaikka.organisaatio_oid,
                    toimipaikka.id,
                    _get_code_translation(lahdejarjestelma_codes, toimipaikka.lahdejarjestelma),
                    toimipaikka.tunniste,
                ]

                if toimipaikka.vakajarjestaja_id != self.organisaatio_id:
                    toimipaikka_values.extend([toimipaikka.vakajarjestaja.nimi, toimipaikka.vakajarjestaja.organisaatio_oid])
                else:
                    toimipaikka_values.extend([None, None])

                toimipaikka_values.extend(
                    [
                        toimipaikka.alkamis_pvm,
                        toimipaikka.paattymis_pvm,
                        _get_code_translation(kasvatusjarjestelma_codes, toimipaikka.kasvatusopillinen_jarjestelma_koodi),
                        _get_code_translation(toimintamuoto_codes, toimipaikka.toimintamuoto_koodi),
                        _get_multiple_code_translations(kieli_codes, toimipaikka.toimintakieli_koodi),
                        _get_multiple_code_translations(jarjestamismuoto_codes, toimipaikka.jarjestamismuoto_koodi),
                        toimipaikka.varhaiskasvatuspaikat,
                        _get_code_translation(kunta_codes, toimipaikka.kunta_koodi),
                        toimipaikka.kayntiosoite,
                        toimipaikka.kayntiosoite_postinumero,
                        toimipaikka.kayntiosoite_postitoimipaikka,
                        toimipaikka.postiosoite,
                        toimipaikka.postinumero,
                        toimipaikka.postitoimipaikka,
                        toimipaikka.puhelinnumero,
                        toimipaikka.sahkopostiosoite,
                    ]
                )

                # Painotus information
                if not isinstance(painotus, TemporaryObject):
                    toimipaikka_values.extend(
                        [painotus.id, _get_code_translation(lahdejarjestelma_codes, painotus.lahdejarjestelma), painotus.tunniste]
                    )
                    if hasattr(painotus, "toimintapainotus_koodi"):
                        toimipaikka_values.extend(
                            [_get_code_translation(toiminnallinen_painotus_codes, painotus.toimintapainotus_koodi), None, None]
                        )
                    elif hasattr(painotus, "kielipainotus_koodi"):
                        toimipaikka_values.extend(
                            [
                                None,
                                _get_code_translation(kieli_codes, painotus.kielipainotus_koodi),
                                _get_code_translation(kielipainotustyyppi_codes, painotus.kielipainotustyyppi_koodi),
                            ]
                        )
                    toimipaikka_values.extend([painotus.alkamis_pvm, painotus.paattymis_pvm])

                self._write_row(toimipaikka_sheet, index, toimipaikka_values)
                index += 1

    def _create_vuosiraportti_report(self):
        tilasto_date = self.report.target_date
        poiminta_time = datetime.time(hour=23, minute=0, second=0)
        poiminta_datetime = datetime.datetime.combine(self.report.target_date_secondary, poiminta_time, datetime.timezone.utc)
        if self.report.report_subtype in (ExcelReportSubtype.ALL.value, ExcelReportSubtype.VARHAISKASVATUS.value):
            self._create_vuosiraportti_varhaiskasvatus(tilasto_date, poiminta_datetime)
        if self.report.report_subtype in (ExcelReportSubtype.ALL.value, ExcelReportSubtype.HENKILOSTO.value):
            self._create_vuosiraportti_henkilosto(tilasto_date, poiminta_datetime)

    def _create_vuosiraportti_varhaiskasvatus(self, tilasto_date, poiminta_datetime):
        sheet = self._add_worksheet(T.EXCEL_VARHAISKASVATUSTIEDOT)
        self._write_headers(sheet, VUOSIRAPORTTI_VARHAISKASVATUS_HEADERS)
        index = 1

        if organisaatio := self.report.organisaatio:
            organisaatio_count = 1
            if organisaatio.paattymis_pvm is None:
                organisaatio_active = organisaatio.alkamis_pvm <= tilasto_date
            else:
                organisaatio_active = organisaatio.alkamis_pvm <= tilasto_date <= organisaatio.paattymis_pvm
        else:
            organisaatio_count = get_yearly_report_organisaatio_count(poiminta_datetime, tilasto_date)
            organisaatio_active = True

        self._write_row(sheet, index, [self._get_translation(T.EXCEL_VAKATOIMIJA_VALITTU_PLURAL), organisaatio_count])
        index += 1
        self._write_row(
            sheet,
            index,
            [self._get_translation(T.EXCEL_VAKATOIMIJA_NIMI), getattr(organisaatio, "nimi", "")],
            align_right_index_list=[1],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [self._get_translation(T.EXCEL_VAKATOIMIJA_VOIMASSA), self._get_boolean_translation(organisaatio_active)],
            align_right_index_list=[1],
        )
        index += 2

        toimipaikka_data = get_yearly_report_toimipaikka_data(poiminta_datetime, tilasto_date, self.organisaatio_id)
        toimipaikka_count = toimipaikka_data.pop("toimipaikka_count")
        varhaiskasvatuspaikat_sum = toimipaikka_data.pop("varhaiskasvatuspaikat_sum")
        toimipaikka_by_toimintamuoto_count = toimipaikka_data

        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TOIMIPAIKKA_PLURAL), toimipaikka_count])
        index += 1
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_VARHAISKASVATUSPAIKAT_MAARA), varhaiskasvatuspaikat_sum])
        index += 1

        toiminnallinen_painotus_count = get_yearly_report_toiminnallinen_painotus_count(
            poiminta_datetime, tilasto_date, self.organisaatio_id
        )
        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_TOIMINNALLINEN_PAINOTUS_PLURAL), toiminnallinen_painotus_count]
        )
        index += 2

        tm_translations = self._get_koodisto_with_translations(Koodistot.toimintamuoto_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TOIMIPAIKKA_BY_TOIMINTAMUOTO)])
        index += 1
        for key, value in toimipaikka_by_toimintamuoto_count.items():
            self._write_row(sheet, index, [_get_code_translation(tm_translations, key), value])
            index += 1
        index += 1

        index = self._write_kielipainotus_data(sheet, index, poiminta_datetime, tilasto_date)
        index += 1

        index = self._write_toimintakieli_data(sheet, index, poiminta_datetime, tilasto_date)
        index += 1

        lapsi_id_data = get_yearly_report_lapsi_ids(poiminta_datetime, tilasto_date, self.organisaatio_id)
        lapsi_id_list = lapsi_id_data["lapsi_id_array"]
        varhaiskasvatussuhde_id_list = lapsi_id_data["varhaiskasvatussuhde_id_array"]

        # Nested dict: {paos (None, False): {toimintamuoto (None, 'tm01'): {...}}}
        vaka_data = get_yearly_report_vaka_data(poiminta_datetime, varhaiskasvatussuhde_id_list)

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_HENKILO_PLURAL),
                _get_nested_value(vaka_data, [None, None], "henkilo_count"),
                _get_nested_value(vaka_data, [False, None], "henkilo_count"),
                _get_nested_value(vaka_data, [True, None], "henkilo_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_PLURAL),
                _get_nested_value(vaka_data, [None, None], "lapsi_count"),
                _get_nested_value(vaka_data, [False, None], "lapsi_count"),
                _get_nested_value(vaka_data, [True, None], "lapsi_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_OSAPAIVAINEN),
                _get_nested_value(vaka_data, [None, None], "osapaivainen_count"),
                _get_nested_value(vaka_data, [False, None], "osapaivainen_count"),
                _get_nested_value(vaka_data, [True, None], "osapaivainen_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_KOKOPAIVAINEN),
                _get_nested_value(vaka_data, [None, None], "kokopaivainen_count"),
                _get_nested_value(vaka_data, [False, None], "kokopaivainen_count"),
                _get_nested_value(vaka_data, [True, None], "kokopaivainen_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_LAPSI_VUOROHOITO),
                _get_nested_value(vaka_data, [None, None], "vuorohoito_count"),
                _get_nested_value(vaka_data, [False, None], "vuorohoito_count"),
                _get_nested_value(vaka_data, [True, None], "vuorohoito_count"),
            ],
        )
        index += 2

        tm_codes = get_koodisto_codes_lower(Koodistot.toimintamuoto_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_LAPSI_BY_TOIMINTAMUOTO)])
        index += 1
        for tm_code in tm_codes:
            code_translation = _get_code_translation(tm_translations, tm_code)
            self._write_row(
                sheet,
                index,
                [
                    code_translation,
                    _get_nested_value(vaka_data, [None, tm_code], "lapsi_count"),
                    _get_nested_value(vaka_data, [False, tm_code], "lapsi_count"),
                    _get_nested_value(vaka_data, [True, tm_code], "lapsi_count"),
                ],
            )
            index += 1
        index += 1

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_VARHAISKASVATUSSUHDE_PLURAL),
                _get_nested_value(vaka_data, [None, None], "suhde_count"),
                _get_nested_value(vaka_data, [False, None], "suhde_count"),
                _get_nested_value(vaka_data, [True, None], "suhde_count"),
            ],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_VARHAISKASVATUSPAATOS_PLURAL),
                _get_nested_value(vaka_data, [None, None], "paatos_count"),
                _get_nested_value(vaka_data, [False, None], "paatos_count"),
                _get_nested_value(vaka_data, [True, None], "paatos_count"),
            ],
        )
        index += 2

        # Nested dict: {paos (None, True, False): {maksun_peruste (None, 'mp01', 'mp02', 'mp03'): {...}}}
        maksutieto_data = get_yearly_report_maksutieto_data(poiminta_datetime, tilasto_date, self.organisaatio_id, lapsi_id_list)

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_MAKSUTIETO_PLURAL),
                _get_nested_value(maksutieto_data, [None, None], "count"),
                _get_nested_value(maksutieto_data, [False, None], "count"),
                _get_nested_value(maksutieto_data, [True, None], "count"),
            ],
        )
        index += 2

        mp_codes = get_koodisto_codes_lower(Koodistot.maksun_peruste_koodit.value)
        mp_translations = self._get_koodisto_with_translations(Koodistot.maksun_peruste_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_MAKSUTIETO_BY_MAKSUN_PERUSTE)])
        index += 1
        for mp_code in mp_codes:
            self._write_row(
                sheet,
                index,
                [
                    _get_code_translation(mp_translations, mp_code),
                    _get_nested_value(maksutieto_data, [None, mp_code], "count"),
                    _get_nested_value(maksutieto_data, [False, mp_code], "count"),
                    _get_nested_value(maksutieto_data, [True, mp_code], "count"),
                ],
            )
            index += 1
        index += 1

        # Add tuen tiedot data if organisaatio is kunta
        if organisaatio is not None:
            organisaatio_yritysmuoto = getattr(organisaatio, "yritysmuoto", "")
        else:
            organisaatio_yritysmuoto = ""

        if organisaatio_yritysmuoto in YRITYSMUOTO_KUNTA:
            latest_tilastointi_pvm = get_latest_tilastointi_pvm_before_date(organisaatio, tilasto_date)
            paatosmaaras = get_tuen_tiedot_tuen_taso_paatosmaaras(organisaatio, latest_tilastointi_pvm)

            self._write_row(
                sheet,
                index,
                [
                    self._get_translation(T.EXCEL_TUEN_HALLINTOPAATOKSET),
                    paatosmaaras["total"] if paatosmaaras["total"] is not None else "-",
                ],
            )
            index += 1
            self._write_row(
                sheet,
                index,
                [self._get_translation(T.EXCEL_TILASTOINTIPAIVAMAARA), latest_tilastointi_pvm if latest_tilastointi_pvm else "-"],
            )
            index += 2
            self._write_row(sheet, index, [self._get_translation(T.EXCEL_TUKIPAATOSTIEDOT)])
            index += 1
            for tuentaso_code in ["TT01", "TT02", "TT03"]:
                self._write_row(
                    sheet,
                    index,
                    [
                        self._get_translation(getattr(T, f"EXCEL_TUENTASO_{tuentaso_code}")),
                        paatosmaaras[tuentaso_code] if paatosmaaras[tuentaso_code] is not None else "-",
                    ],
                )
                index += 1

    def _create_vuosiraportti_henkilosto(self, tilasto_date, poiminta_datetime):
        sheet = self._add_worksheet(T.EXCEL_HENKILOSTOTIEDOT)
        index = 0

        if organisaatio := self.report.organisaatio:
            organisaatio_count = 1
            if organisaatio.paattymis_pvm is None:
                organisaatio_active = organisaatio.alkamis_pvm <= tilasto_date
            else:
                organisaatio_active = organisaatio.alkamis_pvm <= tilasto_date <= organisaatio.paattymis_pvm
        else:
            organisaatio_count = get_yearly_report_organisaatio_count(poiminta_datetime, tilasto_date)
            organisaatio_active = True

        self._write_row(sheet, index, [self._get_translation(T.EXCEL_VAKATOIMIJA_VALITTU_PLURAL), organisaatio_count])
        index += 1
        self._write_row(
            sheet,
            index,
            [self._get_translation(T.EXCEL_VAKATOIMIJA_NIMI), getattr(organisaatio, "nimi", "")],
            align_right_index_list=[1],
        )
        index += 1
        self._write_row(
            sheet,
            index,
            [self._get_translation(T.EXCEL_VAKATOIMIJA_VOIMASSA), self._get_boolean_translation(organisaatio_active)],
            align_right_index_list=[1],
        )
        index += 2

        tyontekija_id_data = get_yearly_report_tyontekija_ids(poiminta_datetime, tilasto_date, self.organisaatio_id)
        palvelussuhde_id_list = tyontekija_id_data["palvelussuhde_id_array"]
        tyoskentelypaikka_id_list = tyontekija_id_data["tyoskentelypaikka_id_array"]

        # Nested dict: {tehtavanimike (None, '12345'): {...}}
        tyoskentelypaikka_data = get_yearly_report_tyoskentelypaikka_data(poiminta_datetime, tyoskentelypaikka_id_list)

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_TYONTEKIJA_PLURAL),
                _get_nested_value(tyoskentelypaikka_data, [None], "henkilo_count"),
            ],
        )
        index += 1

        multiple_tehtavanimike_count = get_yearly_report_tyontekija_multiple_tehtavanimike_count(
            poiminta_datetime, tyoskentelypaikka_id_list
        )
        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_TYONTEKIJA_TEHTAVANIMIKE_MULTIPLE), multiple_tehtavanimike_count]
        )
        index += 2

        tn_codes = get_koodisto_codes_lower(Koodistot.tehtavanimike_koodit.value)
        tn_translations = self._get_koodisto_with_translations(Koodistot.tehtavanimike_koodit.value)
        index_temp = index + len(tn_codes) + 2
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TYONTEKIJA_BY_TEHTAVANIMIKE)])
        index += 1
        self._write_row(sheet, index_temp, [self._get_translation(T.EXCEL_TYONTEKIJA_KELPOINEN_BY_TEHTAVANIMIKE)])
        index_temp += 1

        for tn_code in tn_codes:
            code_translation = _get_code_translation(tn_translations, tn_code)
            count = _get_nested_value(tyoskentelypaikka_data, [tn_code], "henkilo_count")
            kelpoiset_count = _get_nested_value(tyoskentelypaikka_data, [tn_code], "henkilo_kelpoinen_count")
            self._write_row(sheet, index, [code_translation, count])
            index += 1
            self._write_row(sheet, index_temp, [code_translation, kelpoiset_count])
            index_temp += 1
        index = index_temp + 1

        # Nested dict: {tyosuhde (None, '1', '2'): {tyoaika (None, '1', '2'): {...}}}
        palvelussuhde_data = get_yearly_report_palvelussuhde_data(poiminta_datetime, palvelussuhde_id_list)

        ts_codes = get_koodisto_codes_lower(Koodistot.tyosuhde_koodit.value)
        ts_translations = self._get_koodisto_with_translations(Koodistot.tyosuhde_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_PALVELUSSUHDE_BY_TYOSUHDE)])
        index += 1
        for ts_code in ts_codes:
            count = _get_nested_value(palvelussuhde_data, [ts_code, None], "palvelussuhde_count")
            self._write_row(sheet, index, [_get_code_translation(ts_translations, ts_code), count])
            index += 1
        index += 1

        ta_codes = get_koodisto_codes_lower(Koodistot.tyoaika_koodit.value)
        ta_translations = self._get_koodisto_with_translations(Koodistot.tyoaika_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_PALVELUSSUHDE_BY_TYOAIKA)])
        index += 1
        for ta_code in ta_codes:
            count = _get_nested_value(palvelussuhde_data, [None, ta_code], "palvelussuhde_count")
            self._write_row(sheet, index, [_get_code_translation(ta_translations, ta_code), count])
            index += 1
        index += 1

        self._write_row(
            sheet,
            index,
            [
                self._get_translation(T.EXCEL_TYONTEKIJA_KIERTAVA_PLURAL),
                _get_nested_value(tyoskentelypaikka_data, [None], "henkilo_kiertava_count"),
            ],
        )
        index += 2

        vuokrattu_henkilosto_data = get_yearly_report_vuokrattu_henkilosto_data(
            poiminta_datetime, tilasto_date, self.organisaatio_id
        )

        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_VUOKRATTU_HENKILOSTO_TYONTEKIJAMAARA), vuokrattu_henkilosto_data[0]]
        )
        index += 1
        self._write_row(
            sheet, index, [self._get_translation(T.EXCEL_VUOKRATTU_HENKILOSTO_TUNTIMAARA), vuokrattu_henkilosto_data[1]]
        )
        index += 2

        month_translation_list = [
            self._get_translation(T.EXCEL_JANUARY),
            self._get_translation(T.EXCEL_FEBRUARY),
            self._get_translation(T.EXCEL_MARCH),
            self._get_translation(T.EXCEL_APRIL),
            self._get_translation(T.EXCEL_MAY),
            self._get_translation(T.EXCEL_JUNE),
            self._get_translation(T.EXCEL_JULY),
            self._get_translation(T.EXCEL_AUGUST),
            self._get_translation(T.EXCEL_SEPTEMBER),
            self._get_translation(T.EXCEL_OCTOBER),
            self._get_translation(T.EXCEL_NOVEMBER),
            self._get_translation(T.EXCEL_DECEMBER),
        ]
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_FIXED_TERM_EMPLOYMENT)])
        index += 1
        fixed_term_count = get_yearly_report_fixed_term_data(poiminta_datetime, tilasto_date.year, 0, self.organisaatio_id)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_WHOLE_YEAR), fixed_term_count])
        index += 1
        for month_index in range(1, 13):
            fixed_term_count = get_yearly_report_fixed_term_data(
                poiminta_datetime, tilasto_date.year, month_index, self.organisaatio_id
            )
            self._write_row(sheet, index, [month_translation_list[month_index - 1], fixed_term_count])
            index += 1

    def _create_maksutieto_puuttuu_lapsi_report(self):
        # Overlapping Maksutieto
        overlapping_maksutieto_subquery = Maksutieto.objects.filter(
            huoltajuussuhteet__lapsi=OuterRef("id"), alkamis_pvm__lte=self.report.target_date
        ).filter(Q(paattymis_pvm__gte=self.report.target_date) | Q(paattymis_pvm__isnull=True))

        # Active Varhaiskasvatuspaatos and Varhaiskasvatussuhde subquery
        active_vakasuhde_subquery = (
            Varhaiskasvatuspaatos.objects.filter(lapsi=OuterRef("id"), alkamis_pvm__lte=self.report.target_date)
            .filter(
                Q(paattymis_pvm__gte=self.report.target_date) | Q(paattymis_pvm__isnull=True),
                varhaiskasvatussuhteet__alkamis_pvm__lte=self.report.target_date,
            )
            .filter(
                Q(varhaiskasvatussuhteet__paattymis_pvm__gte=self.report.target_date)
                | Q(varhaiskasvatussuhteet__paattymis_pvm__isnull=True)
            )
        )

        lapsi_qs = (
            Lapsi.objects.annotate(
                has_maksutieto_overlap=Exists(overlapping_maksutieto_subquery),
                has_active_vakasuhde=Exists(active_vakasuhde_subquery),
                active_huoltajuussuhteet_count=Count("huoltajuussuhteet", filter=Q(huoltajuussuhteet__voimassa_kytkin=True)),
            )
            .filter(
                has_maksutieto_overlap=False,
                has_active_vakasuhde=True,
                **({"vakatoimija": self.report.organisaatio} if self.report.organisaatio else {}),
            )
            .values(
                "henkilo__id",
                "henkilo__henkilo_oid",
                "henkilo__etunimet",
                "henkilo__sukunimi",
                "henkilo__henkilotunnus",
                "id",
                "active_huoltajuussuhteet_count",
                "vakatoimija__nimi",
            )
            .distinct()
            .order_by("vakatoimija__nimi", "henkilo__henkilo_oid")
        )

        maksutieto_puuttuu_sheet = self._add_worksheet(T.EXCEL_MAKSUTIETO_PUUTTUU_LAPSI)
        self._write_headers(maksutieto_puuttuu_sheet, MAKSUTIETO_PUUTTUU_LAPSI_HEADERS)
        for index, lapsi in enumerate(lapsi_qs.iterator(chunk_size=500), 1):
            lapsi_values = [
                lapsi["vakatoimija__nimi"],
                lapsi["henkilo__henkilo_oid"],
                lapsi["henkilo__etunimet"],
                lapsi["henkilo__sukunimi"],
                decrypt_henkilotunnus(lapsi["henkilo__henkilotunnus"], henkilo_id=lapsi["henkilo__id"], raise_error=False),
                lapsi["id"],
                lapsi["active_huoltajuussuhteet_count"],
            ]

            self._write_row(maksutieto_puuttuu_sheet, index, lapsi_values)

    def _write_kielipainotus_data(self, sheet, index, poiminta_datetime, tilasto_date):
        kielipainotus_data = get_yearly_report_kielipainotus_data(poiminta_datetime, tilasto_date, self.organisaatio_id)
        kielipainotus_count = kielipainotus_data.pop("kielipainotus_count")
        kielipainotus_count_by_kielipainotus_tyyppi = kielipainotus_data
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_KIELIPAINOTUS_PLURAL), kielipainotus_count])
        index += 1

        kp_translations = self._get_koodisto_with_translations(Koodistot.kielipainotustyyppi_koodit.value)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_KIELIPAINOTUS_PLURAL_TYYPPI_PLURAL)])
        index += 1
        for key, value in kielipainotus_count_by_kielipainotus_tyyppi.items():
            self._write_row(sheet, index, [_get_code_translation(kp_translations, key), value])
            index += 1

        return index

    def _write_toimintakieli_data(self, sheet, index, poiminta_datetime, tilasto_date):
        toimintakieli_data = get_yearly_report_toimintakieli_data(poiminta_datetime, tilasto_date, self.organisaatio_id)
        self._write_row(sheet, index, [self._get_translation(T.EXCEL_TOIMINTAKIELI)])
        index += 1

        kieli_codes = self._get_koodisto_with_translations(Koodistot.kieli_koodit.value)
        for toimintakieli_obj in toimintakieli_data:
            key = toimintakieli_obj["language_code"]
            value = toimintakieli_obj["value"]
            self._write_row(sheet, index, [_get_code_translation(kieli_codes, key), value])
            index += 1

        return index

    def _add_worksheet(self, translation_key):
        return self.workbook.add_worksheet(self._get_translation(translation_key))

    def _write_headers(self, worksheet, headers_name):
        headers = TRANSLATIONS[headers_name]
        for index, header in enumerate(headers):
            if not header:
                continue
            worksheet.write(0, index, self._get_translation(header))

    def _get_translation(self, translation_key):
        return get_translation(translation_key.value, self.language)

    def _get_boolean_translation(self, boolean_value):
        return self._get_translation(T.EXCEL_YES) if boolean_value else self._get_translation(T.EXCEL_NO)

    def _get_koodisto_with_translations(self, koodisto):
        return list(
            Z2_Code.objects.filter(Q(koodisto__name=koodisto) & Q(translations__language__iexact=self.language))
            .annotate(name=F("translations__name"))
            .values(
                "code_value",
                "name",
            )
        )

    def _generate_filename(self):
        default_name = self.report.report_type
        if self.report.report_subtype:
            default_name += f"_{self.report.report_subtype}"

        report_name_key = TRANSLATIONS[self.report.report_type]
        if isinstance(report_name_key, dict):
            report_name_key = report_name_key.get(self.report.report_subtype, default_name)

        report_name = self._get_translation(report_name_key)

        if self.admin_user_all_organizations:
            datetime_string = self.report.target_date.strftime("%Y%m%d_%H%M%S")
        else:
            datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        while True:
            unique_identifier = str(uuid.uuid4())[:8]
            filename = f"{report_name}_{datetime_string}_{unique_identifier}.xlsx"
            if not Z8_ExcelReport.objects.filter(filename=filename).exists():
                # Generate filenames until we get one that does not already exist
                return filename

    def _get_s3_object_path(self):
        if self.admin_user_all_organizations:
            return "admin/"
        elif self.toimipaikka_id:
            return f"vakajarjestajat/{self.organisaatio_id}/toimipaikat/{self.toimipaikka_id}/"
        return f"vakajarjestajat/{self.organisaatio_id}/"

    def _write_row(self, worksheet, row, values, align_right_index_list=()):
        for index, value in enumerate(values):
            if not value and (value is None or value == ""):
                # If value is None or empty string, do not write it, however write numbers that equal 0
                continue

            if isinstance(value, datetime.date):
                worksheet.write_datetime(row, index, value)
            elif isinstance(value, int):
                worksheet.write(row, index, value, self.integer_format)
            elif isinstance(value, float) or isinstance(value, Decimal):
                worksheet.write(row, index, value, self.float_format)
            else:
                if index in align_right_index_list:
                    worksheet.write(row, index, value, self.align_right_format)
                else:
                    worksheet.write(row, index, value)


def _get_code_translation(code_list, code):
    if not code:
        return None
    for code_list_item in code_list:
        if code_list_item.get("code_value").lower() == code.lower():
            return f'{code_list_item.get("name")} ({code.lower()})'
    return code


def _get_multiple_code_translations(code_list, code_value_list):
    return ", ".join([_get_code_translation(code_list, code_value) for code_value in code_value_list])


def _get_dates_for_model_and_id(model_name, model_id):
    app_config = apps.get_app_config("varda")
    model = app_config.get_model(model_name)
    if isinstance(model(), Model):
        if model_instance := model.objects.filter(id=model_id).first():
            if hasattr(model_instance, "alkamis_pvm") and hasattr(model_instance, "paattymis_pvm"):
                alkamis_pvm = model_instance.alkamis_pvm.strftime("%d.%m.%Y") if model_instance.alkamis_pvm else ""
                paattymis_pvm = model_instance.paattymis_pvm.strftime("%d.%m.%Y") if model_instance.paattymis_pvm else ""
                return f"{alkamis_pvm}-{paattymis_pvm}"


def _upload_excel_to_s3(file_path, filename):
    if settings.PRODUCTION_ENV:
        env = "prod"
    elif settings.QA_ENV:
        env = "qa"
    else:
        env = "dev"
    bucket_name = f"{env}-{settings.S3_EXCEL_REPORTS}"
    s3_client = S3Client(bucket_name)
    for index in range(0, 5):
        # Try to upload max five times
        result = s3_client.upload_fileobj(file_path, bucket_name, filename)
        if result:
            return True
    return False


def get_s3_object_name(report_instance):
    return f"{report_instance.s3_object_path}{report_instance.filename}"


def get_excel_local_file_path(report_instance):
    return f"{settings.EXCEL_PATH}{report_instance.filename}"


def delete_excel_reports_earlier_than(timestamp):
    report_qs = Z8_ExcelReport.objects.filter(timestamp__lt=timestamp)

    if settings.PRODUCTION_ENV:
        env = "prod"
    elif settings.QA_ENV:
        env = "qa"
    else:
        env = "dev"
    bucket_name = f"{env}-{settings.S3_EXCEL_REPORTS}"
    s3_client = S3Client(bucket_name)

    for report in report_qs:
        if s3_client:
            # In production, QA and DEV environments delete the file from S3
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
                logger.error(f"Error deleting Excel file: {os_error}")


def _encrypt_excel_file(file_path, password):
    """
    Use context management for response object so that data is read and closed properly
    Without it with larger files the process may fail without warning or with error such as
    requests.exceptions.ChunkedEncodingError: ('Connection broken: IncompleteRead(...)',)
    https://requests.readthedocs.io/en/latest/user/advanced/#body-content-workflow
    :param file_path: Excel file path
    :param password: Excel file password
    :return: True if encryption was successful, else False
    """
    with (
        open(file_path, "r+b") as file,
        requests.post(
            # Appmesh TLS handles endpoint verification so we verify=False here to avoid adding a custom CA bundle
            f"{settings.JAVA_URL}/upload",
            files={
                "excel": file,
                "password": (
                    None,
                    password,
                ),
            },
            stream=True,
            verify=False,
        ) as resp,
    ):
        if resp and resp.status_code == status.HTTP_200_OK:
            # File has already been read so move pointer to the beginning of the file
            file.seek(0)
            # Write (encrypted) response contents to the file
            shutil.copyfileobj(resp.raw, file)
            # Truncate any (unencrypted) content after the current pointer location
            file.truncate()
            # Return True as encryption has been successful
            return True
        elif resp is not None:
            logger.error(f"Excel encryption request error, status code: {resp.status_code}, response: {resp.text}")

    # Remove local file if encryption was unsuccessful
    os.remove(file_path)
    return False


def _get_nested_value(nested_dict, value_path, value_key, default_value=0):
    temp_dict = nested_dict
    for path_key in value_path:
        temp_dict = temp_dict.get(path_key, {})
    return temp_dict.get(value_key, default_value)
