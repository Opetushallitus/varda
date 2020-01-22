import boto3
import logging
import os

from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings

# Get an instance of a logger
logger = logging.getLogger(__name__)


class Client:
    def __init__(self):
        self.client = boto3.client(
            'logs',
            region_name='eu-west-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', None)
        )
        if settings.PRODUCTION_ENV:
            self.log_group_name = 'sade-audit-varda'
        else:
            self.log_group_name = 'pallero-audit-varda'
        self.next_sequence_token = '1'

    def create_log_stream(self, log_stream_name):
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group_name,
                logStreamName=log_stream_name
            )
        except ClientError as e:
            logger.error('Could not create log_stream: %s' % e)

    def rejected_log_events_info(self, response):
        if 'rejectedLogEventsInfo' in response:
            logger.warning("Boto3 client rejectedLogEventsInfo: %s" % response['rejectedLogEventsInfo'])

    def get_http_status_code(self, response):
        if ('ResponseMetadata' in response and 'HTTPStatusCode' in response['ResponseMetadata']):
            return response['ResponseMetadata']['HTTPStatusCode']
        return None

    def post_audit_log(self, log_stream_name, log_events_list):
        """
        https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutLogEvents.html

        The batch of events must satisfy the following constraints:
        The maximum batch size is 1,048,576 bytes, and this size is calculated as the sum of all event messages in UTF-8,
        plus 26 bytes for each log event.

        None of the log events in the batch can be more than 2 hours in the future.

        None of the log events in the batch can be older than 14 days or older than the retention period of the log group.

        The log events in the batch must be in chronological ordered by their timestamp. The timestamp is the time the event
        occurred, expressed as the number of milliseconds after Jan 1, 1970 00:00:00 UTC.

        The maximum number of log events in a batch is 10,000.

        A batch of log events in a single request cannot span more than 24 hours. Otherwise, the operation fails.
        """
        MAX_LOOPS = 3
        loop_number = 0
        while True:
            loop_number += 1
            try:
                """
                New log-stream has next_sequence_token as 'null'.
                However, we cannot set that value to null, we need
                to drop the parameter completely away.
                """
                if self.next_sequence_token == "null":
                    response = self.client.put_log_events(
                        logGroupName=self.log_group_name,
                        logStreamName=log_stream_name,
                        logEvents=log_events_list
                    )
                else:
                    response = self.client.put_log_events(
                        logGroupName=self.log_group_name,
                        logStreamName=log_stream_name,
                        logEvents=log_events_list,
                        sequenceToken=self.next_sequence_token
                    )
            except ClientError as e:
                error_str = str(e)
                sequence_token_batch_msg = 'The next batch can be sent with sequenceToken: '
                sequence_token_invalid_msg = 'The next expected sequenceToken is: '
                log_stream_does_not_exist = 'The specified log stream does not exist.'

                if loop_number <= MAX_LOOPS:
                    if sequence_token_batch_msg in error_str:
                        self.next_sequence_token = error_str.split(sequence_token_batch_msg)[1]
                        continue
                    elif sequence_token_invalid_msg in error_str:
                        self.next_sequence_token = error_str.split(sequence_token_invalid_msg)[1]
                        continue
                    elif log_stream_does_not_exist in error_str:
                        self.create_log_stream(log_stream_name)
                        continue
                    else:
                        logger.error("Boto3 client error: %s" % e)

                return None  # Something went wrong. Please check the logs.
            except NoCredentialsError as e:
                logger.error("Boto3 client credentials-error: %s" % e)
                return None

            break

        self.rejected_log_events_info(response)
        return self.get_http_status_code(response)
