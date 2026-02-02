import datetime
import json

import responses
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import transaction, ProgrammingError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from varda.models import (
    Lapsi,
    Huoltaja,
    Maksutieto,
    Varhaiskasvatussuhde,
    Varhaiskasvatuspaatos,
    Henkilo,
    Organisaatio,
    Huoltajuussuhde,
    Palvelussuhde,
    Tutkinto,
    Z5_AuditLog,
    Tukipaatos,
)
from varda.permission_groups import get_oph_yllapitaja_group_name
from varda.tasks import (
    change_lapsi_henkilo_task,
    delete_huoltajat_without_relations_task,
    delete_henkilot_without_relations_task,
    general_monitoring_task,
    reset_superuser_permissions_task,
    remove_inactive_tutkintos,
    add_missing_tukipaatos_paatosmaaras,
    remove_tutkintos_003_if_multiple_tutkinto_koodi,
)
from varda.unit_tests.test_utils import SetUpTestClient, assert_status_code


class TaskTests(TestCase):
    fixtures = ["fixture_basics"]

    def test_delete_huoltajat_task(self):
        lapsi = Lapsi.objects.get(tunniste="testing-lapsi14")
        huoltaja_id = Huoltaja.objects.filter(huoltajuussuhteet__lapsi=lapsi).first().id
        huoltaja_qs = Huoltaja.objects.filter(id=huoltaja_id)

        delete_huoltajat_without_relations_task.delay()
        self.assertIsNotNone(huoltaja_qs.first())

        # Delete Lapsi and related objects
        client = SetUpTestClient("tester11").client()
        maksutieto_id_list = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).values_list("id", flat=True)
        for maksutieto_id in maksutieto_id_list:
            resp = client.delete(f"/api/v1/maksutiedot/{maksutieto_id}/")
            assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        vakasuhde_id_list = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).values_list("id", flat=True)
        for vakasuhde_id in vakasuhde_id_list:
            resp = client.delete(f"/api/v1/varhaiskasvatussuhteet/{vakasuhde_id}/")
            assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        vakapaatos_id_list = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).values_list("id", flat=True)
        for vakapaatos_id in vakapaatos_id_list:
            resp = client.delete(f"/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/")
            assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        resp = client.delete(f"/api/v1/lapset/{lapsi.id}/")
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)

        delete_huoltajat_without_relations_task.delay()
        self.assertIsNone(huoltaja_qs.first())

    @responses.activate
    def test_delete_henkilot_task(self):
        responses_content = {
            "method": responses.POST,
            "url": "https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/",
            "json": "1.2.246.562.24.58772763851",
            "status": status.HTTP_201_CREATED,
        }
        henkilo_json = {
            "henkilotunnus": "211141-207N",
            "etunimet": "Testi",
            "kutsumanimi": "Testi",
            "sukunimi": "Testilä",
        }
        client = SetUpTestClient("tester2").client()
        client_tyontekija = SetUpTestClient("tyontekija_tallentaja").client()
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.34683023489")
        henkilo_id_list = []

        # Create Henkilo without related objects
        responses.add(**responses_content)
        resp_1 = client.post("/api/v1/henkilot/", henkilo_json)
        assert_status_code(resp_1, 201)
        henkilo_1_id = json.loads(resp_1.content)["id"]
        henkilo_id_list.append(henkilo_1_id)

        # Create Henkilo with Lapsi
        responses.reset()
        responses_content["json"] = "1.2.246.562.24.58772763852"
        responses.add(**responses_content)
        henkilo_json["henkilotunnus"] = "010585-802F"
        resp_2_1 = client.post("/api/v1/henkilot/", henkilo_json)
        assert_status_code(resp_2_1, 201)
        henkilo_2_id = json.loads(resp_2_1.content)["id"]
        henkilo_id_list.append(henkilo_2_id)

        lapsi_json = {
            "henkilo": f"/api/v1/henkilot/{henkilo_2_id}/",
            "vakatoimija_oid": vakajarjestaja.organisaatio_oid,
            "lahdejarjestelma": "1",
        }
        resp_2_2 = client.post("/api/v1/lapset/", lapsi_json)
        assert_status_code(resp_2_2, 201)
        lapsi_id = json.loads(resp_2_2.content)["id"]

        # Create Henkilo with Huoltaja
        responses.reset()
        responses_content["json"] = "1.2.246.562.24.58772763853"
        responses.add(**responses_content)
        henkilo_json["henkilotunnus"] = "100520-772J"
        resp_3 = client.post("/api/v1/henkilot/", henkilo_json)
        assert_status_code(resp_3, 201)
        henkilo_3_id = json.loads(resp_3.content)["id"]
        henkilo_id_list.append(henkilo_3_id)

        huoltaja = Huoltaja.objects.create(henkilo_id=henkilo_3_id)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi_id=lapsi_id)

        # Create Henkilo with Tyontekija
        responses.reset()
        responses_content["json"] = "1.2.246.562.24.58772763854"
        responses.add(**responses_content)
        henkilo_json["henkilotunnus"] = "270915-3284"
        resp_4_1 = client_tyontekija.post("/api/v1/henkilot/", henkilo_json)
        assert_status_code(resp_4_1, 201)
        henkilo_4_id = json.loads(resp_4_1.content)["id"]
        henkilo_id_list.append(henkilo_4_id)

        tyontekija_json = {
            "henkilo": f"/api/v1/henkilot/{henkilo_4_id}/",
            "vakajarjestaja_oid": vakajarjestaja.organisaatio_oid,
            "lahdejarjestelma": "1",
        }
        resp_4_2 = client_tyontekija.post("/api/henkilosto/v1/tyontekijat/", tyontekija_json)
        assert_status_code(resp_4_2, 201)

        # Create Henkilo with Tyontekija and Huoltaja
        responses.reset()
        responses_content["json"] = "1.2.246.562.24.58772763855"
        responses.add(**responses_content)
        henkilo_json["henkilotunnus"] = "010411-783Y"
        resp_5_1 = client_tyontekija.post("/api/v1/henkilot/", henkilo_json)
        assert_status_code(resp_5_1, 201)
        henkilo_5_id = json.loads(resp_5_1.content)["id"]
        henkilo_id_list.append(henkilo_5_id)

        tyontekija_json = {
            "henkilo": f"/api/v1/henkilot/{henkilo_5_id}/",
            "vakajarjestaja_oid": vakajarjestaja.organisaatio_oid,
            "lahdejarjestelma": "1",
        }
        resp_5_2 = client_tyontekija.post("/api/henkilosto/v1/tyontekijat/", tyontekija_json)
        assert_status_code(resp_5_2, 201)

        huoltaja = Huoltaja.objects.create(henkilo_id=henkilo_5_id)
        Huoltajuussuhde.objects.create(huoltaja=huoltaja, lapsi_id=lapsi_id)

        delete_henkilot_without_relations_task.delay()
        henkilo_qs = Henkilo.objects.filter(id__in=henkilo_id_list)
        self.assertEqual(henkilo_qs.count(), 5)

        henkilo_qs.update(luonti_pvm=timezone.now() - datetime.timedelta(days=settings.DELETE_HENKILO_WITHOUT_ROLE_IN_DAYS + 1))

        delete_henkilot_without_relations_task.delay()
        self.assertEqual(henkilo_qs.count(), 4)
        self.assertFalse(Henkilo.objects.filter(id=henkilo_1_id).exists())

    def test_general_monitoring_task_users(self):
        oph_group, created = Group.objects.update_or_create(name=get_oph_yllapitaja_group_name())
        oph_group.user_set.add(*User.objects.all())
        with self.assertLogs("varda.tasks", level="ERROR") as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ["ERROR:varda.tasks:There are too many OPH staff users."])
        oph_group.user_set.clear()

        for user in User.objects.all():
            user.is_superuser = True
            user.save()

        with self.assertLogs("varda.tasks", level="ERROR") as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ["ERROR:varda.tasks:There are too many users with is_staff=True or is_superuser=True."])

        for user in User.objects.all():
            user.is_superuser = False
            user.is_staff = True
            user.save()

        with self.assertLogs("varda.tasks", level="ERROR") as cm:
            general_monitoring_task.delay()
            self.assertEqual(cm.output, ["ERROR:varda.tasks:There are too many users with is_staff=True or is_superuser=True."])

        # Test multiple User is_superuser update fails
        with self.assertRaises(ProgrammingError) as context:
            with transaction.atomic():
                User.objects.all().update(is_superuser=True)

        self.assertIn("Cannot update multiple users at once", str(context.exception))

        # Test multiple User is_staff update fails
        with self.assertRaises(ProgrammingError) as context:
            with transaction.atomic():
                User.objects.all().update(is_staff=True)

        self.assertIn("Cannot update multiple users at once", str(context.exception))

    def test_general_monitoring_task_pages(self):
        user = User.objects.get(username="tester2")
        user_luovutuspalvelu = User.objects.get(username="kela_luovutuspalvelu")

        index = 0
        for index in range(20):
            Z5_AuditLog.objects.create(
                user=user, successful_get_request_path="/api/v1/toimipaikat/", query_params=f"page={index}"
            )

        with self.assertNoLogs("varda.tasks", level="ERROR"):
            general_monitoring_task.delay()

        index += 1
        Z5_AuditLog.objects.create(user=user, successful_get_request_path="/api/v1/toimipaikat/", query_params=f"page={index}")
        with self.assertLogs("varda.tasks", level="ERROR") as cm:
            general_monitoring_task.delay()
            self.assertEqual(
                cm.output,
                [
                    "ERROR:varda.tasks:The following APIs are browsed through: <QuerySet "
                    "[{'user': 4, 'successful_get_request_path': '/api/v1/toimipaikat/', "
                    "'page_number_count': 21}]>"
                ],
            )

        Z5_AuditLog.objects.filter(user=user).update(user=user_luovutuspalvelu)
        with self.assertNoLogs("varda.tasks", level="ERROR"):
            general_monitoring_task.delay()

    def test_reset_superuser_permissions_task(self):
        user_qs = User.objects.filter(username="tester2")
        user = user_qs.first()
        user.is_superuser = True
        user.save()

        reset_superuser_permissions_task.delay()
        self.assertEqual(user_qs.first().is_superuser, False)
        self.assertEqual(user_qs.first().is_staff, False)

    def test_change_lapsi_henkilo_task_input(self):
        with self.assertLogs("varda.tasks") as cm:
            change_lapsi_henkilo_task.delay([[1, -1]])
            self.assertEqual(
                cm.output,
                [
                    "WARNING:varda.tasks:No Lapsi object with ID 1 or no Henkilo object with ID -1",
                    "WARNING:varda.tasks:IntegrityError for item [1, -1]",
                    "INFO:varda.tasks:Modified 0 Lapsi objects",
                ],
            )

        huoltaja_henkilo = Henkilo.objects.filter(huoltaja__isnull=False).first().id
        tyontekija_henkilo = Henkilo.objects.filter(tyontekijat__isnull=False).first().id
        for henkilo_id in [huoltaja_henkilo, tyontekija_henkilo]:
            henkilo_input = [1, henkilo_id]
            with self.assertLogs("varda.tasks") as cm:
                change_lapsi_henkilo_task.delay([henkilo_input])
                self.assertEqual(
                    cm.output,
                    [
                        f"WARNING:varda.tasks:Henkilo {henkilo_id} cannot be Tyontekija or Huoltaja",
                        f"WARNING:varda.tasks:IntegrityError for item {henkilo_input}",
                        "INFO:varda.tasks:Modified 0 Lapsi objects",
                    ],
                )

        with self.assertLogs("varda.tasks") as cm:
            henkilo_id = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.4338669286936").id
            lapsi_id = Lapsi.objects.get(tunniste="testing-lapsi13").id
            henkilo_input = [lapsi_id, henkilo_id]
            change_lapsi_henkilo_task.delay([henkilo_input])
            self.assertEqual(
                cm.output,
                [
                    f"WARNING:varda.tasks:Henkilo {henkilo_id} cannot have identical Lapsi as {lapsi_id}",
                    f"WARNING:varda.tasks:IntegrityError for item {henkilo_input}",
                    "INFO:varda.tasks:Modified 0 Lapsi objects",
                ],
            )

    def test_change_lapsi_henkilo_task_correct(self):
        lapsi_id = Lapsi.objects.get(tunniste="testing-lapsi3").id
        henkilo_id = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.8925547856499").id

        client = SetUpTestClient("tester2").client()
        assert_status_code(client.get(f"/api/v1/henkilot/{henkilo_id}/"), status.HTTP_404_NOT_FOUND)

        with self.assertLogs("varda.tasks") as cm:
            change_lapsi_henkilo_task.delay([[lapsi_id, henkilo_id]])
            self.assertEqual(cm.output, ["INFO:varda.tasks:Modified 1 Lapsi objects"])

        assert_status_code(client.get(f"/api/v1/henkilot/{henkilo_id}/"), status.HTTP_200_OK)
        self.assertEqual(henkilo_id, Lapsi.objects.get(id=lapsi_id).henkilo_id)

    def test_remove_inactive_tutkintos(self):
        hetu_hash = "b7b9ddd1c5f273c333199cdedff46d291356a4ad0b783218d0868a79f7a3605b"
        tutkintokoodi_is_found = "321901"
        tutkintokoodi_not_found = "613101"

        # Check tutkinto_koodi existence in Palvelussuhde objects
        self.assertTrue(
            Palvelussuhde.objects.filter(
                tyontekija__henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_is_found
            ).exists()
        )
        self.assertFalse(
            Palvelussuhde.objects.filter(
                tyontekija__henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_not_found
            ).exists()
        )

        # check Tutkinto objects are found before removal
        self.assertTrue(
            Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_is_found).exists()
        )
        self.assertTrue(
            Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_not_found).exists()
        )

        remove_inactive_tutkintos()

        # check Tutkinto objects existence after removal (not removed because created within 90d)
        self.assertTrue(
            Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_is_found).exists()
        )
        self.assertTrue(
            Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_not_found).exists()
        )

        # set Tutkintos created time to 91d ago
        datetime_91d_ago = timezone.now() - datetime.timedelta(days=91)
        Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash).update(luonti_pvm=datetime_91d_ago)

        remove_inactive_tutkintos()

        # check Tutkinto objects existence after removal (now removed because created before 90d ago)
        self.assertTrue(
            Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_is_found).exists()
        )
        self.assertFalse(
            Tutkinto.objects.filter(henkilo__henkilotunnus_unique_hash=hetu_hash, tutkinto_koodi=tutkintokoodi_not_found).exists()
        )

        # create Tutkinto without relation to any Palvelussuhde
        henkilo = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.47279949999")
        created_tutkinto = Tutkinto.objects.create(henkilo=henkilo, tutkinto_koodi="321901")
        Tutkinto.objects.filter(id=created_tutkinto.id).update(luonti_pvm=datetime_91d_ago)

        remove_inactive_tutkintos()

        # check created Tutkinto is not removed
        self.assertTrue(Tutkinto.objects.filter(id=created_tutkinto.id).exists())

    def test_add_missing_tukipaatos_paatosmaaras_add_task(self):
        vakajarjestaja = Organisaatio.objects.get(nimi="Tester organisaatio")
        Tukipaatos.objects.create(
            vakajarjestaja=vakajarjestaja,
            paatosmaara=5,
            yksityinen_jarjestaja=False,
            ikaryhma_koodi="IR01",
            tuentaso_koodi="TT01",
            tilastointi_pvm=datetime.date(2024, 5, 31),
            lahdejarjestelma="1",
        )
        self.assertEqual(
            Tukipaatos.objects.filter(vakajarjestaja=vakajarjestaja, tilastointi_pvm=datetime.date(2024, 5, 31)).count(), 1
        )

        # Check added Tukipaatoses after using task-function
        add_missing_tukipaatos_paatosmaaras()
        self.assertEqual(
            Tukipaatos.objects.filter(vakajarjestaja=vakajarjestaja, tilastointi_pvm=datetime.date(2024, 5, 31)).count(), 30
        )

        for yksityinen in (True, False):
            for ikaryhma in ["IR01", "IR02", "IR03", "IR04", "IR05"]:
                for tuentaso in ["TT01", "TT02", "TT03"]:
                    tukipaatoses = Tukipaatos.objects.filter(
                        vakajarjestaja=vakajarjestaja,
                        tilastointi_pvm=datetime.date(2024, 5, 31),
                        yksityinen_jarjestaja=yksityinen,
                        ikaryhma_koodi=ikaryhma,
                        tuentaso_koodi=tuentaso,
                    )
                    self.assertEqual(tukipaatoses.count(), 1)
                    if not (ikaryhma == "IR01" and tuentaso == "TT01"):
                        self.assertEqual(tukipaatoses.first().paatosmaara, 0)

    def test_add_missing_tukipaatos_paatosmaaras_no_add_task(self):
        vakajarjestaja = Organisaatio.objects.get(nimi="Tester organisaatio")
        for yksityinen in (True, False):
            for ikaryhma in ["IR01", "IR02", "IR03", "IR04", "IR05"]:
                for tuentaso in ["TT01", "TT02", "TT03"]:
                    Tukipaatos.objects.create(
                        vakajarjestaja=vakajarjestaja,
                        paatosmaara=5,
                        yksityinen_jarjestaja=yksityinen,
                        ikaryhma_koodi=ikaryhma,
                        tuentaso_koodi=tuentaso,
                        tilastointi_pvm=datetime.date(2024, 6, 1),
                        lahdejarjestelma="1",
                    )
        self.assertEqual(
            Tukipaatos.objects.filter(vakajarjestaja=vakajarjestaja, tilastointi_pvm=datetime.date(2024, 6, 1)).count(), 30
        )

        # check the count is same after using task-function
        add_missing_tukipaatos_paatosmaaras()
        self.assertEqual(
            Tukipaatos.objects.filter(vakajarjestaja=vakajarjestaja, tilastointi_pvm=datetime.date(2024, 6, 1)).count(), 30
        )

    def test_remove_tutkintos_003_if_multiple_tutkinto_koodi(self):
        henkilo = Henkilo.objects.get(henkilo_oid="1.2.987654321")
        self.assertEqual(Tutkinto.objects.filter(henkilo=henkilo).count(), 0)

        org1 = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.34683023489")
        org2 = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.93957375488")
        org3 = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.93957375486")

        # Add Tutkinto objects
        Tutkinto.objects.create(henkilo=henkilo, vakajarjestaja=org1, tutkinto_koodi="003")
        Tutkinto.objects.create(henkilo=henkilo, vakajarjestaja=org2, tutkinto_koodi="003")
        Tutkinto.objects.create(henkilo=henkilo, vakajarjestaja=org2, tutkinto_koodi="321901")
        Tutkinto.objects.create(henkilo=henkilo, vakajarjestaja=org3, tutkinto_koodi="321901")
        Tutkinto.objects.create(henkilo=henkilo, vakajarjestaja=org3, tutkinto_koodi="712104")

        # Check Tutkinto objects after task-function
        remove_tutkintos_003_if_multiple_tutkinto_koodi()

        # Check only 003 tutkinto_koodi is not removed
        tutkinnot_org1 = Tutkinto.objects.filter(henkilo=henkilo, vakajarjestaja=org1)
        self.assertEqual(tutkinnot_org1.count(), 1)
        self.assertEqual(tutkinnot_org1.first().tutkinto_koodi, "003")

        # Check 003 with another tutkinto_koodi is removed
        tutkinnot_org2 = Tutkinto.objects.filter(henkilo=henkilo, vakajarjestaja=org2)
        self.assertEqual(tutkinnot_org2.count(), 1)
        self.assertEqual(tutkinnot_org2.first().tutkinto_koodi, "321901")

        # Check there is no remowal if 003 tutkinto_koodi is missing
        tutkinnot_org3 = Tutkinto.objects.filter(henkilo=henkilo, vakajarjestaja=org3)
        self.assertEqual(tutkinnot_org3.count(), 2)
