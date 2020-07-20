import json

from django.contrib.auth.models import Group
from django.test import TestCase
from guardian.shortcuts import assign_perm
from rest_framework import status

from varda.models import VakaJarjestaja, Tyontekija, Henkilo
from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient


class VardaHenkilostoViewSetTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_tyontekija_list_vakajarjestaja_tyontekija_user(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        expected_henkilo_count = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).count()
        vakajarjestaja_id = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

    def test_tyontekija_list_vakajarjestaja_taydennyskoulutus_user(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        expected_henkilo_count = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).count()
        vakajarjestaja_id = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

    def test_tyontekija_list_toimipaikka_tyontekija_user(self):
        client = SetUpTestClient('tyontekija_toimipaikka_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        toimipaikka_oid = '1.2.246.562.10.9395737548810'
        expected_henkilo_count = Tyontekija.objects.filter(palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid=toimipaikka_oid).distinct().count()
        vakajarjestaja_id = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertEqual(resp_content['count'], expected_henkilo_count)

        # Check direct permission also (tyontekija without tyoskentelypaikka)
        user = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.9395737548810')
        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')
        assign_perm('view_tyontekija', user, tyontekija)  # assing permission to tyontekija without tyoskentelypaikka
        resp_after_extra_permission = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/'.format(vakajarjestaja_id))
        resp_content_after_extra_permission = json.loads(resp_after_extra_permission.content)
        self.assertEqual(resp_content_after_extra_permission['count'], expected_henkilo_count + 1)

    def test_tyontekija_list_filters(self):
        client = SetUpTestClient('credadmin').client()
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        vakajarjestaja_id = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_oid).values_list('id', flat=True).first()
        toimipaikka_oid = '1.2.246.562.10.9395737548810'
        result_qs = Henkilo.objects.filter(tyontekijat__vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).distinct()
        query_result_list = [
            ('', result_qs),
            ('toimipaikka_oid={}'.format(toimipaikka_oid),
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid=toimipaikka_oid)
             ),
            ('kiertava_tyontekija_kytkin=false',
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=False)
             ),
            ('kiertava_tyontekija_kytkin=true',
             result_qs.filter(tyontekijat__palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=True)
             ),
            ('search=matti',
             result_qs.filter(etunimet__contains='Matti')
             ),
        ]
        for query, exptected_value in query_result_list:
            resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/?{}'.format(vakajarjestaja_id, query))
            assert_status_code(resp, status.HTTP_200_OK)
            resp_content = json.loads(resp.content)
            self.assertEqual(resp_content['count'], exptected_value.count())

        resp = client.get('/api/ui/vakajarjestajat/{}/tyontekija-list/?page_size=2'.format(vakajarjestaja_id))
        assert_status_code(resp, status.HTTP_200_OK)
        resp_content = json.loads(resp.content)
        self.assertEqual(len(resp_content['results']), 2)
