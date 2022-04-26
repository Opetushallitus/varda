import json

from django.contrib.auth.models import Group
from django.db.models import Q
from django.test import TestCase
from guardian.shortcuts import assign_perm
from rest_framework import status

from varda.misc import hash_string
from varda.models import Organisaatio, Tyontekija, Henkilo, Lapsi, Toimipaikka, Palvelussuhde
from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient, post_henkilo_to_get_permissions


class VardaHenkilostoViewSetTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_tyontekija_list_vakajarjestaja_tyontekija_user(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        expected_henkilo_count = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).count()
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertGreater(resp_content['count'], 0)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

    def test_tyontekija_list_vakajarjestaja_taydennyskoulutus_user(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        expected_henkilo_count = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).count()
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertGreater(resp_content['count'], 0)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

    def test_tyontekija_list_toimipaikka_tyontekija_user(self):
        client = SetUpTestClient('tyontekija_toimipaikka_tallentaja_9395737548815').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        expected_henkilo_count = Tyontekija.objects.filter(palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid=toimipaikka_oid).distinct().count()
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertGreater(resp_content['count'], 0)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

        # Check direct permission also (tyontekija without tyoskentelypaikka)
        group_tyontekija_tallentaja_9395737548815 = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.9395737548815')
        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')
        # assing permission to tyontekija without tyoskentelypaikka
        assign_perm('view_tyontekija', group_tyontekija_tallentaja_9395737548815, tyontekija)
        resp_after_extra_permission = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        resp_content_after_extra_permission = json.loads(resp_after_extra_permission.content)
        self.assertGreater(resp_content_after_extra_permission['count'], 0)
        self.assertEqual(resp_content_after_extra_permission['count'], expected_henkilo_count + 1)

    def test_tyontekija_list_filters(self):
        client = SetUpTestClient('credadmin').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        toimipaikka_id = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid).id
        result_qs = Henkilo.objects.filter(tyontekijat__vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).distinct()
        query_result_list = [
            ('', result_qs),
            ('toimipaikka_oid={}'.format(toimipaikka_oid),
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid=toimipaikka_oid)
             ),
            ('toimipaikka_id={}'.format(toimipaikka_id),
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__id=toimipaikka_id)
             ),
            ('kiertava_tyontekija_kytkin=false',
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=False)
             ),
            ('kiertava_tyontekija_kytkin=true',
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=True)
             ),
            ('search=daniella',
             result_qs.filter(etunimet__contains='Daniella')
             ),
            ('search={}'.format(hash_string('020400A928E')),
             result_qs.filter(henkilotunnus_unique_hash__iexact=hash_string('020400A928E'))
             ),
            ('search=1.2.246.562.24.2431884920044',
             result_qs.filter(henkilo_oid__iexact='1.2.246.562.24.2431884920044')
             ),
            ('voimassa_pvm=2020-03-01',
             result_qs.filter(Q(tyontekijat__palvelussuhteet__alkamis_pvm__lte='2020-03-01') &
                              (Q(tyontekijat__palvelussuhteet__paattymis_pvm__gte='2020-03-01') |
                               Q(tyontekijat__palvelussuhteet__paattymis_pvm__isnull=True)))
             ),
        ]
        for query, exptected_value in query_result_list:
            resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/?{}'.format(vakajarjestaja_id, query))
            assert_status_code(resp, status.HTTP_200_OK)
            resp_content = json.loads(resp.content)
            self.assertGreater(resp_content['count'], 0, query)
            self.assertEqual(resp_content['count'], exptected_value.count(), query)

        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/?page_size=2'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertEqual(len(resp_content['results']), 2)

    def test_lapsi_list_vakajarjestaja_huoltajatieto_user(self):
        client = SetUpTestClient('huoltajatietojen_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        vakajarjestaja_condition = Q(lapsi__vakatoimija__organisaatio_oid=vakajarjestaja_oid) | Q(lapsi__oma_organisaatio__organisaatio_oid=vakajarjestaja_oid) | Q(lapsi__paos_organisaatio__organisaatio_oid=vakajarjestaja_oid)
        expected_henkilo_count = Henkilo.objects.filter(vakajarjestaja_condition).distinct().count()
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/lapsi-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertGreater(resp_content['count'], 0)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

    def test_lapsi_list_vakajarjestaja_vakatieto_user(self):
        client = SetUpTestClient('vakatietojen_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        vakajarjestaja_condition = Q(lapsi__vakatoimija__organisaatio_oid=vakajarjestaja_oid) | Q(lapsi__oma_organisaatio__organisaatio_oid=vakajarjestaja_oid) | Q(lapsi__paos_organisaatio__organisaatio_oid=vakajarjestaja_oid)
        expected_henkilo_count = Henkilo.objects.filter(vakajarjestaja_condition).distinct().count()
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/lapsi-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertGreater(resp_content['count'], 0)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

    def test_lapsi_list_toimipaikka_tyontekija_user(self):
        client = SetUpTestClient('vakatietojen_toimipaikka_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        toimipaikka_oid = '1.2.246.562.10.9395737548810'
        expected_henkilo_count = Lapsi.objects.filter(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid=toimipaikka_oid).distinct().count()
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/lapsi-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertGreater(resp_content['count'], 0)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

        # Check lapsi with direct permission ("irtolapset") are NOT shown
        user = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.9395737548810')
        lapsi = Lapsi.objects.filter(vakatoimija__isnull=True).order_by('-id').first()
        assign_perm('view_lapsi', user, lapsi)  # assing permission to tyontekija without tyoskentelypaikka
        resp_after_extra_permission = client.get('/api/ui/vakajarjestajat/{}/lapsi-list/'.format(vakajarjestaja_id))
        resp_content_after_extra_permission = json.loads(resp_after_extra_permission.content)
        self.assertGreater(resp_content_after_extra_permission['count'], 0)
        self.assertEqual(resp_content_after_extra_permission['count'], expected_henkilo_count)

    def test_lapsi_list_filters(self):
        client = SetUpTestClient('credadmin').client()
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        vakajarjestaja_id = Organisaatio.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        toimipaikka_oid = '1.2.246.562.10.9395737548810'
        toimipaikka_id = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid).id
        vakajarjestaja_condition = Q(lapsi__vakatoimija__organisaatio_oid=vakajarjestaja_oid) | Q(lapsi__oma_organisaatio__organisaatio_oid=vakajarjestaja_oid) | Q(lapsi__paos_organisaatio__organisaatio_oid=vakajarjestaja_oid)
        result_qs = Henkilo.objects.filter(vakajarjestaja_condition).distinct()
        query_result_list = [
            ('', result_qs),
            ('toimipaikka_oid={}'.format(toimipaikka_oid),
             result_qs.filter(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid=toimipaikka_oid)
             ),
            ('toimipaikka_id={}'.format(toimipaikka_id),
             result_qs.filter(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__id=toimipaikka_id)
             ),
            ('search=aamu',
             result_qs.filter(etunimet__contains='Aamu')
             ),
            ('search={}'.format(hash_string('120699-985W')),
             result_qs.filter(henkilotunnus_unique_hash__iexact=hash_string('120699-985W'))
             ),
            ('search=1.2.246.562.24.6815981182311',
             result_qs.filter(henkilo_oid__iexact='1.2.246.562.24.6815981182311')
             ),
            ('voimassa_pvm=2020-01-01',
             result_qs.filter(Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte='2020-01-01') &
                              (Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte='2020-01-01') |
                               Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True)))
             ),
        ]
        for query, exptected_value in query_result_list:
            resp = client.get('/api/ui/vakajarjestajat/{}/lapsi-list/?{}'.format(vakajarjestaja_id, query))
            assert_status_code(resp, status.HTTP_200_OK)
            resp_content = json.loads(resp.content)
            self.assertGreater(resp_content['count'], 0, query)
            self.assertEqual(resp_content['count'], exptected_value.count(), query)

        resp = client.get('/api/ui/vakajarjestajat/{}/lapsi-list/?page_size=2'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertEqual(len(resp_content['results']), 2)

    def test_api_ui_vakajarjestajat(self):
        self.maxDiff = None
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/ui/vakajarjestajat/')
        assert_status_code(resp, 200)

        admin_vakajarjestajat = [
            {
                'nimi': 'Frontti organisaatio',
                'id': 4,
                'url': 'http://testserver/api/v1/vakajarjestajat/4/',
                'organisaatio_oid': '1.2.246.562.10.93957375484',
                'kunnallinen_kytkin': True,
                'y_tunnus': '2156233-6',
                'alkamis_pvm': '2018-09-25',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'Tester organisaatio',
                'id': 2,
                'url': 'http://testserver/api/v1/vakajarjestajat/2/',
                'organisaatio_oid': '1.2.246.562.10.93957375488',
                'kunnallinen_kytkin': False,
                'y_tunnus': '1825748-8',
                'alkamis_pvm': '2017-02-03',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'Tester2 organisaatio',
                'id': 1,
                'url': 'http://testserver/api/v1/vakajarjestajat/1/',
                'organisaatio_oid': '1.2.246.562.10.34683023489',
                'kunnallinen_kytkin': True,
                'y_tunnus': '8500570-7',
                'alkamis_pvm': '2017-02-03',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'varda-testi organisaatio',
                'id': 3,
                'url': 'http://testserver/api/v1/vakajarjestajat/3/',
                'organisaatio_oid': '1.2.246.562.10.93957375486',
                'kunnallinen_kytkin': False,
                'y_tunnus': '2617455-1',
                'alkamis_pvm': '2018-09-13',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'Tester 10 organisaatio',
                'id': 5,
                'url': 'http://testserver/api/v1/vakajarjestajat/5/',
                'organisaatio_oid': '1.2.246.562.10.57294396385',
                'kunnallinen_kytkin': True,
                'y_tunnus': '8685083-0',
                'alkamis_pvm': '2019-01-01',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'Tester 11 organisaatio',
                'id': 6,
                'url': 'http://testserver/api/v1/vakajarjestajat/6/',
                'organisaatio_oid': '1.2.246.562.10.52966755795',
                'kunnallinen_kytkin': True,
                'y_tunnus': '1428881-8',
                'alkamis_pvm': '2019-02-01',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'Kansaneläkelaitos',
                'id': 7,
                'url': 'http://testserver/api/v1/vakajarjestajat/7/',
                'organisaatio_oid': '1.2.246.562.10.2013121014482686198719',
                'kunnallinen_kytkin': False,
                'y_tunnus': '0246246-0',
                'alkamis_pvm': '1979-01-02',
                'paattymis_pvm': None,
                'active': True
            },
            {
                'nimi': 'Opetushallitus',
                'id': 8,
                'url': 'http://testserver/api/v1/vakajarjestajat/8/',
                'organisaatio_oid': '1.2.246.562.10.00000000001',
                'kunnallinen_kytkin': False,
                'y_tunnus': '',
                'alkamis_pvm': '1970-01-01',
                'paattymis_pvm': None,
                'active': True
            }
        ]
        self.assertCountEqual(json.loads(resp.content), admin_vakajarjestajat)

    def test_api_get_toimipaikan_lapset_json(self):
        toimipaikan_lapset_json = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [
                {
                    'etunimet': 'Arpa Noppa',
                    'sukunimi': 'Kuutio',
                    'henkilo_oid': '1.2.246.562.24.6815981182311',
                    'syntyma_pvm': '1948-05-11',
                    'oma_organisaatio_nimi': 'Tester2 organisaatio',
                    'paos_organisaatio_nimi': 'Tester organisaatio',
                    'lapsi_id': 4,
                    'lapsi_url': 'http://testserver/api/v1/lapset/4/?format=json'
                },
                {
                    'etunimet': 'Teila Aamu Runelma',
                    'sukunimi': 'Testilä',
                    'henkilo_oid': '1.2.246.562.24.86012997950',
                    'syntyma_pvm': '2018-03-11',
                    'oma_organisaatio_nimi': 'Tester2 organisaatio',
                    'paos_organisaatio_nimi': 'Tester organisaatio',
                    'lapsi_id': 8,
                    'lapsi_url': 'http://testserver/api/v1/lapset/8/?format=json'
                }
            ]
        }
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/ui/vakajarjestajat/1/lapset/?toimipaikat=5&format=json')
        self.assertEqual(json.loads(resp.content), toimipaikan_lapset_json)

    def test_api_toimipaikan_lapset_henkilo_nimi_filter(self):
        toimipaikan_lapset_henkilo_filter_json = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'etunimet': 'Susanna',
                    'sukunimi': 'Virtanen',
                    'henkilo_oid': '1.2.246.562.24.58672764848',
                    'syntyma_pvm': '2016-05-12',
                    'lapsi_id': 2,
                    'lapsi_url': 'http://testserver/api/v1/lapset/2/?format=json'
                }
            ]
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/ui/vakajarjestajat/2/lapset/?toimipaikat=1&search=sUSa+TA&format=json')
        self.assertEqual(json.loads(resp.content), toimipaikan_lapset_henkilo_filter_json)

    def test_toimipaikan_lapset_huoltajatieto_tallentaja(self):
        client = SetUpTestClient('huoltajatietojen_tallentaja').client()
        accepted_response_json = {
            'count': 3,
            'next': None,
            'previous': None,
            'results': [
                {
                    'etunimet': 'Teila Aamu Runelma',
                    'sukunimi': 'Testilä',
                    'henkilo_oid': '1.2.246.562.24.86012997950',
                    'syntyma_pvm': '2018-03-11',
                    'lapsi_id': 6,
                    'lapsi_url': 'http://testserver/api/v1/lapset/6/?format=json'
                },
                {
                    'etunimet': 'Anni',
                    'henkilo_oid': '1.2.246.562.24.2395579779541',
                    'lapsi_id': 16,
                    'lapsi_url': 'http://testserver/api/v1/lapset/16/?format=json',
                    'sukunimi': 'Testinen',
                    'syntyma_pvm': '2020-10-27'
                },
                {
                    'etunimet': 'Tuula-Testi',
                    'sukunimi': 'Vanhanen',
                    'henkilo_oid': '1.2.246.562.24.49084901392',
                    'syntyma_pvm': '1934-03-17',
                    'lapsi_id': 3,
                    'lapsi_url': 'http://testserver/api/v1/lapset/3/?format=json'
                }
            ]
        }
        resp = client.get('/api/ui/vakajarjestajat/1/lapset/?toimipaikat=2&format=json')
        self.assertEqual(json.loads(resp.content), accepted_response_json)

    def test_api_lapset_paos_toimipaikka_filter(self):
        # Tested lapsi (henkilo 16 010215A951T) is paos-lapsi between vakajarjestaja 1.2.246.562.10.34683023489 and
        # 1.2.246.562.10.93957375488 as well as own one in both vakajarjestajat.
        client = SetUpTestClient('tester5').client()  # VARDA-TALLENTAJA_1.2.246.562.10.93957375488
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        vakajarjestaja_id = Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid).id
        toimipaikka_oid = '1.2.246.562.10.9395737548817'
        toimipaikka_id = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid).id
        resp_ui_list_lapset = client.get(f'/api/ui/vakajarjestajat/{vakajarjestaja_id}/lapsi-list/?toimipaikka_id={toimipaikka_id}')
        assert_status_code(resp_ui_list_lapset, status.HTTP_200_OK)
        expected_henkilo_oid = '1.2.246.562.24.86012997950'
        henkilo_result = next(henkilo for henkilo in resp_ui_list_lapset.data['results'] if henkilo['henkilo_oid'] == expected_henkilo_oid)
        lapset_results = henkilo_result['lapset']
        self.assertEqual(len(lapset_results), 1)
        lapset_result = lapset_results[0]
        expected_results = {
            'vakatoimija_oid': None,
            'oma_organisaatio_oid': '1.2.246.562.10.34683023489',
            'paos_organisaatio_oid': '1.2.246.562.10.93957375488',
        }
        self.assertTrue(expected_results.items() <= lapset_result.items())
        self.assertEqual(len(lapset_result['toimipaikat']), 1)
        expected_toimipaikka_results = {
            'organisaatio_oid': toimipaikka_oid,
        }
        toimipaikka_result = lapset_result['toimipaikat'][0]
        self.assertTrue(expected_toimipaikka_results.items() <= toimipaikka_result.items())

    def test_api_lapset_paos_permissions(self):
        # PAOS-organisaatio should not see non-PAOS Lapsi objects in selected Toimipaikka
        paos_client = SetUpTestClient('tester2').client()
        toimipaikka_client = SetUpTestClient('tester8').client()

        henkilo_oid = '1.2.246.562.24.49084901392'
        toimipaikka_oid = '1.2.246.562.10.9395737548817'
        toimipaikka_id = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid).id
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        paos_vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        paos_vakajarjestaja_id = Organisaatio.objects.get(organisaatio_oid=paos_vakajarjestaja_oid)

        post_henkilo_to_get_permissions(toimipaikka_client, henkilo_oid=henkilo_oid)

        lapsi = {
            'toimipaikka_oid': toimipaikka_oid,
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid,
            'lahdejarjestelma': '1'
        }
        resp_lapsi = toimipaikka_client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi, status.HTTP_201_CREATED)
        lapsi_id = json.loads(resp_lapsi.content)['id']

        vakapaatos = {
            'toimipaikka_oid': toimipaikka_oid,
            'lapsi': f'/api/v1/lapset/{lapsi_id}/',
            'alkamis_pvm': '2020-12-01',
            'hakemus_pvm': '2020-12-01',
            'vuorohoito_kytkin': False,
            'tilapainen_vaka_kytkin': False,
            'pikakasittely_kytkin': False,
            'tuntimaara_viikossa': '32.0',
            'paivittainen_vaka_kytkin': True,
            'kokopaivainen_vaka_kytkin': True,
            'jarjestamismuoto_koodi': 'jm04',
            'lahdejarjestelma': '1'
        }
        resp_vakapaatos = toimipaikka_client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_vakapaatos, status.HTTP_201_CREATED)
        vakapaatos_id = json.loads(resp_vakapaatos.content)['id']

        vakasuhde = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/',
            'toimipaikka_oid': toimipaikka_oid,
            'alkamis_pvm': '2020-12-01',
            'lahdejarjestelma': '1'
        }
        resp_vakasuhde = toimipaikka_client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp_vakasuhde, status.HTTP_201_CREATED)

        resp_ui_lapset = paos_client.get(f'/api/ui/vakajarjestajat/{paos_vakajarjestaja_id}/lapset/?toimipaikat={toimipaikka_id}')
        assert_status_code(resp_ui_lapset, status.HTTP_200_OK)
        lapset_results = json.loads(resp_ui_lapset.content)['results']
        self.assertIsNone(next((lapsi for lapsi in lapset_results if lapsi['lapsi_id'] == lapsi_id), None))

    def test_ui_tyontekijat_json(self):
        tyontekijat_json = {
            'count': 3,
            'next': None,
            'previous': None,
            'results': [
                {
                    'etunimet': 'Aatu',
                    'sukunimi': 'Uraputki',
                    'henkilo_oid': '1.2.246.562.24.2431884920041',
                    'tyontekija_id': 1,
                    'tyontekija_url': 'http://testserver/api/henkilosto/v1/tyontekijat/1/?format=json',
                    'vakajarjestaja_nimi': 'Tester2 organisaatio'
                },
                {
                    "etunimet": "Bella",
                    "sukunimi": "Uraputki",
                    "henkilo_oid": "1.2.246.562.24.2431884920042",
                    "tyontekija_id": 2,
                    "tyontekija_url": "http://testserver/api/henkilosto/v1/tyontekijat/2/?format=json",
                    "vakajarjestaja_nimi": "Tester2 organisaatio"
                },
                {
                    'etunimet': 'Daniella',
                    'sukunimi': 'Uraputki',
                    'henkilo_oid': '1.2.246.562.24.2431884920044',
                    'tyontekija_id': 4,
                    'tyontekija_url': 'http://testserver/api/henkilosto/v1/tyontekijat/4/?format=json',
                    'vakajarjestaja_nimi': 'Tester2 organisaatio'
                }
            ]
        }
        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp = client.get('/api/ui/vakajarjestajat/1/tyontekijat/?toimipaikat=2&format=json')
        self.assertEqual(json.loads(resp.content), tyontekijat_json)

    def test_ui_tyontekijat_filter_nimi(self):
        toimipaikan_lapset_henkilo_filter_json = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'etunimet': 'Aatu',
                    'sukunimi': 'Uraputki',
                    'henkilo_oid': '1.2.246.562.24.2431884920041',
                    'tyontekija_id': 1,
                    'tyontekija_url': 'http://testserver/api/henkilosto/v1/tyontekijat/1/?format=json',
                    'vakajarjestaja_nimi': 'Tester2 organisaatio'
                }
            ]
        }
        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp = client.get('/api/ui/vakajarjestajat/1/tyontekijat/?toimipaikat=2&search=aAt+putki&format=json')
        self.assertEqual(json.loads(resp.content), toimipaikan_lapset_henkilo_filter_json)

    def test_ui_tyontekija_filter_tehtavanimike(self):
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka_1 = Toimipaikka.objects.filter(nimi__iexact='Paivakoti kukkanen').first()
        toimipaikka_2 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548815')

        tyoskentelypaikka_1 = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka_1.id),
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-09-02',
            'tehtavanimike_koodi': '64212',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        tyoskentelypaikka_2 = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka_2.id),
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-09-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp_tyoskentelypaikka_1 = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka_1)
        assert_status_code(resp_tyoskentelypaikka_1, status.HTTP_201_CREATED)
        resp_tyoskentelypaikka_2 = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka_2)
        assert_status_code(resp_tyoskentelypaikka_2, status.HTTP_201_CREATED)

        resp_ui_1 = client.get(f'/api/ui/vakajarjestajat/1/tyontekijat/?toimipaikat={toimipaikka_1.id}&tehtavanimike=64212')
        self.assertEqual(json.loads(resp_ui_1.content)['count'], 1)

        # Tyontekija has tehtavanimike 39407 in other toimipaikka, so it should now show up in results
        resp_ui_2 = client.get(f'/api/ui/vakajarjestajat/1/tyontekijat/?toimipaikat={toimipaikka_1.id}&tehtavanimike=39407')
        self.assertEqual(json.loads(resp_ui_2.content)['count'], 0)

        resp_ui_2 = client.get(f'/api/ui/vakajarjestajat/1/tyontekijat/?tehtavanimike=39407&search={palvelussuhde.tyontekija.henkilo.etunimet}')
        self.assertEqual(json.loads(resp_ui_2.content)['count'], 1)

    def test_ui_tyontekija_filter_kiertava(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        kiertavat_count = Tyontekija.objects.filter(palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=True).count()

        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp = client.get(f'/api/ui/vakajarjestajat/{vakajarjestaja.id}/tyontekijat/?kiertava=true')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_json = json.loads(resp.content)
        self.assertEqual(resp_json['count'], kiertavat_count)
