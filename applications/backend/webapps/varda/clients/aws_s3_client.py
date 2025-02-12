import base64
import boto3
import hashlib
import logging

from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings


logger = logging.getLogger(__name__)


class Client:
    if settings.PRODUCTION_ENV:
        env = 'prod'
    elif settings.QA_ENV:
        env = 'qa'
    else:
        env = 'dev'
    bucket_name = f'{env}-{settings.S3_LUOVUTUSPALVELU_CLIENT_CERTIFICATES}'

    def __init__(self):
        try:
            self.client = boto3.client('s3')
            self._create_bucket_if_not_exist(self.bucket_name)
        except NoCredentialsError as e:
            logger.error(e)

    def _create_bucket_if_not_exist(self, bucket_name):
        """
        :param bucket_name: string
        :return:
        """
        bucket_exists = True
        try:
            self.client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            logger.warning(e)
            bucket_exists = False

        if not bucket_exists:
            try:
                self.client.create_bucket(
                    ACL='private',
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': 'eu-west-1'
                    }
                )
            except ClientError:
                logger.warning(f'S3 bucket already exists: {bucket_name}')

    def upload_file(self, file, path):
        """
        Upload file to s3 object storage.

        :param file: b'bytes'|file: local file to be uploaded
        :param path: string,
        :return: True if success, else False
        """
        md = hashlib.md5(file.encode('utf-8')).digest()  # https://stackoverflow.com/a/60556534/8689704
        contents_md5 = base64.b64encode(md).decode('utf-8')

        try:
            self.client.put_object(
                ACL='private',
                Body=file,
                Bucket=self.bucket_name,
                Key=path,
                ContentMD5=contents_md5
            )
        except ClientError as e:
            logger.error(e)
            return False

        return True

    def create_presigned_url(self, object_name, expiration=3600):
        """
        Generate a presigned URL to download an S3 object.

        :param object_name: string
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as string. If error, returns None.
        """
        # Generate a presigned URL for the S3 object
        try:
            response = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
        except ClientError as e:
            logger.error(e)
            return None

        # The response contains the presigned URL
        return response
