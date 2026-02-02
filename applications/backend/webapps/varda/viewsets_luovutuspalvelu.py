import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda.enums.error_messages import ErrorMessages
from varda.enums.country_codes import CountryCode
from varda.clients.aws_boto3_pca_client import Client as Boto3PcaClient
from varda.clients.aws_s3_client import Client as AwsS3Client
from varda.misc import CustomServerErrorException, single_line_with_linebreaks_parse
from varda.models import LuovutuspalveluClientCsr, Organisaatio
from varda.permissions import ClientCertPermissions
from varda.serializers_luovutuspalvelu import UploadSerializer


logger = logging.getLogger(__name__)


class CsrViewset(GenericViewSet, CreateModelMixin):
    """
    create:
        Upload CSR and receive URLs for client certificate and trust chain.
    """

    queryset = LuovutuspalveluClientCsr.objects.none()
    serializer_class = UploadSerializer
    permission_classes = (ClientCertPermissions,)
    if settings.PRODUCTION_ENV:
        env = "prod"
    elif settings.QA_ENV:
        env = "qa"
    else:
        env = "dev"
    bucket_name = f"{env}-{settings.S3_LUOVUTUSPALVELU_CLIENT_CERTIFICATES}"
    s3client = AwsS3Client(bucket_name)

    def create(self, request, *args, **kwargs):
        """
        CSR must be
        - PEM encoded
        - Using RSA public key
        - Signed using SHA-2 family hash
        - C (Country) must be 'FI'
        - CN (Common name) must match with the data in Organization table.

        Client certificate validity max 365 days.

        Example of creating a valid CSR:
        $ openssl req -new -newkey rsa:2048 -nodes -keyout your_domain.key -out your_domain.csr
        """
        user_groups = request.user.groups.all()
        self._validate_user_groups_length(user_groups)

        file_uploaded = request.FILES.get("file_uploaded")
        if file_uploaded is None:
            raise ValidationError({"csr": [ErrorMessages.LU002.value]})
        file_uploaded_in_bytes = file_uploaded.read()

        csr = self._validate_csr_pem_encoded(file_uploaded_in_bytes)
        self._validate_csr_public_key(csr)
        self._validate_signature_hash(csr)
        self._validate_csr_signature_valid(csr)
        organisaatio = self._validate_organisaatio(user_groups)
        self._validate_csr_country_and_common_name(csr, organisaatio)
        client_certificate_validity_end_date = self._get_certificate_validity_end_date()

        """
        CSR is valid. Next, check if a valid certificate is already created and available in s3 and it has
        validity of more than 6 months, otherwise create a new client certificate.
        """
        valid_client_certificates = LuovutuspalveluClientCsr.objects.filter(
            organisaatio=organisaatio, expiration_date__gt=timezone.now() + timedelta(days=180)
        )

        # If user needs to change the private key, then we need to create a new certificate even though an existing
        # certificate is otherwise available.
        change_private_key_string = request.POST.get("change_private_key", "")
        if change_private_key_string.lower() == "true":
            change_private_key_bool = True
        elif change_private_key_string.lower() in ["false", ""]:
            change_private_key_bool = False
        else:
            raise ValidationError({"csr": [ErrorMessages.LU012.value]})
        if change_private_key_bool:
            valid_client_certificates.all().delete()
            valid_client_certificates = LuovutuspalveluClientCsr.objects.none()

        if valid_client_certificates.exists():
            client_cert = valid_client_certificates.first()
            client_cert_s3_bucket_key = client_cert.client_cert_s3_bucket_key
            cert_chain_s3_bucket_key = client_cert.cert_chain_s3_bucket_key
            expiration_date = client_cert.expiration_date.isoformat(timespec="seconds")
            certificates = {
                "url_certificate": self._get_presigned_url(client_cert_s3_bucket_key),
                "url_certificate_chain": self._get_presigned_url(cert_chain_s3_bucket_key),
                "validity_end_date": expiration_date,
            }
        else:  # Create a new certificate
            certificates = self._create_client_certificate(
                file_uploaded_in_bytes, organisaatio.organisaatio_oid, client_certificate_validity_end_date["aws"]
            )
            certificates["validity_end_date"] = client_certificate_validity_end_date["client"]

            LuovutuspalveluClientCsr.objects.create(
                organisaatio=organisaatio,
                client_cert_s3_bucket_key=certificates["client_cert_s3_bucket_key"],
                cert_chain_s3_bucket_key=certificates["cert_chain_s3_bucket_key"],
                expiration_date=client_certificate_validity_end_date["client"],
            )
            del certificates["client_cert_s3_bucket_key"]
            del certificates["cert_chain_s3_bucket_key"]

        return Response(certificates)

    def _validate_user_groups_length(self, user_groups):
        if len(user_groups) != 1:
            """
            Palvelukayttaja should have only one active permission group.
            Permission group itself is already checked in permission_classes (i.e. VARDA_LUOVUTUSPALVELU)
            """
            raise ValidationError({"csr": [ErrorMessages.LU001.value]})

    def _validate_csr_pem_encoded(self, file_uploaded_in_bytes):
        try:
            csr = x509.load_pem_x509_csr(file_uploaded_in_bytes)
        except ValueError as e:
            logger.error(e)
            raise ValidationError({"csr": [ErrorMessages.LU003.value]})
        return csr

    def _validate_csr_public_key(self, csr):
        public_key = csr.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValidationError({"csr": [ErrorMessages.LU004.value]})

    def _validate_signature_hash(self, csr):
        # We support SHA-2 family signature hashes
        # https://cryptography.io/en/latest/hazmat/primitives/cryptographic-hashes/#sha-2-family
        if not isinstance(
            csr.signature_hash_algorithm,
            (hashes.SHA224, hashes.SHA256, hashes.SHA384, hashes.SHA512, hashes.SHA512_224, hashes.SHA512_256),
        ):
            raise ValidationError({"csr": [ErrorMessages.LU005.value]})

    def _validate_csr_signature_valid(self, csr):
        if not csr.is_signature_valid:
            raise ValidationError({"csr": [ErrorMessages.LU006.value]})

    def _validate_organisaatio(self, user_groups):
        invalid_permission_group = False
        user_group_name = user_groups.first().name
        organisaatio = None
        organisaatio_oid = ""
        try:
            organisaatio_oid = user_group_name.rsplit("_", 1)[1]
        except IndexError:
            invalid_permission_group = True

        try:
            organisaatio = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
        except Organisaatio.DoesNotExist:
            invalid_permission_group = True

        if invalid_permission_group:
            logger.error(f"Error in Luovutuspalvelu user permission group {user_group_name}.")
            raise CustomServerErrorException
        return organisaatio

    def _validate_csr_country_and_common_name(self, csr, organisaatio):
        csr_common_name = None
        for attribute in csr.subject:
            if attribute.rfc4514_attribute_name == "C" and attribute.value != CountryCode.FI.value:
                raise ValidationError({"csr": [ErrorMessages.LU007.value]})

            if attribute.rfc4514_attribute_name == "CN":
                csr_common_name = attribute.value

        if csr_common_name is None:
            raise ValidationError({"csr": [ErrorMessages.LU008.value]})

        if csr_common_name != organisaatio.client_cert_common_name:
            raise ValidationError({"csr": [ErrorMessages.LU009.value]})

    def _get_certificate_validity_end_date(self):
        """
        Client-cert expires in 365 days, or less, depending on the validity of CA-certificate.

        :return: dict {aws: int(YYYYMMDDHHMMSS), client: isoformat}
        """
        ca_certificate_expiration_date = datetime.fromisoformat(settings.AWS_CERTIFICATE_AUTHORITY_EXPIRATION_DATE)
        date_now = timezone.now()
        days = (ca_certificate_expiration_date - date_now).days

        if days == 0:
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})

        elif days > 365:
            ca_certificate_expiration_date = date_now + timedelta(days=365)

        validity_end_date = {
            "aws": int(ca_certificate_expiration_date.strftime("%Y%m%d%H%M%S")),
            "client": ca_certificate_expiration_date.isoformat(timespec="seconds"),
        }

        return validity_end_date

    def _create_client_certificate(self, file_uploaded, organisaatio_oid, client_certificate_validity_end_date):
        organisaatio_oid_last_part = organisaatio_oid.rsplit(".", 1)[1]
        client = Boto3PcaClient()

        resp_issue_cert = client.issue_certificate(
            file_uploaded, organisaatio_oid_last_part, client_certificate_validity_end_date
        )
        if not resp_issue_cert["success"]:
            raise ValidationError({"csr": [ErrorMessages.LU010.value, {"details": resp_issue_cert["msg"]}]})

        try:
            certificate_arn = resp_issue_cert["certificate"]["CertificateArn"]
        except KeyError:
            logger.error(f"Key-error in {resp_issue_cert}")
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})

        resp_get_cert = client.get_certificate(certificate_arn)
        if not resp_get_cert["success"]:
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})

        try:
            certificate = single_line_with_linebreaks_parse(resp_get_cert["certificate"]["Certificate"])
            certificate_chain = single_line_with_linebreaks_parse(resp_get_cert["certificate"]["CertificateChain"])
        except KeyError:
            logger.error(f"Key-error in {resp_get_cert}")
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})

        return self._upload_certificates_to_s3(organisaatio_oid, certificate, certificate_chain)

    def _upload_certificates_to_s3(self, organisaatio_oid, certificate, certificate_chain):
        """
        Upload certificate and chain to s3, and create a presigned urls for fetching files.

        :param organisaatio_oid:
        :param certificate:
        :param certificate_chain:
        :return: A dict containing the urls for crt and chain
        """
        date_now = timezone.now().strftime("%Y-%m-%d")
        client_cert_s3_bucket_key = f"{organisaatio_oid}/user-{date_now}.crt"
        resp_upload_file = self.s3client.upload_file(certificate, client_cert_s3_bucket_key)
        if not resp_upload_file:
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})

        cert_chain_s3_bucket_key = f"{organisaatio_oid}/chain-{date_now}.crt"
        resp_upload_file = self.s3client.upload_file(certificate_chain, cert_chain_s3_bucket_key)
        if not resp_upload_file:
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})

        url_certificate = self._get_presigned_url(client_cert_s3_bucket_key)
        url_certificate_chain = self._get_presigned_url(cert_chain_s3_bucket_key)

        return {
            "url_certificate": url_certificate,
            "url_certificate_chain": url_certificate_chain,
            "client_cert_s3_bucket_key": client_cert_s3_bucket_key,
            "cert_chain_s3_bucket_key": cert_chain_s3_bucket_key,
        }

    def _get_presigned_url(self, s3_bucket_key):
        url_certificate = self.s3client.create_presigned_url(s3_bucket_key)
        if not url_certificate:
            raise ValidationError({"csr": [ErrorMessages.LU011.value]})
        return url_certificate
