import datetime
import json
import logging
import os

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from varda.apps import init_alive_log
from varda.clients.oph_audit_log_client import Client
from varda.constants import ALIVE_BOOT_TIME_CACHE_KEY, ALIVE_SEQ_CACHE_KEY
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.misc import get_queryset_in_chunks
from varda.models import Aikaleima, LogData, Z5_AuditLog, Z12_DataAccessLog


logger = logging.getLogger(__name__)

# The maximum number of log events in a batch is 10 000.
AWS_LOG_BATCH_MAX_SIZE = 10000
# The maximum batch size is 1 048 576 bytes
AWS_LOG_BATCH_MAX_BYTES = 1048576
# Overhead added to each event message
AWS_OVERHEAD_IN_BYTES_PER_EVENT = 26
# Events in a batch cannot span more than 24 hours, but use 22 hours as limit just to be safe
AWS_SPAN_LIMIT_IN_MS = 1000 * 60 * 60 * 22


def get_size(event):
    return (len(event["message"].encode("utf-8")) if isinstance(event, dict) else 1) + AWS_OVERHEAD_IN_BYTES_PER_EVENT


def get_batch_size_in_bytes(audit_log_batch):
    """
    https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutLogEvents.html

    The maximum batch size is 1,048,576 bytes, and this size is calculated as the
    sum of all event messages in UTF-8, plus 26 bytes for each log event.
    """
    return sum(get_size(event) for event in audit_log_batch)


def get_batch_end_index(audit_log_events, start_index):
    """
    Determine end index of batch that conforms to AWS restrictions.
    :param audit_log_events: list of all log events to be sent
    :param start_index: from which index we need to start the batch
    :return: end index of the batch
    """
    batch_size = AWS_LOG_BATCH_MAX_SIZE
    end_index = len(audit_log_events)

    while batch_size > 0:
        end_index = min(len(audit_log_events), start_index + batch_size)

        # Calculate batch size in bytes
        audit_log_batch = audit_log_events[start_index:end_index]
        batch_size_in_bytes = get_batch_size_in_bytes(audit_log_batch)
        exceeds_size = batch_size_in_bytes > AWS_LOG_BATCH_MAX_BYTES

        # Determine timespan of the batch
        first_timestamp = audit_log_events[start_index]["timestamp"]
        # end_index is exclusive so get timestamp of last event in current batch
        last_timestamp = audit_log_events[end_index - 1]["timestamp"]
        exceeds_timespan = abs(last_timestamp - first_timestamp) > AWS_SPAN_LIMIT_IN_MS

        if exceeds_size or exceeds_timespan:
            # Reduce batch size, exceeds size or timespan restrictions
            if batch_size > 1000:
                batch_size -= 1000
            elif 100 < batch_size <= 1000:
                batch_size -= 100
            elif 10 < batch_size <= 100:
                batch_size -= 10
            else:
                batch_size -= 1
        else:
            # Batch is the right size and timespan, exit loop
            break

    return end_index


def get_epoch_time_in_ms(date_time):
    return int(date_time.timestamp() * 1000)


def get_audit_log_row(log_seq, hostname, environment, timestamp, operation, target_url, query_params, username):
    return json.dumps(
        {
            "version": 1,
            "logSeq": log_seq,
            "type": "log",
            "hostname": hostname,
            "timestamp": timestamp.isoformat(),
            "environment": environment,
            "serviceName": "varda",
            "applicationType": "backend",
            "operation": operation,
            "target": target_url,
            "query_params": query_params,
            "user": username,
        }
    )


def send_read_audit_log(aws_log_client, datetime_end, hostname, environment):
    stream_name = "varda-get-stream"
    aikaleima_avain = AikaleimaAvain.AUDIT_LOG_AWS_LAST_UPDATE.value.format("READ")
    aikaleima, created = Aikaleima.objects.get_or_create(avain=aikaleima_avain)

    audit_log_qs = (
        Z5_AuditLog.objects.filter(time_of_event__gte=aikaleima.aikaleima)
        .filter(time_of_event__lt=datetime_end)
        .order_by("time_of_event")
    )
    log_data, created = LogData.objects.get_or_create(log_type=stream_name)

    for audit_log_chunk in get_queryset_in_chunks(audit_log_qs, chunk_size=AWS_LOG_BATCH_MAX_SIZE):
        # Process audit log events in batches of AWS_LOG_BATCH_MAX_SIZE to limit memory usage
        audit_log_list = []
        for audit_log in audit_log_chunk:
            log_data.log_seq += 1
            audit_log_list.append(
                {
                    "timestamp": get_epoch_time_in_ms(audit_log.time_of_event),
                    "message": get_audit_log_row(
                        log_data.log_seq,
                        hostname,
                        environment,
                        audit_log.time_of_event,
                        "GET",
                        audit_log.successful_get_request_path,
                        audit_log.query_params,
                        audit_log.user.username,
                    ),
                }
            )

        is_successful = post_log_events(aws_log_client, stream_name, audit_log_list, log_data, aikaleima)
        if not is_successful:
            # Post failed, stop processing and do not save Aikaleima
            return None

    # Successfully sent all logs, update Aikaleima
    aikaleima.aikaleima = datetime_end
    aikaleima.save()


