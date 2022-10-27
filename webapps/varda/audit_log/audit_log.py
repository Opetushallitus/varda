import datetime
import json
import logging
import os

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from varda.apps import init_alive_log
from varda.clients.oph_audit_log_client import Client
from varda.constants import ALIVE_BOOT_TIME_CACHE_KEY, ALIVE_SEQ_CACHE_KEY
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.models import Aikaleima, LogData, Z5_AuditLog


# Get an instance of a logger
logger = logging.getLogger(__name__)

"""
The maximum number of log events in a batch is 10 000.
The maximum batch size is 1 048 576 bytes
"""
AWS_LOG_BATCH_MAX_SIZE = 10000
AWS_LOG_BATCH_MAX_BYTES = 1048576
AWS_OVERHEAD_IN_BYTES_PER_EVENT = 26
TWENTY_FOUR_HOURS_IN_MS = 1000 * 60 * 60 * 22  # trying a quick fix for CSCVARDA-1662 (24 -> 22)


def get_size(event):
    return (len(event['message']) if isinstance(event, dict) else 1) + AWS_OVERHEAD_IN_BYTES_PER_EVENT


def get_batch_size_in_bytes(audit_log_batch):
    """
    https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutLogEvents.html

    The maximum batch size is 1,048,576 bytes, and this size is calculated as the
    sum of all event messages in UTF-8, plus 26 bytes for each log event.
    """
    return sum(get_size(event) for event in audit_log_batch)


def get_batch_end_index_size_bytes(audit_log_events, start_index):
    """
    :param audit_log_events: list of all log events to be sent
    :param start_index: from which index we need to start the batch
    :return: end_index of the batch, calculated using the max batch size in bytes
    """
    batch_size = AWS_LOG_BATCH_MAX_SIZE
    end_index = len(audit_log_events) - 1
    while batch_size > 0:
        end_index = min(len(audit_log_events) - 1, start_index + batch_size)
        if end_index == len(audit_log_events) - 1:
            audit_log_batch = audit_log_events[start_index:]
        else:
            audit_log_batch = audit_log_events[start_index:end_index]

        batch_size_in_bytes = get_batch_size_in_bytes(audit_log_batch)
        if batch_size_in_bytes > AWS_LOG_BATCH_MAX_BYTES:
            if batch_size > 1000:
                batch_size -= 1000
            elif 100 < batch_size <= 1000:
                batch_size -= 100
            elif 10 < batch_size <= 100:
                batch_size -= 10
            else:
                batch_size -= 1
        else:
            break
    return end_index


def get_batch_end_index_time(audit_log_events, start_index):
    """
    :param audit_log_events: list of all log events to be sent
    :param start_index: from which index we need to start the batch
    :return: end_index of the batch, calculated using the 24hr time window between first and last event in batch
    """
    batch_size = AWS_LOG_BATCH_MAX_SIZE
    end_index = len(audit_log_events) - 1
    while batch_size > 0:
        end_index = min(len(audit_log_events) - 1, start_index + batch_size)
        if audit_log_events[start_index]['timestamp'] + TWENTY_FOUR_HOURS_IN_MS < audit_log_events[end_index]['timestamp']:
            if batch_size > 1000:
                batch_size -= 1000
            elif 100 < batch_size <= 1000:
                batch_size -= 100
            elif 10 < batch_size <= 100:
                batch_size -= 10
            else:
                batch_size -= 1
        else:
            break
    return end_index


def get_batch_end_index(audit_log_events, start_index):
    batch_end_index_size_bytes = get_batch_end_index_size_bytes(audit_log_events, start_index)
    batch_end_index_time = get_batch_end_index_time(audit_log_events, start_index)
    return min(batch_end_index_size_bytes, batch_end_index_time)


def get_epoch_time_in_ms(date_time):
    return int(date_time.timestamp() * 1000)


def get_log_row(log_seq, hostname, environment, timestamp, operation, target_url, query_params, username):
    return json.dumps({
        'version': 1,
        'logSeq': log_seq,
        'type': 'log',
        'hostname': hostname,
        'timestamp': str(timestamp),
        'environment': environment,
        'serviceName': 'varda',
        'applicationType': 'backend',
        'operation': operation,
        'target': target_url,
        'query_params': query_params,
        'user': username
    })


def send_read_audit_log(aws_log_client, logs_since, logs_until, hostname, environment):
    stream_name = 'varda-get-stream'
    new_audit_log = (Z5_AuditLog.objects
                     .filter(time_of_event__gte=logs_since)
                     .filter(time_of_event__lt=logs_until)
                     .order_by('time_of_event'))
    log_data_state, created = LogData.objects.get_or_create(log_type=stream_name)
    audit_log_events = []

    for audit_log_event in new_audit_log:
        log_data_state.log_seq += 1
        timestamp = get_epoch_time_in_ms(audit_log_event.time_of_event)
        audit_log_events.append({'timestamp': timestamp,
                                 'message': get_log_row(log_data_state.log_seq,
                                                        hostname,
                                                        environment,
                                                        timestamp,
                                                        'GET',
                                                        audit_log_event.successful_get_request_path,
                                                        audit_log_event.query_params,
                                                        audit_log_event.user.username)})

    if audit_log_events:
        start_index = 0
        continue_looping = True
        post_was_successful = False

        while continue_looping:
            end_index = get_batch_end_index(audit_log_events, start_index)
            if end_index == len(audit_log_events) - 1:
                audit_log_batch = audit_log_events[start_index:]
                continue_looping = False
            else:
                audit_log_batch = audit_log_events[start_index:end_index]

            post_http_status_code = aws_log_client.post_audit_log(stream_name, audit_log_batch)  # 200 is successful
            if post_http_status_code == 200:
                post_was_successful = True  # If one of the batch-posts was successful, save the log_data_state
            else:
                logger.warning('Audit log post to aws failed with status code: {}'.format(post_http_status_code))
            start_index = end_index

        if post_was_successful:
            log_data_state.save()


