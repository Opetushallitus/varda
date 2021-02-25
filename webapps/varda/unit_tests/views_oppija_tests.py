import json

from django.test import TestCase
from rest_framework import status

from varda.models import Z3_AdditionalCasUserFields, Z5_AuditLog, Henkilo, VakaJarjestaja
from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient, assert_validation_error
from django.contrib.auth.models import User
from varda.custom_auth import _oppija_post_login_handler


class VardaOppijaViewsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_api_varhaiskasvatustiedot_get_data(self):
        # Mock Huoltaja login
        user_suomifi = User.objects.create(username='suomi.fi#010280-952L#010215A951T', is_staff=False, is_active=True)
        user_suomifi.personOid = '1.2.246.562.24.86012997950'
        user_suomifi.impersonatorPersonOid = '1.2.246.562.24.1234567890'
        _oppija_post_login_handler(user_suomifi)

        client_suomifi_tester = SetUpTestClient('suomi.fi#010280-952L#010215A951T').client()

        henkilotiedot_response = {
            'henkilo_oid': '1.2.246.562.24.86012997950',
            'henkilotunnus': '010215A951T',
            'etunimet': 'Teila Aamu Runelma',
            'kutsumanimi': 'Teila',
            'sukunimi': 'Testilä',
            'aidinkieli_koodi': 'FI',
            'sukupuoli_koodi': '1',
            'syntyma_pvm': '2018-03-11',
            'kotikunta_koodi': '915',
            'katuosoite': 'Koivukuja 4',
            'postinumero': '01230',
            'postitoimipaikka': 'Vantaa'
        }

        resp_henkilotiedot = client_suomifi_tester.get('/api/oppija/v1/henkilotiedot/1.2.246.562.24.86012997950/',
                                                       content_type='application/json')
        resp_henkilotiedot_json = json.loads(resp_henkilotiedot.content)
        del resp_henkilotiedot_json['id']
        self.assertEqual(resp_henkilotiedot_json, henkilotiedot_response)

        varhaiskasvatustiedot_response = {
            'voimassaolevia_varhaiskasvatuspaatoksia': 1,
            'lapset': [
                {
                    'yhteysosoite': 'frontti@end.com',
                    'varhaiskasvatuksen_jarjestaja': 'Frontti organisaatio',
                    'aktiivinen_toimija': True,
                    'varhaiskasvatuspaatokset': [
                        {
                            'alkamis_pvm': '2019-11-11',
                            'hakemus_pvm': '2019-01-01',
                            'paattymis_pvm': '2019-12-22',
                            'paivittainen_vaka_kytkin': True,
                            'kokopaivainen_vaka_kytkin': False,
                            'tilapainen_vaka_kytkin': False,
                            'jarjestamismuoto_koodi': 'jm04',
                            'vuorohoito_kytkin': False,
                            'pikakasittely_kytkin': True,
                            'tuntimaara_viikossa': '30.5',
                            'varhaiskasvatussuhteet': []
                        }
                    ]
                },
                {
                    'yhteysosoite': 'organization@domain.com',
                    'varhaiskasvatuksen_jarjestaja': 'Tester organisaatio',
                    'aktiivinen_toimija': True,
                    'varhaiskasvatuspaatokset': [
                        {
                            'alkamis_pvm': '2019-11-11',
                            'hakemus_pvm': '2019-11-01',
                            'paattymis_pvm': '2019-12-22',
                            'paivittainen_vaka_kytkin': True,
                            'kokopaivainen_vaka_kytkin': False,
                            'tilapainen_vaka_kytkin': False,
                            'jarjestamismuoto_koodi': 'jm03',
                            'vuorohoito_kytkin': False,
                            'pikakasittely_kytkin': True,
                            'tuntimaara_viikossa': '30.5',
                            'varhaiskasvatussuhteet': [
                                {
                                    'alkamis_pvm': '2018-05-01',
                                    'paattymis_pvm': '2019-10-24',
                                    'toimipaikka': {
                                        'toimipaikka_nimi': 'Espoo',
                                        'toimipaikka_kunta_koodi': '091'
                                    },
                                    'yhteysosoite': 'test1@espoo.fi'
                                },
                                {
                                    'alkamis_pvm': '2018-09-05',
                                    'paattymis_pvm': '2019-04-20',
                                    'toimipaikka': {
                                        'toimipaikka_nimi': 'Espoo_2',
                                        'toimipaikka_kunta_koodi': '091'
                                    },
                                    'yhteysosoite': 'organization@domain.com'
                                },
                            ]
                        }
                    ]
                },
                {
                    'yhteysosoite': 'organization@domain.com',
                    'varhaiskasvatuksen_jarjestaja': 'Tester2 organisaatio',
                    'aktiivinen_toimija': True,
                    'varhaiskasvatuspaatokset': [
                        {
                            'alkamis_pvm': '2018-10-05',
                            'hakemus_pvm': '2018-10-05',
                            'paattymis_pvm': None,
                            'paivittainen_vaka_kytkin': True,
                            'kokopaivainen_vaka_kytkin': True,
                            'tilapainen_vaka_kytkin': False,
                            'jarjestamismuoto_koodi': 'jm03',
                            'vuorohoito_kytkin': False,
                            'pikakasittely_kytkin': False,
                            'tuntimaara_viikossa': '39.0',
                            'varhaiskasvatussuhteet': [
                                {
                                    'alkamis_pvm': '2019-11-11',
                                    'paattymis_pvm': None,
                                    'toimipaikka': {
                                        'toimipaikka_nimi': 'Espoo_3',
                                        'toimipaikka_kunta_koodi': '091'
                                    },
                                    'yhteysosoite': 'organization@domain.com'
                                }
                            ]
                        }
                    ]
                },
                {
                    'yhteysosoite': 'organization@domain.com',
                    'varhaiskasvatuksen_jarjestaja': 'Tester2 organisaatio',
                    'aktiivinen_toimija': True,
                    'varhaiskasvatuspaatokset': [
                        {
                            'alkamis_pvm': '2019-02-11',
                            'hakemus_pvm': '2019-01-01',
                            'paattymis_pvm': '2019-10-24',
                            'paivittainen_vaka_kytkin': None,
                            'kokopaivainen_vaka_kytkin': None,
                            'tilapainen_vaka_kytkin': False,
                            'jarjestamismuoto_koodi': 'jm03',
                            'vuorohoito_kytkin': True,
                            'pikakasittely_kytkin': True,
                            'tuntimaara_viikossa': '37.5',
                            'varhaiskasvatussuhteet': [
                                {
                                    'alkamis_pvm': '2018-02-11',
                                    'paattymis_pvm': '2019-02-24',
                                    'toimipaikka': {
                                        'toimipaikka_nimi': 'Tester2 toimipaikka',
                                        'toimipaikka_kunta_koodi': '091'
                                    },
                                    'yhteysosoite': 'test2@domain.com'
                                }
                            ]
                        }
                    ]
                },
            ]
        }
        resp_varhaiskasvatustiedot = client_suomifi_tester.get('/api/oppija/v1/varhaiskasvatustiedot/1.2.246.562.24.86012997950/',
                                                               content_type='application/json')
        resp_varhaiskasvatustiedot_json = json.loads(resp_varhaiskasvatustiedot.content)
        # Remove ID:s because they tend to change and sort for expected behaviour
        resp_varhaiskasvatustiedot_json['lapset'] = sorted(resp_varhaiskasvatustiedot_json['lapset'], key=lambda key: (key['varhaiskasvatuksen_jarjestaja'], key['varhaiskasvatuspaatokset'][0]['alkamis_pvm']))
        for lapsi in resp_varhaiskasvatustiedot_json['lapset']:
            del lapsi['id']
            lapsi['varhaiskasvatuspaatokset'] = sorted(lapsi['varhaiskasvatuspaatokset'], key=lambda key: key['alkamis_pvm'])
            for vakapaatos in lapsi['varhaiskasvatuspaatokset']:
                del vakapaatos['id']
                vakapaatos['varhaiskasvatussuhteet'] = sorted(vakapaatos['varhaiskasvatussuhteet'], key=lambda key: key['alkamis_pvm'])
                for vakasuhde in vakapaatos['varhaiskasvatussuhteet']:
                    del vakasuhde['id']

        assert_status_code(resp_varhaiskasvatustiedot, status.HTTP_200_OK)
        self.assertEqual(resp_varhaiskasvatustiedot_json, varhaiskasvatustiedot_response)

        request_count = Z5_AuditLog.objects.filter(user__username='suomi.fi#010280-952L#010215A951T').count()
        self.assertEqual(request_count, 2)

    def test_get_varhaiskasvatustiedot_data_no_permission(self):
        client = SetUpTestClient('tester2').client()
        resp_varhaiskasvatustiedot_api = client.get('/api/oppija/v1/varhaiskasvatustiedot/1.2.246.562.24.86012997950/',
                                                    content_type='application/json')
        assert_status_code(resp_varhaiskasvatustiedot_api, status.HTTP_403_FORBIDDEN)

    def test_api_varhaiskasvatustiedot_cant_access_wrong_lapsi(self):
        lapsi_oid = '1.2.246.562.24.86012997950'
        other_lapsi_oid = '1.2.246.562.24.47279942650'
        huoltaja_oid = ''
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        resp_varhaiskasvatustiedot_api = client_suomifi_tester.get('/api/oppija/v1/varhaiskasvatustiedot/{}/'.format(other_lapsi_oid),
                                                                   content_type='application/json')
        assert_status_code(resp_varhaiskasvatustiedot_api, status.HTTP_403_FORBIDDEN)

    def test_api_varhaiskasvatustiedot_no_oid(self):
        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = ''
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        resp_varhaiskasvatustiedot_api = client_suomifi_tester.get('/api/oppija/v1/varhaiskasvatustiedot/{}/'.format(lapsi_oid),
                                                                   content_type='application/json')
        assert_status_code(resp_varhaiskasvatustiedot_api, status.HTTP_200_OK)

        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = None
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        resp_varhaiskasvatustiedot_api = client_suomifi_tester.get('/api/oppija/v1/varhaiskasvatustiedot/{}/'.format(lapsi_oid),
                                                                   content_type='application/json')
        assert_status_code(resp_varhaiskasvatustiedot_api, status.HTTP_200_OK)

        request_count = Z5_AuditLog.objects.filter(user__username='suomi.fi#010280-952L#010215A951T').count()
        self.assertEqual(request_count, 2)

    def test_vakajarjestaja_paattymis_pvm_yhteystieto_osoite(self):
        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = ''
        vakajarjestaja_oid = '1.2.246.562.10.93957375484'
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        # add end date
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid)
        vakajarjestaja_nimi = vakajarjestaja.nimi
        vakajarjestaja.paattymis_pvm = '2019-01-01'
        vakajarjestaja.save()
        resp_varhaiskasvatustiedot_api = client_suomifi_tester.get('/api/oppija/v1/varhaiskasvatustiedot/{}/'.format(lapsi_oid),
                                                                   content_type='application/json')
        assert_status_code(resp_varhaiskasvatustiedot_api, status.HTTP_200_OK)
        resp_json = json.loads(resp_varhaiskasvatustiedot_api.content)
        for lapsi in resp_json['lapset']:
            if lapsi['varhaiskasvatuksen_jarjestaja'] == vakajarjestaja_nimi:
                self.assertEqual(lapsi['yhteysosoite'], None)
                self.assertFalse(lapsi['aktiivinen_toimija'])

    def test_api_turvakielto(self):
        def _assert_all_resp_status(client, correct_status):
            url_list = [f'/api/oppija/v1/henkilotiedot/{lapsi_oid}/',
                        f'/api/oppija/v1/varhaiskasvatustiedot/{lapsi_oid}/',
                        f'/api/oppija/v1/huoltajatiedot/{lapsi_oid}/',
                        f'/api/oppija/v1/tyontekijatiedot/{lapsi_oid}/']
            for url in url_list:
                resp = client.get(url)
                assert_status_code(resp, correct_status)

        lapsi_oid = '1.2.246.562.24.6779627637492'
        huoltaja_oid = '1.2.246.562.24.3367432256266'

        client_valtuudet = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        _assert_all_resp_status(client_valtuudet, status.HTTP_200_OK)

        Henkilo.objects.filter(henkilo_oid=lapsi_oid).update(turvakielto=True)
        _assert_all_resp_status(client_valtuudet, status.HTTP_404_NOT_FOUND)

        # Lapsi can still get their own information
        client_lapsi = self._create_oppija_cas_user_and_assert_henkilo_oid(lapsi_oid)
        _assert_all_resp_status(client_lapsi, status.HTTP_200_OK)

    def _create_oppija_cas_user_and_assert_huoltaja_oid(self, huoltaja_oid, lapsi_oid):
        user_suomifi, is_created = User.objects.get_or_create(username='suomi.fi#010280-952L#010215A951T',
                                                              is_staff=False,
                                                              is_active=True)
        user_suomifi.personOid = lapsi_oid
        user_suomifi.impersonatorPersonOid = huoltaja_oid
        _oppija_post_login_handler(user_suomifi)

        additional_cas_user_fields = Z3_AdditionalCasUserFields.objects.filter(user=user_suomifi).first()
        expected_huoltaja_oid = additional_cas_user_fields.henkilo_oid
        self.assertEqual(expected_huoltaja_oid, huoltaja_oid)
        expected_huollettava_oid = additional_cas_user_fields.huollettava_oid_list[0]
        self.assertEqual(expected_huollettava_oid, lapsi_oid)

        return SetUpTestClient(user_suomifi.username).client()

    def test_api_tyontekijatiedot(self):
        henkilo_oid = '1.2.246.562.24.2431884920041'
        henkilo_obj = Henkilo.objects.get(henkilo_oid=henkilo_oid)

        client = self._create_oppija_cas_user_and_assert_henkilo_oid(henkilo_oid)
        resp_henkilotiedot = client.get(f'/api/oppija/v1/henkilotiedot/{henkilo_oid}/')
        assert_status_code(resp_henkilotiedot, status.HTTP_200_OK)
        resp_henkilotiedot_json = json.loads(resp_henkilotiedot.content)

        # Assert some of the returned information is correct
        self.assertEqual(resp_henkilotiedot_json['henkilo_oid'], henkilo_oid)

        resp_huoltajatiedot = client.get(f'/api/oppija/v1/huoltajatiedot/{henkilo_oid}/')
        assert_status_code(resp_huoltajatiedot, status.HTTP_200_OK)
        resp_huoltajatiedot_json = json.loads(resp_huoltajatiedot.content)

        self.assertIsNone(resp_huoltajatiedot_json['huoltaja_id'])
        self.assertIsNone(resp_huoltajatiedot_json['huoltajuussuhteet'])

        resp_tyontekijatiedot = client.get(f'/api/oppija/v1/tyontekijatiedot/{henkilo_oid}/')
        assert_status_code(resp_tyontekijatiedot, status.HTTP_200_OK)
        resp_tyontekijatiedot_json = json.loads(resp_tyontekijatiedot.content)

        self.assertEqual(len(resp_tyontekijatiedot_json['tyontekijat']), henkilo_obj.tyontekijat.count())
        tyontekija_obj = henkilo_obj.tyontekijat.first()
        tyontekija_json = next(tyontekija for tyontekija in resp_tyontekijatiedot_json['tyontekijat']
                               if tyontekija['id'] == tyontekija_obj.id)
        self.assertEqual(len(tyontekija_json['tutkinnot']),
                         tyontekija_obj.henkilo.tutkinnot.filter(vakajarjestaja=tyontekija_obj.vakajarjestaja).count())

        self.assertEqual(len(tyontekija_json['palvelussuhteet']), tyontekija_obj.palvelussuhteet.count())
        palvelussuhde_obj = tyontekija_obj.palvelussuhteet.first()
        palvelussuhde_json = next(palvelussuhde for palvelussuhde in tyontekija_json['palvelussuhteet']
                                  if palvelussuhde['id'] == palvelussuhde_obj.id)
        self.assertEqual(len(palvelussuhde_json['tyoskentelypaikat']), palvelussuhde_obj.tyoskentelypaikat.count())
        self.assertEqual(palvelussuhde_json['tyoaika_viikossa'], str(palvelussuhde_obj.tyoaika_viikossa))

        self.assertEqual(len(tyontekija_json['taydennyskoulutukset']),
                         tyontekija_obj.taydennyskoulutukset_tyontekijat.values('taydennyskoulutus').distinct().count())
        taydennyskoulutus_obj = tyontekija_obj.taydennyskoulutukset_tyontekijat.first().taydennyskoulutus
        taydennyskoulutus_json = next(taydennyskoulutus for taydennyskoulutus in tyontekija_json['taydennyskoulutukset']
                                      if taydennyskoulutus['id'] == taydennyskoulutus_obj.id)
        self.assertEqual(len(taydennyskoulutus_json['tehtavanimike_koodi_list']),
                         tyontekija_obj.taydennyskoulutukset_tyontekijat.filter(taydennyskoulutus=taydennyskoulutus_obj).count())

    def test_api_huoltajatiedot(self):
        henkilo_oid = '1.2.246.562.24.3367432256266'
        henkilo_obj = Henkilo.objects.get(henkilo_oid=henkilo_oid)

        client = self._create_oppija_cas_user_and_assert_henkilo_oid(henkilo_oid)
        resp_henkilotiedot = client.get(f'/api/oppija/v1/henkilotiedot/{henkilo_oid}/')
        assert_status_code(resp_henkilotiedot, status.HTTP_200_OK)
        resp_henkilotiedot_json = json.loads(resp_henkilotiedot.content)

        # Assert some of the returned information is correct
        self.assertEqual(resp_henkilotiedot_json['sukunimi'], henkilo_obj.sukunimi)
        self.assertEqual(resp_henkilotiedot_json['katuosoite'], henkilo_obj.katuosoite)

        resp_tyontekijatiedot = client.get(f'/api/oppija/v1/tyontekijatiedot/{henkilo_oid}/')
        assert_status_code(resp_tyontekijatiedot, status.HTTP_200_OK)
        resp_tyontekijatiedot_json = json.loads(resp_tyontekijatiedot.content)

        self.assertEqual(resp_tyontekijatiedot_json['tyontekijat'], None)

        resp_huoltajatiedot = client.get(f'/api/oppija/v1/huoltajatiedot/{henkilo_oid}/')
        assert_status_code(resp_huoltajatiedot, status.HTTP_200_OK)
        resp_huoltajatiedot_json = json.loads(resp_huoltajatiedot.content)

        huoltaja_obj = henkilo_obj.huoltaja
        self.assertEqual(resp_huoltajatiedot_json['huoltaja_id'], huoltaja_obj.id)
        self.assertEqual(len(resp_huoltajatiedot_json['huoltajuussuhteet']), huoltaja_obj.huoltajuussuhteet.count())
        huoltajuussuhde_obj = huoltaja_obj.huoltajuussuhteet.first()
        huoltajuussuhde_json = next(huoltajuussuhde for huoltajuussuhde in resp_huoltajatiedot_json['huoltajuussuhteet']
                                    if huoltajuussuhde['lapsi_id'] == huoltajuussuhde_obj.lapsi.id)
        self.assertEqual(huoltajuussuhde_json['vakatoimija_nimi'], huoltajuussuhde_obj.lapsi.vakatoimija.nimi)
        self.assertIsNone(huoltajuussuhde_json['oma_organisaatio_id'])
        self.assertEqual(len(huoltajuussuhde_json['maksutiedot']), huoltajuussuhde_obj.maksutiedot.count())

        maksutieto_obj = huoltajuussuhde_obj.maksutiedot.first()
        maksutieto_json = next(maksutieto for maksutieto in huoltajuussuhde_json['maksutiedot']
                               if maksutieto['id'] == maksutieto_obj.id)
        self.assertEqual(maksutieto_json['huoltaja_lkm'], maksutieto_obj.huoltajuussuhteet.count())
        self.assertEqual(maksutieto_json['maksun_peruste_koodi'], maksutieto_obj.maksun_peruste_koodi)

    def test_api_henkilotiedot_unauthorized(self):
        # Different OID
        client_1 = self._create_oppija_cas_user_and_assert_henkilo_oid('1.2.246.562.24.3367432256266')
        resp_1 = client_1.get('/api/oppija/v1/henkilotiedot/1.2.246.562.24.3367432256265/')
        assert_status_code(resp_1, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_1, 'errors', 'PE006', 'User does not have permission to perform this action.')

        # Normal virkailija account
        client_2 = SetUpTestClient('tester2').client()
        resp_2 = client_2.get('/api/oppija/v1/henkilotiedot/1.2.246.562.24.6722258949565/')
        assert_status_code(resp_2, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_2, 'errors', 'PE006', 'User does not have permission to perform this action.')

    def test_api_tyontekijatiedot_valtuudet(self):
        henkilo_oid = '1.2.246.562.24.2431884920041'
        henkilo_obj = Henkilo.objects.get(henkilo_oid=henkilo_oid)

        client = self._create_oppija_cas_user_and_assert_huoltaja_oid(None, henkilo_oid)
        resp_tyontekijatiedot = client.get(f'/api/oppija/v1/tyontekijatiedot/{henkilo_oid}/')
        assert_status_code(resp_tyontekijatiedot, status.HTTP_200_OK)
        resp_tyontekijatiedot_json = json.loads(resp_tyontekijatiedot.content)
        self.assertEqual(len(resp_tyontekijatiedot_json['tyontekijat']), henkilo_obj.tyontekijat.count())

    def test_api_henkilotiedot_admin(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/oppija/v1/henkilotiedot/1.2.246.562.24.3367432256266/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_henkilotiedot_no_oid(self):
        client = self._create_oppija_cas_user_and_assert_henkilo_oid(None, assert_oid=False)
        resp = client.get('/api/oppija/v1/henkilotiedot/1.2.246.562.24.3367432256266/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

    def _create_oppija_cas_user_and_assert_henkilo_oid(self, henkilo_oid, assert_oid=True):
        user_suomifi = User.objects.create(username='suomi.fi#060570-601B', is_staff=False, is_active=True)
        user_suomifi.personOid = henkilo_oid
        _oppija_post_login_handler(user_suomifi)

        if assert_oid:
            expected_henkilo_oid = Z3_AdditionalCasUserFields.objects.get(user=user_suomifi).henkilo_oid
            self.assertEqual(expected_henkilo_oid, henkilo_oid)
        return SetUpTestClient(user_suomifi.username).client()
