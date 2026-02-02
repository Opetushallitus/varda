import base64
import boto3
import hashlib
import logging

from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError


logger = logging.getLogger(__name__)


class Client:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

        try:
            self.client = boto3.client("s3")
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
                    ACL="private", Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
                )
            except ClientError:
                logger.warning(f"S3 bucket already exists: {bucket_name}")

    def upload_file(self, file, path):
        """
        Upload file (in bytes|file) to s3 object storage.

        :param file: b'bytes'|file: local file to be uploaded
        :param path: string,
        :return: True if success, else False
        """
        md = hashlib.md5(file.encode("utf-8")).digest()  # https://stackoverflow.com/a/60556534/8689704
        contents_md5 = base64.b64encode(md).decode("utf-8")

        try:
            self.client.put_object(ACL="private", Body=file, Bucket=self.bucket_name, Key=path, ContentMD5=contents_md5)
        except ClientError as e:
            logger.error(e)
            return False

        return True

    def upload_fileobj(self, file_path, bucket_name, object_name):
        """
        Upload file (from file_path) to s3 object storage.

        :param file_path: string, local file to be uploaded
        :param bucket_name:
        :param object_name: string, e.g. vakajarjestaja/xx/filename.ext
        :return: True if success, else False
        """
        try:
            data = open(file_path, "rb")
        except IOError:
            logger.error(f"Could not read file. File path: {file_path}.")
            return False

        if not object_name:
            logger.error("Could not upload file. Check object_name.")
            return False

        try:
            self.client.upload_fileobj(data, bucket_name, object_name)
        except (ClientError, NoCredentialsError, ParamValidationError) as e:
            logger.error(f"Could not upload file. Error: {e}.")
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
                "get_object", Params={"Bucket": self.bucket_name, "Key": object_name}, ExpiresIn=expiration
            )
        except ClientError as e:
            logger.error(e)
            return None

        # The response contains the presigned URL
        return response

    def delete_file(self, object_name):
        """
        Delete file.
        :param object_name: string
        :return: True if request was successful, otherwise False
        """
        if not self.bucket_name:
            logger.error("Could not delete file. Check bucket name.")
            return False

        if not object_name:
            logger.error("Could not delete file. Check object_name.")
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
        except (ClientError, NoCredentialsError, ParamValidationError) as e:
            logger.error(f"Could not delete file. Error: {e}.")
            return False

        # We cannot determine if file was actually deleted or not, so return True if request is successful
        # https://github.com/boto/boto3/issues/759
        return True
