import datetime

from boto3 import Session
from botocore.auth import SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from redis.credentials import CredentialProvider


def get_elasticache_iam_token(replication_group_id, user_id):
    """
    Get a short-lived IAM authentication token for ElastiCache connection. boto3 support probably coming at some point.
    https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/auth-iam.html#auth-iam-Connecting
    :return: authentication token
    """
    aws_request = AWSRequest(method="GET", url=f"http://{replication_group_id}/", params={"Action": "connect", "User": user_id})
    # Sign request using AWS SigV4
    aws_credentials = Session().get_credentials().get_frozen_credentials()
    # Token is valid for 900 seconds
    SigV4QueryAuth(aws_credentials, "elasticache", "eu-west-1", expires=900).add_auth(aws_request)
    return aws_request.url.replace("http://", "")


class IAMTokenCredentialProvider(CredentialProvider):
    current_iam_token = None
    token_datetime = None

    def __init__(self, replication_group_id, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id
        self.replication_group_id = replication_group_id

    def get_credentials(self):
        now = datetime.datetime.now()
        if (
            not IAMTokenCredentialProvider.current_iam_token
            or IAMTokenCredentialProvider.token_datetime < now - datetime.timedelta(seconds=600)
        ):
            # Generate new token if it does not exist or token is older than 600 seconds
            IAMTokenCredentialProvider.current_iam_token = get_elasticache_iam_token(self.replication_group_id, self.user_id)
            IAMTokenCredentialProvider.token_datetime = now
        return self.user_id, IAMTokenCredentialProvider.current_iam_token
