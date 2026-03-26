import boto3
import logging
import time

from botocore.exceptions import ClientError
from django.conf import settings


logger = logging.getLogger(__name__)


class Client:
    def __init__(self):
        self.client = boto3.client("acm-pca")

    def list_certificate_authorities(self):
        return self.client.list_certificate_authorities(ResourceOwner="OTHER_ACCOUNTS")

    def get_certificate(self, certificate_arn):
        """
        :param certificate_arn:
        :return:

        Boto3 raises RequestInProgressException quite often: as a workaround wait a while and try again -loop.
        """
        cert_response = {"success": False, "certificate": None, "msg": None}

        i = 1
        while i < 4:
            try:
                certificate = self.client.get_certificate(
                    CertificateAuthorityArn=settings.AWS_CERTIFICATE_AUTHORITY_ARN, CertificateArn=certificate_arn
                )
                cert_response["success"] = True
                cert_response["certificate"] = certificate
                break
            except ClientError as err:
                logger.error(err)
                time.sleep(3)
                i += 1

        return cert_response

    def issue_certificate(self, csr_file_bytes, organisaatio_oid_last_part, client_certificate_validity_end_date):
        """
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/acm-pca/client/issue_certificate.html
        :param csr_file_bytes: in bytes
        :param organisaatio_oid_last_part:
        :param client_certificate_validity_end_date:
        :return: Dict {'success': False, 'certificate': None, 'msg': None}
        """
        cert_response = {"success": False, "certificate": None, "msg": None, "end_date": None}
        try:
            cert = self.client.issue_certificate(
                ApiPassthrough={
                    "Extensions": {
                        "ExtendedKeyUsage": [
                            {"ExtendedKeyUsageType": "CLIENT_AUTH"},
                        ],
                        "KeyUsage": {"DigitalSignature": True, "KeyEncipherment": True},
                    }
                },
                CertificateAuthorityArn=settings.AWS_CERTIFICATE_AUTHORITY_ARN,
                Csr=csr_file_bytes,
                SigningAlgorithm="SHA512WITHRSA",
                Validity={
                    "Value": client_certificate_validity_end_date,
                    "Type": "END_DATE",  # accepts value format YYYYMMDDHHMMSS
                },
                IdempotencyToken=organisaatio_oid_last_part,  # max length 36 characters
            )
            cert_response["success"] = True
            cert_response["certificate"] = cert
        except ClientError as err:
            cert_response["msg"] = err.response["Error"]["Message"]

        return cert_response