def get_api_endpoint_from_model_name(model_name_verbose_plural):
    endpoint = model_name_verbose_plural
    endpoint = endpoint.replace(" ", "")
    endpoint = endpoint.replace("ö", "o")
    endpoint = endpoint.replace("ä", "a")
    return endpoint


def send_changed_model_log(aws_log_client, model_name, datetime_end, hostname, environment):
    stream_name = f"varda-changed-{model_name}-stream"
    aikaleima_avain = AikaleimaAvain.AUDIT_LOG_AWS_LAST_UPDATE.value.format(model_name.upper())
    aikaleima, created = Aikaleima.objects.get_or_create(avain=aikaleima_avain)

    model = apps.get_model("varda", model_name)
    api_endpoint = get_api_endpoint_from_model_name(model._meta.verbose_name_plural)

    historical_filter = Q(history_date__gte=aikaleima.aikaleima, history_date__lt=datetime_end)
    if model_name == "henkilo":
        # We want to exclude the changes coming from Oppijanumerorekisteri.
        historical_filter &= Q(history_type__in=["+", "-"])

    historical_qs = model.history.filter(historical_filter).order_by("history_date")
    log_data, created = LogData.objects.get_or_create(log_type=stream_name)

    for historical_data_chunk in get_queryset_in_chunks(historical_qs, chunk_size=AWS_LOG_BATCH_MAX_SIZE):
        # Process historical data in batches of AWS_LOG_BATCH_MAX_SIZE to limit memory usage
        historical_data_list = []
        for historical_data in historical_data_chunk:
            log_data.log_seq += 1
            change_url = "/api/v1/{}/{}/".format(api_endpoint, historical_data.id)
            history_user = historical_data.history_user
            username = history_user.username if history_user else "None"

            match historical_data.history_type:
                case "+":
                    operation = "CREATE"
                case "-":
                    operation = "DELETE"
                case _:
                    operation = "CHANGE"

            historical_data_list.append(
                {
                    "timestamp": get_epoch_time_in_ms(historical_data.history_date),
                    "message": get_audit_log_row(
                        log_data.log_seq,
                        hostname,
                        environment,
                        historical_data.history_date,
                        operation,
                        change_url,
                        None,
                        username,
                    ),
                }
            )

        is_successful = post_log_events(aws_log_client, stream_name, historical_data_list, log_data, aikaleima)
        if not is_successful:
            # Post failed, stop processing and do not save Aikaleima
            return None

    # Successfully sent all logs, update Aikaleima
    aikaleima.aikaleima = datetime_end
    aikaleima.save()


def collect_audit_log_and_send_to_aws():
    aws_log_client = Client()
    hostname = os.getenv("VARDA_HOSTNAME", "localhost")
    environment = "production" if settings.PRODUCTION_ENV else "testing"

    datetime_end = datetime.datetime.now(tz=datetime.timezone.utc)

    # GET-requests need special handling (taken from Z5_AuditLog)
    send_read_audit_log(aws_log_client, datetime_end, hostname, environment)

    # CREATE, UPDATE, DELETE (taken from historical-models)
    for varda_model in apps.get_app_config("varda").get_models():
        if hasattr(varda_model, "history"):
            send_changed_model_log(aws_log_client, varda_model.get_name(), datetime_end, hostname, environment)


