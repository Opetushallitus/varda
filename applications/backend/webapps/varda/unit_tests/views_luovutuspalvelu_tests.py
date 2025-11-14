import io
import json

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, dsa
from cryptography.x509.oid import NameOID
from django.test import TestCase

from varda.unit_tests.test_utils import SetUpTestClient


class VardaViewsLuovutuspalveluTests(TestCase):
    fixtures = ["fixture_basics"]

    """
    Luovutuspalvelu related view-tests
    """

    def test_csr_get_not_allowed(self):
        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.get("/api/client/v1/csr/")
        self.assertEqual(resp.status_code, 405)
        self.assertEqual(json.loads(resp.content), {"detail": 'Method "GET" not allowed.'})

    def test_csr_post_no_data(self):
        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content), {"csr": [{"error_code": "LU002", "description": "No file uploaded.", "translations": []}]}
        )

    def test_csr_upload_random_file(self):
        client = SetUpTestClient("kela_luovutuspalvelu").client()
        with open("manage.py", "rb") as f:
            resp = client.post("/api/client/v1/csr/", {"file_uploaded": f})
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(
                json.loads(resp.content),
                {"csr": [{"error_code": "LU003", "description": "Uploaded file is not PEM encoded CSR.", "translations": []}]},
            )

    def test_invalid_csr_encoding(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Virginia"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Richmond"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Organization"),
                        x509.NameAttribute(NameOID.COMMON_NAME, "example.com"),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
            .public_bytes(encoding=Encoding.DER)
        )

        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/", {"file_uploaded": io.BytesIO(csr)})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content),
            {"csr": [{"error_code": "LU003", "description": "Uploaded file is not PEM encoded CSR.", "translations": []}]},
        )

    def test_invalid_csr_private_key(self):
        private_key = dsa.generate_private_key(key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Virginia"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Richmond"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Organization"),
                        x509.NameAttribute(NameOID.COMMON_NAME, "example.com"),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
            .public_bytes(encoding=Encoding.PEM)
        )

        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/", {"file_uploaded": io.BytesIO(csr)})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content),
            {"csr": [{"error_code": "LU004", "description": "CSR public key is not of type RSAPublicKey.", "translations": []}]},
        )

    def test_invalid_csr_country(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Virginia"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Richmond"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Organization"),
                        x509.NameAttribute(NameOID.COMMON_NAME, "example.com"),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
            .public_bytes(encoding=Encoding.PEM)
        )

        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/", {"file_uploaded": io.BytesIO(csr)})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content),
            {"csr": [{"error_code": "LU007", "description": "CSR Subject C (Country) must be FI.", "translations": []}]},
        )

    def test_invalid_csr_cn_missing(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "FI"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Virginia"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Richmond"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Organization"),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
            .public_bytes(encoding=Encoding.PEM)
        )

        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/", {"file_uploaded": io.BytesIO(csr)})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content),
            {"csr": [{"error_code": "LU008", "description": "CSR Subject CN is missing.", "translations": []}]},
        )

    def test_invalid_csr_cn_not_matching_organization(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "FI"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Virginia"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Richmond"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Organization"),
                        x509.NameAttribute(NameOID.COMMON_NAME, "example.com"),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
            .public_bytes(encoding=Encoding.PEM)
        )

        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/", {"file_uploaded": io.BytesIO(csr)})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content),
            {
                "csr": [
                    {
                        "error_code": "LU009",
                        "description": "CSR Subject CN is not matching with the Organization data.",
                        "translations": [],
                    }
                ]
            },
        )

    def test_invalid_change_private_key(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "FI"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Uusimaa"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Helsinki"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Kela"),
                        x509.NameAttribute(NameOID.COMMON_NAME, "varda.kela.fi"),
                    ]
                )
            )
            .sign(private_key, hashes.SHA256())
            .public_bytes(encoding=Encoding.PEM)
        )

        client = SetUpTestClient("kela_luovutuspalvelu").client()
        resp = client.post("/api/client/v1/csr/", {"file_uploaded": io.BytesIO(csr), "change_private_key": 123})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            json.loads(resp.content),
            {"csr": [{"error_code": "LU012", "description": "Invalid value in change_private_key.", "translations": []}]},
        )
