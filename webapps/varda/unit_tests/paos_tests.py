import json

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from guardian.models import GroupObjectPermission
from varda.models import Toimipaikka, PaosOikeus
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
