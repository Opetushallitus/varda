import datetime
import json

from django.contrib.auth.models import User
from django.db.models import Q
from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIClient

from varda.models import (VakaJarjestaja, Toimipaikka, Varhaiskasvatussuhde, Varhaiskasvatuspaatos, Maksutieto, Lapsi,
                          Henkilo, Huoltajuussuhde)
from varda.organisation_transformations import transfer_toimipaikat_to_vakajarjestaja
from varda.permissions import object_ids_organization_has_permissions_to
from varda.unit_tests.test_utils import assert_status_code


class SetUpTestClient:
    def __init__(self, name):
        self.name = name

    def client(self):
        user = User.objects.get(username=self.name)
        api_c = APIClient()
        api_c.force_authenticate(user=user)
        return api_c


class OrganisationTransformationsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_transfer_simple_toimipaikka(self):
        today = datetime.date.today()
        admin = User.objects.get(username='credadmin')

        old_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'
        toimipaikka_oid = '1.2.246.562.10.6727877596658'

        old_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=old_vakajarjestaja_oid)
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid)

        lapsi_qs = (Lapsi.objects
                    .filter(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka=toimipaikka)
                    .distinct())
        lapsi_id_list_1 = list(lapsi_qs.values_list('id', flat=True))

        active_filter = Q(paattymis_pvm=None) | Q(paattymis_pvm__gt=today)

        vakapaatos_qs = Varhaiskasvatuspaatos.objects.filter(lapsi__in=lapsi_qs)
        vakapaatos_id_list_1 = list(vakapaatos_qs.values_list('id', flat=True))
        vakapaatos_active_count = vakapaatos_qs.filter(active_filter).count()

        vakasuhde_qs = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__in=vakapaatos_qs)
        vakasuhde_id_list_1 = list(vakasuhde_qs.values_list('id', flat=True))
        vakasuhde_active_count = vakasuhde_qs.filter(active_filter).count()

        maksutieto_qs = Maksutieto.objects.filter(huoltajuussuhteet__lapsi__in=lapsi_qs).distinct()
        maksutieto_id_list_1 = list(maksutieto_qs.values_list('id', flat=True))
        maksutieto_active_count = maksutieto_qs.filter(active_filter).count()

        huoltajuussuhde_count = Huoltajuussuhde.objects.all().count()

        # Assert permissions before transfer
        check_if_organization_has_permissions(self, old_vakajarjestaja_oid, toimipaikka.id, lapsi_id_list_1,
                                              vakapaatos_id_list_1, vakasuhde_id_list_1, maksutieto_id_list_1,
                                              has_permissions=True)
        check_if_organization_has_permissions(self, new_vakajarjestaja_oid, toimipaikka.id, lapsi_id_list_1,
                                              vakapaatos_id_list_1, vakasuhde_id_list_1, maksutieto_id_list_1,
                                              has_permissions=False)

        # Transfer toimipaikka 1.2.246.562.10.6727877596658 to vakajarjestaja 1.2.246.562.10.52966755795
        transfer_toimipaikat_to_vakajarjestaja(admin, new_vakajarjestaja.id, [toimipaikka.id])

        # Assert old lapsi objects don't exist (they are deleted)
        self.assertFalse(Lapsi.objects.filter(id__in=lapsi_id_list_1).exists())
        # Assert number of lapset hasn't changed
        self.assertEqual(lapsi_qs.count(), len(lapsi_id_list_1))

        # Assert new vakapaatokset, vakasuhteet and maksutiedot were created to replace active ones
        self.assertEqual(vakapaatos_qs.count(), len(vakapaatos_id_list_1) + vakapaatos_active_count)
        self.assertEqual(vakasuhde_qs.count(), len(vakasuhde_id_list_1) + vakasuhde_active_count)
        self.assertEqual(maksutieto_qs.count(), len(maksutieto_id_list_1) + maksutieto_active_count)

        # Assert number of huoltajuussuhteet didn't change (old ones removed)
        self.assertEqual(huoltajuussuhde_count, Huoltajuussuhde.objects.all().count())

        # Assert permissions after transfer
        new_lapsi_id_list_1 = list(lapsi_qs.values_list('id', flat=True))
        check_if_organization_has_permissions(self, old_vakajarjestaja_oid, toimipaikka.id, new_lapsi_id_list_1,
                                              vakapaatos_id_list_1, vakasuhde_id_list_1, maksutieto_id_list_1,
                                              has_permissions=False)
        check_if_organization_has_permissions(self, new_vakajarjestaja_oid, toimipaikka.id, new_lapsi_id_list_1,
                                              vakapaatos_id_list_1, vakasuhde_id_list_1, maksutieto_id_list_1,
                                              has_permissions=True)

        lapsi_id_list_2 = list(lapsi_qs.values_list('id', flat=True))
        vakapaatos_id_list_2 = list(vakapaatos_qs.values_list('id', flat=True))
        vakasuhde_id_list_2 = list(vakasuhde_qs.values_list('id', flat=True))
        maksutieto_id_list_2 = list(maksutieto_qs.values_list('id', flat=True))
        # Transfer toimipaikka 1.2.246.562.10.6727877596658 back to vakajarjestaja 1.2.246.562.10.57294396385
        transfer_toimipaikat_to_vakajarjestaja(admin, old_vakajarjestaja.id, [toimipaikka.id])

        # Assert old lapsi objects don't exist (they are deleted)
        self.assertFalse(Lapsi.objects.filter(id__in=lapsi_id_list_2).exists())
        # Assert number of lapset hasn't changed
        self.assertEqual(lapsi_qs.count(), len(lapsi_id_list_2))

        # Assert new vakapaatokset, vakasuhteet and maksutiedot were created to replace active ones
        self.assertEqual(vakapaatos_qs.count(), len(vakapaatos_id_list_2) + vakapaatos_active_count)
        self.assertEqual(vakasuhde_qs.count(), len(vakasuhde_id_list_2) + vakasuhde_active_count)
        self.assertEqual(maksutieto_qs.count(), len(maksutieto_id_list_2) + maksutieto_active_count)

        # Assert number of huoltajuussuhteet didn't change (old ones removed)
        self.assertEqual(huoltajuussuhde_count, Huoltajuussuhde.objects.all().count())

        new_lapsi_id_list_2 = list(lapsi_qs.values_list('id', flat=True))
        # Assert permissions are same as in the beginning
        check_if_organization_has_permissions(self, old_vakajarjestaja_oid, toimipaikka.id, new_lapsi_id_list_2,
                                              vakapaatos_id_list_2, vakasuhde_id_list_2, maksutieto_id_list_2,
                                              has_permissions=True)
        check_if_organization_has_permissions(self, new_vakajarjestaja_oid, toimipaikka.id, new_lapsi_id_list_2,
                                              vakapaatos_id_list_2, vakasuhde_id_list_2, maksutieto_id_list_2,
                                              has_permissions=False)

    def test_transfer_toimipaikka_vakasuhde_in_other_toimipaikka(self):
        admin = User.objects.get(username='credadmin')

        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'
        toimipaikka_oid = '1.2.246.562.10.6727877596658'
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid)

        # Create vakasuhde to other toimipaikka
        vakapaatos = Varhaiskasvatuspaatos.objects.filter(varhaiskasvatussuhteet__toimipaikka=toimipaikka).first()
        vakasuhde = {
            'varhaiskasvatuspaatos': '/api/v1/varhaiskasvatuspaatokset/{0}/'.format(vakapaatos.id),
            'toimipaikka_oid': '1.2.246.562.10.2565458382544',
            'alkamis_pvm': '2020-02-02'
        }
        client = SetUpTestClient('tester10').client()
        vakasuhde_resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(vakasuhde_resp, 201)
        vakasuhde_id = json.loads(vakasuhde_resp.content)['id']

        # Transfer toimipaikka 1.2.246.562.10.6727877596658 to vakajarjestaja 1.2.246.562.10.52966755795
        transfer_toimipaikat_to_vakajarjestaja(admin, new_vakajarjestaja.id, [toimipaikka.id])

        # Assert vakasuhde has paattymis_pvm
        self.assertNotEqual(Varhaiskasvatussuhde.objects.get(id=vakasuhde_id).paattymis_pvm, None)

    def test_transfer_new_vakajarjestaja_has_existing_lapsi(self):
        admin = User.objects.get(username='credadmin')

        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'
        toimipaikka_oid = '1.2.246.562.10.6727877596658'
        lapsi_henkilo_oid = '1.2.246.562.24.6779627637492'
        other_toimipaikka_oid = '1.2.246.562.10.9625978384762'
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid)
        lapsi_henkilo = Henkilo.objects.get(henkilo_oid=lapsi_henkilo_oid)

        old_lapsi_id = (Lapsi.objects.get(henkilo__henkilo_oid=lapsi_henkilo_oid,
                                          varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka=toimipaikka.id)
                        .id)

        client = SetUpTestClient('tester11').client()
        # Create lapsi
        lapsi = {
            'henkilo': '/api/v1/henkilot/{0}/'.format(lapsi_henkilo.id),
            'vakatoimija_oid': new_vakajarjestaja_oid
        }
        lapsi_resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(lapsi_resp, 201)

        # Create vakapaatos
        vakapaatos = {
            'lapsi': json.loads(lapsi_resp.content)['url'],
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2020-03-01',
            'alkamis_pvm': '2020-03-01'
        }
        vakapaatos_resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(vakapaatos_resp, 201)

        # Create vakasuhde
        vakasuhde = {
            'toimipaikka_oid': other_toimipaikka_oid,
            'varhaiskasvatuspaatos': json.loads(vakapaatos_resp.content)['url'],
            'alkamis_pvm': '2020-03-20'
        }
        vakasuhde_resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(vakasuhde_resp, 201)

        total_huoltajuussuhde_count = Huoltajuussuhde.objects.all().count()
        lapsi_huoltajuussuhde_count = Huoltajuussuhde.objects.filter(lapsi=old_lapsi_id).all().count()

        # Transfer toimipaikka 1.2.246.562.10.6727877596658 to vakajarjestaja 1.2.246.562.10.52966755795
        transfer_toimipaikat_to_vakajarjestaja(admin, new_vakajarjestaja.id, [toimipaikka.id])

        # Assert old lapsi object doesn't exist
        self.assertFalse(Lapsi.objects.filter(id=old_lapsi_id).exists())

        lapsi_id_list = object_ids_organization_has_permissions_to(new_vakajarjestaja_oid, Lapsi)
        new_lapsi = (Lapsi.objects.filter(id__in=lapsi_id_list,
                                          henkilo__henkilo_oid=lapsi_henkilo_oid,
                                          varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka=toimipaikka.id)
                     .distinct())
        # Assert new vakajarjestaja has only one lapsi linked to henkilo 1.2.246.562.24.6779627637492
        self.assertEqual(new_lapsi.count(), 1)

        # Assert it has three different vakapaatos (two to transferred toimipaikka, inactive and new active)
        self.assertEqual(new_lapsi.first().varhaiskasvatuspaatokset.count(), 3)

        # Assert number of huoltajuussuhteet decreased as existing lapsi already had them
        self.assertEqual(total_huoltajuussuhde_count - lapsi_huoltajuussuhde_count,
                         Huoltajuussuhde.objects.all().count())

    def test_transfer_toimipaikka_has_paos_lapsi(self):
        admin = User.objects.get(username='credadmin')

        old_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'
        paos_vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        toimipaikka_oid = '1.2.246.562.10.6727877596658'
        paos_henkilo_oid = '1.2.246.562.24.58672764848'

        old_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=old_vakajarjestaja_oid)
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)
        paos_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=paos_vakajarjestaja_oid)
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid)
        paos_henkilo = Henkilo.objects.get(henkilo_oid=paos_henkilo_oid)

        # Create paos-toiminta and paos-lapsi
        toimipaikka.jarjestamismuoto_koodi = ['jm03']
        toimipaikka.save()

        client_paos_toiminta_1 = SetUpTestClient('tester10').client()
        paos_toiminta = {
            'oma_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(old_vakajarjestaja.id),
            'paos_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(paos_vakajarjestaja.id)
        }

        resp_paos_toiminta_1 = client_paos_toiminta_1.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp_paos_toiminta_1, 201)

        client_paos_toiminta_2 = SetUpTestClient('tester4').client()
        paos_toiminta = {
            'oma_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(paos_vakajarjestaja.id),
            'paos_toimipaikka': '/api/v1/toimipaikat/{0}/'.format(toimipaikka.id)
        }

        resp_paos_toiminta_2 = client_paos_toiminta_2.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp_paos_toiminta_2, 201)

        client_paos_lapsi = SetUpTestClient('tester2').client()
        paos_lapsi = {
            'henkilo': '/api/v1/henkilot/{0}/'.format(paos_henkilo.id),
            'oma_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(paos_vakajarjestaja.id),
            'paos_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(old_vakajarjestaja.id)
        }
        resp_paos_lapsi = client_paos_lapsi.post('/api/v1/lapset/', paos_lapsi)
        assert_status_code(resp_paos_lapsi, 201)

        paos_vakapaatos = {
            'lapsi': json.loads(resp_paos_lapsi.content)['url'],
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm03',
            'hakemus_pvm': '2020-04-01',
            'alkamis_pvm': '2020-04-01'
        }
        resp_paos_vakapaatos = client_paos_lapsi.post('/api/v1/varhaiskasvatuspaatokset/', paos_vakapaatos)
        assert_status_code(resp_paos_vakapaatos, 201)

        paos_vakasuhde = {
            'toimipaikka_oid': toimipaikka_oid,
            'varhaiskasvatuspaatos': json.loads(resp_paos_vakapaatos.content)['url'],
            'alkamis_pvm': '2020-04-20'
        }
        paos_vakasuhde_resp = client_paos_lapsi.post('/api/v1/varhaiskasvatussuhteet/', paos_vakasuhde)
        assert_status_code(paos_vakasuhde_resp, 201)

        with self.assertRaises(serializers.ValidationError):
            # Transfer toimipaikka 1.2.246.562.10.6727877596658 to vakajarjestaja 1.2.246.562.10.52966755795
            transfer_toimipaikat_to_vakajarjestaja(admin, new_vakajarjestaja.id, [toimipaikka.id])


