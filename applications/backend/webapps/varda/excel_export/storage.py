import gzip
import json
import logging
import os
import shutil

from pathlib import Path

import requests

from django.conf import settings
from rest_framework import status

from varda.clients.aws_s3_client import Client as S3Client
from varda.excel_export.constants import ExcelReportType
from varda.models import Z8_ExcelReport

logger = logging.getLogger(__name__)


def _upload_excel_to_s3(file_path, filename):
    bucket_name = _get_report_storage_bucket_name()
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


def _get_report_storage_bucket_name():
    if settings.PRODUCTION_ENV:
        env = "prod"
    elif settings.QA_ENV:
        env = "qa"
    else:
        env = "dev"
    return f"{env}-{settings.S3_EXCEL_REPORTS}"


def _uses_report_object_storage():
    return settings.PRODUCTION_ENV or settings.QA_ENV or (settings.DEV_ENV and settings.ENVIRONMENT_TYPE is not None)


_TYONTEKIJATIEDOT_JSON_NIMET = {
    ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value: "voimassa",
    ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value: "maaraaikaiset_voimassa",
}
_TOIMIPAIKAT_JSON_NIMET = {ExcelReportType.TOIMIPAIKAT_VOIMASSA.value: "voimassa"}


def get_tyontekijatiedot_json_nimet(report):
    raportti = _TYONTEKIJATIEDOT_JSON_NIMET.get(report.report_type)
    if raportti is None:
        raise ValueError(f"Unsupported employee report type {report.report_type}")
    nimi = f"tyontekijatiedot_{raportti}"
    return {
        "object": f"massahaut/{report.id}/{nimi}.json.gz",
        "access_object": f"massahaut/{report.id}/{nimi}.access.json.gz",
        "local": f"{settings.EXCEL_PATH}massahaku_{report.id}_{nimi}.json.gz",
        "access_local": f"{settings.EXCEL_PATH}massahaku_{report.id}_{nimi}.access.json.gz",
    }


def _store_gzip_json_artifact(report, file_path, object_name, data):
    try:
        Path(settings.EXCEL_PATH).mkdir(parents=True, exist_ok=True)
        file_descriptor = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(file_descriptor, "wb") as file:
            with gzip.open(file, "wt", encoding="utf-8") as json_file:
                json.dump(data, json_file, separators=(",", ":"))
    except (OSError, TypeError) as exception:
        logger.error("Unable to create JSON artifact for mass report %s: %s", report.id, exception)
        raise

    if _uses_report_object_storage():
        upload_result = _upload_excel_to_s3(file_path, object_name)
        if not upload_result:
            raise RuntimeError(f"Unable to upload JSON artifact for mass report {report.id}")
        os.remove(file_path)


def store_tyontekijatiedot_json(report, json_data, henkilo_id_oid_set):
    nimet = get_tyontekijatiedot_json_nimet(report)
    _store_gzip_json_artifact(
        report,
        nimet["local"],
        nimet["object"],
        json_data,
    )
    _store_gzip_json_artifact(
        report,
        nimet["access_local"],
        nimet["access_object"],
        sorted(henkilo_id_oid_set),
    )


def get_toimipaikat_json_nimet(report):
    if report.report_type not in _TOIMIPAIKAT_JSON_NIMET:
        raise ValueError(f"Unsupported toimipaikat report type {report.report_type}")
    nimi = f"toimipaikat_{_TOIMIPAIKAT_JSON_NIMET[report.report_type]}"
    return {
        "object": f"massahaut/{report.id}/{nimi}.json.gz",
        "local": f"{settings.EXCEL_PATH}massahaku_{report.id}_{nimi}.json.gz",
    }


def store_toimipaikat_json(report, json_data):
    nimet = get_toimipaikat_json_nimet(report)
    _store_gzip_json_artifact(report, nimet["local"], nimet["object"], json_data)


def read_toimipaikat_json(report):
    nimet = get_toimipaikat_json_nimet(report)
    return _read_gzip_json_artifact(report, nimet["local"], nimet["object"])


