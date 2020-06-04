import json

import responses
from django.test import TestCase

from rest_framework import status

from varda.models import Z5_AuditLog
from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient


class VardaPermissionsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    """
    Anonymous cannot see root api.
    """
    def test_permissions_root_url_anonymous(self):
        resp = self.client.get('/api/v1/?format=json')
        self.assertEqual(json.loads(resp.content)["detail"], "Authentication credentials were not provided.")

    def test_permissions_root_url_authenticated(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/?format=json')
        self.assertEqual(len(json.loads(resp.content)), 12)

    """
    Everyone should see only one vakajarjestaja:
    - Except anonymous: not allowed to see anything
    - If authenticated (kunta): should see their own
    """
    def test_permissions_vakajarjestaja_anonymous(self):
        resp = self.client.get('/api/v1/vakajarjestajat/?format=json')
        assert_status_code(resp, 403)

    def test_permissions_vakajarjestaja_authenticated(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/vakajarjestajat/?format=json')
        self.assertEqual(json.loads(resp.content)["count"], 1)
        self.assertEqual(json.loads(resp.content)["results"][0]["y_tunnus"], "8500570-7")

    """
    Henkilo-object: reverse-relation (to Lapsi, Huoltaja) permissions
    """
    def test_permissions_henkilo_reverse_relations_1(self):
        resp = self.client.get('/api/v1/henkilot/2/?format=json')
        assert_status_code(resp, 403)

    def test_permissions_henkilo_reverse_relations_2(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/henkilot/2/?format=json')
        self.assertEqual(len(json.loads(resp.content)["lapsi"]), 1)
        self.assertEqual(json.loads(resp.content)["lapsi"][0], "http://testserver/api/v1/lapset/1/")

    def test_permissions_henkilo_reverse_relations_3(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/henkilot/2/?format=json')
        self.assertEqual(len(json.loads(resp.content)["lapsi"]), 0)

    def test_permissions_henkilo_reverse_relations_4(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/henkilot/2/?format=json')
        self.assertEqual(len(json.loads(resp.content)["lapsi"]), 1)
        self.assertEqual(json.loads(resp.content)["lapsi"][0], "http://testserver/api/v1/lapset/1/")

    def test_permissions_henkilo_reverse_relations_5(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/henkilot/4/?format=json')
        self.assertNotIn('huoltaja', json.loads(resp.content))

    def test_permissions_henkilo_reverse_relations_6(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/henkilot/4/?format=json')
        self.assertEqual(len(json.loads(resp.content)['huoltaja']), 1)
        self.assertEqual(json.loads(resp.content)['huoltaja'][0], "http://testserver/api/admin/huoltajat/1/")

    """
    Making POST-requests:
    - If anonymous: never allowed
    - If authenticated: should be allowed, except vakajarjestaja, and if no object/relation violations!
    """
    def test_permissions_post_requests_vakajarjestaja(self):
        vakajarjestaja = {
            "nimi": "Testikaupunki",
            "y_tunnus": "5482703-8",
            "sahkopostiosoite": "testi@kaupunki.fi",
            "tilinumero": "FI12 3456 7890 1234 56",
            "puhelinnumero": "00112"
        }
        resp = self.client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, 403)  # anonymous not allowed

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, 403)  # authenticated not allowed

    @responses.activate
    def test_permissions_post_requests_toimipaikka(self):
        # This test relies on organisaatio_client default error handling
        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/1/",
            "nimi": "Pasilan toimipiste 2",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite": "Pasilankatu 123",
            "kayntiosoite_postitoimipaikka": "Helsinki",
            "kayntiosoite_postinumero": "00200",
            "postiosoite": "Pasilankatu 123",
            "postitoimipaikka": "Helsinki",
            "postinumero": "00200",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj99",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": "FI",
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }
        resp = self.client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 403)  # anonymous not allowed

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'nimi': ['Could not check toimipaikka-duplicates from Organisaatiopalvelu. Please try again later.']})

        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/2/",
            "nimi": "Pasilan toimipiste 2",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite": "Pasilankatu 123",
            "kayntiosoite_postitoimipaikka": "Helsinki",
            "kayntiosoite_postinumero": "00200",
            "postiosoite": "Pasilankatu 123",
            "postitoimipaikka": "Helsinki",
            "postinumero": "00200",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj98",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": "FI",
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        self.assertEqual(json.loads(resp.content), {"vakajarjestaja": ["Invalid hyperlink - Object does not exist."]})
        assert_status_code(resp, 400)  # vakajarjestaja not owned by tester2

    def test_permissions_henkilo(self):
        henkilo = {
            "henkilotunnus": "120516A123V"
        }

        resp = self.client.put('/api/v1/henkilot/3/', henkilo)
        assert_status_code(resp, 403)  # anonymous not allowed

        client = SetUpTestClient('tester').client()
        resp = client.put('/api/v1/henkilot/3/', henkilo)
        assert_status_code(resp, 403)  # updates disabled for authenticated users

        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/henkilot/3/')
        assert_status_code(resp, 403)  # delete disabled for authenticated users

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/3/', henkilo)
        assert_status_code(resp, 405)  # HTTP-method not allowed (POST, for henkilo-id)

    @responses.activate
    def test_get_henkilot(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            "henkilotunnus": "090471-813K",
            "etunimet": "Kaarle-Johan",
            "kutsumanimi": "Kaarle-Johan",
            "sukunimi": "Mattson"
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)

        new_henkilo_url = json.loads(resp.content)["url"]

        resp = self.client.get(new_henkilo_url)
        assert_status_code(resp, 403)  # anonymous not allowed

        client = SetUpTestClient('tester').client()
        resp = client.get(new_henkilo_url)
        assert_status_code(resp, 200)

        client = SetUpTestClient('tester2').client()
        resp = client.get(new_henkilo_url)
        assert_status_code(resp, 200)

    @responses.activate
    def test_create_relation_to_someone_elses_created_henkilo(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            "henkilotunnus": "090471-813K",
            "etunimet": "Kaarle-Johan",
            "kutsumanimi": "Kaarle-Johan",
            "sukunimi": "Mattson"
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)

        new_henkilo_url = json.loads(resp.content)["url"]
        lapsi = {
            "henkilo": new_henkilo_url
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 201)

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 201)

    """
    Tests for nested viewsets, e.g. /api/v1/lapset/33/huoltajat/
    """
    def test_get_huoltajat_by_parent_id(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/lapset/1/huoltajat/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)["count"], 2)

        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/lapset/1/huoltajat/')
        assert_status_code(resp, 403)

        resp = client.get('/api/v1/lapset/3/huoltajat/')
        assert_status_code(resp, 403)

        resp = self.client.get('/api/v1/lapset/1/huoltajat/')  # anonymous
        assert_status_code(resp, 403)

        resp = self.client.get('/api/v1/lapset/3/huoltajat/')
        assert_status_code(resp, 403)

    def test_get_lapset_by_parent_id(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/admin/huoltajat/1/lapset/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)["count"], 1)

        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/admin/huoltajat/1/lapset/')
        assert_status_code(resp, 403)

        resp = client.get('/api/admin/huoltajat/3/lapset/')
        assert_status_code(resp, 403)

    @responses.activate
    def test_get_lapset_by_parent_id_2(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            "henkilotunnus": "090471-813K",
            "etunimet": "Kaarle-Johan",
            "kutsumanimi": "Kaarle-Johan",
            "sukunimi": "Mattson"
        }

        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)

        new_henkilo_url = json.loads(resp.content)["url"]
        lapsi = {
            "henkilo": new_henkilo_url
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 201)

        henkilo_2 = {
            "henkilotunnus": "251150-711U",
            "etunimet": "Johanna Maarit",
            "kutsumanimi": "Maarit",
            "sukunimi": "Nieminen"
        }

        resp = client.post('/api/v1/henkilot/', henkilo_2)
        assert_status_code(resp, 201)

        new_henkilo_url_2 = json.loads(resp.content)["url"]

        huoltaja = {
            "henkilo": new_henkilo_url_2,
        }

        resp = client.post('/api/admin/huoltajat/', huoltaja)
        assert_status_code(resp, 405)

    def test_create_non_unique_lapsi_within_vakajarjestaja(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/lapset/1/')
        henkilo_url = json.loads(resp.content)["henkilo"]
        lapsi = {
            "henkilo": henkilo_url
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 200)  # Lapsi is already added

    def test_api_push_paos_lapsi_no_vaka_tallentaja_permissions(self):
        """
        tester-user has toimipaikka-tallentaja-permissions.
        """
        client = SetUpTestClient('tester').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            "paos_organisaatio": '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'User does not have permissions.'})

    def test_try_to_change_henkilo(self):
        client = SetUpTestClient('tester').client()
        lapsi = {
            "henkilo": "http://testserver/api/v1/henkilot/8/",
        }
        resp = client.put('/api/v1/lapset/1/', lapsi)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'henkilo': ['This cannot be changed.']})

    def test_push_correct_paos_toiminta_organisaatio_without_permissions(self):
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/2/",
            "paos_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/3/"
        }
        client = SetUpTestClient('tester').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', data=paos_toiminta, content_type='application/json')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'You do not have permission to perform this action.'})

    def test_get_paos_toiminnat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/paos-toiminnat/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'You do not have permission to perform this action.'})

    def test_get_toimipaikat(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['count'], 7)

        """
        TODO:
        client = SetUpTestClient('antero_jenkins').client()
        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)["count"], 1)

        client = SetUpTestClient('antero_platform').client()
        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, 403)
        """

    def test_view_content_as_anonymous(self):
        # vaka-jarjestajat tested already elsewhere
        resp = self.client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/toiminnallisetpainotukset/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/kielipainotukset/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/henkilot/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/admin/huoltajat/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/lapset/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/varhaiskasvatuspaatokset/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/varhaiskasvatussuhteet/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/maksutiedot/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

        resp = self.client.get('/api/v1/paos-toiminnat/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

    def test_audit_log_collected_for_authenticated_users(self):
        self.client.get('/api/v1/vakajarjestajat/')
        query_length = len(Z5_AuditLog.objects.all())
        self.assertEqual(query_length, 0)

        client = SetUpTestClient('tester').client()
        client.get('/api/v1/vakajarjestajat/')
        query_length = len(Z5_AuditLog.objects.all())
        self.assertEqual(query_length, 1)

    def test_audit_log_collected_when_fetching_user(self):
        data = {'henkilo_oid': '1.2.246.562.24.47279942650'}
        client = SetUpTestClient('tester').client()
        client.post('/api/v1/hae-henkilo/', data)
        audit_log = Z5_AuditLog.objects.all()[0]
        self.assertEqual(audit_log.user.username, "tester")
        self.assertEqual(audit_log.successful_get_request_path, "/api/v1/hae-henkilo/id=2")

    def test_audit_log_for_toimipaikan_lapset(self):
        client = SetUpTestClient('tester').client()
        client.get('/api/ui/toimipaikat/1/lapset/')
        audit_log = Z5_AuditLog.objects.all()[0]
        self.assertEqual(audit_log.successful_get_request_path, '/api/ui/toimipaikat/1/lapset/')

    def test_audit_log_for_nested_resources(self):
        client = SetUpTestClient('tester').client()
        client.get('/api/v1/vakajarjestajat/1/toimipaikat/')
        query_length = len(Z5_AuditLog.objects.all())
        self.assertEqual(query_length, 1)

        client.get('/api/v1/vakajarjestajat/2/toimipaikat/')
        audit_log = Z5_AuditLog.objects.all()[1]
        self.assertEqual(audit_log.successful_get_request_path, '/api/v1/vakajarjestajat/2/toimipaikat/')

    def test_huoltaja_tallentaja_dont_see_vakatiedot(self):
        """
        tester cannot see vakatiedot for this maksutiedot<->lapsi,
        tester2 can see.
        """
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/maksutiedot/2/')
        lapsi_url = json.loads(resp.content)['lapsi']
        resp = client.get(lapsi_url)
        assert_status_code(resp, 200)
        vakapaatos_url = json.loads(resp.content)['varhaiskasvatuspaatokset_top'][0]
        resp = client.get(vakapaatos_url)
        assert_status_code(resp, 200)

        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/maksutiedot/2/')
        lapsi_url = json.loads(resp.content)['lapsi']
        resp = client.get(lapsi_url)
        assert_status_code(resp, 200)
        vakapaatos_url = json.loads(resp.content)['varhaiskasvatuspaatokset_top'][0]
        resp = client.get(vakapaatos_url)
        assert_status_code(resp, 404)

    """
    TODO: Reporting related permissions
    """
    """
    def test_permissions_reporting_root_url_anonymous(self):
        resp = self.client.get('/reporting/api/v1/')
        assert_status_code(resp, 200)

    def test_permissions_reporting_url_anonymous(self):
        resp = self.client.get('/reporting/api/v1/lapset-ryhmittain/')
        assert_status_code(resp, 403)

    def test_permissions_reporting_url_authenticated(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/reporting/api/v1/lapset-ryhmittain/')
        assert_status_code(resp, 403)

    def test_permissions_reporting_url_antero_user(self):
        client = SetUpTestClient('antero_platform').client()
        resp = client.get('/reporting/api/v1/lapset-ryhmittain/')
        assert_status_code(resp, 200)
    """
