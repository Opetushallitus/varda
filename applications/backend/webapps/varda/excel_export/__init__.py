"""
Excel reports. Tasks are kept in this module so that Celery task names (varda.excel_export.*) do not change.
"""

import logging

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

from varda.custom_celery import custom_shared_task
from varda.enums.reporting import ReportStatus
from varda.excel_export.constants import ExcelReportType
from varda.excel_export.reports import REPORT_GENERATORS
from varda.excel_export.reports.toimipaikat import (
    create_toimipaikat_voimassa_json_from_data,
    load_toimipaikat_voimassa_data,
)
from varda.excel_export.reports.tyontekijatiedot import (
    _massahaku_snapshot,
    create_tyontekijatiedot_json_from_data,
    load_tyontekijatiedot_data,
)
from varda.excel_export.storage import store_toimipaikat_json, store_tyontekijatiedot_json
from varda.models import Z8_ExcelReport

logger = logging.getLogger(__name__)


def _get_report_generator(report, **kwargs):
    generator_class = REPORT_GENERATORS.get(report.report_type)
    if not generator_class:
        logger.error(f"Unknown Excel report type {report.report_type} for report {report.id}")
        report.status = ReportStatus.FAILED.value
        report.save(using=DEFAULT_DB_ALIAS)
        return None
    return generator_class(report, **kwargs)


@custom_shared_task(single_instance=True)
def create_excel_report_task(report_id):
    report = Z8_ExcelReport.objects.filter(id=report_id).first()
    if not report or report.status != ReportStatus.PENDING.value:
        logger.error(f"Error starting Excel report creation with id {report_id}")
        return

    if report_generator := _get_report_generator(report):
        report_generator.generate()


@custom_shared_task(single_instance=True)
def create_mass_excel_report_task(report_id):
    report = Z8_ExcelReport.objects.using(DEFAULT_DB_ALIAS).filter(id=report_id).first()
    if not report or report.status != ReportStatus.PENDING.value:
        logger.error(f"Error starting Excel report creation with id {report_id}")
        return

    logger.info(
        "Starting mass Excel report generation: report_id=%s report_type=%s data_db_alias=%s",
        report.id,
        report.report_type,
        settings.READER_DB,
    )
    try:
        if report.report_type in (
            ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value,
            ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value,
        ):
            report.status = ReportStatus.CREATING.value
            report.save(using=DEFAULT_DB_ALIAS)
            with _massahaku_snapshot(settings.READER_DB):
                report_generator = _get_report_generator(report, data_db_alias=settings.READER_DB)
                report_data = load_tyontekijatiedot_data(report_generator, report_generator._get_palvelussuhde_filter())
                report_generator.report_data = report_data
            henkilo_id_oid_set = report_data["henkilo_id_oid_set"]
            json_data = create_tyontekijatiedot_json_from_data(report_data, report.report_type)
            store_tyontekijatiedot_json(report, json_data, henkilo_id_oid_set)
        elif report.report_type == ExcelReportType.TOIMIPAIKAT_VOIMASSA.value:
            report.status = ReportStatus.CREATING.value
            report.save(using=DEFAULT_DB_ALIAS)
            with _massahaku_snapshot(settings.READER_DB):
                report_generator = _get_report_generator(report, data_db_alias=settings.READER_DB)
                report_data = load_toimipaikat_voimassa_data(report_generator)
                report_generator.report_data = report_data
            store_toimipaikat_json(report, create_toimipaikat_voimassa_json_from_data(report_data))
        else:
            report_generator = _get_report_generator(report, data_db_alias=settings.READER_DB)
        if not report_generator:
            return
        report_generator.generate()
        logger.info(
            "Mass Excel report generation completed: report_id=%s report_type=%s data_db_alias=%s status=%s",
            report.id,
            report.report_type,
            settings.READER_DB,
            report.status,
        )
    except Exception:
        logger.exception("Mass Excel report generation failed for report %s", report.id)
        report.status = ReportStatus.FAILED.value
        report.save(using=DEFAULT_DB_ALIAS)
        raise
