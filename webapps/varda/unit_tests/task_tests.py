import datetime
import json

import responses
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from varda.models import (Lapsi, Huoltaja, Maksutieto, Varhaiskasvatussuhde, Varhaiskasvatuspaatos, Henkilo,
                          Organisaatio, Huoltajuussuhde, Z5_AuditLog)
from varda.permission_groups import get_oph_yllapitaja_group_name
from varda.permissions import reassign_all_lapsi_permissions
from varda.tasks import (change_lapsi_henkilo_task, delete_huoltajat_without_relations_task,
                         delete_henkilot_without_relations_task,
                         general_monitoring_task, merge_duplicate_child_task, reset_superuser_permissions_task)
from varda.unit_tests.test_utils import SetUpTestClient, assert_status_code


class TaskTests(TestCase):
    fixtures = ['fixture_basics']

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
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
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

        huoltaja = Huoltaja.objects.create(henkilo_id=henkilo_3_id)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi_id=lapsi_id)

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

        huoltaja = Huoltaja.objects.create(henkilo_id=henkilo_5_id)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi_id=lapsi_id)

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

    def test_merge_duplicate_child_task_input(self):
        with self.assertRaises(TypeError) as cm:
            merge_duplicate_child_task.delay('test')
        exception_msg = 'Invalid list, please check the format'
        self.assertEqual(str(cm.exception), exception_msg)

        with self.assertRaises(TypeError) as cm:
            merge_duplicate_child_task.delay(['test'])
        exception_msg = 'List is not a list of lists, please check the input format'
        self.assertEqual(str(cm.exception), exception_msg)

        with self.assertRaises(TypeError) as cm:
            merge_duplicate_child_task.delay([[1, 'test']])
        exception_msg = "List length is not equal to two or contains non-integer values [1, 'test']"
        self.assertEqual(str(cm.exception), exception_msg)

        with self.assertRaises(TypeError) as cm:
            merge_duplicate_child_task.delay([[1, 2, 3]])
        exception_msg = 'List length is not equal to two or contains non-integer values [1, 2, 3]'
        self.assertEqual(str(cm.exception), exception_msg)

        with self.assertLogs('varda.tasks') as cm:
            merge_duplicate_child_task.delay([[1, -1]])
            self.assertEqual(cm.output, ['WARNING:varda.tasks:No Lapsi object with ID 1 or ID -1',
                                         'WARNING:varda.tasks:IntegrityError for item [1, -1]',
                                         'INFO:varda.tasks:Merged 0 Lapsi objects'])

        with self.assertLogs('varda.tasks') as cm:
            merge_duplicate_child_task.delay([[1, 1]])
            self.assertEqual(cm.output, ['WARNING:varda.tasks:Cannot merge Lapsi with ID 1 with itself',
                                         'WARNING:varda.tasks:IntegrityError for item [1, 1]',
                                         'INFO:varda.tasks:Merged 0 Lapsi objects'])

        with self.assertLogs('varda.tasks') as cm:
            lapsi_id_1 = Lapsi.objects.get(tunniste='testing-lapsi1').id
            lapsi_id_2 = Lapsi.objects.get(tunniste='testing-lapsi3').id
            lapsi_input = [lapsi_id_1, lapsi_id_2]
            merge_duplicate_child_task.delay([lapsi_input])
            self.assertEqual(cm.output, [
                f'WARNING:varda.tasks:Cannot merge Lapsi objects {lapsi_input} with different Organisaatio relation',
                f'WARNING:varda.tasks:IntegrityError for item {lapsi_input}', 'INFO:varda.tasks:Merged 0 Lapsi objects'
            ])

    def test_merge_duplicate_child_task_correct(self):
        new_lapsi = Lapsi.objects.get(tunniste='testing-lapsi1')
        # Generate a duplicate Lapsi manually as there are validations in API
        henkilo = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.47279942650')
        organisaatio = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        old_lapsi = Lapsi.objects.create(henkilo=henkilo, vakatoimija=organisaatio, lahdejarjestelma='1')
        old_lapsi_id = old_lapsi.id
        for huoltajuussuhde in new_lapsi.huoltajuussuhteet.all():
            Huoltajuussuhde(lapsi=old_lapsi, huoltaja=huoltajuussuhde.huoltaja,
                            voimassa_kytkin=huoltajuussuhde.voimassa_kytkin).save()
        # Assign permissions
        reassign_all_lapsi_permissions(old_lapsi)

        client = SetUpTestClient('tester5').client()
        vakapaatos = {
            'lapsi': f'/api/v1/lapset/{old_lapsi_id}/',
            'vuorohoito_kytkin': False,
            'pikakasittely_kytkin': False,
            'tuntimaara_viikossa': 37.5,
            'paivittainen_vaka_kytkin': False,
            'kokopaivainen_vaka_kytkin': False,
            'tilapainen_vaka_kytkin': False,
            'jarjestamismuoto_koodi': 'jm04',
            'hakemus_pvm': '2022-03-12',
            'alkamis_pvm': '2022-03-12',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp, status.HTTP_201_CREATED)
        vakapaatos_id = json.loads(resp.content)['id']
        vakasuhde = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/',
            'toimipaikka_oid': '1.2.246.562.10.9395737548811',
            'alkamis_pvm': '2022-03-13',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp, status.HTTP_201_CREATED)

        client = SetUpTestClient('tester7').client()
        maksutieto = {
            'lapsi': f'/api/v1/lapset/{old_lapsi_id}/',
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'}
            ],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0.00,
            'asiakasmaksu': 0.00,
            'perheen_koko': 3,
            'alkamis_pvm': '2022-04-01',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        maksutieto_id = json.loads(resp.content)['id']

        # Has huoltajatieto permissions only in Toimipaikka 1.2.246.562.10.9395737548810
        client = SetUpTestClient('tester').client()
        assert_status_code(client.get(f'/api/v1/maksutiedot/{maksutieto_id}/'), status.HTTP_404_NOT_FOUND)

        vakapaatos_count = Varhaiskasvatuspaatos.objects.filter(lapsi__in=[new_lapsi, old_lapsi]).count()
        vakasuhde_count = (Varhaiskasvatussuhde.objects
                           .filter(varhaiskasvatuspaatos__lapsi__in=[new_lapsi, old_lapsi])
                           .count())
        maksutieto_count = (Maksutieto.objects
                            .filter(huoltajuussuhteet__lapsi__in=[new_lapsi, old_lapsi])
                            .distinct().count())

        with self.assertLogs('varda.tasks') as cm:
            merge_duplicate_child_task.delay([[new_lapsi.id, old_lapsi_id]])
            self.assertEqual(cm.output, ['INFO:varda.tasks:Merged 1 Lapsi objects'])

        self.assertFalse(Lapsi.objects.filter(id=old_lapsi_id).exists())

        self.assertEqual(vakapaatos_count, Varhaiskasvatuspaatos.objects.filter(lapsi=new_lapsi).count())
        self.assertEqual(vakasuhde_count,
                         Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=new_lapsi).count())
        self.assertEqual(maksutieto_count,
                         Maksutieto.objects.filter(huoltajuussuhteet__lapsi=new_lapsi).distinct().count())

        # new_lapsi has Varhaiskasvatussuhde to 1.2.246.562.10.9395737548810 so it should have permissions to
        # new Maksutieto object
        assert_status_code(client.get(f'/api/v1/maksutiedot/{maksutieto_id}/'), status.HTTP_200_OK)

    def test_change_lapsi_henkilo_task_input(self):
        with self.assertLogs('varda.tasks') as cm:
            change_lapsi_henkilo_task.delay([[1, -1]])
            self.assertEqual(cm.output, [
                'WARNING:varda.tasks:No Lapsi object with ID 1 or no Henkilo object with ID -1',
                'WARNING:varda.tasks:IntegrityError for item [1, -1]', 'INFO:varda.tasks:Modified 0 Lapsi objects'
            ])

        huoltaja_henkilo = Henkilo.objects.filter(huoltaja__isnull=False).first().id
        tyontekija_henkilo = Henkilo.objects.filter(tyontekijat__isnull=False).first().id
        for henkilo_id in [huoltaja_henkilo, tyontekija_henkilo]:
            henkilo_input = [1, henkilo_id]
            with self.assertLogs('varda.tasks') as cm:
                change_lapsi_henkilo_task.delay([henkilo_input])
                self.assertEqual(cm.output, [
                    f'WARNING:varda.tasks:Henkilo {henkilo_id} cannot be Tyontekija or Huoltaja',
                    f'WARNING:varda.tasks:IntegrityError for item {henkilo_input}',
                    'INFO:varda.tasks:Modified 0 Lapsi objects'
                ])

        with self.assertLogs('varda.tasks') as cm:
            henkilo_id = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.4338669286936').id
            lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi13').id
            henkilo_input = [lapsi_id, henkilo_id]
            change_lapsi_henkilo_task.delay([henkilo_input])
            self.assertEqual(cm.output, [
                f'WARNING:varda.tasks:Henkilo {henkilo_id} cannot have identical Lapsi as {lapsi_id}',
                f'WARNING:varda.tasks:IntegrityError for item {henkilo_input}',
                'INFO:varda.tasks:Modified 0 Lapsi objects'
            ])

    def test_change_lapsi_henkilo_task_correct(self):
        lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi3').id
        henkilo_id = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.8925547856499').id

        client = SetUpTestClient('tester2').client()
        assert_status_code(client.get(f'/api/v1/henkilot/{henkilo_id}/'), status.HTTP_404_NOT_FOUND)

        with self.assertLogs('varda.tasks') as cm:
            change_lapsi_henkilo_task.delay([[lapsi_id, henkilo_id]])
            self.assertEqual(cm.output, ['INFO:varda.tasks:Modified 1 Lapsi objects'])

        assert_status_code(client.get(f'/api/v1/henkilot/{henkilo_id}/'), status.HTTP_200_OK)
        self.assertEqual(henkilo_id, Lapsi.objects.get(id=lapsi_id).henkilo_id)
