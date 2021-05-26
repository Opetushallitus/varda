import datetime
import json

from django.db.models import Q
from django.test import TestCase
from rest_framework import serializers, status

from varda.models import (VakaJarjestaja, Toimipaikka, Varhaiskasvatussuhde, Varhaiskasvatuspaatos, Maksutieto, Lapsi,
                          Henkilo, ToiminnallinenPainotus, KieliPainotus, PidempiPoissaolo, Tyoskentelypaikka,
                          Palvelussuhde, Tutkinto, Tyontekija, Taydennyskoulutus, TilapainenHenkilosto)
from varda.organisation_transformations import transfer_toimipaikat_to_vakajarjestaja
from varda.permissions import object_ids_organization_has_permissions_to
from varda.unit_tests.test_utils import assert_status_code, post_henkilo_to_get_permissions, SetUpTestClient


class OrganisationTransformationsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_toimipaikat_transfer_simple(self):
        old_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'

        old_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=old_vakajarjestaja_oid)
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)

        permission_id_list_nested_before_old = self._get_id_list_nested_for_vakajarjestaja(old_vakajarjestaja)
        permission_id_list_nested_before_new = self._get_id_list_nested_for_vakajarjestaja(new_vakajarjestaja)

        # Assert permissions before transfer
        self._assert_organization_has_permissions(old_vakajarjestaja_oid, permission_id_list_nested_before_old, has_permissions=True)
        self._assert_organization_has_permissions(new_vakajarjestaja_oid, permission_id_list_nested_before_old, has_permissions=False)

        # Transfer Toimipaikat of VakaJarjestaja 1.2.246.562.10.57294396385 to
        # VakaJarjestaja 1.2.246.562.10.52966755795
        transfer_toimipaikat_to_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Assert permissions after transfer
        self._assert_organization_has_permissions(old_vakajarjestaja_oid, permission_id_list_nested_before_old, has_permissions=False)
        self._assert_organization_has_permissions(new_vakajarjestaja_oid, permission_id_list_nested_before_old, has_permissions=True)

        # Assert new_vakajarjestaja has correct number of related objects
        permission_id_list_nested_after_new = self._get_id_list_nested_for_vakajarjestaja(new_vakajarjestaja)
        for index in range(0, len(permission_id_list_nested_before_old)):
            self.assertEqual(len(permission_id_list_nested_after_new[index]),
                             len(permission_id_list_nested_before_new[index]) + len(permission_id_list_nested_before_old[index]))

        # Assert old_vakajarjestaja does not have related objects
        permission_id_list_nested_after_old = self._get_id_list_nested_for_vakajarjestaja(old_vakajarjestaja)
        for permission_list in permission_id_list_nested_after_old:
            self.assertEqual(0, len(permission_list))

    def test_transfer_new_vakajarjestaja_has_existing_lapsi(self):
        old_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'

        old_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=old_vakajarjestaja_oid)
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)

        lapsi_henkilo_oid = '1.2.246.562.24.6779627637492'
        lapsi_henkilo = Henkilo.objects.get(henkilo_oid=lapsi_henkilo_oid)
        old_lapsi_id = Lapsi.objects.get(henkilo__henkilo_oid=lapsi_henkilo_oid, vakatoimija=old_vakajarjestaja).id
        maksutieto = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=old_lapsi_id).first()

        client = SetUpTestClient('tester11').client()
        post_henkilo_to_get_permissions(client, henkilo_id=lapsi_henkilo.id)
        lapsi = {
            'henkilo': '/api/v1/henkilot/{0}/'.format(lapsi_henkilo.id),
            'vakatoimija_oid': new_vakajarjestaja_oid,
            'lahdejarjestelma': '1',
        }
        lapsi_resp = client.post('/api/v1/lapset/', lapsi)
        lapsi_qs = Lapsi.objects.filter(id=json.loads(lapsi_resp.content)['id'])
        assert_status_code(lapsi_resp, status.HTTP_201_CREATED)

        vakapaatos = {
            'lapsi': json.loads(lapsi_resp.content)['url'],
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2020-03-01',
            'alkamis_pvm': '2020-03-01',
            'lahdejarjestelma': '1',
        }
        vakapaatos_resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(vakapaatos_resp, status.HTTP_201_CREATED)

        new_vakajarjestaja_toimipaikka_oid = '1.2.246.562.10.9625978384762'
        vakasuhde = {
            'toimipaikka_oid': new_vakajarjestaja_toimipaikka_oid,
            'varhaiskasvatuspaatos': json.loads(vakapaatos_resp.content)['url'],
            'alkamis_pvm': '2020-03-20',
            'lahdejarjestelma': '1',
        }
        vakasuhde_resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(vakasuhde_resp, status.HTTP_201_CREATED)

        # Transfer Toimipaikat of VakaJarjestaja 1.2.246.562.10.57294396385 to
        # VakaJarjestaja 1.2.246.562.10.52966755795
        transfer_toimipaikat_to_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Assert old lapsi object doesn't exist
        self.assertFalse(Lapsi.objects.filter(id=old_lapsi_id).exists())

        # Assert new vakajarjestaja has only one lapsi linked to henkilo 1.2.246.562.24.6779627637492
        self.assertEqual(1, Lapsi.objects.filter(henkilo=lapsi_henkilo, vakatoimija=new_vakajarjestaja).count())

        # Assert it has two different vakapaatos (existing and transferred)
        self.assertEqual(lapsi_qs.first().varhaiskasvatuspaatokset.count(), 2)

        # Assert Maksutieto has been transferred to the new Lapsi
        self.assertEqual(len(set(maksutieto.huoltajuussuhteet.values_list('lapsi', flat=True))), 1)
        self.assertEqual(maksutieto.huoltajuussuhteet.values_list('lapsi', flat=True)[0], lapsi_qs.first().id)

    def test_transfer_toimipaikka_has_paos_lapsi(self):
        paos_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        oma_vakajarjestaja_oid = '1.2.246.562.10.52966755795'
        toimipaikka_oid = '1.2.246.562.10.6727877596658'
        paos_henkilo_oid = '1.2.246.562.24.58672764848'

        paos_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=paos_vakajarjestaja_oid)
        oma_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=oma_vakajarjestaja_oid)
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid)
        paos_henkilo = Henkilo.objects.get(henkilo_oid=paos_henkilo_oid)

        # Create paos-toiminta and paos-lapsi
        toimipaikka.jarjestamismuoto_koodi = ['jm03']
        toimipaikka.save()

        client_paos_toiminta_1 = SetUpTestClient('tester10').client()
        paos_toiminta = {
            'oma_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(paos_vakajarjestaja.id),
            'paos_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(oma_vakajarjestaja.id)
        }

        resp_paos_toiminta_1 = client_paos_toiminta_1.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp_paos_toiminta_1, status.HTTP_201_CREATED)

        client_paos_toiminta_2 = SetUpTestClient('tester11').client()
        paos_toiminta = {
            'oma_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(oma_vakajarjestaja.id),
            'paos_toimipaikka': '/api/v1/toimipaikat/{0}/'.format(toimipaikka.id)
        }

        resp_paos_toiminta_2 = client_paos_toiminta_2.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp_paos_toiminta_2, status.HTTP_201_CREATED)

        client_paos_lapsi = SetUpTestClient('tester11').client()
        post_henkilo_to_get_permissions(client_paos_lapsi, henkilo_id=paos_henkilo.id)
        paos_lapsi = {
            'henkilo': '/api/v1/henkilot/{0}/'.format(paos_henkilo.id),
            'oma_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(oma_vakajarjestaja.id),
            'paos_organisaatio': '/api/v1/vakajarjestajat/{0}/'.format(paos_vakajarjestaja.id),
            'lahdejarjestelma': '1'
        }
        resp_paos_lapsi = client_paos_lapsi.post('/api/v1/lapset/', paos_lapsi)
        paos_lapsi_id = json.loads(resp_paos_lapsi.content)['id']
        assert_status_code(resp_paos_lapsi, status.HTTP_201_CREATED)

        paos_vakapaatos = {
            'lapsi': json.loads(resp_paos_lapsi.content)['url'],
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm03',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2020-04-01',
            'alkamis_pvm': '2020-04-01',
            'lahdejarjestelma': '1'
        }
        resp_paos_vakapaatos = client_paos_lapsi.post('/api/v1/varhaiskasvatuspaatokset/', paos_vakapaatos)
        assert_status_code(resp_paos_vakapaatos, status.HTTP_201_CREATED)

        paos_vakasuhde = {
            'toimipaikka_oid': toimipaikka_oid,
            'varhaiskasvatuspaatos': json.loads(resp_paos_vakapaatos.content)['url'],
            'alkamis_pvm': '2020-04-20',
            'lahdejarjestelma': '1'
        }
        paos_vakasuhde_resp = client_paos_lapsi.post('/api/v1/varhaiskasvatussuhteet/', paos_vakasuhde)
        assert_status_code(paos_vakasuhde_resp, status.HTTP_201_CREATED)

        with self.assertRaises(serializers.ValidationError):
            # Transfer Toimipaikat of paos_vakajarjestaja to oma_vakajarjestaja
            transfer_toimipaikat_to_vakajarjestaja(oma_vakajarjestaja, paos_vakajarjestaja)

        # However, we can transfer Toimipaikat of oma_vakajarjestaja to paos_vakajarjestaja
        transfer_toimipaikat_to_vakajarjestaja(paos_vakajarjestaja, oma_vakajarjestaja)

        # Assert oma_vakajarjestaja has only permissions to the created PAOS-lapsi
        self.assertCountEqual((paos_lapsi_id,),
                              object_ids_organization_has_permissions_to(oma_vakajarjestaja_oid, Lapsi))

    def test_transfer_new_vakajarjestaja_has_existing_tyontekija(self):
        old_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'

        old_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=old_vakajarjestaja_oid)
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)

        tyontekija_henkilo_oid = '1.2.246.562.24.4645229637988'
        tyontekija_henkilo = Henkilo.objects.get(henkilo_oid=tyontekija_henkilo_oid)
        old_tyontekija_id = Tyontekija.objects.get(henkilo=tyontekija_henkilo, vakajarjestaja=old_vakajarjestaja).id
        tutkinto_code = '321901'
        old_tutkinto_id = Tutkinto.objects.get(henkilo=tyontekija_henkilo, vakajarjestaja=old_vakajarjestaja,
                                               tutkinto_koodi=tutkinto_code).id
        taydennyskoulutus = Taydennyskoulutus.objects.get(tunniste='testing-taydennyskoulutus3')

        client = SetUpTestClient('tester11').client()
        post_henkilo_to_get_permissions(client, henkilo_id=tyontekija_henkilo.id)

        tyontekija = {
            'henkilo': f'/api/v1/henkilot/{tyontekija_henkilo.id}/',
            'vakajarjestaja_oid': new_vakajarjestaja_oid,
            'lahdejarjestelma': '1',
        }
        tyontekija_resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        tyontekija_qs = Tyontekija.objects.filter(id=json.loads(tyontekija_resp.content)['id'])
        assert_status_code(tyontekija_resp, status.HTTP_201_CREATED)

        tutkinto = {
            'vakajarjestaja_oid': new_vakajarjestaja_oid,
            'henkilo_oid': tyontekija_henkilo_oid,
            'tutkinto_koodi': tutkinto_code
        }

        tutkinto_resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(tutkinto_resp, status.HTTP_201_CREATED)

        palvelussuhde = {
            'tyontekija': json.loads(tyontekija_resp.content)['url'],
            'tyosuhde_koodi': 1,
            'tyoaika_koodi': 1,
            'tutkinto_koodi': tutkinto_code,
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-09-01',
            'lahdejarjestelma': '1',
        }
        palvelussuhde_resp = client.post('/api/henkilosto/v1/palvelussuhteet/', palvelussuhde)
        assert_status_code(palvelussuhde_resp, status.HTTP_201_CREATED)

        new_vakajarjestaja_toimipaikka_oid = '1.2.246.562.10.9625978384762'
        tyoskentelypaikka = {
            'toimipaikka_oid': new_vakajarjestaja_toimipaikka_oid,
            'palvelussuhde': json.loads(palvelussuhde_resp.content)['url'],
            'alkamis_pvm': '2020-09-20',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }
        tyoskentelypaikka_resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)
        assert_status_code(tyoskentelypaikka_resp, status.HTTP_201_CREATED)

        # Transfer Toimipaikat of VakaJarjestaja 1.2.246.562.10.57294396385 to
        # VakaJarjestaja 1.2.246.562.10.52966755795
        transfer_toimipaikat_to_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Assert old Tyontekija object doesn't exist
        self.assertFalse(Tyontekija.objects.filter(id=old_tyontekija_id).exists())

        # Assert old Tutkinto object doesn't exist
        self.assertFalse(Tutkinto.objects.filter(id=old_tutkinto_id).exists())

        # Assert new_vakajarjestaja has only one Tyontekija linked to Henkilo 1.2.246.562.24.4645229637988
        self.assertEqual(1, Tyontekija.objects.filter(henkilo=tyontekija_henkilo,
                                                      vakajarjestaja=new_vakajarjestaja).count())

        # Assert it has two different Palvelussuhde (existing and transferred)
        self.assertEqual(tyontekija_qs.first().palvelussuhteet.count(), 2)

        # Assert existing Tyontekija has been added to Taydennyskoulutus
        self.assertEqual(len(set(taydennyskoulutus.taydennyskoulutukset_tyontekijat
                                 .values_list('tyontekija', flat=True))), 1)
        self.assertEqual(taydennyskoulutus.tyontekijat.all()[0].id, tyontekija_qs.first().id)

    def test_transfer_new_vakajarjestaja_has_existing_tilapainen_henkilosto(self):
        old_vakajarjestaja_oid = '1.2.246.562.10.57294396385'
        new_vakajarjestaja_oid = '1.2.246.562.10.52966755795'

        old_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=old_vakajarjestaja_oid)
        new_vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=new_vakajarjestaja_oid)

        old_tilapainen_henkilosto = TilapainenHenkilosto.objects.get(tunniste='testing-tilapainenhenkilosto2')
        old_tilapainen_henkilosto.kuukausi = datetime.date(year=2020, month=9, day=1)
        old_tilapainen_henkilosto.save()
        existing_tilapainen_henkilosto = TilapainenHenkilosto.objects.get(tunniste='testing-tilapainenhenkilosto3')
        existing_tilapainen_henkilosto.kuukausi = datetime.date(year=2020, month=9, day=2)
        existing_tilapainen_henkilosto.save()

        transfer_toimipaikat_to_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)

        # Old TilapainenHenkilosto object has been deleted
        self.assertFalse(TilapainenHenkilosto.objects.filter(id=old_tilapainen_henkilosto.id).exists())

        # Information has been united
        tilapainen_henkilosto = TilapainenHenkilosto.objects.get(id=existing_tilapainen_henkilosto.id)
        self.assertEqual(tilapainen_henkilosto.tuntimaara,
                         old_tilapainen_henkilosto.tuntimaara + existing_tilapainen_henkilosto.tuntimaara)
        self.assertEqual(tilapainen_henkilosto.tyontekijamaara,
                         old_tilapainen_henkilosto.tyontekijamaara + existing_tilapainen_henkilosto.tyontekijamaara)

    def _get_id_list_nested_for_vakajarjestaja(self, vakajarjestaja):
        toimipaikka_qs = Toimipaikka.objects.filter(vakajarjestaja=vakajarjestaja).distinct()
        permission_id_list_nested = [list(toimipaikka_qs.values_list('id', flat=True))]

        toiminnallinen_painotus_qs = ToiminnallinenPainotus.objects.filter(toimipaikka__in=toimipaikka_qs)
        permission_id_list_nested.append(list(toiminnallinen_painotus_qs.values_list('id', flat=True)))

        kielipainotus_qs = KieliPainotus.objects.filter(toimipaikka__in=toimipaikka_qs)
        permission_id_list_nested.append(list(kielipainotus_qs.values_list('id', flat=True)))

        henkilo_qs = Henkilo.objects.filter(Q(lapsi__vakatoimija=vakajarjestaja) |
                                            Q(tyontekijat__vakajarjestaja=vakajarjestaja)).distinct()
        permission_id_list_nested.append(list(henkilo_qs.values_list('id', flat=True)))

        lapsi_qs = Lapsi.objects.filter(vakatoimija=vakajarjestaja)
        permission_id_list_nested.append(list(lapsi_qs.values_list('id', flat=True)))

        vakapaatos_qs = Varhaiskasvatuspaatos.objects.filter(lapsi__in=lapsi_qs)
        permission_id_list_nested.append(list(vakapaatos_qs.values_list('id', flat=True)))

        vakasuhde_qs = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__in=vakapaatos_qs)
        permission_id_list_nested.append(list(vakasuhde_qs.values_list('id', flat=True)))

        maksutieto_qs = Maksutieto.objects.filter(huoltajuussuhteet__lapsi__in=lapsi_qs).distinct()
        permission_id_list_nested.append(list(maksutieto_qs.values_list('id', flat=True)))

        tyontekija_qs = Tyontekija.objects.filter(vakajarjestaja=vakajarjestaja)
        permission_id_list_nested.append(list(tyontekija_qs.values_list('id', flat=True)))

        tutkinto_qs = Tutkinto.objects.filter(vakajarjestaja=vakajarjestaja)
        permission_id_list_nested.append(list(tutkinto_qs.values_list('id', flat=True)))

        palvelussuhde_qs = Palvelussuhde.objects.filter(tyontekija__in=tyontekija_qs)
        permission_id_list_nested.append(list(palvelussuhde_qs.values_list('id', flat=True)))

        tyoskentelypaikka_qs = Tyoskentelypaikka.objects.filter(palvelussuhde__in=palvelussuhde_qs)
        permission_id_list_nested.append(list(tyoskentelypaikka_qs.values_list('id', flat=True)))

        pidempi_poissaolo_qs = PidempiPoissaolo.objects.filter(palvelussuhde__in=palvelussuhde_qs)
        permission_id_list_nested.append(list(pidempi_poissaolo_qs.values_list('id', flat=True)))

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(tyontekijat__vakajarjestaja=vakajarjestaja).distinct()
        permission_id_list_nested.append(list(taydennyskoulutus_qs.values_list('id', flat=True)))

        tilapainen_henkilosto_qs = TilapainenHenkilosto.objects.filter(vakajarjestaja=vakajarjestaja)
        permission_id_list_nested.append(list(tilapainen_henkilosto_qs.values_list('id', flat=True)))

        return permission_id_list_nested

    def _assert_organization_has_permissions(self, organisaatio_oid, permission_id_list_nested, has_permissions=True):
        model_list = (Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, Lapsi, Varhaiskasvatuspaatos,
                      Varhaiskasvatussuhde, Maksutieto, Tyontekija, Tutkinto, Palvelussuhde, Tyoskentelypaikka,
                      PidempiPoissaolo, Taydennyskoulutus, TilapainenHenkilosto,)
        existing_permission_id_list_nested = [object_ids_organization_has_permissions_to(organisaatio_oid, model)
                                              for model in model_list]

        assert_function = self.assertTrue if has_permissions else self.assertFalse

        for index in range(0, len(model_list)):
            permissions = permission_id_list_nested[index]
            existing_permissions = existing_permission_id_list_nested[index]

            if not permissions:
                continue

            assert_function(set(permissions).issubset(existing_permissions))