def get_api_endpoint_from_model_name(model_name_verbose_plural):
    endpoint = model_name_verbose_plural
    endpoint = endpoint.replace(' ', '')
    endpoint = endpoint.replace('ö', 'o')
    endpoint = endpoint.replace('ä', 'a')
    return endpoint


def send_changed_model_log(aws_log_client, model_name, logs_since, logs_until, hostname, environment):
    changed_model = apps.get_model('varda', model_name)
    historical_model = apps.get_model('varda', 'historical{}'.format(model_name))
    stream_name = 'varda-changed-{}-stream'.format(model_name)
    api_endpoint = get_api_endpoint_from_model_name(changed_model._meta.verbose_name_plural)

    historical_model_q_obj = Q(history_date__gte=logs_since, history_date__lt=logs_until)
    if model_name == 'henkilo':
        """
        We want to exclude the changes coming from Oppijanumerorekisteri.
        """
        historical_model_q_obj = historical_model_q_obj & Q(history_type__in=['+', '-'])

    new_audit_log = historical_model.objects.filter(historical_model_q_obj).order_by('history_date')

    log_data_state, created = LogData.objects.get_or_create(log_type=stream_name)
    audit_log_events = []

    for audit_log_event in new_audit_log:
        log_data_state.log_seq += 1
        timestamp = get_epoch_time_in_ms(audit_log_event.history_date)
        change_url = '/api/v1/{}/{}/'.format(api_endpoint, audit_log_event.id)
        history_user = audit_log_event.history_user
        username = history_user.username if history_user else 'None'

        if audit_log_event.history_type == '+':
            operation = 'CREATE'
        elif audit_log_event.history_type == '-':
            operation = 'DELETE'
        else:  # history_type == '~'
            operation = 'CHANGE'

        audit_log_events.append({'timestamp': timestamp,
                                 'message': get_log_row(log_data_state.log_seq,
                                                        hostname,
                                                        environment,
                                                        timestamp,
                                                        operation,
                                                        change_url,
                                                        None,
                                                        username)})

    if audit_log_events:
        start_index = 0
        continue_looping = True
        post_was_successful = False

        while continue_looping:
            end_index = get_batch_end_index(audit_log_events, start_index)
            if end_index == len(audit_log_events) - 1:
                audit_log_batch = audit_log_events[start_index:]
                continue_looping = False
            else:
                audit_log_batch = audit_log_events[start_index:end_index]

            post_http_status_code = aws_log_client.post_audit_log(stream_name, audit_log_batch)  # 200 is successful
            if post_http_status_code == 200:
                post_was_successful = True  # If one of the batch-posts was successful, save the log_data_state
            else:
                logger.warning('Audit log post to aws failed with status code: {}'.format(post_http_status_code))
            start_index = end_index

        if post_was_successful:
            log_data_state.save()


def collect_audit_log_and_send_to_aws():
    aws_log_client = Client()
    hostname = os.getenv('VARDA_HOSTNAME', 'localhost')
    environment = 'production' if settings.PRODUCTION_ENV else 'testing'

    aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.AUDIT_LOG_AWS_LAST_UPDATE.name)
    start_datetime = aikaleima.aikaleima
    end_datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    """
    GET-requests need special handling (taken from Z5_AuditLog)
    """
    send_read_audit_log(aws_log_client, start_datetime, end_datetime, hostname, environment)

    """
    CREATE, UPDATE, DELETE (taken from historical-models)
    """
    audit_log_models = []
    varda_models = [ct.model_class() for ct in ContentType.objects.filter(app_label='varda')]
    for varda_model in varda_models:
        if hasattr(varda_model, 'history'):
            audit_log_models.append(varda_model.__name__.lower())

    for audit_log_model in audit_log_models:
        send_changed_model_log(aws_log_client, audit_log_model, start_datetime, end_datetime, hostname, environment)

    aikaleima.aikaleima = end_datetime
    aikaleima.save()


def send_alive_log_to_aws():
    log_seq = cache.get(ALIVE_SEQ_CACHE_KEY)
    boot_time = cache.get(ALIVE_BOOT_TIME_CACHE_KEY)
    if log_seq is None or boot_time is None:
        log_seq, boot_time = init_alive_log()

    aws_client = Client()
    stream_name = 'varda-alive-stream'

    hostname = os.getenv('VARDA_HOSTNAME', 'localhost')
    environment = 'production' if settings.PRODUCTION_ENV else 'testing'
    timestamp = timezone.now()
    message = 'started' if log_seq == 0 else 'alive'
    audit_log_events = [{
        'timestamp': get_epoch_time_in_ms(timestamp),
        'message': json.dumps({
            'version': 1,
            'logSeq': log_seq,
            'type': 'alive',
            'bootTime': str(boot_time),
            'hostname': hostname,
            'environment': environment,
            'timestamp': str(timestamp),
            'serviceName': 'varda',
            'applicationType': 'backend',
            'message': message
        })
    }]

    post_http_status_code = aws_client.post_audit_log(stream_name, audit_log_events)  # 200 is successful
    if post_http_status_code == 200:
        cache.set(ALIVE_SEQ_CACHE_KEY, log_seq + 1, None)
    else:
        logger.warning('Alive log post to aws failed with status code: {}'.format(post_http_status_code))
