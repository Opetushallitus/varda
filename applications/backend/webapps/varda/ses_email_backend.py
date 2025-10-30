import boto3
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address


class SesEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        ses_client = boto3.client("ses")

        for email_message in email_messages:
            if not email_message.recipients():
                # No recipients
                continue

            encoding = email_message.encoding or settings.DEFAULT_CHARSET
            source = sanitize_address(email_message.from_email, encoding)
            destinations = [sanitize_address(addr, encoding) for addr in email_message.recipients()]
            message = email_message.message()

            ses_client.send_raw_email(
                Source=source,
                Destinations=destinations,
                RawMessage={"Data": message.as_bytes(linesep="\r\n")},
                SourceArn=settings.SES_IDENTITY_ARN,
                FromArn=settings.SES_IDENTITY_ARN,
                ConfigurationSetName=settings.SES_CONFIGURATION_SET_NAME,
            )
