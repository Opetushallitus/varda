import datetime
import json

import responses
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from varda.models import (Lapsi, Huoltaja, Maksutieto, Varhaiskasvatussuhde, Varhaiskasvatuspaatos, Henkilo,
                          VakaJarjestaja, Huoltajuussuhde, Z5_AuditLog)
from varda.permission_groups import get_oph_yllapitaja_group_name
from varda.tasks import (delete_huoltajat_without_relations_task, delete_henkilot_without_relations_task,
                         general_monitoring_task, reset_superuser_permissions_task)
from varda.unit_tests.test_utils import SetUpTestClient, assert_status_code


class TaskTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_delete_huoltajat_task(self):
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi14')
        huoltaja_id = Huoltaja.objects.filter(huoltajuussuhteet__lapsi=lapsi).first().id
        huoltaja_qs = Huoltaja.objects.filter(id=huoltaja_id)

        delete_huoltajat_without_relations_task.delay()
        self.assertIsNotNone(huoltaja_qs.first())

        # Delete Lapsi and related objects
        client = SetUpTestClient('tester11').client()
        maksutieto_id_list = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).values_list('id', flat=True)
        for maksutieto_id in maksutieto_id_list:
            resp = client.delete(f'/api/v1/maksutiedot/{maksutieto_id}/')
            assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        vakasuhde_id_list = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).values_list('id', flat=True)
        for vakasuhde_id in vakasuhde_id_list:
            resp = client.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde_id}/')
            assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        vakapaatos_id_list = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).values_list('id', flat=True)
        for vakapaatos_id in vakapaatos_id_list:
            resp = client.delete(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/')
            assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        resp = client.delete(f'/api/v1/lapset/{lapsi.id}/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)

        delete_huoltajat_without_relations_task.delay()
        self.assertIsNone(huoltaja_qs.first())

    @responses.activate
    def test_delete_henkilot_task(self):
        responses_content = {'method': responses.POST,
                             'url': 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                             'json': '1.2.246.562.24.58772763851',
                             'status': status.HTTP_201_CREATED}
        henkilo_json = {
            'henkilotunnus': '211141-207N',
            'etunimet': 'Testi',
            'kutsumanimi': 'Testi',
            'sukunimi': 'Testilä',
        }
        client = SetUpTestClient('tester2').client()
        client_tyontekija = SetUpTestClient('tyontekija_tallentaja').client()
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        henkilo_id_list = []

        # Create Henkilo without related objects
        responses.add(**responses_content)
        resp_1 = client.post('/api/v1/henkilot/', henkilo_json)
        assert_status_code(resp_1, 201)
        henkilo_1_id = json.loads(resp_1.content)['id']
        henkilo_id_list.append(henkilo_1_id)

        # Create Henkilo with Lapsi
        responses.reset()
        responses_content['json'] = '1.2.246.562.24.58772763852'
        responses.add(**responses_content)
        henkilo_json['henkilotunnus'] = '010585-802F'
        resp_2_1 = client.post('/api/v1/henkilot/', henkilo_json)
        assert_status_code(resp_2_1, 201)
        henkilo_2_id = json.loads(resp_2_1.content)['id']
        henkilo_id_list.append(henkilo_2_id)

        lapsi_json = {
            'henkilo': f'/api/v1/henkilot/{henkilo_2_id}/',
            'vakatoimija_oid': vakajarjestaja.organisaatio_oid,
            'lahdejarjestelma': '1'
        }
        resp_2_2 = client.post('/api/v1/lapset/', lapsi_json)
        assert_status_code(resp_2_2, 201)
        lapsi_id = json.loads(resp_2_2.content)['id']

        # Create Henkilo with Huoltaja
        responses.reset()
        responses_content['json'] = '1.2.246.562.24.58772763853'
        responses.add(**responses_content)
        henkilo_json['henkilotunnus'] = '100520-772J'
        resp_3 = client.post('/api/v1/henkilot/', henkilo_json)
        assert_status_code(resp_3, 201)
        henkilo_3_id = json.loads(resp_3.content)['id']
        henkilo_id_list.append(henkilo_3_id)

        huoltaja = Huoltaja.objects.create(henkilo_id=henkilo_3_id, changed_by_id=1)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi_id=lapsi_id, changed_by_id=1)

        # Create Henkilo with Tyontekija
        responses.reset()
        responses_content['json'] = '1.2.246.562.24.58772763854'
        responses.add(**responses_content)
        henkilo_json['henkilotunnus'] = '270915-3284'
        resp_4_1 = client_tyontekija.post('/api/v1/henkilot/', henkilo_json)
        assert_status_code(resp_4_1, 201)
        henkilo_4_id = json.loads(resp_4_1.content)['id']
        henkilo_id_list.append(henkilo_4_id)

        tyontekija_json = {
            'henkilo': f'/api/v1/henkilot/{henkilo_4_id}/',
            'vakajarjestaja_oid': vakajarjestaja.organisaatio_oid,
            'lahdejarjestelma': '1'
        }
        resp_4_2 = client_tyontekija.post('/api/henkilosto/v1/tyontekijat/', tyontekija_json)
        assert_status_code(resp_4_2, 201)

        # Create Henkilo with Tyontekija and Huoltaja
        responses.reset()
        responses_content['json'] = '1.2.246.562.24.58772763855'
        responses.add(**responses_content)
        henkilo_json['henkilotunnus'] = '010411-783Y'
        resp_5_1 = client_tyontekija.post('/api/v1/henkilot/', henkilo_json)
        assert_status_code(resp_5_1, 201)
        henkilo_5_id = json.loads(resp_5_1.content)['id']
        henkilo_id_list.append(henkilo_5_id)

        tyontekija_json = {
            'henkilo': f'/api/v1/henkilot/{henkilo_5_id}/',
            'vakajarjestaja_oid': vakajarjestaja.organisaatio_oid,
            'lahdejarjestelma': '1'
        }
        resp_5_2 = client_tyontekija.post('/api/henkilosto/v1/tyontekijat/', tyontekija_json)
        assert_status_code(resp_5_2, 201)

        huoltaja = Huoltaja.objects.create(henkilo_id=henkilo_5_id, changed_by_id=1)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi_id=lapsi_id, changed_by_id=1)

        delete_henkilot_without_relations_task.delay()
        henkilo_qs = Henkilo.objects.filter(id__in=henkilo_id_list)
        self.assertEqual(henkilo_qs.count(), 5)

        henkilo_qs.update(luonti_pvm=timezone.now() - datetime.timedelta(days=100))

        delete_henkilot_without_relations_task.delay()
        self.assertEqual(henkilo_qs.count(), 4)
        self.assertFalse(Henkilo.objects.filter(id=henkilo_1_id).exists())

    def test_general_monitoring_task_users(self):
        oph_group, created = Group.objects.update_or_create(name=get_oph_yllapitaja_group_name())
        oph_group.user_set.add(*User.objects.all())
        with self.assertLogs('varda.tasks', level='ERROR') as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ['ERROR:varda.tasks:There are too many OPH staff users.'])
        oph_group.user_set.clear()

        User.objects.all().update(is_superuser=True)
        with self.assertLogs('varda.tasks', level='ERROR') as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ['ERROR:varda.tasks:There are too many users with is_staff=True or '
                                         'is_superuser=True.'])
        User.objects.all().update(is_superuser=False, is_staff=True)
        with self.assertLogs('varda.tasks', level='ERROR') as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ['ERROR:varda.tasks:There are too many users with is_staff=True or '
                                         'is_superuser=True.'])

    def test_general_monitoring_task_pages(self):
        user = User.objects.get(username='tester2')
        user_luovutuspalvelu = User.objects.get(username='kela_luovutuspalvelu')

        index = 0
        for index in range(20):
            Z5_AuditLog.objects.create(user=user, successful_get_request_path='/api/v1/toimipaikat/',
                                       query_params=f'page={index}')

        with self.assertNoLogs('varda.tasks', level='ERROR'):
            general_monitoring_task.delay()

        index += 1
        Z5_AuditLog.objects.create(user=user, successful_get_request_path='/api/v1/toimipaikat/',
                                   query_params=f'page={index}')
        with self.assertLogs('varda.tasks', level='ERROR') as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ["ERROR:varda.tasks:The following APIs are browsed through: <QuerySet "
                                         "[{'user': 4, 'successful_get_request_path': '/api/v1/toimipaikat/', "
                                         "'page_number_count': 21}]>"])

        Z5_AuditLog.objects.filter(user=user).update(user=user_luovutuspalvelu)
        with self.assertNoLogs('varda.tasks', level='ERROR'):
            general_monitoring_task.delay()

    def test_reset_superuser_permissions_task(self):
        user_qs = User.objects.filter(username='tester2')
        user = user_qs.first()
        user.is_superuser = True
        user.save()

        reset_superuser_permissions_task.delay()
        self.assertEqual(user_qs.first().is_superuser, False)
        self.assertEqual(user_qs.first().is_staff, False)