def _read_gzip_json_artifact(report, file_path, object_name):
    if _uses_report_object_storage():
        artifact = S3Client(_get_report_storage_bucket_name()).get_file(object_name)
        if artifact is None:
            return None
        try:
            return json.loads(gzip.decompress(artifact))
        except (OSError, gzip.BadGzipFile, json.JSONDecodeError, UnicodeDecodeError) as exception:
            logger.error("Unable to read JSON artifact for mass report %s: %s", report.id, exception)
            return None

    try:
        with gzip.open(file_path, "rt", encoding="utf-8") as json_file:
            return json.load(json_file)
    except (OSError, gzip.BadGzipFile, json.JSONDecodeError, UnicodeDecodeError) as exception:
        logger.error("Unable to read JSON artifact for mass report %s: %s", report.id, exception)
        return None


def read_tyontekijatiedot_json(report):
    nimet = get_tyontekijatiedot_json_nimet(report)
    return _read_gzip_json_artifact(
        report,
        nimet["local"],
        nimet["object"],
    )


def read_tyontekijatiedot_json_access(report):
    nimet = get_tyontekijatiedot_json_nimet(report)
    access_data = _read_gzip_json_artifact(
        report,
        nimet["access_local"],
        nimet["access_object"],
    )
    return [tuple(item) for item in access_data] if access_data is not None else None


def _delete_tyontekijatiedot_s3_artifacts(s3_client, report):
    if report.report_type not in _TYONTEKIJATIEDOT_JSON_NIMET:
        return True

    nimet = get_tyontekijatiedot_json_nimet(report)
    json_result = s3_client.delete_file(nimet["object"])
    access_result = s3_client.delete_file(nimet["access_object"])
    return json_result and access_result


def _delete_toimipaikat_s3_artifacts(s3_client, report):
    if report.report_type not in _TOIMIPAIKAT_JSON_NIMET:
        return True
    nimet = get_toimipaikat_json_nimet(report)
    return s3_client.delete_file(nimet["object"])


def _delete_tyontekijatiedot_local_artifacts(report):
    if report.report_type not in _TYONTEKIJATIEDOT_JSON_NIMET:
        return True

    nimet = get_tyontekijatiedot_json_nimet(report)
    success = True
    for file_path in (nimet["local"], nimet["access_local"]):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as os_error:
            success = False
            logger.error(f"Error deleting JSON artifact: {os_error}")
    return success


def _delete_toimipaikat_local_artifacts(report):
    if report.report_type not in _TOIMIPAIKAT_JSON_NIMET:
        return True
    nimet = get_toimipaikat_json_nimet(report)
    try:
        if os.path.exists(nimet["local"]):
            os.remove(nimet["local"])
    except OSError as os_error:
        logger.error(f"Error deleting JSON artifact: {os_error}")
        return False
    return True


def delete_excel_reports_earlier_than(timestamp):
    report_qs = Z8_ExcelReport.objects.filter(timestamp__lt=timestamp)

    s3_client = S3Client(_get_report_storage_bucket_name()) if _uses_report_object_storage() else None

    for report in report_qs:
        if s3_client:
            # In production, QA and DEV environments delete the file from S3
            for index in range(0, 5):
                # Try to deletion five times
                result = s3_client.delete_file(get_s3_object_name(report))
                json_result = _delete_tyontekijatiedot_s3_artifacts(s3_client, report) and _delete_toimipaikat_s3_artifacts(
                    s3_client, report
                )
                if result and json_result:
                    # Deleted from S3 so delete instance from database
                    report.delete()
                    break
        else:
            # In other environments delete the local file
            excel_deleted = True
            try:
                os.remove(get_excel_local_file_path(report))
            except OSError as os_error:
                excel_deleted = False
                logger.error(f"Error deleting Excel file: {os_error}")
            json_artifacts_deleted = _delete_tyontekijatiedot_local_artifacts(report) and _delete_toimipaikat_local_artifacts(
                report
            )
            if excel_deleted and json_artifacts_deleted:
                # Deleted locally so delete instance from database
                report.delete()


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
            f"{settings.JAVA_URL}/upload",
            files={
                "excel": file,
                "password": (
                    None,
                    password,
                ),
            },
            stream=True,
            verify="/tls/ca.crt",
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
