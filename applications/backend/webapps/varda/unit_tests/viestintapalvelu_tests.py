import json
from datetime import timedelta

import responses
from django.conf import settings
from django.core import mail

from django.utils import timezone
from rest_framework import status

from varda.constants import MAXIMUM_ASIAKASMAKSU
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.message_type import MessageType
from varda.enums.yhteystieto import YhteystietoTyyppi, Yhteystietoryhmatyyppi
from varda.models import (
    Aikaleima,
    Henkilo,
    Maksutieto,
    Organisaatio,
    Toimipaikka,
    Tyoskentelypaikka,
    Z11_MessageLog,
    Z11_MessageTarget,
    Z6_LastRequest,
    Z6_RequestLog,
    Lapsi,
)
from varda.tasks import update_last_request_table_task
from varda.unit_tests.test_utils import (
    assert_status_code,
    mock_admin_user,
    mock_date_decorator_factory,
    SetUpTestClient,
    RollbackTestCase,
)
from varda.viestintapalvelu import (
    send_no_paakayttaja_message,
    send_no_transfers_message,
    send_puutteelliset_tiedot_message,
    update_message_targets_and_paakayttaja_status,
)


class ViestintapalveluTests(RollbackTestCase):
    fixtures = ["fixture_basics"]

    @responses.activate
    def test_update_message_targets_and_paakayttaja_status(self):
        org_with_paakayttaja = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.57294396385")
        org_without_paakayttaja = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.52966755795")
        org_not_vakajarjestaja = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.2013121014482686198719")

        henkilo_oid = "1.2.246.562.24.10067105747"

        kayttaja_response = [
            {
                "oidHenkilo": henkilo_oid,
                "kayttajaTyyppi": "VIRKAILIJA",
                "organisaatiot": [
                    {
                        "organisaatioOid": org_with_paakayttaja.organisaatio_oid,
                        "kayttooikeudet": [
                            {"palvelu": "VARDA", "oikeus": "HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA"},
                            {"palvelu": "VARDA", "oikeus": "VARDA-PAAKAYTTAJA"},
                        ],
                    },
                    {
                        "organisaatioOid": org_without_paakayttaja.organisaatio_oid,
                        "kayttooikeudet": [{"palvelu": "VARDA", "oikeus": "VARDA-TALLENTAJA"}],
                    },
                    {
                        "organisaatioOid": org_not_vakajarjestaja.organisaatio_oid,
                        "kayttooikeudet": [{"palvelu": "VARDA", "oikeus": "VARDA-PAAKAYTTAJA"}],
                    },
                ],
            }
        ]
        responses.add(
            method=responses.GET,
            status=status.HTTP_200_OK,
            json=kayttaja_response,
            url="https://virkailija.testiopintopolku.fi/kayttooikeus-service/kayttooikeus/kayttaja?palvelu=VARDA&offset=0",
        )

        language = "fi"
        email = "test@example.com"
        yhteystiedot_response = [
            {
                "oidHenkilo": henkilo_oid,
                "asiointikieli": language,
                "yhteystiedotRyhma": [
                    {
                        "id": 500,
                        "ryhmaKuvaus": Yhteystietoryhmatyyppi.TYOOSOITE.value,
                        "yhteystieto": [
                            {"yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_SAHKOPOSTI.value, "yhteystietoArvo": email}
                        ],
                    }
                ],
            }
        ]
        responses.add(
            method=responses.POST,
            status=status.HTTP_200_OK,
            json=yhteystiedot_response,
            url="https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/yhteystiedot",
        )

        update_message_targets_and_paakayttaja_status()

        self.assertEqual(Z11_MessageTarget.objects.count(), 1)

        message_target = Z11_MessageTarget.objects.first()
        self.assertEqual(message_target.organisaatio.id, org_with_paakayttaja.id)
        self.assertEqual(message_target.email, email)
        self.assertEqual(message_target.language, language)
        self.assertEqual(message_target.organisaatio.id, org_with_paakayttaja.id)
        self.assertEqual(message_target.user_type, Kayttajatyyppi.PAAKAYTTAJA.value)

        aikaleima_qs = Aikaleima.objects.filter(avain=AikaleimaAvain.NO_PAAKAYTTAJA.value)
        self.assertEqual(aikaleima_qs.count(), Organisaatio.vakajarjestajat.count() - 1)
        self.assertTrue(aikaleima_qs.filter(organisaatio=org_without_paakayttaja).exists())

        # org_without_paakayttaja gets VARDA-PAAKAYTTAJA user
        kayttaja_response[0]["organisaatiot"][1]["kayttooikeudet"].append({"palvelu": "VARDA", "oikeus": "VARDA-PAAKAYTTAJA"})
        responses.replace(
            method_or_response=responses.GET,
            status=status.HTTP_200_OK,
            json=kayttaja_response,
            url="https://virkailija.testiopintopolku.fi/kayttooikeus-service/kayttooikeus/kayttaja?palvelu=VARDA&offset=0",
        )

        update_message_targets_and_paakayttaja_status()
        self.assertEqual(Z11_MessageTarget.objects.count(), 2)
        self.assertEqual(aikaleima_qs.count(), Organisaatio.vakajarjestajat.count() - 2)
        self.assertFalse(aikaleima_qs.filter(organisaatio=org_without_paakayttaja).exists())

    @responses.activate
    def test_email_selection_logic(self):
        henkilo_oid = "1.2.246.562.24.10067105747"
        organisaatio = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.57294396385")

        kayttaja_response = [
            {
                "oidHenkilo": henkilo_oid,
                "kayttajaTyyppi": "VIRKAILIJA",
                "organisaatiot": [
                    {
                        "organisaatioOid": organisaatio.organisaatio_oid,
                        "kayttooikeudet": [{"palvelu": "VARDA", "oikeus": "VARDA-PAAKAYTTAJA"}],
                    }
                ],
            }
        ]
        responses.add(
            method=responses.GET,
            status=status.HTTP_200_OK,
            json=kayttaja_response,
            url="https://virkailija.testiopintopolku.fi/kayttooikeus-service/kayttooikeus/kayttaja?palvelu=VARDA&offset=0",
        )

        language = "fi"
        email = "test@example.com"
        # ryhmaKuvaus == yhteystietotyyppi2 with the biggest ID should be selected
        yhteystiedot_response = [
            {
                "oidHenkilo": henkilo_oid,
                "asiointikieli": language,
                "yhteystiedotRyhma": [
                    {
                        "id": 50000,
                        "ryhmaKuvaus": Yhteystietoryhmatyyppi.TYOOSOITE.value,
                        "yhteystieto": [
                            {"yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_KATUOSOITE.value, "yhteystietoArvo": "not real"}
                        ],
                    },
                    {
                        "id": 5000,
                        "ryhmaKuvaus": Yhteystietoryhmatyyppi.VTJ_VAKINAINEN_KOTIMAINEN_OSOITE.value,
                        "yhteystieto": [
                            {
                                "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_SAHKOPOSTI.value,
                                "yhteystietoArvo": "error@example.invalid",
                            }
                        ],
                    },
                    {
                        "id": 50,
                        "ryhmaKuvaus": Yhteystietoryhmatyyppi.TYOOSOITE.value,
                        "yhteystieto": [
                            {
                                "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_SAHKOPOSTI.value,
                                "yhteystietoArvo": "error@example.invalid",
                            }
                        ],
                    },
                    {
                        "id": 500,
                        "ryhmaKuvaus": Yhteystietoryhmatyyppi.TYOOSOITE.value,
                        "yhteystieto": [
                            {"yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_SAHKOPOSTI.value, "yhteystietoArvo": email}
                        ],
                    },
                    {
                        "id": 499,
                        "ryhmaKuvaus": Yhteystietoryhmatyyppi.TYOOSOITE.value,
                        "yhteystieto": [
                            {
                                "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_SAHKOPOSTI.value,
                                "yhteystietoArvo": "error@example.invalid",
                            }
                        ],
                    },
                ],
            }
        ]
        responses.add(
            method=responses.POST,
            status=status.HTTP_200_OK,
            json=yhteystiedot_response,
            url="https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/yhteystiedot",
        )

        update_message_targets_and_paakayttaja_status()

        self.assertEqual(Z11_MessageTarget.objects.count(), 1)
        message_target = Z11_MessageTarget.objects.first()
        self.assertEqual(message_target.organisaatio.id, organisaatio.id)
        self.assertEqual(message_target.email, email)

    def test_no_paakayttaja_message(self):
        organisaatio = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.57294396385")
        aikaleima = Aikaleima.objects.create(avain=AikaleimaAvain.NO_PAAKAYTTAJA.value, organisaatio=organisaatio)

        message_count = 0
        message_qs = Z11_MessageLog.objects.filter(
            message_type=MessageType.NO_PAAKAYTTAJA.value, organisaatio=organisaatio
        ).order_by("-timestamp")

        # aikaleima is not older than error_limit
        send_no_paakayttaja_message()
        self.assertEqual(message_qs.count(), 0)

        # aikaleima is older than error_limit
        aikaleima.aikaleima -= timedelta(days=31)
        aikaleima.save()

        send_no_paakayttaja_message()
        message_count += 1

        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(mail.outbox), message_count)
        message = message_qs.first()
        self.assertEqual(message.email, organisaatio.sahkopostiosoite)

        # aikaleima is older than error_limit but message has been sent after frequency_limit
        send_no_paakayttaja_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(mail.outbox), message_count)

        # aikaleima is older than error_limit and message has not been sent after frequency_limit
        message.timestamp -= timedelta(days=31)
        message.save()

        send_no_paakayttaja_message()
        message_count += 1

        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(mail.outbox), message_count)

        # Organisaatio does not have email
        message = message_qs.first()
        message.timestamp -= timedelta(days=31)
        message.save()

        organisaatio.sahkopostiosoite = ""
        organisaatio.save()

        send_no_paakayttaja_message()
        message_count += 1

        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(mail.outbox), message_count)
        message = message_qs.first()
        self.assertEqual(message.email, settings.OPH_EMAIL)

    def test_puutteelliset_tiedot_message(self):
        mock_admin_user("tester2")
        client_admin = SetUpTestClient("tester2").client()

        organisaatio_puutteelliset_list = []
        for organisaatio in Organisaatio.vakajarjestajat.all():
            resp_lapset = client_admin.get(f"/api/v1/vakajarjestajat/{organisaatio.id}/error-report-lapset/")
            assert_status_code(resp_lapset, status.HTTP_200_OK)
            resp_tyontekijat = client_admin.get(f"/api/v1/vakajarjestajat/{organisaatio.id}/error-report-tyontekijat/")
            assert_status_code(resp_tyontekijat, status.HTTP_200_OK)
            resp_toimipaikat = client_admin.get(f"/api/v1/vakajarjestajat/{organisaatio.id}/error-report-toimipaikat/")
            assert_status_code(resp_toimipaikat, status.HTTP_200_OK)

            if (
                json.loads(resp_lapset.content)["results"]
                or json.loads(resp_tyontekijat.content)["results"]
                or json.loads(resp_toimipaikat.content)["results"]
            ):
                organisaatio_puutteelliset_list.append(organisaatio)

        if organisaatio_puutteelliset_list:
            organisaatio = organisaatio_puutteelliset_list[0]
            Z11_MessageTarget.objects.create(
                organisaatio=organisaatio, email="test1@email.com", user_type=Kayttajatyyppi.PAAKAYTTAJA.value
            )
            Z11_MessageTarget.objects.create(
                organisaatio=organisaatio, email="test2@email.com", user_type=Kayttajatyyppi.PAAKAYTTAJA.value
            )
            Z11_MessageTarget.objects.create(
                organisaatio=organisaatio, email="test3@email.com", user_type=Kayttajatyyppi.PAAKAYTTAJA.value
            )

        send_puutteelliset_tiedot_message()

        target_count = 0
        for organisaatio in organisaatio_puutteelliset_list:
            target_count += organisaatio.message_targets.count() or 1

            target_email_set = set(organisaatio.message_targets.values_list("email", flat=True)) or {settings.OPH_EMAIL}
            message_email_set = set(Z11_MessageLog.objects.filter(organisaatio=organisaatio).values_list("email", flat=True))
            self.assertEqual(target_email_set, message_email_set)

        self.assertEqual(Z11_MessageLog.objects.count(), target_count)
        self.assertEqual(len(mail.outbox), target_count)

    @mock_date_decorator_factory("varda.viewsets_reporting.datetime", "2022-02-01")
    def test_puutteelliset_tiedot_message_permissions(self):
        organisaatio = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.57294396385")

        email = "test@example.com"
        Z11_MessageTarget.objects.create(organisaatio=organisaatio, email=email, user_type=Kayttajatyyppi.PAAKAYTTAJA.value)

        message_count = 0
        message_qs = Z11_MessageLog.objects.filter(organisaatio=organisaatio, message_type=MessageType.PUUTTEELLISET_TIEDOT.value)
        send_puutteelliset_tiedot_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Generate error for each puutteellinen category
        # Varhaiskasvatus
        henkilo_lapsi = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.4338669286936")
        hetu = henkilo_lapsi.henkilotunnus
        henkilo_lapsi.henkilotunnus = ""
        henkilo_lapsi.save()

        send_puutteelliset_tiedot_message()
        message_count += 1
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Reset
        henkilo_lapsi.henkilotunnus = hetu
        henkilo_lapsi.save()
        send_puutteelliset_tiedot_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Maksutiedot
        maksutieto = Maksutieto.objects.get(tunniste="testing-maksutieto6")
        maksutieto.asiakasmaksu = MAXIMUM_ASIAKASMAKSU + 5
        maksutieto.save()

        send_puutteelliset_tiedot_message()
        message_count += 1
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Reset
        maksutieto.asiakasmaksu = 50
        maksutieto.save()
        send_puutteelliset_tiedot_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Henkilöstötiedot
        henkilo_tyontekija = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.4645229637988")
        hetu = henkilo_tyontekija.henkilotunnus
        henkilo_tyontekija.henkilotunnus = ""
        henkilo_tyontekija.save()

        send_puutteelliset_tiedot_message()
        message_count += 1
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Reset
        henkilo_tyontekija.henkilotunnus = hetu
        henkilo_tyontekija.save()
        send_puutteelliset_tiedot_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Toimipaikka varhaiskasvatus
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid="1.2.246.562.10.6727877596658")
        toimipaikka.varhaiskasvatuspaikat = 0
        toimipaikka.save()

        send_puutteelliset_tiedot_message()
        message_count += 1
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Reset
        toimipaikka.varhaiskasvatuspaikat = 100
        toimipaikka.save()
        send_puutteelliset_tiedot_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Toimipaikka henkilöstö
        tyoskentelypaikka = Tyoskentelypaikka.objects.get(tunniste="testing-tyoskentelypaikka6-1")
        tyoskentelypaikka.toimipaikka = Toimipaikka.objects.get(organisaatio_oid="1.2.246.562.10.2565458382544")
        tyoskentelypaikka.save()

        send_puutteelliset_tiedot_message()
        message_count += 1
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # Reset
        tyoskentelypaikka.toimipaikka = toimipaikka
        tyoskentelypaikka.save()
        send_puutteelliset_tiedot_message()
        self.assertEqual(message_qs.count(), message_count)
        self.assertEqual(len(list(filter(lambda email: organisaatio.nimi in email.body, mail.outbox))), message_count)

        # All emails were sent to the right address
        self.assertEqual(message_qs.filter(email=email).count(), message_count)

    def test_no_transfers_message(self):
        # Kunnallinen and yksityinen Organisaatio have different error_limit values
        for yritysmuoto, error_limit in (
            (
                "41",
                30,
            ),
            (
                "16",
                180,
            ),
        ):
            client = SetUpTestClient("tester10").client()

            organisaatio = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.57294396385")

            email = "test@example.com"
            Z11_MessageTarget.objects.create(organisaatio=organisaatio, email=email, user_type=Kayttajatyyppi.PAAKAYTTAJA.value)

            lapsi = Lapsi.objects.get(tunniste="testing-lapsi13")
            tyoskentelypaikka = Tyoskentelypaikka.objects.get(tunniste="testing-tyoskentelypaikka6-1")

            message_qs = Z11_MessageLog.objects.filter(organisaatio=organisaatio, message_type=MessageType.NO_TRANSFERS.value)

            # Update Organisaatio yritysmuoto
            organisaatio.yritysmuoto = yritysmuoto
            organisaatio.save()

            message_count = 0

            # No transfers but Organisaatio has been created after error_limit
            send_no_transfers_message()
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # No transfers and Organisaatio has been created after error_limit
            organisaatio.luonti_pvm -= timedelta(days=error_limit + 1)
            organisaatio.save()
            send_no_transfers_message()
            message_count += 1
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # Failed vaka transfer but message has been recently sent
            assert_status_code(client.patch(f"/api/v1/lapset/{lapsi.id}/", {"tunniste": "%&#?!"}), status.HTTP_400_BAD_REQUEST)
            update_last_request_table_task(init=True)
            send_no_transfers_message()
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # Failed vaka transfer
            old_date = timezone.now() - timedelta(days=365)
            message_qs.update(timestamp=old_date)
            send_no_transfers_message()
            message_count += 1
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # Failed vaka and henkilosto transfer
            Z6_LastRequest.objects.all().delete()
            assert_status_code(
                client.patch(f"/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka.id}/", {"paattymis_pvm": "testitunniste"}),
                status.HTTP_400_BAD_REQUEST,
            )
            update_last_request_table_task(init=True)
            message_qs.update(timestamp=old_date)
            send_no_transfers_message()
            message_count += 1
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # Successful vaka transfer
            Z6_LastRequest.objects.all().delete()
            assert_status_code(client.patch(f"/api/v1/lapset/{lapsi.id}/", {"tunniste": "testitunniste"}), status.HTTP_200_OK)
            update_last_request_table_task(init=True)
            message_qs.update(timestamp=old_date)
            send_no_transfers_message()
            message_count += 1
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # Successful henkilosto transfer
            Z6_LastRequest.objects.all().delete()
            Z6_RequestLog.objects.all().delete()
            assert_status_code(
                client.patch(f"/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka.id}/", {"tunniste": "testitunniste"}),
                status.HTTP_200_OK,
            )
            update_last_request_table_task(init=True)
            message_qs.update(timestamp=old_date)
            send_no_transfers_message()
            message_count += 1
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # Successful vaka and henkilosto transfers
            Z6_LastRequest.objects.all().delete()
            Z6_RequestLog.objects.all().delete()
            assert_status_code(client.patch(f"/api/v1/lapset/{lapsi.id}/", {"tunniste": "testitunniste"}), status.HTTP_200_OK)
            assert_status_code(
                client.patch(f"/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka.id}/", {"tunniste": "testitunniste"}),
                status.HTTP_200_OK,
            )
            update_last_request_table_task(init=True)
            message_qs.update(timestamp=old_date)
            send_no_transfers_message()
            self.assertEqual(message_qs.count(), message_count)
            self.assertEqual(len(mail.outbox), message_count)

            # All emails were sent to the right address
            self.assertEqual(message_qs.filter(email=email).count(), message_count)

            # Reset DB and test outbox
            self.reset_db()
            mail.outbox = []
