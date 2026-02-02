import boto3
import json
import logging
import os

from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError
from django.conf import settings


logger = logging.getLogger(__name__)


class Client:
    if settings.PRODUCTION_ENV:
        env = "prod"
    else:
        env = "qa"
    bucket_name = f"oph-lampi-{env}"

    def __init__(self):
        try:
            sts_client = boto3.client("sts")
            response = sts_client.assume_role(
                RoleArn=os.getenv("AWS_STS_LAMPI_ROLE_ARN", ""),
                RoleSessionName=f"Data-dump-uploader-{self.env}",
                ExternalId=os.getenv("AWS_STS_LAMPI_EXTERNAL_ID", ""),
            )
            credentials = response["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
            self.client = session.client("s3")
        except NoCredentialsError as e:
            logger.error(e)

    def upload_file(self, file_path, object_name):
        """
        Upload file to s3 object storage using gzip compression.

        :param file_path: string, local file to be uploaded
        :param object_name: string, e.g. varda_lapsi.csv
        :return: s3 upload_fileobj response or None

        Example response:
        {
          'ResponseMetadata': {
            'RequestId': 'RW17X42QWXMZWJT5',
            'HostId': 'PR2O+jy4Cfbw54n5caP0mYomTjNfxvETQcVA7hfrqtOD4qAN3H1Yt6/U8bGvnEavIqqg7dxRsv0ZVTPwIbYHldsYizPOSUEW',
            'HTTPStatusCode': 200,
            'HTTPHeaders': {
              'x-amz-id-2': 'PR2O+jy4Cfbw54n5caP0mYomTjNfxvETQcVA7hfrqtOD4qAN3H1Yt6/U8bGvnEavIqqg7dxRsv0ZVTPwIbYHldsYizPOSUEW',
              'x-amz-request-id': 'RW17X42QWXMZWJT5',
              'date': 'Tue, 13 Aug 2024 11:55:04 GMT',
              'x-amz-version-id': 'vKYfZ0wuxtC5MO4ImXqD.ScShLNVtulP',
              'x-amz-server-side-encryption': 'AES256',
              'etag': '"490f9efcb9c259b561ac14126eb89f3d"',
              'server': 'AmazonS3',
              'content-length': '0'
            },
            'RetryAttempts': 1
          },
          'ETag': '"490f9efcb9c259b561ac14126eb89f3d"',
          'ServerSideEncryption': 'AES256',
          'VersionId': 'vKYfZ0wuxtC5MO4ImXqD.ScShLNVtulP'
        }
        """
        response = None

        try:
            data = open(file_path, "rb")
        except IOError:
            logger.error(f"Lampi: Could not read file. File path: {file_path}.")
            return None

        if not object_name:
            logger.error(f"Lampi: Could not upload file. Check object_name. File path: {file_path}")
            return None

        content_type = "text/csv" if "csv" in object_name else "text/plain"
        try:
            response = self.client.put_object(
                Bucket=self.bucket_name, Key=object_name, Body=data, ContentType=content_type, ContentEncoding="gzip"
            )
        except (ClientError, NoCredentialsError, ParamValidationError) as e:
            logger.error(f"Lampi: Could not upload file. Error: {e}.")

        return response

    def upload_json_file(self, file_path, json_dict):
        """
        Upload json file to s3 object storage.

        :param file_path: string, local file to be uploaded
        :param json_dict: string, e.g. varda_lapsi.csv
        :return: s3 upload_fileobj response or None
        """
        response = None

        if not file_path:
            logger.error("Lampi: Could not upload file. Check file_path.")
            return None

        try:
            response = self.client.put_object(
                Bucket=self.bucket_name, Key=file_path, Body=json.dumps(json_dict), ContentType="application/json"
            )
        except (ClientError, NoCredentialsError, ParamValidationError) as e:
            logger.error(f"Lampi: Could not upload file. Error: {e}.")

        return response
