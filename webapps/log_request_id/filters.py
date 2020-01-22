import os
import uuid
import logging
from log_request_id import local


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        vardahost = os.getenv('VARDA_HOSTNAME', '')

        # Environment variable overrides headers
        if vardahost:
            record.request_host = vardahost
        else:
            record.request_host = getattr(local, 'request_host', '')

        # If there is no id, let's generate one
        if not hasattr(local, 'request_id'):
            uuido = uuid.uuid4()
            uuids = str(uuido)
            uuids = uuids.replace("-", "")
            local.request_id = uuids

        record.request_id = getattr(local, 'request_id', '')
        return True