def post_log_events(aws_client, stream_name, event_list, log_data, aikaleima):
    """
    Post log events to CloudWatch.
    :param aws_client: oph_audit_log_client.Client
    :param stream_name: CloudWatch log stream name
    :param event_list: list of events
    :param log_data: LogData instance
    :param aikaleima: Aikaleima instance
    :return: True if request was successful, else false
    """
    is_successful = True
    start_index = 0

    # Immediately return True if e.g. event_list is empty
    while event_list:
        end_index = get_batch_end_index(event_list, start_index)
        log_batch = event_list[start_index:end_index]

        response_status = aws_client.post_audit_log(stream_name, log_batch)

        if response_status == 200:
            last_message = json.loads(log_batch[-1]["message"])
            # Save log_seq
            log_data.log_seq = last_message["logSeq"]
            log_data.save()

            # Update Aikaleima in case next batch fails
            aikaleima.aikaleima = datetime.datetime.fromisoformat(last_message["timestamp"])
            aikaleima.save()

            start_index = end_index
            if len(event_list) == end_index:
                # This was the last batch, exit loop
                break
        else:
            logger.error(f"Log post to AWS failed with status code: {response_status}")
            is_successful = False
            break

    return is_successful


def send_alive_log_to_aws():
    log_seq = cache.get(ALIVE_SEQ_CACHE_KEY)
    boot_time = cache.get(ALIVE_BOOT_TIME_CACHE_KEY)
    if log_seq is None or boot_time is None:
        log_seq, boot_time = init_alive_log()

    aws_client = Client()
    stream_name = "varda-alive-stream"

    hostname = os.getenv("VARDA_HOSTNAME", "localhost")
    environment = "production" if settings.PRODUCTION_ENV else "testing"
    timestamp = timezone.now()
    message = "started" if log_seq == 0 else "alive"
    audit_log_events = [
        {
            "timestamp": get_epoch_time_in_ms(timestamp),
            "message": json.dumps(
                {
                    "version": 1,
                    "logSeq": log_seq,
                    "type": "alive",
                    "bootTime": str(boot_time),
                    "hostname": hostname,
                    "environment": environment,
                    "timestamp": str(timestamp),
                    "serviceName": "varda",
                    "applicationType": "backend",
                    "message": message,
                }
            ),
        }
    ]

    post_http_status_code = aws_client.post_audit_log(stream_name, audit_log_events)  # 200 is successful
    if post_http_status_code == 200:
        cache.set(ALIVE_SEQ_CACHE_KEY, log_seq + 1, None)
    else:
        logger.warning(f"Alive log post to aws failed with status code: {post_http_status_code}")


def send_data_access_log():
    aws_client = Client()
    hostname = os.getenv("VARDA_HOSTNAME", "localhost")
    environment = "production" if settings.PRODUCTION_ENV else "testing"
    boot_time = cache.get(ALIVE_BOOT_TIME_CACHE_KEY, None)
    # Transform boot_time to ISO string if it exists
    boot_time_str = boot_time.isoformat() if boot_time else None

    stream_name = "varda-data-access-stream"
    aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.DATA_ACCESS_LOG_AWS_LAST_UPDATE.value)
    end_timestamp = timezone.now()
    log_data, created = LogData.objects.get_or_create(log_type=stream_name)

    data_access_log_qs = Z12_DataAccessLog.objects.filter(
        timestamp__gt=aikaleima.aikaleima, timestamp__lte=end_timestamp
    ).order_by("timestamp")

    # Build event list from DataAccessLog instances
    for data_access_chunk in get_queryset_in_chunks(data_access_log_qs, chunk_size=AWS_LOG_BATCH_MAX_SIZE):
        event_list = []
        for data_access_log in data_access_chunk:
            log_data.log_seq += 1

            # Get OID for User related to this DataAccessLog
            if additional_fields := getattr(data_access_log.user, "additional_cas_user_fields", None):
                user_oid = additional_fields.henkilo_oid or None
            else:
                user_oid = None

            event_list.append(
                {
                    "timestamp": get_epoch_time_in_ms(data_access_log.timestamp),
                    "message": json.dumps(
                        {
                            "version": 1,
                            "logSeq": log_data.log_seq,
                            "bootTime": boot_time_str,
                            "type": "dataAccess",
                            "environment": environment,
                            "hostname": hostname,
                            "timestamp": data_access_log.timestamp.isoformat(),
                            "serviceName": "varda",
                            "applicationType": "backend",
                            "user": {"oid": user_oid},
                            "target": {"oppijaHenkiloOid": data_access_log.henkilo_oid},
                            "organizationOid": data_access_log.organisaatio.organisaatio_oid,
                            "operation": data_access_log.access_type,
                        }
                    ),
                }
            )

        is_successful = post_log_events(aws_client, stream_name, event_list, log_data, aikaleima)
        if not is_successful:
            # Post failed, stop processing and do not save Aikaleima
            return None

    # Successfully sent all logs, update Aikaleima
    aikaleima.aikaleima = end_timestamp
    aikaleima.save()
