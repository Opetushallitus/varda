import json

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from guardian.models import GroupObjectPermission
from varda.models import Toimipaikka, PaosOikeus
from varda.permissions import change_paos_tallentaja_organization
from varda.unit_tests.test_utils import assert_status_code
from varda.unit_tests.views_tests import SetUpTestClient


class VardaPaosTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_paos_toiminnat_with_same_toimipaikka_names(self):
        client = SetUpTestClient('tester4').client()
        resp = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)["count"], 2)

    def test_paos_permissions_when_organization_link_disables(self):
        """
        Toimipaikka_5 is a PAOS-toimipaikka, and tester2 has a view_permission to it.

        Let's first remove all the permissions for toimipaikka_5 so that tester2
        doesn't have permissions to it anymore from anywhere.

        Next disable the paos-link between the organizations vaka_1 and vaka_2 and
        check that tester2 doesn't see toimipaikka_5.

        Finally enable the paos-link again, and verify that tester2 has a view_permission to toimipaikka_5.
        """
        tester2 = User.objects.get(username='tester2')
        toimipaikka_5 = Toimipaikka.objects.get(id=5)
        client = SetUpTestClient('tester3').client()

        model_name = 'toimipaikka'
        content_type = ContentType.objects.filter(model=model_name).first()
        (GroupObjectPermission
         .objects
         .filter(object_pk=toimipaikka_5, content_type=content_type)
         .delete())  # delete all the (group)permissions for toimipaikka_5.
        self.assertFalse(tester2.has_perm('view_toimipaikka', toimipaikka_5))  # tester2 cannot see toimipaikka_5

        resp = client.get('/api/v1/paos-toiminnat/1/')
        assert_status_code(resp, 200)
        data = json.loads(resp.content)
        paos_toiminta = {
            'oma_organisaatio': data['oma_organisaatio'],
            'paos_organisaatio': data['paos_organisaatio']
        }
        resp = client.delete('/api/v1/paos-toiminnat/1/')
        assert_status_code(resp, 204)
        self.assertFalse(PaosOikeus.objects.get(id=1).voimassa_kytkin)  # link is now disabled

        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp, 201)
        self.assertTrue(PaosOikeus.objects.get(id=1).voimassa_kytkin)  # link is now enabled again
        self.assertTrue(tester2.has_perm('view_toimipaikka', toimipaikka_5))  # tester2 can see toimipaikka_5

    def test_change_paos_tallentaja(self):
        """
        In test data we have the following PAOS-agreement/link.
         * jarjestaja = vakajarjestaja_1
         * tuottaja = vakajarjestaja_2
         * paos_toimipaikka = toimipaikka_5
         * tallentaja = vakajarjestaja_1

        Let's check first tester2 (vakajarjestaja_1) can modify a vakasuhde connected to toimipaikka_5.
        And tester5 (vakajarjestaja_2) cannot.

        Then change the paos_tallentaja, and verify that these work the opposite way.

        PAOS-tallentaja change affects vakapaatokset also. This is also tested below.

        Finally, disable the paos-link between the organizations, and verify that either
        vakajarjestaja cannot make updates anymore.

        Test that GET works even if PUT fails.
        """
        tester2_client = SetUpTestClient('tester2').client()  # tallentaja_vakajarjestaja_1
        tester5_client = SetUpTestClient('tester5').client()  # tallentaja_vakajarjestaja_2

        resp = tester2_client.get('/api/v1/varhaiskasvatussuhteet/4/')
        vakasuhde_4 = resp.content

        resp = tester2_client.get('/api/v1/varhaiskasvatuspaatokset/4/')
        vakapaatos_4 = resp.content

        resp_tester2 = tester2_client.put('/api/v1/varhaiskasvatussuhteet/4/', vakasuhde_4, content_type='application/json')
        assert_status_code(resp_tester2, 200)
        resp_tester5 = tester5_client.put('/api/v1/varhaiskasvatussuhteet/4/', vakasuhde_4, content_type='application/json')
        assert_status_code(resp_tester5, 403)
        resp_tester5 = tester5_client.get('/api/v1/varhaiskasvatussuhteet/4/')
        assert_status_code(resp_tester5, 200)

        resp_tester2 = tester2_client.put('/api/v1/varhaiskasvatuspaatokset/4/', vakapaatos_4, content_type='application/json')
        assert_status_code(resp_tester2, 200)
        resp_tester5 = tester5_client.put('/api/v1/varhaiskasvatuspaatokset/4/', vakapaatos_4, content_type='application/json')
        assert_status_code(resp_tester5, 403)
        resp_tester5 = tester5_client.get('/api/v1/varhaiskasvatuspaatokset/4/')
        assert_status_code(resp_tester5, 200)

        """
        Change paos-tallentaja.
        """
        jarjestaja_kunta_organisaatio_id = 1
        tuottaja_organisaatio_id = 2
        tallentaja_organisaatio_id = 2  # This is now changed (from 1 -> 2)
        voimassa_kytkin = True
        change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                            tallentaja_organisaatio_id, voimassa_kytkin)

        resp_tester2 = tester2_client.put('/api/v1/varhaiskasvatussuhteet/4/', vakasuhde_4, content_type='application/json')
        assert_status_code(resp_tester2, 403)
        resp_tester2 = tester2_client.get('/api/v1/varhaiskasvatussuhteet/4/')
        assert_status_code(resp_tester2, 200)
        resp_tester5 = tester5_client.put('/api/v1/varhaiskasvatussuhteet/4/', vakasuhde_4, content_type='application/json')
        assert_status_code(resp_tester5, 200)

        resp_tester2 = tester2_client.put('/api/v1/varhaiskasvatuspaatokset/4/', vakapaatos_4, content_type='application/json')
        assert_status_code(resp_tester2, 403)
        resp_tester2 = tester2_client.get('/api/v1/varhaiskasvatuspaatokset/4/')
        assert_status_code(resp_tester2, 200)
        resp_tester5 = tester5_client.put('/api/v1/varhaiskasvatuspaatokset/4/', vakapaatos_4, content_type='application/json')
        assert_status_code(resp_tester5, 200)

        """
        Disable the paos-link between the organizations.
        """
        voimassa_kytkin = False  # Finally check that no one can update the vakasuhde anymore
        change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                            tallentaja_organisaatio_id, voimassa_kytkin)

        resp_tester2 = tester2_client.put('/api/v1/varhaiskasvatussuhteet/4/', vakasuhde_4, content_type='application/json')
        assert_status_code(resp_tester2, 403)
        self.assertEqual(json.loads(resp_tester2.content), {'detail': 'User does not have permissions to change this object.'})
        resp_tester5 = tester5_client.put('/api/v1/varhaiskasvatussuhteet/4/', vakasuhde_4, content_type='application/json')
        assert_status_code(resp_tester5, 403)
        self.assertEqual(json.loads(resp_tester5.content), {'detail': 'User does not have permissions to change this object.'})

        resp_tester2 = tester2_client.put('/api/v1/varhaiskasvatuspaatokset/4/', vakapaatos_4, content_type='application/json')
        assert_status_code(resp_tester2, 403)
        self.assertEqual(json.loads(resp_tester2.content), {'detail': 'User does not have permissions to change this object.'})
        resp_tester5 = tester5_client.put('/api/v1/varhaiskasvatuspaatokset/4/', vakapaatos_4, content_type='application/json')
        assert_status_code(resp_tester5, 403)
        self.assertEqual(json.loads(resp_tester5.content), {'detail': 'User does not have permissions to change this object.'})

        resp_tester2 = tester2_client.get('/api/v1/varhaiskasvatussuhteet/4/')
        assert_status_code(resp_tester2, 200)
        resp_tester5 = tester5_client.get('/api/v1/varhaiskasvatussuhteet/4/')
        assert_status_code(resp_tester5, 200)

        resp_tester2 = tester2_client.get('/api/v1/varhaiskasvatuspaatokset/4/')
        assert_status_code(resp_tester2, 200)
        resp_tester5 = tester5_client.get('/api/v1/varhaiskasvatuspaatokset/4/')
        assert_status_code(resp_tester5, 200)
