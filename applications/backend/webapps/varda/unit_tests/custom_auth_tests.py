from unittest.mock import MagicMock, patch

import requests
import responses

from django.conf import settings
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed

from varda.constants import CAS_TIMEOUT_TUPLE
from varda.custom_auth import CustomBasicAuthentication, _get_huollettavat_oids
from varda.misc import encrypt_string, hash_string
from varda.models import Henkilo, Huoltaja, Huoltajuussuhde, Lapsi, Z1_OphAuthentication
from varda.oph_yhteiskayttopalvelu_autentikaatio import get_service_ticket


class GetHuollettavatOidsTests(TestCase):
    def _create_henkilo(self, henkilo_oid, hetu):
        return Henkilo.objects.create(
            henkilotunnus=encrypt_string(hetu),
            henkilotunnus_unique_hash=hash_string(hetu),
            henkilo_oid=henkilo_oid,
            etunimet="Testi",
            kutsumanimi="Testi",
            sukunimi="Henkilo",
        )

    def _create_lapsi(self, henkilo):
        return Lapsi.objects.create(henkilo=henkilo)

    @patch("varda.custom_auth.get_vtj_service")
    @patch("varda.custom_auth.create_henkilo_in_varda_if_not_found")
    def test_returns_local_lapsi_oids_without_vtj_fetch(self, mock_create_henkilo, mock_get_vtj_service):
        huoltaja_henkilo = self._create_henkilo("1.2.246.562.24.10000000001", "010180-900C")
        lapsi_henkilo = self._create_henkilo("1.2.246.562.24.10000000002", "020210A900R")
        lapsi = self._create_lapsi(lapsi_henkilo)
        huoltaja = Huoltaja.objects.create(henkilo=huoltaja_henkilo)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi=lapsi, voimassa_kytkin=True)
        mock_create_henkilo.return_value = huoltaja_henkilo.id

        result = _get_huollettavat_oids(huoltaja_henkilo.henkilo_oid, "010180-900C")

        self.assertEqual(list(result), [lapsi_henkilo.henkilo_oid])
        mock_get_vtj_service.assert_not_called()

    @patch("varda.custom_auth.get_vtj_service")
    @patch("varda.custom_auth.create_henkilo_in_varda_if_not_found")
    def test_creates_huoltaja_and_huoltajuussuhde_from_vtj_lapsi(self, mock_create_henkilo, mock_get_vtj_service):
        huoltaja_henkilo = self._create_henkilo("1.2.246.562.24.10000000003", "010180-901D")
        lapsi_henkilo = self._create_henkilo("1.2.246.562.24.10000000004", "030310A9011")
        lapsi = self._create_lapsi(lapsi_henkilo)
        service = MagicMock()
        service.get_henkilo.return_value = {"lapset": [{"hetu": "030310A9011"}]}
        mock_get_vtj_service.return_value = service
        mock_create_henkilo.return_value = huoltaja_henkilo.id

        result = _get_huollettavat_oids(huoltaja_henkilo.henkilo_oid, "010180-901D")

        huoltaja = Huoltaja.objects.get(henkilo=huoltaja_henkilo)
        self.assertEqual(result, [lapsi_henkilo.henkilo_oid])
        self.assertTrue(Huoltajuussuhde.objects.filter(huoltaja=huoltaja, lapsi=lapsi, voimassa_kytkin=True).exists())

    @patch("varda.custom_auth.get_vtj_service")
    @patch("varda.custom_auth.create_henkilo_in_varda_if_not_found")
    def test_reactivates_existing_inactive_huoltajuussuhde_from_vtj(self, mock_create_henkilo, mock_get_vtj_service):
        huoltaja_henkilo = self._create_henkilo("1.2.246.562.24.10000000005", "010180-902E")
        lapsi_henkilo = self._create_henkilo("1.2.246.562.24.10000000006", "040410A902B")
        lapsi = self._create_lapsi(lapsi_henkilo)
        huoltaja = Huoltaja.objects.create(henkilo=huoltaja_henkilo)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi=lapsi, voimassa_kytkin=False)
        service = MagicMock()
        service.get_henkilo.return_value = {"lapset": [{"hetu": "040410A902B"}]}
        mock_get_vtj_service.return_value = service
        mock_create_henkilo.return_value = huoltaja_henkilo.id

        result = _get_huollettavat_oids(huoltaja_henkilo.henkilo_oid, "010180-902E")

        self.assertEqual(result, [lapsi_henkilo.henkilo_oid])
        self.assertEqual(Huoltajuussuhde.objects.filter(huoltaja=huoltaja, lapsi=lapsi).count(), 1)
        self.assertTrue(Huoltajuussuhde.objects.get(huoltaja=huoltaja, lapsi=lapsi).voimassa_kytkin)

    @patch("varda.custom_auth.get_vtj_service")
    @patch("varda.custom_auth.create_henkilo_in_varda_if_not_found")
    def test_skip_vtj_lapset_without_local_lapsi(self, mock_create_henkilo, mock_get_vtj_service):
        huoltaja_henkilo = self._create_henkilo("1.2.246.562.24.10000000007", "010180-903F")
        self._create_henkilo("1.2.246.562.24.10000000008", "050510A903L")
        service = MagicMock()
        service.get_henkilo.return_value = {"lapset": [{"hetu": "050510A903L"}, {"hetu": "060610A9042"}]}
        mock_get_vtj_service.return_value = service
        mock_create_henkilo.return_value = huoltaja_henkilo.id

        result = _get_huollettavat_oids(huoltaja_henkilo.henkilo_oid, "010180-903F")

        self.assertEqual(result, [])
        self.assertFalse(Huoltaja.objects.filter(henkilo=huoltaja_henkilo).exists())
        self.assertFalse(Huoltajuussuhde.objects.filter(huoltaja__henkilo=huoltaja_henkilo).exists())

    @patch("varda.custom_auth.get_vtj_service")
    @patch("varda.custom_auth.create_henkilo_in_varda_if_not_found")
    def test_empty_vtj_lapset_response_does_not_create_huoltaja(self, mock_create_henkilo, mock_get_vtj_service):
        huoltaja_henkilo = self._create_henkilo("1.2.246.562.24.10000000009", "010180-904G")
        service = MagicMock()
        service.get_henkilo.return_value = {"lapset": []}
        mock_get_vtj_service.return_value = service
        mock_create_henkilo.return_value = huoltaja_henkilo.id

        result = _get_huollettavat_oids(huoltaja_henkilo.henkilo_oid, "010180-904G")

        self.assertEqual(result, [])
        self.assertFalse(Huoltaja.objects.filter(henkilo=huoltaja_henkilo).exists())


