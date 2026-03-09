import responses
from django.test import TestCase
from rest_framework import status

from varda.models import Henkilo
from varda.unit_tests.test_utils import SetUpTestClient, assert_validation_error


class VardaHenkiloViewSetTests(TestCase):
    fixtures = ["fixture_basics"]

    @responses.activate
    def test_henkilo_with_multiple_hetu_not_create_duplicate(self):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/hetu=210669-043K",
            json={
                "oidHenkilo": "1.2.987654321",
                "hetu": "020476-321F",
                "etunimet": "Pauliina",
                "kutsumanimi": "Pauliina",
                "sukunimi": "Virtanen",
            },
            status=status.HTTP_200_OK,
        )
        responses.add(
            responses.POST,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/",
            json="1.2.987654321",
            status=status.HTTP_201_CREATED,
        )
        henkilo = {"henkilotunnus": "210669-043K", "etunimet": "Pauliina", "kutsumanimi": "Pauliina", "sukunimi": "Virtanen"}
        client = SetUpTestClient("tester").client()
        resp = client.post("/api/v1/henkilot/", henkilo)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual("1.2.987654321", resp.json()["henkilo_oid"])

        henkilo_count = Henkilo.objects.filter(henkilo_oid="1.2.987654321").count()
        self.assertEqual(1, henkilo_count)

    @responses.activate
    def test_henkilo_hetu_change_not_create_duplicate(self):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/hetu=210669-043K",
            json={
                "oidHenkilo": "1.2.987654321",
                "hetu": "210669-043K",
                "etunimet": "Pauliina",
                "kutsumanimi": "Pauliina",
                "sukunimi": "Virtanen",
                "yksiloityVTJ": True,
            },
            status=status.HTTP_200_OK,
        )
        henkilo = {"henkilotunnus": "210669-043K", "etunimet": "Pauliina", "kutsumanimi": "Pauliina", "sukunimi": "Virtanen"}
        client = SetUpTestClient("tester").client()
        resp = client.post("/api/v1/henkilot/", henkilo)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual("1.2.987654321", resp.json()["henkilo_oid"])

        henkilo_count = Henkilo.objects.filter(henkilo_oid="1.2.987654321").count()
        self.assertEqual(1, henkilo_count)

    @responses.activate
    def test_henkilo_add_no_oid_response(self):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/hetu=010106A991Y",
            json={
                "oidHenkilo": "",
                "hetu": "010106A991Y",
                "etunimet": "Nooid",
                "kutsumanimi": "Nooid",
                "sukunimi": "Fromonr",
                "yksiloityVTJ": True,
            },
            status=status.HTTP_200_OK,
        )
        henkilo = {"henkilotunnus": "010106A991Y", "etunimet": "Nooid", "kutsumanimi": "Nooid", "sukunimi": "Fromonr"}
        client = SetUpTestClient("tester").client()
        resp = client.post("/api/v1/henkilot/", henkilo)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ["henkilo_oid"], "HE018", "Henkilo is missing national identification number.")

        henkilo_count = Henkilo.objects.filter(etunimet="Nooid", sukunimi="Fromonr").count()
        self.assertEqual(0, henkilo_count)

    @responses.activate
    def test_henkilo_add_faulty_oid_response(self):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/hetu=010106A991Y",
            json={
                "oidHenkilo": "1.2.246.562.00.10234567891",
                "hetu": "010106A991Y",
                "etunimet": "Faultyoid",
                "kutsumanimi": "Faultyoid",
                "sukunimi": "Fromonr",
                "yksiloityVTJ": True,
            },
            status=status.HTTP_200_OK,
        )
        henkilo = {"henkilotunnus": "010106A991Y", "etunimet": "Faultyoid", "kutsumanimi": "Faultyoid", "sukunimi": "Fromonr"}
        client = SetUpTestClient("tester").client()
        resp = client.post("/api/v1/henkilot/", henkilo)
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        assert_validation_error(resp, ["henkilo_oid"], "MI011", "Not an OID for a person.")

        henkilo_count = Henkilo.objects.filter(etunimet="Faultyoid", sukunimi="Fromonr").count()
        self.assertEqual(0, henkilo_count)

    @responses.activate
    def test_henkilo_change_no_oid_response(self):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/hetu=210669-043K",
            json={
                "oidHenkilo": "",
                "hetu": "210669-043K",
                "etunimet": "Pauliina",
                "kutsumanimi": "Pauliina",
                "sukunimi": "Virtanen",
                "yksiloityVTJ": True,
            },
            status=status.HTTP_200_OK,
        )
        henkilo = {"henkilotunnus": "210669-043K", "etunimet": "Pauliina", "kutsumanimi": "Pauliina", "sukunimi": "Virtanen"}
        client = SetUpTestClient("tester").client()
        resp = client.post("/api/v1/henkilot/", henkilo)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ["henkilo_oid"], "HE018", "Henkilo is missing national identification number.")
