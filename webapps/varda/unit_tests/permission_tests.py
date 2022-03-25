import json
import re
import time
from math import isclose
from unittest.mock import patch

import responses
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase, override_settings

from rest_framework import status
from rest_framework.test import APIClient

from varda.models import Z4_CasKayttoOikeudet, Z5_AuditLog, Organisaatio
from varda.unit_tests.kayttooikeus_palvelukayttaja_tests import mock_cas_palvelukayttaja_responses
from varda.unit_tests.test_utils import (assert_status_code, base64_encoding, TEST_CACHE_SETTINGS, SetUpTestClient,
                                         assert_validation_error, post_henkilo_to_get_permissions)


class VardaPermissionsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    """
    Anonymous cannot see root api.
    """
    def test_permissions_root_url_anonymous(self):
        resp = self.client.get('/api/v1/?format=json')
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

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
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_permissions_vakajarjestaja_authenticated(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/vakajarjestajat/?format=json')
        self.assertEqual(json.loads(resp.content)['count'], 1)
        self.assertEqual(json.loads(resp.content)['results'][0]['y_tunnus'], '8500570-7')

    """
    Henkilo-object: reverse-relation (to Lapsi, Huoltaja) permissions
    """
    def test_permissions_henkilo_reverse_relations_1(self):
        resp = self.client.get('/api/v1/henkilot/2/?format=json')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_permissions_henkilo_reverse_relations_2(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/henkilot/2/?format=json')
        self.assertEqual(len(json.loads(resp.content)['lapsi']), 1)
        self.assertEqual(json.loads(resp.content)['lapsi'][0], 'http://testserver/api/v1/lapset/1/')

    def test_permissions_henkilo_reverse_relations_3(self):
        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_id=2)
        resp = client.get('/api/v1/henkilot/2/?format=json')
        self.assertEqual(len(json.loads(resp.content)['lapsi']), 0)

    def test_permissions_henkilo_reverse_relations_4(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/henkilot/2/?format=json')
        self.assertEqual(len(json.loads(resp.content)['lapsi']), 1)
        self.assertEqual(json.loads(resp.content)['lapsi'][0], 'http://testserver/api/v1/lapset/1/')

    def test_permissions_henkilo_reverse_relations_5(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/henkilot/4/?format=json')
        self.assertNotIn('huoltaja', json.loads(resp.content))

    def test_permissions_henkilo_reverse_relations_6(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/henkilot/4/?format=json')
        self.assertEqual(len(json.loads(resp.content)['huoltaja']), 1)
        self.assertEqual(json.loads(resp.content)['huoltaja'][0], 'http://testserver/api/admin/huoltajat/1/')

    """
    Making POST-requests:
    - If anonymous: never allowed
    - If authenticated: should be allowed, except vakajarjestaja, and if no object/relation violations!
    """
    def test_permissions_post_requests_vakajarjestaja(self):
        vakajarjestaja = {
            'nimi': 'Testikaupunki',
            'y_tunnus': '5482703-8',
            'sahkopostiosoite': 'testi@kaupunki.fi',
            'puhelinnumero': '00112'
        }
        resp = self.client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # anonymous not allowed

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # authenticated not allowed

    @responses.activate
    def test_permissions_post_requests_toimipaikka(self):
        # This test relies on organisaatio_client default error handling
        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/1/',
            'nimi': 'Pasilan toimipiste 2',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Pasilankatu 123',
            'kayntiosoite_postitoimipaikka': 'Helsinki',
            'kayntiosoite_postinumero': '00200',
            'postiosoite': 'Pasilankatu 123',
            'postitoimipaikka': 'Helsinki',
            'postinumero': '00200',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj99',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': 'FI',
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1'
        }
        resp = self.client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # anonymous not allowed

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'TP007', 'Could not check duplicates from Organisaatiopalvelu. Please try again later.')

        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/2/',
            'nimi': 'Pasilan toimipiste 2',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Pasilankatu 123',
            'kayntiosoite_postitoimipaikka': 'Helsinki',
            'kayntiosoite_postinumero': '00200',
            'postiosoite': 'Pasilankatu 123',
            'postitoimipaikka': 'Helsinki',
            'postinumero': '00200',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj98',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': 'FI',
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1'
        }
        client = SetUpTestClient('tester2').client()
        resp2 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_validation_error(resp2, 'vakajarjestaja', 'GE008', 'Invalid hyperlink, object does not exist.')
        assert_status_code(resp2, status.HTTP_400_BAD_REQUEST)  # vakajarjestaja not owned by tester2

    def test_permissions_henkilo(self):
        henkilo = {
            'henkilotunnus': '120516A123V'
        }

        resp = self.client.put('/api/v1/henkilot/3/', henkilo)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # anonymous not allowed

        client = SetUpTestClient('tester').client()
        resp = client.put('/api/v1/henkilot/3/', henkilo)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # updates disabled for authenticated users

        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/henkilot/3/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # delete disabled for authenticated users

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/3/', henkilo)
        assert_status_code(resp, status.HTTP_405_METHOD_NOT_ALLOWED)  # HTTP-method not allowed (POST, for henkilo-id)

    @responses.activate
    def test_get_henkilot(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '090471-813K',
            'etunimet': 'Kaarle-Johan',
            'kutsumanimi': 'Kaarle-Johan',
            'sukunimi': 'Mattson'
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)

        new_henkilo_url = json.loads(resp.content)['url']

        resp = self.client.get(new_henkilo_url)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)  # anonymous not allowed

        client = SetUpTestClient('tester').client()
        resp = client.get(new_henkilo_url)
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)  # tester does not have permissions to the created Henkilo object

        client = SetUpTestClient('tester2').client()
        resp = client.get(new_henkilo_url)
        assert_status_code(resp, status.HTTP_200_OK)

    @responses.activate
    def test_create_relation_to_someone_elses_created_henkilo(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '090471-813K',
            'etunimet': 'Kaarle-Johan',
            'kutsumanimi': 'Kaarle-Johan',
            'sukunimi': 'Mattson',
        }
        organisaatio_oid_34683023489 = '1.2.246.562.10.34683023489'
        vakajarjestaja_id_34683023489 = Organisaatio.objects.filter(organisaatio_oid=organisaatio_oid_34683023489).first().id

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)

        new_henkilo_url = json.loads(resp.content)['url']
        lapsi = {
            'henkilo': new_henkilo_url,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id_34683023489),
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)

        organisaatio_oid_93957375488 = '1.2.246.562.10.93957375488'
        vakajarjestaja_id_93957375488 = Organisaatio.objects.filter(organisaatio_oid=organisaatio_oid_93957375488).first().id
        vakajarjestaja_url_93957375488 = 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id_93957375488)
        lapsi.update({'vakatoimija': vakajarjestaja_url_93957375488})

        client = SetUpTestClient('tester5').client()
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilo', 'GE008', 'Invalid hyperlink, object does not exist.')

        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)

    """
    Tests for nested viewsets, e.g. /api/v1/lapset/33/huoltajat/
    """
    def test_get_huoltajat_by_parent_id(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/lapset/1/huoltajat/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], 2)

        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/lapset/1/huoltajat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

        resp = client.get('/api/v1/lapset/3/huoltajat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

        resp = self.client.get('/api/v1/lapset/1/huoltajat/')  # anonymous
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

        resp = self.client.get('/api/v1/lapset/3/huoltajat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_get_lapset_by_parent_id(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/admin/huoltajat/1/lapset/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], 1)

        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/admin/huoltajat/1/lapset/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

        resp = client.get('/api/admin/huoltajat/3/lapset/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    @responses.activate
    def test_get_lapset_by_parent_id_2(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '090471-813K',
            'etunimet': 'Kaarle-Johan',
            'kutsumanimi': 'Kaarle-Johan',
            'sukunimi': 'Mattson'
        }

        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)

        new_henkilo_url = json.loads(resp.content)['url']
        lapsi = {
            'henkilo': new_henkilo_url,
            'vakatoimija': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)

        henkilo_2 = {
            'henkilotunnus': '251150-711U',
            'etunimet': 'Johanna Maarit',
            'kutsumanimi': 'Maarit',
            'sukunimi': 'Nieminen'
        }

        resp = client.post('/api/v1/henkilot/', henkilo_2)
        assert_status_code(resp, status.HTTP_201_CREATED)

        new_henkilo_url_2 = json.loads(resp.content)['url']

        huoltaja = {
            'henkilo': new_henkilo_url_2,
        }

        resp = client.post('/api/admin/huoltajat/', huoltaja)
        assert_status_code(resp, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_non_unique_lapsi_within_vakajarjestaja(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/lapset/1/')
        henkilo_url = json.loads(resp.content)['henkilo']
        vakatoimija_url = json.loads(resp.content)['vakatoimija']
        lapsi = {
            'henkilo': henkilo_url,
            'vakatoimija': vakatoimija_url,
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_200_OK)  # Lapsi is already added

    def test_api_push_paos_lapsi_no_vaka_tallentaja_permissions(self):
        """
        tester-user has toimipaikka-tallentaja-permissions.
        """
        client = SetUpTestClient('tester').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE003', 'User does not have permissions.')

    def test_try_to_change_henkilo(self):
        client = SetUpTestClient('tester').client()
        organisaatio_oid = '1.2.246.562.10.93957375488'
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=organisaatio_oid).first().id
        post_henkilo_to_get_permissions(client, henkilo_id=8)
        lapsi = {
            'henkilo': 'http://testserver/api/v1/henkilot/8/',
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id),
            'lahdejarjestelma': '1'
        }
        resp = client.put('/api/v1/lapset/1/', lapsi)
        assert_status_code(resp, 400)
        assert_validation_error(resp, 'henkilo', 'GE013', 'Changing of this field is not allowed.')

    def test_push_correct_paos_toiminta_organisaatio_without_permissions(self):
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/2/',
            'paos_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/3/'
        }
        client = SetUpTestClient('tester').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', data=paos_toiminta, content_type='application/json')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

    def test_get_paos_toiminnat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/paos-toiminnat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

    def test_get_toimipaikat(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], 10)

    def test_view_content_as_anonymous(self):
        # vaka-jarjestajat tested already elsewhere
        resp = self.client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/toiminnallisetpainotukset/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/kielipainotukset/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/henkilot/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/admin/huoltajat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/lapset/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/varhaiskasvatuspaatokset/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/varhaiskasvatussuhteet/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/maksutiedot/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

        resp = self.client.get('/api/v1/paos-toiminnat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

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
        self.assertEqual(audit_log.user.username, 'tester')
        self.assertEqual(audit_log.successful_get_request_path, '/api/v1/hae-henkilo/id=2')

    def test_audit_log_for_toimipaikan_lapset(self):
        client = SetUpTestClient('tester').client()
        client.get('/api/ui/vakajarjestajat/2/lapset/?toimipaikat=1')
        audit_log = Z5_AuditLog.objects.all()[0]
        self.assertEqual(audit_log.successful_get_request_path, '/api/ui/vakajarjestajat/2/lapset/')

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
        resp = client.get('/api/v1/maksutiedot/1:testing-maksutieto2/')
        lapsi_url = json.loads(resp.content)['lapsi']
        resp = client.get(lapsi_url)
        assert_status_code(resp, status.HTTP_200_OK)
        vakapaatos_url = json.loads(resp.content)['varhaiskasvatuspaatokset_top'][0]
        resp = client.get(vakapaatos_url)
        assert_status_code(resp, status.HTTP_200_OK)

        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/maksutiedot/1:testing-maksutieto2/')
        lapsi_url = json.loads(resp.content)['lapsi']
        resp = client.get(lapsi_url)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.content)['varhaiskasvatuspaatokset_top']), 0)

    def test_toimijatiedot_update(self):
        vakajarjestaja_qs = Organisaatio.objects.filter(organisaatio_oid='1.2.246.562.10.34683023489')
        new_email = 'test@email.com'
        client = SetUpTestClient('tester2').client()

        vakajarjestaja_patch = {
            'sahkopostiosoite': new_email
        }
        resp = client.patch(f'/api/v1/vakajarjestajat/{vakajarjestaja_qs.first().id}/', vakajarjestaja_patch)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(vakajarjestaja_qs.first().sahkopostiosoite, new_email)

        # Remove user from toimijatiedot tallentaja group
        group = Group.objects.get(name='VARDA_TOIMIJATIEDOT_TALLENTAJA_1.2.246.562.10.34683023489')
        User.objects.get(username='tester2').groups.remove(group)

        resp_fail = client.patch(f'/api/v1/vakajarjestajat/{vakajarjestaja_qs.first().id}/', vakajarjestaja_patch)
        assert_status_code(resp_fail, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_fail, 'errors', 'PE006', 'User does not have permission to perform this action.')

    @responses.activate
    def test_henkilo_lapsi_permissions(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.246.562.24.47509942636',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '280616A148T',
            'etunimet': 'Testi Tero',
            'kutsumanimi': 'Testi',
            'sukunimi': 'Testinen'
        }

        vaka_vakajarjestaja_client = SetUpTestClient('vakatietojen_tallentaja').client()
        vaka_vakajarjestaja_client_2 = SetUpTestClient('huoltajatietojen_tallentaja').client()
        vaka_toimipaikka_client = SetUpTestClient('vakatietojen_toimipaikka_tallentaja_9395737548815').client()
        henkilosto_vakajarjestaja_client = SetUpTestClient('tyontekija_tallentaja').client()
        henkilosto_toimipaikka_client = SetUpTestClient('tyontekija_toimipaikka_tallentaja_9395737548815').client()

        resp_henkilo_post = vaka_vakajarjestaja_client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp_henkilo_post, status.HTTP_201_CREATED)
        henkilo_id = json.loads(resp_henkilo_post.content)['id']
        self._assert_permissions_to_henkilo(henkilo_id, (vaka_vakajarjestaja_client,),
                                            (vaka_vakajarjestaja_client_2, vaka_toimipaikka_client,
                                             henkilosto_vakajarjestaja_client, henkilosto_toimipaikka_client,))

        vakatoimija_oid = '1.2.246.562.10.34683023489'
        lapsi_tunniste = 'testing-lapsi'
        lapsi = {
            'henkilo': f'/api/v1/henkilot/{henkilo_id}/',
            'vakatoimija_oid': vakatoimija_oid,
            'lahdejarjestelma': '1',
            'tunniste': lapsi_tunniste,
        }
        resp_lapsi_post = vaka_vakajarjestaja_client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi_post, status.HTTP_201_CREATED)
        self._assert_permissions_to_henkilo(henkilo_id, (vaka_vakajarjestaja_client, vaka_vakajarjestaja_client_2,),
                                            (vaka_toimipaikka_client, henkilosto_vakajarjestaja_client,
                                             henkilosto_toimipaikka_client,))

        vakapaatos_tunniste = 'testing-vakapaatos'
        vakapaatos = {
            'lapsi_tunniste': lapsi_tunniste,
            'jarjestamismuoto_koodi': 'jm01',
            'tuntimaara_viikossa': 45,
            'tilapainen_vaka_kytkin': False,
            'vuorohoito': False,
            'kokopaivainen_vaka_kytkin': True,
            'hakemus_pvm': '2021-01-01',
            'alkamis_pvm': '2021-01-05',
            'lahdejarjestelma': '1',
            'tunniste': vakapaatos_tunniste,
        }
        resp_vakapaatos_post = vaka_vakajarjestaja_client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_vakapaatos_post, status.HTTP_201_CREATED)

        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        vakasuhde = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos_tunniste,
            'alkamis_pvm': '2021-02-01',
            'toimipaikka_oid': toimipaikka_oid,
            'lahdejarjestelma': '1',
        }
        resp_vakasuhde_post = vaka_vakajarjestaja_client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp_vakasuhde_post, status.HTTP_201_CREATED)

        self._assert_permissions_to_henkilo(henkilo_id, (vaka_vakajarjestaja_client, vaka_vakajarjestaja_client_2,
                                                         vaka_toimipaikka_client,), (henkilosto_vakajarjestaja_client,
                                                                                     henkilosto_toimipaikka_client,))

    @responses.activate
    def test_henkilo_paos_lapsi_permissions(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.246.562.24.47509942636',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '280616A148T',
            'etunimet': 'Testi Tero',
            'kutsumanimi': 'Testi',
            'sukunimi': 'Testinen'
        }

        oma_client = SetUpTestClient('vakatietojen_tallentaja').client()
        paos_client = SetUpTestClient('tester5').client()
        toimipaikka_client = SetUpTestClient('tester8').client()

        resp_henkilo_post = oma_client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp_henkilo_post, status.HTTP_201_CREATED)
        henkilo_id = json.loads(resp_henkilo_post.content)['id']
        self._assert_permissions_to_henkilo(henkilo_id, (oma_client,), (paos_client, toimipaikka_client,))

        oma_oid = '1.2.246.562.10.34683023489'
        paos_oid = '1.2.246.562.10.93957375488'
        lapsi_tunniste = 'testing-lapsi'
        lapsi = {
            'henkilo': f'/api/v1/henkilot/{henkilo_id}/',
            'oma_organisaatio_oid': oma_oid,
            'paos_organisaatio_oid': paos_oid,
            'lahdejarjestelma': '1',
            'tunniste': lapsi_tunniste,
        }
        resp_lapsi_post = oma_client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi_post, status.HTTP_201_CREATED)
        self._assert_permissions_to_henkilo(henkilo_id, (oma_client, paos_client,), (toimipaikka_client,))

        vakapaatos_tunniste = 'testing-vakapaatos'
        vakapaatos = {
            'lapsi_tunniste': lapsi_tunniste,
            'jarjestamismuoto_koodi': 'jm02',
            'tuntimaara_viikossa': 45,
            'tilapainen_vaka_kytkin': False,
            'vuorohoito': False,
            'kokopaivainen_vaka_kytkin': True,
            'hakemus_pvm': '2021-01-01',
            'alkamis_pvm': '2021-01-05',
            'lahdejarjestelma': '1',
            'tunniste': vakapaatos_tunniste,
        }
        resp_vakapaatos_post = oma_client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_vakapaatos_post, status.HTTP_201_CREATED)

        toimipaikka_oid = '1.2.246.562.10.9395737548817'
        vakasuhde = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos_tunniste,
            'alkamis_pvm': '2021-02-01',
            'toimipaikka_oid': toimipaikka_oid,
            'lahdejarjestelma': '1',
        }
        resp_vakasuhde_post = oma_client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp_vakasuhde_post, status.HTTP_201_CREATED)

        self._assert_permissions_to_henkilo(henkilo_id, (oma_client, paos_client, toimipaikka_client,), [])

    @responses.activate
    def test_henkilo_tyontekija_permissions(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.246.562.24.47509942636',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '280616A148T',
            'etunimet': 'Testi Tero',
            'kutsumanimi': 'Testi',
            'sukunimi': 'Testinen'
        }

        henkilosto_vakajarjestaja_client = SetUpTestClient('tyontekija_tallentaja').client()
        henkilosto_vakajarjestaja_client_2 = SetUpTestClient('tyontekija_katselija').client()
        henkilosto_toimipaikka_client = SetUpTestClient('tyontekija_toimipaikka_tallentaja_9395737548815').client()
        taydennyskoulutus_client = SetUpTestClient('taydennyskoulutus_tallentaja').client()
        tilapainen_client = SetUpTestClient('tilapaiset_tallentaja').client()
        vaka_vakajarjestaja_client = SetUpTestClient('vakatietojen_tallentaja').client()
        vaka_toimipaikka_client = SetUpTestClient('vakatietojen_toimipaikka_tallentaja_9395737548815').client()

        resp_henkilo_post = henkilosto_vakajarjestaja_client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp_henkilo_post, status.HTTP_201_CREATED)
        henkilo_id = json.loads(resp_henkilo_post.content)['id']
        self._assert_permissions_to_henkilo(henkilo_id, (henkilosto_vakajarjestaja_client,),
                                            (henkilosto_vakajarjestaja_client_2, henkilosto_toimipaikka_client,
                                             vaka_vakajarjestaja_client, vaka_toimipaikka_client,))

        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        tyontekija_tunniste = 'testing-tyontekija'
        tyontekija = {
            'henkilo': f'/api/v1/henkilot/{henkilo_id}/',
            'vakajarjestaja_oid': vakajarjestaja_oid,
            'lahdejarjestelma': '1',
            'tunniste': tyontekija_tunniste,
        }
        resp_tyontekija_post = henkilosto_vakajarjestaja_client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_tyontekija_post, status.HTTP_201_CREATED)
        self._assert_permissions_to_henkilo(henkilo_id, (henkilosto_vakajarjestaja_client,
                                                         henkilosto_vakajarjestaja_client_2,),
                                            (henkilosto_toimipaikka_client, vaka_vakajarjestaja_client,
                                             vaka_toimipaikka_client))

        tutkinto_koodi = '001'
        tutkinto = {
            'henkilo': f'/api/v1/henkilot/{henkilo_id}/',
            'vakajarjestaja_oid': vakajarjestaja_oid,
            'tutkinto_koodi': tutkinto_koodi
        }
        resp_tutkinto_post = henkilosto_vakajarjestaja_client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp_tutkinto_post, status.HTTP_201_CREATED)

        palvelussuhde_tunniste = 'testing-palvelussuhde'
        palvelussuhde = {
            'tyontekija_tunniste': tyontekija_tunniste,
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': tutkinto_koodi,
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2021-02-01',
            'lahdejarjestelma': '1',
            'tunniste': palvelussuhde_tunniste,
        }
        resp_palvelussuhde_post = henkilosto_vakajarjestaja_client.post('/api/henkilosto/v1/palvelussuhteet/',
                                                                        palvelussuhde)
        assert_status_code(resp_palvelussuhde_post, status.HTTP_201_CREATED)

        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        tyoskentelypaikka = {
            'palvelussuhde_tunniste': palvelussuhde_tunniste,
            'toimipaikka_oid': toimipaikka_oid,
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }
        resp_tyoskentelypaikka_post = henkilosto_vakajarjestaja_client.post('/api/henkilosto/v1/tyoskentelypaikat/',
                                                                            tyoskentelypaikka)
        assert_status_code(resp_tyoskentelypaikka_post, status.HTTP_201_CREATED)

        self._assert_permissions_to_henkilo(henkilo_id, (henkilosto_vakajarjestaja_client,
                                                         henkilosto_vakajarjestaja_client_2,
                                                         henkilosto_toimipaikka_client,),
                                            (vaka_vakajarjestaja_client, vaka_toimipaikka_client,))

        for client in (taydennyskoulutus_client, tilapainen_client,):
            resp = client.get(f'/api/v1/henkilot/{henkilo_id}/')
            assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def _assert_permissions_to_henkilo(self, henkilo_id, clients_with_permissions, clients_without_permissions):
        url = f'/api/v1/henkilot/{henkilo_id}/'

        for client in clients_with_permissions:
            resp = client.get(url)
            assert_status_code(resp, status.HTTP_200_OK)

        for client in clients_without_permissions:
            resp = client.get(url)
            assert_status_code(resp, status.HTTP_404_NOT_FOUND)

    rest_throttle_settings = settings.REST_FRAMEWORK.copy()
    rest_throttle_settings['DEFAULT_THROTTLE_RATES']['auth'] = '5/hour'
    rest_throttle_settings['DEFAULT_THROTTLE_RATES']['auth_token'] = '7/hour'

    @override_settings(CACHES=TEST_CACHE_SETTINGS)
    @override_settings(REST_FRAMEWORK=rest_throttle_settings)
    @responses.activate
    def test_auth_throttle_basic(self):
        cache.clear()
        limit = 5
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/kayttooikeus-service/henkilo/current/omattiedot/',
                      status=status.HTTP_401_UNAUTHORIZED)
        client = APIClient()

        for i in range(limit):
            resp = client.get('/api/user/apikey/', **{'HTTP_AUTHORIZATION': 'Basic dGVzdDp0ZXN0'})
            assert_status_code(resp, status.HTTP_403_FORBIDDEN)
            assert_validation_error(resp, 'errors', 'PE007', 'User authentication failed.')

        resp = client.get('/api/user/apikey/', **{'HTTP_AUTHORIZATION': 'Basic dGVzdDp0ZXN0'})
        assert_status_code(resp, status.HTTP_429_TOO_MANY_REQUESTS)
        assert_validation_error(resp, 'errors', 'DY008')
        self._assert_throttle_seconds_close(resp)

        # Perform successful authentication
        responses.reset()
        organisaatiot = [
            {
                'organisaatioOid': '1.2.246.562.10.93957375488',
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                    },
                ]
            }
        ]
        mock_cas_palvelukayttaja_responses(organisaatiot, 'tester')

        base64_string = base64_encoding('tester:password')
        resp = client.get('/api/user/apikey/', **{'HTTP_AUTHORIZATION': f'Basic {base64_string}'})
        assert_status_code(resp, status.HTTP_429_TOO_MANY_REQUESTS)
        assert_validation_error(resp, 'errors', 'DY008')
        self._assert_throttle_seconds_close(resp)

        with patch('rest_framework.throttling.SimpleRateThrottle.timer') as mock_time:
            # SimpleRateThrottle.timer() returns one hour later
            mock_time.return_value = time.time() + (60 * 60)
            for i in range(limit + 5):
                # Successful authentications don't affect throttling
                resp = client.get('/api/user/apikey/', **{'HTTP_AUTHORIZATION': f'Basic {base64_string}'})
                assert_status_code(resp, status.HTTP_200_OK)

    @override_settings(CACHES=TEST_CACHE_SETTINGS)
    @override_settings(REST_FRAMEWORK=rest_throttle_settings)
    def test_auth_throttle_token(self):
        cache.clear()
        limit = 7

        token_client = SetUpTestClient('tester').client()
        token = json.loads(token_client.get('/api/user/apikey/').content)['token']

        client = APIClient()

        for i in range(limit):
            resp = client.get('/api/v1/vakajarjestajat/', **{'HTTP_AUTHORIZATION': 'Token dGVzdDp0ZXN0'})
            assert_status_code(resp, status.HTTP_403_FORBIDDEN)
            assert_validation_error(resp, 'errors', 'PE007', 'User authentication failed.')

        resp = client.get('/api/v1/vakajarjestajat/', **{'HTTP_AUTHORIZATION': 'Token dGVzdDp0ZXN0'})
        assert_status_code(resp, status.HTTP_429_TOO_MANY_REQUESTS)
        assert_validation_error(resp, 'errors', 'DY008')
        self._assert_throttle_seconds_close(resp)

        # Perform successful authentication
        resp = client.get('/api/v1/vakajarjestajat/', **{'HTTP_AUTHORIZATION': f'Token {token}'})
        assert_status_code(resp, status.HTTP_429_TOO_MANY_REQUESTS)
        assert_validation_error(resp, 'errors', 'DY008')
        self._assert_throttle_seconds_close(resp)

        with patch('rest_framework.throttling.SimpleRateThrottle.timer') as mock_time:
            # SimpleRateThrottle.timer() returns one hour later
            mock_time.return_value = time.time() + (60 * 60)
            for i in range(limit + 5):
                # Successful authentications don't affect throttling
                resp = client.get('/api/v1/vakajarjestajat/', **{'HTTP_AUTHORIZATION': f'Token {token}'})
                assert_status_code(resp, status.HTTP_200_OK)

    @override_settings(CACHES=TEST_CACHE_SETTINGS)
    @override_settings(REST_FRAMEWORK=rest_throttle_settings)
    def test_auth_throttle_session(self):
        cache.clear()
        limit = 5

        session_client = APIClient()
        session_client.force_login(User.objects.get(username='tester'))
        session_key = session_client.session.session_key

        client = APIClient()
        client.cookies[settings.SESSION_COOKIE_NAME] = 'invalid_session_key'

        for i in range(limit):
            resp = client.get('/api/v1/toimipaikat/')
            assert_status_code(resp, status.HTTP_403_FORBIDDEN)
            # Invalid session_key raises NotAuthenticated instead of AuthenticationFailed
            assert_validation_error(resp, 'errors', 'PE007', 'User authentication failed.')

        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, status.HTTP_429_TOO_MANY_REQUESTS)
        assert_validation_error(resp, 'errors', 'DY008')
        self._assert_throttle_seconds_close(resp)

        # Perform successful authentication
        client.cookies[settings.SESSION_COOKIE_NAME] = session_key

        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, status.HTTP_429_TOO_MANY_REQUESTS)
        assert_validation_error(resp, 'errors', 'DY008')
        self._assert_throttle_seconds_close(resp)

        with patch('rest_framework.throttling.SimpleRateThrottle.timer') as mock_time:
            # SimpleRateThrottle.timer() returns one hour later
            mock_time.return_value = time.time() + (60 * 60)
            for i in range(limit + 5):
                # Successful authentications don't affect throttling
                resp = client.get('/api/v1/toimipaikat/')
                assert_status_code(resp, status.HTTP_200_OK)

    def _assert_throttle_seconds_close(self, resp, compare_to=60 * 60, error_margin=10):
        throttle_regex = re.compile(r'again in ([\d]+) second')
        error_description = json.loads(resp.content)['errors'][0]['description']
        seconds = int(throttle_regex.search(error_description).group(1))
        self.assertTrue(isclose(seconds, compare_to, abs_tol=error_margin))
