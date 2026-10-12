import logging
import os
import uuid

from celery import current_task
from django.conf import settings
from pythonjsonlogger.jsonlogger import JsonFormatter

from varda.custom_middleware import local_thread
from varda.helper_functions import hide_hetu


class ProductionLikeFilter(logging.Filter):
    def filter(self, record):
        return settings.PRODUCTION_ENV or settings.QA_ENV


class StdoutFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelname.upper() in ["DEBUG", "INFO", "WARNING"]


class StderrFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelname.upper() not in ["DEBUG", "INFO", "WARNING"]


class CeleryFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Returns True if logger name starts with 'celery' or current Celery task exists (worker is running the process)
        is_celery_logger = getattr(record, "name", "").lower().startswith("celery")
        return True if is_celery_logger or current_task else False


class SensitiveJsonFormatter(JsonFormatter):
    def add_fields(self, log_record: dict[str, any], record: logging.LogRecord, message_dict: dict[str, any]) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["source"] = "python"
        log_record["host"] = self._get_host()
        log_record["requestId"] = self._get_request_id()
        log_record["username"] = getattr(local_thread, "username", "")

    def format(self, record: logging.LogRecord) -> str:
        formatted_record = super().format(record)
        return hide_hetu(formatted_record, hide_date=False)

    def _get_host(self):
        if hostname := os.getenv("VARDA_HOSTNAME", None):
            return hostname
        return getattr(local_thread, "request_host", "")

    def _get_request_id(self):
        # If there is no request ID, let's generate one
        if not hasattr(local_thread, "request_id"):
            uuido = uuid.uuid4()
            uuids = str(uuido)
            uuids = uuids.replace("-", "")
            local_thread.request_id = uuids

        # Use camel case so that it matches Nginx field name
        return getattr(local_thread, "request_id", "")