class CasTimeoutTests(TestCase):
    TGT_URL = settings.OPINTOPOLKU_DOMAIN + "/cas/v1/tickets"
    TGT_LOCATION = settings.OPINTOPOLKU_DOMAIN + "/cas/v1/tickets/TGT-1"
    OMATTIEDOT_URL = settings.OPINTOPOLKU_DOMAIN + "/kayttooikeus-service/henkilo/current/omattiedot"

    def _add_tgt_response(self):
        responses.add(responses.POST, self.TGT_URL, status=201, headers={"Location": self.TGT_LOCATION})

    @responses.activate
    @patch("varda.oph_yhteiskayttopalvelu_autentikaatio.sleep")
    def test_palvelukayttaja_apikey_cas_timeout(self, mock_sleep):
        self._add_tgt_response()
        responses.add(responses.POST, self.TGT_LOCATION, body=requests.exceptions.ReadTimeout())
        responses.add(responses.GET, self.OMATTIEDOT_URL, body=requests.exceptions.ReadTimeout())

        with (
            patch("varda.oph_yhteiskayttopalvelu_autentikaatio.requests.post", wraps=requests.post) as mock_post,
            patch("varda.custom_auth.requests.get", wraps=requests.get) as mock_get,
            self.assertRaises(AuthenticationFailed),
        ):
            CustomBasicAuthentication()._authenticate_and_get_omattiedot("palvelukayttaja", "salasana")

        for mock_call in mock_post.call_args_list + mock_get.call_args_list:
            self.assertEqual(mock_call.kwargs["timeout"], CAS_TIMEOUT_TUPLE)
        # Service ticket request that timed out is not retried, palvelukayttaja is waiting in a web worker
        self.assertEqual([call.request.url for call in responses.calls], [self.TGT_URL, self.TGT_LOCATION, self.OMATTIEDOT_URL])
        mock_sleep.assert_not_called()

    @responses.activate
    @patch("varda.oph_yhteiskayttopalvelu_autentikaatio.sleep")
    def test_internal_request_cas_timeout_is_retried(self, mock_sleep):
        Z1_OphAuthentication.objects.update_or_create(id=1, defaults={"ticketing_granting_ticket": self.TGT_LOCATION})
        responses.add(responses.POST, self.TGT_LOCATION, body=requests.exceptions.ReadTimeout())

        self.assertEqual(get_service_ticket("oppijanumerorekisteri-service", None, None, False, False), "")
        self.assertEqual(len(responses.calls), 4)
        self.assertEqual(mock_sleep.call_count, 4)
