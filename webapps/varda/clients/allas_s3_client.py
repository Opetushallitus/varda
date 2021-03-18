import boto3
import logging
import os

from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError
from django.conf import settings

# Get an instance of a logger
logger = logging.getLogger(__name__)


class Client:
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ALLAS_ACCESS_KEY_ID', None),
            aws_secret_access_key=os.getenv('AWS_ALLAS_SECRET_ACCESS_KEY', None),
            endpoint_url=settings.ALLAS_S3_ENDPOINT_URL
        )

    def upload_file(self, file_path, object_name):
        """
        Upload file to s3 object storage.

        :param file_path: string, local file to be uploaded
        :param object_name: string, e.g. vakajarjestaja/xx/filename.ext
        :return: True if success, else False
        """
        try:
            data = open(file_path, 'rb')
        except IOError:
            logger.error(f'Could not read file. File path: {file_path}.')
            return False

        bucket_name = settings.ALLAS_USER_FILES_BUCKET
        if not bucket_name:
            logger.error('Could not upload file. Check bucket name.')
            return False

        if not object_name:
            logger.error('Could not upload file. Check object_name.')
            return False

        try:
            self.client.upload_fileobj(data, bucket_name, object_name)
        except (ClientError, NoCredentialsError, ParamValidationError) as e:
            logger.error(f'Could not upload file. Error: {e}.')
            return False

        return True

    def create_presigned_url(self, object_name, expiration=3600):
        """
        Generate a presigned URL to share an S3 object

        :param object_name: string
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as string. If error, returns None.
        """
        bucket_name = settings.ALLAS_USER_FILES_BUCKET
        if not bucket_name:
            logger.error('Could not create presigned url. Check bucket name.')
            return None

        if not object_name:
            logger.error('Could not create presigned url. Check object_name.')
            return None

        # Generate a presigned URL for the S3 object
        try:
            response = self.client.generate_presigned_url('get_object',
                                                          Params={'Bucket': bucket_name,
                                                                  'Key': object_name},
                                                          ExpiresIn=expiration)
        except (ClientError, NoCredentialsError, ParamValidationError) as e:
            logger.error(f'Could not create presigned URL. Error: {e}.')
            return None

        # The response contains the presigned URL
        return response

    def delete_file(self, object_name):
        """
        Delete file. If file is not found, do nothing.

        :param object_name: string
        :return: None
        """
        bucket_name = settings.ALLAS_USER_FILES_BUCKET
        if not bucket_name:
            logger.error('Could not delete file. Check bucket name.')
            return None

        if not object_name:
            logger.error('Could not delete file. Check object_name.')
            return None

        self.client.delete_object(Bucket=bucket_name, Key=object_name)