def check_if_organization_has_permissions(self,
                                          organisaatio_oid,
                                          toimipaikka_id,
                                          lapsi_id_list,
                                          vakapaatos_id_list,
                                          vakasuhde_id_list,
                                          maksutieto_id_list,
                                          has_permissions=True):
    # List of toimipaikat organization has permissions to
    toimipaikka_list_permissions = object_ids_organization_has_permissions_to(organisaatio_oid, Toimipaikka)
    # List of lapset organization has permissions to
    lapsi_list_permissions = object_ids_organization_has_permissions_to(organisaatio_oid, Lapsi)
    # List of varhaiskasvatuspaatokset organization has permissions to
    vakapaatos_list_permissions = object_ids_organization_has_permissions_to(organisaatio_oid, Varhaiskasvatuspaatos)
    # List of varhaiskasvatussuhteet organization has permissions to
    vakasuhde_list_permissions = object_ids_organization_has_permissions_to(organisaatio_oid, Varhaiskasvatussuhde)
    # List of maksutiedot organization has permissions to
    maksutieto_list_permissions = object_ids_organization_has_permissions_to(organisaatio_oid, Maksutieto)

    # Assert user has or doesn't have permissions
    if has_permissions:
        # Assert user has permissions to toimipaikka
        self.assertIn(toimipaikka_id, toimipaikka_list_permissions)
        # Assert user has permissions to lapset
        self.assertTrue(set(lapsi_id_list).issubset(lapsi_list_permissions))
        # Assert user has permissions to vakapaatokset
        self.assertTrue(set(vakapaatos_id_list).issubset(vakapaatos_list_permissions))
        # Assert user has permissions to vakasuhteet
        self.assertTrue(set(vakasuhde_id_list).issubset(vakasuhde_list_permissions))
        # Assert user has permissions to vakasuhteet
        self.assertTrue(set(maksutieto_id_list).issubset(maksutieto_list_permissions))
    else:
        # Assert user doesn't have permissions to toimipaikka
        self.assertNotIn(toimipaikka_id, toimipaikka_list_permissions)
        # Assert user doesn't have permissions to lapset
        self.assertFalse(set(lapsi_id_list).issubset(lapsi_list_permissions))
        # Assert user doesn't have permissions to vakapaatokset
        self.assertFalse(set(vakapaatos_id_list).issubset(vakapaatos_list_permissions))
        # Assert user doesn't have permissions to vakasuhteet
        self.assertFalse(set(vakasuhde_id_list).issubset(vakasuhde_list_permissions))
        # Assert user doesn't have permissions to vakasuhteet
        self.assertFalse(set(maksutieto_id_list).issubset(maksutieto_list_permissions))
