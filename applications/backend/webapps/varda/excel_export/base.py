import datetime
import logging
import math
import os
import uuid

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models import F, Q
from django.utils import timezone
from xlsxwriter.exceptions import XlsxFileError

from varda.enums.data_access_type import DataAccessType
from varda.enums.reporting import ReportStatus
from varda.enums.translation import Translation as T
from varda.excel_export.storage import _encrypt_excel_file, _upload_excel_to_s3, get_excel_local_file_path
from varda.excel_export.workbook import AutofitWorkbook
from varda.lokalisointipalvelu import get_translation
from varda.misc import decrypt_excel_report_password
from varda.models import Z2_Code, Z8_ExcelReport, Z8_ExcelReportLog
from varda.request_logging import save_data_access_log

logger = logging.getLogger(__name__)


class BaseExcelReportGenerator:
    """
    Common base for Excel reports. Subclasses set filename_key and implement _create_excel_report().
    """

    filename_key = None

    def __init__(self, report, data_db_alias=DEFAULT_DB_ALIAS):
        self.report = report
        self.data_db_alias = data_db_alias
        self.language = report.language
        self.admin_user_all_organizations = report.admin_user_all_organizations
        self.organisaatio_id = getattr(report.organisaatio, "id", None)
        self.toimipaikka_id = getattr(report.toimipaikka, "id", None)

        self.workbook = None
        self.integer_format = None
        self.float_format = None
        self.align_right_format = None

        self.henkilo_id_oid_set = set()

    def _create_excel_report(self):
        raise NotImplementedError

    def _get_filename_key(self):
        if self.filename_key is None:
            raise NotImplementedError(f"{type(self).__name__} must define filename_key or override _get_filename_key()")
        return self.filename_key

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

    def _target_date(self):
        return self.report.target_date or datetime.date.today()

    def _add_worksheet(self, translation_key):
        MAX_SHEET_NAME_LENGTH = 30
        translation = self._get_translation(translation_key)
        return self.workbook.add_worksheet(translation[:MAX_SHEET_NAME_LENGTH])

    def _write_headers(self, worksheet, headers):
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
            Z2_Code.objects.using(self.data_db_alias)
            .filter(Q(koodisto__name=koodisto) & Q(translations__language__iexact=self.language))
            .annotate(name=F("translations__name"))
            .values(
                "code_value",
                "name",
            )
        )

    def _generate_filename(self):
        report_name = self._get_translation(self._get_filename_key())

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
