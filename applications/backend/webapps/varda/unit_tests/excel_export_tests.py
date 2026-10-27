import datetime
import os
import tempfile

from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings

from varda.clients.aws_s3_client import Client as S3Client
from varda.constants import TYOSUHDE_KOODI_MAARAAIKAINEN
from varda.enums.koodistot import Koodistot
from varda.enums.reporting import ReportStatus
from varda.enums.supported_language import SupportedLanguage
from varda.enums.translation import Translation as T
from varda.excel_export import create_mass_excel_report_task
from varda.excel_export.base import BaseExcelReportGenerator
from varda.excel_export.constants import ExcelReportType
from varda.excel_export.reports import REPORT_GENERATORS
from varda.excel_export.reports.toimipaikat import (
    ToimipaikatVoimassaReportGenerator,
    create_toimipaikat_voimassa_json_from_data,
    load_toimipaikat_voimassa_data,
)
from varda.excel_export.reports.tyontekijatiedot import (
    TyontekijatiedotMaaraaikaisetVoimassaReportGenerator,
    TyontekijatiedotVoimassaReportGenerator,
    _massahaku_snapshot,
    create_tyontekijatiedot_json_from_data,
    create_tyontekijatiedot_voimassa_json_from_data,
    load_tyontekijatiedot_data,
)
from varda.excel_export.storage import (
    _delete_toimipaikat_s3_artifacts,
    _delete_tyontekijatiedot_s3_artifacts,
    delete_excel_reports_earlier_than,
    get_excel_local_file_path,
    get_toimipaikat_json_nimet,
    get_tyontekijatiedot_json_nimet,
    read_toimipaikat_json,
    read_tyontekijatiedot_json,
    read_tyontekijatiedot_json_access,
    store_toimipaikat_json,
    store_tyontekijatiedot_json,
)
from varda.models import (
    Henkilo,
    KieliPainotus,
    Organisaatio,
    Palvelussuhde,
    PaosToiminta,
    ToiminnallinenPainotus,
    Toimipaikka,
    Tyontekija,
    Tyoskentelypaikka,
)

REPORT_TYPE = "TEST_REPORT_TYPE"


class _TestReportGenerator(BaseExcelReportGenerator):
    filename_key = T.EXCEL_FILENAME_VAKATIEDOT_VOIMASSA

    def _create_excel_report(self):
        pass


class ExcelReportGeneratorDatabaseAliasTests(SimpleTestCase):
    @staticmethod
    def _report():
        return SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=None,
            toimipaikka=None,
        )

    def test_excel_report_generator_uses_default_database_alias(self):
        report = self._report()

        generator = _TestReportGenerator(report)

        self.assertEqual(generator.data_db_alias, DEFAULT_DB_ALIAS)

    def test_excel_report_generator_uses_explicit_database_alias(self):
        report = self._report()

        generator = _TestReportGenerator(report, data_db_alias="reader")

        self.assertEqual(generator.data_db_alias, "reader")

    def test_tyontekijatiedot_excel_renderer_uses_materialized_data(self):
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=None,
            toimipaikka=None,
        )
        report_data = {
            "tyontekijat": [],
            "koodistot": {koodisto.value: [] for koodisto in Koodistot},
            "henkilo_id_oid_set": set(),
        }
        generator = TyontekijatiedotVoimassaReportGenerator(report, report_data=report_data)
        with (
            mock.patch.object(generator, "_get_tyontekijatiedot_queryset", side_effect=AssertionError),
            mock.patch.object(generator, "_add_worksheet") as add_worksheet,
            mock.patch.object(generator, "_write_headers"),
        ):
            generator._create_excel_report()

        add_worksheet.assert_called_once()

    def test_tyontekijatiedot_json_uses_requested_report_type(self):
        report_data = {"tyontekijat": [], "koodistot": {koodisto.value: [] for koodisto in Koodistot}}

        json_data = create_tyontekijatiedot_json_from_data(
            report_data, ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value
        )

        self.assertEqual(json_data["raportti"], ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value)
        self.assertEqual(json_data["schema_version"], 1)
        self.assertEqual(json_data["tyontekijat"], [])

    def test_toimipaikat_json_nests_painotukset_without_duplicate_toimipaikat(self):
        report_data = {
            "koodistot": {
                name: []
                for name in (
                    "kunta",
                    "kasvatusopillinen_jarjestelma",
                    "toiminnallinen_painotus",
                    "kieli",
                    "kielipainotustyyppi",
                    "toimintamuoto",
                    "jarjestamismuoto",
                    "lahdejarjestelma",
                )
            },
            "toimipaikat": [
                {
                    "nimi": "Toimipaikka",
                    "oid": "1.2.3",
                    "id": 1,
                    "lahdejarjestelma": None,
                    "tunniste": None,
                    "palveluntuottaja": None,
                    "alkamis_pvm": datetime.date(2026, 1, 1),
                    "paattymis_pvm": None,
                    "kasvatusopillinen_jarjestelma": None,
                    "toimintamuoto": None,
                    "toimintakieli": [],
                    "jarjestamismuoto": [],
                    "varhaiskasvatuspaikat": 10,
                    "kunta": None,
                    "kayntiosoite": "Katu 1",
                    "kayntiosoite_postinumero": "00100",
                    "kayntiosoite_postitoimipaikka": "Helsinki",
                    "postiosoite": "Katu 1",
                    "postinumero": "00100",
                    "postitoimipaikka": "Helsinki",
                    "puhelinnumero": "010",
                    "sahkopostiosoite": "test@example.com",
                    "painotukset": [
                        {
                            "id": 2,
                            "lahdejarjestelma": None,
                            "tunniste": None,
                            "toiminnallinen_painotus": "1",
                            "kielipainotus": None,
                            "kielipainotuksen_tyyppi": None,
                            "alkamis_pvm": datetime.date(2026, 1, 1),
                            "paattymis_pvm": None,
                        }
                    ],
                }
            ],
        }

        json_data = create_toimipaikat_voimassa_json_from_data(report_data)

        self.assertEqual(len(json_data["toimipaikat"]), 1)
        self.assertEqual(len(json_data["toimipaikat"][0]["painotukset"]), 1)
        self.assertEqual(json_data["toimipaikat"][0]["painotukset"][0]["id"], 2)


class ToimipaikatJsonStorageTests(TestCase):
    def test_toimipaikat_json_artifacts_round_trip(self):
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TOIMIPAIKAT_VOIMASSA.value)
        json_data = {"raportti": report.report_type, "schema_version": 1, "toimipaikat": []}

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            override_settings(EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=True, ENVIRONMENT_TYPE=None),
        ):
            store_toimipaikat_json(report, json_data)

            self.assertTrue(os.path.exists(get_toimipaikat_json_nimet(report)["local"]))
            self.assertEqual(read_toimipaikat_json(report), json_data)


class ToimipaikatVoimassaDatabaseTests(TestCase):
    fixtures = ["fixture_basics"]

    def setUp(self):
        self.organisaatio = Organisaatio.objects.create(
            nimi="Massahaku järjestäjä",
            y_tunnus="1234567-9",
            organisaatio_oid="1.2.246.562.10.99999999990",
            kunta_koodi="091",
            postiosoite="Katu 1",
            postinumero="00100",
            postitoimipaikka="Helsinki",
            integraatio_organisaatio=[],
        )
        self.paos_organisaatio = Organisaatio.objects.create(
            nimi="PAOS tuottaja",
            y_tunnus="1234567-8",
            organisaatio_oid="1.2.246.562.10.99999999991",
            kunta_koodi="091",
            postiosoite="Katu 1",
            postinumero="00100",
            postitoimipaikka="Helsinki",
            integraatio_organisaatio=[],
        )

    def _create_toimipaikka(self, name, start_date, end_date=None, vakajarjestaja=None):
        return Toimipaikka.objects.create(
            vakajarjestaja=vakajarjestaja or self.organisaatio,
            nimi=name,
            organisaatio_oid=f"1.2.246.562.10.{abs(hash(name)) % 1000000000:09d}",
            kayntiosoite="Testikatu 1",
            kayntiosoite_postinumero="00100",
            kayntiosoite_postitoimipaikka="Helsinki",
            postiosoite="Testikatu 1",
            postinumero="00100",
            postitoimipaikka="Helsinki",
            kunta_koodi="091",
            puhelinnumero="091234567",
            sahkopostiosoite="test@example.com",
            kasvatusopillinen_jarjestelma_koodi="1",
            toimintamuoto_koodi="1",
            toimintakieli_koodi=["fi"],
            jarjestamismuoto_koodi=["1"],
            varhaiskasvatuspaikat=10,
            alkamis_pvm=start_date,
            paattymis_pvm=end_date,
            lahdejarjestelma="20",
        )

    def _report(self, toimipaikka=None):
        return SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=self.organisaatio,
            toimipaikka=toimipaikka,
            target_date=datetime.date(2026, 8, 10),
            target_date_secondary=None,
        )

    def test_json_and_excel_share_three_painotus_rows_and_filter_scope(self):
        toimipaikka = self._create_toimipaikka("A Painotukset", datetime.date(2020, 1, 1))
        ToiminnallinenPainotus.objects.create(
            toimipaikka=toimipaikka,
            toimintapainotus_koodi="1",
            alkamis_pvm=datetime.date(2020, 1, 1),
            lahdejarjestelma="20",
        )
        ToiminnallinenPainotus.objects.create(
            toimipaikka=toimipaikka,
            toimintapainotus_koodi="2",
            alkamis_pvm=datetime.date(2020, 1, 1),
            lahdejarjestelma="20",
        )
        KieliPainotus.objects.create(
            toimipaikka=toimipaikka,
            kielipainotus_koodi="fi",
            kielipainotustyyppi_koodi="1",
            alkamis_pvm=datetime.date(2020, 1, 1),
            lahdejarjestelma="20",
        )
        self._create_toimipaikka("Expired", datetime.date(2020, 1, 1), datetime.date(2026, 8, 9))
        paos_toimipaikka = self._create_toimipaikka("Z PAOS", datetime.date(2020, 1, 1), vakajarjestaja=self.paos_organisaatio)
        PaosToiminta.objects.create(
            oma_organisaatio=self.organisaatio,
            paos_organisaatio=self.paos_organisaatio,
            paos_toimipaikka=paos_toimipaikka,
            voimassa_kytkin=True,
        )
        report = self._report()
        generator = ToimipaikatVoimassaReportGenerator(report)

        report_data = load_toimipaikat_voimassa_data(generator)
        json_data = create_toimipaikat_voimassa_json_from_data(report_data)

        self.assertEqual([item["nimi"] for item in json_data["toimipaikat"]], ["A Painotukset", "Z PAOS"])
        self.assertEqual(
            len(next(item for item in json_data["toimipaikat"] if item["nimi"] == "A Painotukset")["painotukset"]), 3
        )

        def capture_excel_rows(report_generator, report_data=None):
            rows = []
            report_generator.report_data = report_data
            report_generator._add_worksheet = mock.Mock()
            report_generator._write_headers = mock.Mock()
            report_generator._write_row = lambda sheet, index, values: rows.append(values)
            report_generator._create_excel_report()
            return rows

        actual_rows = capture_excel_rows(ToimipaikatVoimassaReportGenerator(report))
        materialized_rows = capture_excel_rows(ToimipaikatVoimassaReportGenerator(report), report_data)
        self.assertEqual(materialized_rows, actual_rows)
        self.assertEqual(len(materialized_rows), 4)
        self.assertEqual([row[0] for row in materialized_rows], ["A Painotukset", "A Painotukset", "A Painotukset", "Z PAOS"])
        painotus_ids = [painotus["id"] for painotus in report_data["toimipaikat"][0]["painotukset"]]
        self.assertEqual([row[23] for row in materialized_rows[:3]], painotus_ids)
        self.assertEqual(len(materialized_rows[3]), 23)

        filtered_generator = ToimipaikatVoimassaReportGenerator(self._report(toimipaikka=toimipaikka))
        filtered_data = load_toimipaikat_voimassa_data(filtered_generator)
        self.assertEqual([item["id"] for item in filtered_data["toimipaikat"]], [toimipaikka.id])

    def test_excel_keeps_one_row_for_toimipaikka_without_painotukset(self):
        toimipaikka = self._create_toimipaikka("No painotukset", datetime.date(2020, 1, 1))
        generator = ToimipaikatVoimassaReportGenerator(self._report())
        report_data = load_toimipaikat_voimassa_data(generator)
        rows = []
        generator.report_data = report_data
        generator._add_worksheet = mock.Mock()
        generator._write_headers = mock.Mock()
        generator._write_row = lambda sheet, index, values: rows.append(values)

        generator._create_excel_report()

        row = next(row for row in rows if row[0] == toimipaikka.nimi)
        self.assertEqual(len(rows), 1)
        self.assertEqual(row[0:3], [toimipaikka.nimi, toimipaikka.organisaatio_oid, toimipaikka.id])

    def test_expired_painotukset_are_preserved_in_excel_and_json(self):
        target_date = datetime.date(2026, 8, 10)
        toimipaikka = self._create_toimipaikka("Expired painotukset", datetime.date(2020, 1, 1))
        active_toiminnallinen = ToiminnallinenPainotus.objects.create(
            toimipaikka=toimipaikka,
            toimintapainotus_koodi="1",
            alkamis_pvm=datetime.date(2026, 1, 1),
            paattymis_pvm=datetime.date(2026, 12, 31),
            lahdejarjestelma="20",
        )
        expired_toiminnallinen = ToiminnallinenPainotus.objects.create(
            toimipaikka=toimipaikka,
            toimintapainotus_koodi="2",
            alkamis_pvm=datetime.date(2025, 1, 1),
            paattymis_pvm=datetime.date(2026, 8, 9),
            lahdejarjestelma="20",
        )
        active_kieli = KieliPainotus.objects.create(
            toimipaikka=toimipaikka,
            kielipainotus_koodi="fi",
            kielipainotustyyppi_koodi="1",
            alkamis_pvm=datetime.date(2026, 1, 1),
            paattymis_pvm=datetime.date(2026, 12, 31),
            lahdejarjestelma="20",
        )
        expired_kieli = KieliPainotus.objects.create(
            toimipaikka=toimipaikka,
            kielipainotus_koodi="sv",
            kielipainotustyyppi_koodi="1",
            alkamis_pvm=datetime.date(2025, 1, 1),
            paattymis_pvm=datetime.date(2026, 8, 9),
            lahdejarjestelma="20",
        )
        report = self._report()
        report.target_date = target_date

        def capture_rows(report_generator, report_data=None):
            rows = []
            report_generator.report_data = report_data
            report_generator._add_worksheet = mock.Mock()
            report_generator._write_headers = mock.Mock()
            report_generator._write_row = lambda sheet, index, values: rows.append(values)
            report_generator._create_excel_report()
            return rows

        original_rows = capture_rows(ToimipaikatVoimassaReportGenerator(report))
        report_data = load_toimipaikat_voimassa_data(ToimipaikatVoimassaReportGenerator(report))
        materialized_rows = capture_rows(ToimipaikatVoimassaReportGenerator(report), report_data)
        json_data = create_toimipaikat_voimassa_json_from_data(report_data)

        self.assertCountEqual(original_rows, materialized_rows)

        def excel_painotus(row):
            if row[26] is not None:
                return ("toiminnallinen", row[23], row[29], row[30])
            return ("kieli", row[23], row[29], row[30])

        expected_excel_painotukset = [
            ("toiminnallinen", active_toiminnallinen.id, active_toiminnallinen.alkamis_pvm, active_toiminnallinen.paattymis_pvm),
            (
                "toiminnallinen",
                expired_toiminnallinen.id,
                expired_toiminnallinen.alkamis_pvm,
                expired_toiminnallinen.paattymis_pvm,
            ),
            ("kieli", active_kieli.id, active_kieli.alkamis_pvm, active_kieli.paattymis_pvm),
            ("kieli", expired_kieli.id, expired_kieli.alkamis_pvm, expired_kieli.paattymis_pvm),
        ]
        self.assertCountEqual([excel_painotus(row) for row in original_rows], expected_excel_painotukset)
        self.assertCountEqual([excel_painotus(row) for row in materialized_rows], expected_excel_painotukset)

        self.assertEqual(len(json_data["toimipaikat"]), 1)
        self.assertEqual(len(json_data["toimipaikat"][0]["painotukset"]), 4)

        def json_painotus(painotus):
            painotus_type = "toiminnallinen" if painotus["toiminnallinen_painotus"] else "kieli"
            return (painotus_type, painotus["id"], painotus["alkamis_pvm"], painotus["paattymis_pvm"])

        expected_json_painotukset = [
            ("toiminnallinen", active_toiminnallinen.id, "2026-01-01", "2026-12-31"),
            ("toiminnallinen", expired_toiminnallinen.id, "2025-01-01", "2026-08-09"),
            ("kieli", active_kieli.id, "2026-01-01", "2026-12-31"),
            ("kieli", expired_kieli.id, "2025-01-01", "2026-08-09"),
        ]
        self.assertCountEqual(
            [json_painotus(painotus) for painotus in json_data["toimipaikat"][0]["painotukset"]],
            expected_json_painotukset,
        )


class TyontekijatiedotMaaraaikaisetFilterTests(TestCase):
    fixtures = ["fixture_basics"]

    def test_filter_includes_fixed_term_relationships_and_preserves_date_boundaries(self):
        organisaatio = Organisaatio.objects.create(
            nimi="Testiorganisaatio",
            y_tunnus="1234567-8",
            organisaatio_oid="1.2.246.562.10.99999999999",
            kunta_koodi="091",
            postiosoite="Testikatu 1",
            postinumero="00100",
            postitoimipaikka="Helsinki",
            integraatio_organisaatio=[],
        )
        henkilo = Henkilo.objects.create(
            henkilo_oid="1.2.246.562.24.99999999999999999999",
            etunimet="Testi",
            kutsumanimi="Testi",
            sukunimi="Työntekijä",
        )
        tyontekija = Tyontekija.objects.create(henkilo=henkilo, vakajarjestaja=organisaatio, lahdejarjestelma="20")
        toimipaikka = Toimipaikka.objects.create(
            vakajarjestaja=organisaatio,
            nimi="Testitoimipaikka",
            kayntiosoite="Testikatu 2",
            kayntiosoite_postinumero="00100",
            kayntiosoite_postitoimipaikka="Helsinki",
            postiosoite="Testikatu 2",
            postinumero="00100",
            postitoimipaikka="Helsinki",
            kunta_koodi="091",
            puhelinnumero="091234567",
            sahkopostiosoite="testitoimipaikka@example.com",
            kasvatusopillinen_jarjestelma_koodi="1",
            toimintamuoto_koodi="1",
            toimintakieli_koodi=["fi"],
            jarjestamismuoto_koodi=["1"],
            varhaiskasvatuspaikat=10,
            alkamis_pvm=datetime.date(2020, 1, 1),
            lahdejarjestelma="20",
        )
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=organisaatio,
            toimipaikka=None,
            target_date=datetime.date(2026, 8, 10),
            target_date_secondary=datetime.date(2026, 8, 20),
        )
        relationships = {
            "qualifying": (datetime.date(2026, 8, 10), datetime.date(2026, 8, 20), TYOSUHDE_KOODI_MAARAAIKAINEN),
            "secondary_date_boundary": (
                datetime.date(2026, 8, 20),
                datetime.date(2026, 8, 20),
                TYOSUHDE_KOODI_MAARAAIKAINEN,
            ),
            "permanent": (datetime.date(2026, 8, 10), None, "1"),
            "starts_after_range": (datetime.date(2026, 8, 21), None, TYOSUHDE_KOODI_MAARAAIKAINEN),
            "ends_before_range": (datetime.date(2026, 8, 1), datetime.date(2026, 8, 9), TYOSUHDE_KOODI_MAARAAIKAINEN),
        }
        created_relationships = {}
        for name, (start_date, end_date, relationship_type) in relationships.items():
            palvelussuhde = Palvelussuhde.objects.create(
                tyontekija=tyontekija,
                tyosuhde_koodi=relationship_type,
                tyoaika_koodi="1",
                tutkinto_koodi="381241",
                tyoaika_viikossa=Decimal("10.00"),
                alkamis_pvm=start_date,
                paattymis_pvm=end_date,
                lahdejarjestelma="20",
            )
            Tyoskentelypaikka.objects.create(
                palvelussuhde=palvelussuhde,
                toimipaikka=toimipaikka,
                tehtavanimike_koodi="84724",
                kelpoisuus_kytkin=False,
                kiertava_tyontekija_kytkin=False,
                alkamis_pvm=start_date,
                paattymis_pvm=end_date,
                lahdejarjestelma="20",
            )
            created_relationships[name] = palvelussuhde

        generator = TyontekijatiedotMaaraaikaisetVoimassaReportGenerator(report)
        filtered_ids = set(
            generator._get_tyontekijatiedot_queryset(generator._get_palvelussuhde_filter()).values_list("id", flat=True)
        )

        self.assertEqual(
            filtered_ids,
            {
                created_relationships["qualifying"].id,
                created_relationships["secondary_date_boundary"].id,
            },
        )


class S3UploadTests(SimpleTestCase):
    def test_shared_upload_does_not_override_bucket_encryption(self):
        client = S3Client.__new__(S3Client)
        client.client = mock.Mock()

        with tempfile.NamedTemporaryFile() as file:
            client.upload_fileobj(file.name, "reports", "report.json.gz")

        client.client.upload_fileobj.assert_called_once_with(mock.ANY, "reports", "report.json.gz")

    def test_tyontekijatiedot_maaraaikaiset_artifact_names_are_report_specific(self):
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value)

        self.assertEqual(
            get_tyontekijatiedot_json_nimet(report),
            {
                "object": "massahaut/123/tyontekijatiedot_maaraaikaiset_voimassa.json.gz",
                "access_object": "massahaut/123/tyontekijatiedot_maaraaikaiset_voimassa.access.json.gz",
                "local": f"{settings.EXCEL_PATH}massahaku_123_tyontekijatiedot_maaraaikaiset_voimassa.json.gz",
                "access_local": f"{settings.EXCEL_PATH}massahaku_123_tyontekijatiedot_maaraaikaiset_voimassa.access.json.gz",
            },
        )

    def test_tyontekijatiedot_voimassa_artifact_names_are_report_specific(self):
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value)

        self.assertEqual(
            get_tyontekijatiedot_json_nimet(report),
            {
                "object": "massahaut/123/tyontekijatiedot_voimassa.json.gz",
                "access_object": "massahaut/123/tyontekijatiedot_voimassa.access.json.gz",
                "local": f"{settings.EXCEL_PATH}massahaku_123_tyontekijatiedot_voimassa.json.gz",
                "access_local": f"{settings.EXCEL_PATH}massahaku_123_tyontekijatiedot_voimassa.access.json.gz",
            },
        )

    def test_toimipaikat_artifact_has_no_access_sidecar(self):
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TOIMIPAIKAT_VOIMASSA.value)

        self.assertEqual(
            get_toimipaikat_json_nimet(report),
            {
                "object": "massahaut/123/toimipaikat_voimassa.json.gz",
                "local": f"{settings.EXCEL_PATH}massahaku_123_toimipaikat_voimassa.json.gz",
            },
        )

    def test_tyontekijatiedot_s3_cleanup_attempts_both_json_artifacts(self):
        report = SimpleNamespace(id=123, report_type="TYONTEKIJATIEDOT_VOIMASSA")
        client = mock.Mock()
        client.delete_file.side_effect = [False, True]

        self.assertFalse(_delete_tyontekijatiedot_s3_artifacts(client, report))

        self.assertEqual(client.delete_file.call_count, 2)

    def test_toimipaikat_s3_cleanup_deletes_only_json_artifact(self):
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TOIMIPAIKAT_VOIMASSA.value)
        client = mock.Mock()

        self.assertTrue(_delete_toimipaikat_s3_artifacts(client, report))

        client.delete_file.assert_called_once_with("massahaut/123/toimipaikat_voimassa.json.gz")


class LocalReportCleanupTests(SimpleTestCase):
    @staticmethod
    def _report():
        return mock.Mock(id=123, report_type="TYONTEKIJATIEDOT_VOIMASSA")

    def _delete_report(self, report, temp_dir):
        with (
            override_settings(EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=True, ENVIRONMENT_TYPE=None),
            mock.patch("varda.excel_export.storage.S3Client", return_value=None),
            mock.patch("varda.excel_export.storage.Z8_ExcelReport.objects.filter", return_value=[report]),
        ):
            delete_excel_reports_earlier_than(datetime.datetime.now())

    def test_cleanup_does_not_instantiate_s3_client(self):
        with (
            override_settings(PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=True, ENVIRONMENT_TYPE=None),
            mock.patch("varda.excel_export.storage.S3Client") as client_class,
            mock.patch("varda.excel_export.storage.Z8_ExcelReport.objects.filter", return_value=[]),
        ):
            delete_excel_reports_earlier_than(datetime.datetime.now())

        client_class.assert_not_called()

    def test_missing_excel_still_deletes_json_artifacts(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            for path in (
                get_tyontekijatiedot_json_nimet(report)["local"],
                get_tyontekijatiedot_json_nimet(report)["access_local"],
            ):
                open(path, "w").close()

            self._delete_report(report, temp_dir)

            self.assertFalse(os.path.exists(get_tyontekijatiedot_json_nimet(report)["local"]))
            self.assertFalse(os.path.exists(get_tyontekijatiedot_json_nimet(report)["access_local"]))
            report.delete.assert_not_called()

    def test_missing_json_artifact_does_not_prevent_other_json_cleanup(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            access_path = get_tyontekijatiedot_json_nimet(report)["access_local"]
            open(access_path, "w").close()

            self._delete_report(report, temp_dir)

            self.assertFalse(os.path.exists(access_path))

    def test_cleanup_removes_maaraaikaiset_json_artifacts(self):
        report = mock.Mock(
            id=123,
            report_type=ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value,
        )
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            for path in (
                get_tyontekijatiedot_json_nimet(report)["local"],
                get_tyontekijatiedot_json_nimet(report)["access_local"],
            ):
                open(path, "w").close()

            self._delete_report(report, temp_dir)

            self.assertFalse(os.path.exists(get_tyontekijatiedot_json_nimet(report)["local"]))
            self.assertFalse(os.path.exists(get_tyontekijatiedot_json_nimet(report)["access_local"]))

    def test_cleanup_removes_toimipaikat_json_artifact(self):
        report = mock.Mock(id=123, report_type=ExcelReportType.TOIMIPAIKAT_VOIMASSA.value)
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            path = get_toimipaikat_json_nimet(report)["local"]
            open(path, "w").close()

            self._delete_report(report, temp_dir)

            self.assertFalse(os.path.exists(path))

    def test_successful_cleanup_deletes_report_record(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            for path in (
                get_excel_local_file_path(report),
                get_tyontekijatiedot_json_nimet(report)["local"],
                get_tyontekijatiedot_json_nimet(report)["access_local"],
            ):
                open(path, "w").close()

            self._delete_report(report, temp_dir)

            report.delete.assert_called_once_with()


class TyontekijaReportDatabaseAliasTests(TestCase):
    def test_koodisto_query_uses_data_database_alias(self):
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=None,
            toimipaikka=None,
        )
        generator = _TestReportGenerator(report, data_db_alias="reader")

        queryset = mock.MagicMock()
        queryset.filter.return_value = queryset
        queryset.annotate.return_value = queryset
        queryset.values.return_value = queryset
        queryset.__iter__.return_value = iter(())

        with (
            mock.patch("varda.excel_export.base.Z2_Code.objects.using", return_value=queryset) as using_mock,
            mock.patch("varda.excel_export.base.Z2_Code.objects.filter", return_value=queryset),
        ):
            generator._get_koodisto_with_translations(Koodistot.tutkinto_koodit.value)

        using_mock.assert_called_once_with("reader")

    def test_tyontekija_queryset_prefetches_report_relationships(self):
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=SimpleNamespace(id=123),
            toimipaikka=None,
        )
        generator = TyontekijatiedotVoimassaReportGenerator(report, data_db_alias="reader")
        queryset = mock.MagicMock()
        queryset.filter.return_value = queryset
        queryset.distinct.return_value = queryset
        queryset.select_related.return_value = queryset
        queryset.prefetch_related.return_value = queryset
        queryset.order_by.return_value = queryset

        with mock.patch("varda.excel_export.reports.tyontekijatiedot.Palvelussuhde.objects.using", return_value=queryset):
            generator._get_tyontekijatiedot_queryset()

        prefetches = queryset.prefetch_related.call_args.args
        self.assertEqual(
            {prefetch.prefetch_through for prefetch in prefetches},
            {"tyoskentelypaikat", "pidemmatpoissaolot", "tyontekija__henkilo__tutkinnot"},
        )
        tyoskentelypaikka_prefetch = next(prefetch for prefetch in prefetches if prefetch.prefetch_through == "tyoskentelypaikat")
        self.assertIn("toimipaikka", tyoskentelypaikka_prefetch.queryset.query.select_related)


class TyontekijaReportJsonTests(SimpleTestCase):
    def test_tyontekijatiedot_json_groups_tyoskentelypaikat_and_poissaolot_without_multiplication(self):
        def related_manager(items):
            class RelatedManager:
                def all(self):
                    return self

                def filter(self, **kwargs):
                    return self

                def order_by(self, *args):
                    return self

                def __iter__(self):
                    return iter(items)

            return RelatedManager()

        organisaatio = SimpleNamespace(id=123)
        henkilo = SimpleNamespace(
            id=10,
            henkilo_oid="1.2.246.562.24.10000921949",
            etunimet="Ritva",
            sukunimi="Aaltio",
            henkilotunnus="encrypted",
            turvakielto=False,
            tutkinnot=related_manager(
                [
                    SimpleNamespace(
                        vakajarjestaja_id=123,
                        tutkinto_koodi="381241",
                        luonti_pvm=datetime.datetime(2024, 1, 1),
                    )
                ]
            ),
        )
        toimipaikka = SimpleNamespace(nimi="DH Elka", organisaatio_oid="1.2.246.562.10.45694690657", id=4492)
        tyoskentelypaikat = [
            SimpleNamespace(
                id=1541802,
                tunniste=None,
                kiertava_tyontekija_kytkin=False,
                toimipaikka=toimipaikka,
                tehtavanimike_koodi="84724",
                kelpoisuus_kytkin=False,
                alkamis_pvm=datetime.date(2023, 10, 19),
                paattymis_pvm=datetime.date(2026, 12, 31),
            ),
            SimpleNamespace(
                id=1541803,
                tunniste="wp-2",
                kiertava_tyontekija_kytkin=True,
                toimipaikka=None,
                tehtavanimike_koodi="84724",
                kelpoisuus_kytkin=True,
                alkamis_pvm=datetime.date(2023, 11, 19),
                paattymis_pvm=None,
            ),
        ]
        poissaolot = [
            SimpleNamespace(
                id=1867217,
                tunniste="1867217",
                alkamis_pvm=datetime.date(2023, 8, 29),
                paattymis_pvm=datetime.date(2025, 11, 17),
            ),
            SimpleNamespace(
                id=1867218,
                tunniste=None,
                alkamis_pvm=datetime.date(2024, 8, 29),
                paattymis_pvm=None,
            ),
        ]
        tyontekija = SimpleNamespace(
            id=46371,
            henkilo=henkilo,
            sahkopostiosoite="email-4811@example.com",
            lahdejarjestelma="20",
        )
        palvelussuhde = SimpleNamespace(
            id=884240,
            tunniste=None,
            tyontekija=tyontekija,
            tyosuhde_koodi="1",
            tyoaika_koodi="1",
            tutkinto_koodi="381241",
            tyoaika_viikossa=Decimal("13.00"),
            alkamis_pvm=datetime.date(2023, 8, 22),
            paattymis_pvm=datetime.date(2026, 12, 31),
            tyoskentelypaikat=related_manager(tyoskentelypaikat),
            pidemmatpoissaolot=related_manager(poissaolot),
            _report_tyoskentelypaikat=tyoskentelypaikat,
            _report_pidemmatpoissaolot=poissaolot,
        )
        query = SimpleNamespace(iterator=lambda chunk_size: iter([palvelussuhde]))
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=organisaatio,
            toimipaikka=None,
            target_date=datetime.date(2026, 8, 10),
        )
        koodistot = {
            Koodistot.tutkinto_koodit.value: [{"code_value": "381241", "name": "Kasvatus- ja ohjausalan perustutkinto"}],
            Koodistot.tyosuhde_koodit.value: [{"code_value": "1", "name": "Toistaiseksi voimassaoleva"}],
            Koodistot.tyoaika_koodit.value: [{"code_value": "1", "name": "Kokoaikainen"}],
            Koodistot.tehtavanimike_koodit.value: [{"code_value": "84724", "name": "Varhaiskasvatuksen lastenhoitaja"}],
            Koodistot.lahdejarjestelma_koodit.value: [{"code_value": "20", "name": "Mepco Public"}],
        }

        with (
            mock.patch.object(TyontekijatiedotVoimassaReportGenerator, "_get_tyontekijatiedot_queryset", return_value=query),
            mock.patch.object(
                TyontekijatiedotVoimassaReportGenerator,
                "_get_koodisto_with_translations",
                side_effect=lambda koodisto: koodistot[koodisto],
            ),
            mock.patch("varda.excel_export.reports.tyontekijatiedot.decrypt_henkilotunnus", return_value="090593-6006"),
        ):
            generator = TyontekijatiedotVoimassaReportGenerator(report)
            report_data = load_tyontekijatiedot_data(generator, generator._get_palvelussuhde_filter())
            result = create_tyontekijatiedot_voimassa_json_from_data(report_data)

        tyontekija = result["tyontekijat"][0]
        palvelussuhde = tyontekija["palvelussuhteet"][0]
        self.assertEqual(len(result["tyontekijat"]), 1)
        self.assertEqual(tyontekija["tyontekija_id"], 46371)
        self.assertFalse(tyontekija["turvakielto"])
        self.assertEqual(palvelussuhde["viikkotyoaika"], 13.0)
        self.assertEqual(len(palvelussuhde["tyoskentelypaikat"]), 2)
        self.assertEqual(len(palvelussuhde["poissaolot"]), 2)
        self.assertEqual(palvelussuhde["tyoskentelypaikat"][0]["alkamis_pvm"], "2023-10-19")
        self.assertIsNone(palvelussuhde["tyoskentelypaikat"][1]["toimipaikka"])


class TyontekijatiedotVoimassaSnapshotTests(TransactionTestCase):
    def test_tyontekijatiedot_voimassa_snapshot_uses_repeatable_read(self):
        with _massahaku_snapshot(DEFAULT_DB_ALIAS):
            with connection.cursor() as cursor:
                cursor.execute("SHOW TRANSACTION ISOLATION LEVEL")
                isolation_level = cursor.fetchone()[0]

        self.assertEqual(isolation_level, "repeatable read")


class MassExcelReportTaskTests(TestCase):
    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_uses_writer_control_record_and_reader_generator(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.PENDING.value, report_type=REPORT_TYPE)
        generator_mock = mock.Mock()

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch.dict("varda.excel_export.REPORT_GENERATORS", {REPORT_TYPE: generator_mock}),
        ):
            using_mock.return_value.filter.return_value.first.return_value = report
            generator = generator_mock.return_value

            create_mass_excel_report_task.run(report_id)

        using_mock.assert_called_once_with(DEFAULT_DB_ALIAS)
        using_mock.return_value.filter.assert_called_once_with(id=report_id)
        generator_mock.assert_called_once_with(report, data_db_alias="reader")
        generator.generate.assert_called_once_with()

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_generates_tyontekija_json_snapshot(self):
        report_id = 123
        report_type = ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value
        report = SimpleNamespace(
            id=report_id,
            status=ReportStatus.PENDING.value,
            report_type=report_type,
            save=mock.Mock(side_effect=lambda **kwargs: events.append(f"status -> {report.status}")),
        )
        report_data = {
            "tyontekijat": [],
            "koodistot": {koodisto.value: [] for koodisto in Koodistot},
            "henkilo_id_oid_set": set(),
        }
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        events = []
        generator_mock = mock.Mock()

        @mock.patch("varda.excel_export._massahaku_snapshot")
        def run_task(snapshot_mock):
            snapshot_mock.return_value.__enter__.side_effect = lambda: events.append("begin")
            snapshot_mock.return_value.__exit__.side_effect = lambda *args: events.append("commit")
            return create_mass_excel_report_task.run(report_id)

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch("varda.excel_export.load_tyontekijatiedot_data", return_value=report_data) as json_mock,
            mock.patch("varda.excel_export.store_tyontekijatiedot_json") as store_mock,
            mock.patch.dict("varda.excel_export.REPORT_GENERATORS", {report_type: generator_mock}),
        ):
            using_mock.return_value.filter.return_value.first.return_value = report
            json_mock.side_effect = lambda *args, **kwargs: (events.append("load") or report_data)
            store_mock.side_effect = lambda *args, **kwargs: events.append("store")
            generator_mock.return_value.generate.side_effect = lambda *args, **kwargs: events.append("render")

            run_task()

        json_mock.assert_called_once_with(generator_mock.return_value, generator_mock.return_value._get_palvelussuhde_filter())
        store_mock.assert_called_once_with(report, json_data, mock.ANY)
        self.assertFalse(hasattr(report, "json_data"))
        generator_mock.assert_called_once_with(report, data_db_alias="reader")
        generator_mock.return_value.generate.assert_called_once_with()
        self.assertEqual(events, ["status -> CREATING", "begin", "load", "commit", "store", "render"])

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_generates_toimipaikat_json_and_excel_from_shared_data(self):
        report_id = 123
        report_type = ExcelReportType.TOIMIPAIKAT_VOIMASSA.value
        report = SimpleNamespace(
            id=report_id,
            status=ReportStatus.PENDING.value,
            report_type=report_type,
            save=mock.Mock(side_effect=lambda **kwargs: events.append(f"status -> {report.status}")),
        )
        report_data = {"toimipaikat": [], "koodistot": {}}
        json_data = {"raportti": report_type, "schema_version": 1, "toimipaikat": []}
        events = []
        generator_mock = mock.Mock()

        @mock.patch("varda.excel_export._massahaku_snapshot")
        def run_task(snapshot_mock):
            snapshot_mock.return_value.__enter__.side_effect = lambda: events.append("begin")
            snapshot_mock.return_value.__exit__.side_effect = lambda *args: events.append("commit")
            return create_mass_excel_report_task.run(report_id)

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch("varda.excel_export.load_toimipaikat_voimassa_data", return_value=report_data) as load_mock,
            mock.patch("varda.excel_export.create_toimipaikat_voimassa_json_from_data", return_value=json_data),
            mock.patch("varda.excel_export.store_toimipaikat_json") as store_mock,
            mock.patch.dict("varda.excel_export.REPORT_GENERATORS", {report_type: generator_mock}),
        ):
            using_mock.return_value.filter.return_value.first.return_value = report
            load_mock.side_effect = lambda *args, **kwargs: (events.append("load") or report_data)
            store_mock.side_effect = lambda *args, **kwargs: events.append("store")
            generator_mock.return_value.generate.side_effect = lambda: events.append("render")

            run_task()

        generator_mock.assert_called_once_with(report, data_db_alias="reader")
        load_mock.assert_called_once_with(generator_mock.return_value)
        store_mock.assert_called_once_with(report, json_data)
        self.assertIs(generator_mock.return_value.report_data, report_data)
        generator_mock.return_value.generate.assert_called_once_with()
        self.assertEqual(events, ["status -> CREATING", "begin", "load", "commit", "store", "render"])

    def test_tyontekijatiedot_json_snapshot_is_gzip_artifact_not_database_data(self):
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value)
        access_data = {(10, "1.2.246.562.10.1")}

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            override_settings(EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=True, ENVIRONMENT_TYPE=None),
        ):
            store_tyontekijatiedot_json(report, json_data, access_data)

            artifact_path = get_tyontekijatiedot_json_nimet(report)["local"]
            self.assertTrue(os.path.exists(artifact_path))
            self.assertEqual(os.stat(artifact_path).st_mode & 0o777, 0o600)
            self.assertEqual(read_tyontekijatiedot_json(report), json_data)
            self.assertEqual(read_tyontekijatiedot_json_access(report), list(access_data))
            self.assertTrue(os.path.exists(get_tyontekijatiedot_json_nimet(report)["access_local"]))

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_uses_maaraaikaiset_generator_and_shared_data(self):
        report = SimpleNamespace(
            id=123,
            status=ReportStatus.PENDING.value,
            report_type=ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value,
            save=mock.Mock(),
        )
        report_data = {
            "tyontekijat": [],
            "koodistot": {koodisto.value: [] for koodisto in Koodistot},
            "henkilo_id_oid_set": set(),
        }
        json_data = {
            "raportti": ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value,
            "schema_version": 1,
            "tyontekijat": [],
        }
        generator_mock = mock.Mock()

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch("varda.excel_export._massahaku_snapshot"),
            mock.patch("varda.excel_export.load_tyontekijatiedot_data", return_value=report_data) as load_mock,
            mock.patch("varda.excel_export.create_tyontekijatiedot_json_from_data", return_value=json_data),
            mock.patch("varda.excel_export.store_tyontekijatiedot_json") as store_mock,
            mock.patch.dict(
                "varda.excel_export.REPORT_GENERATORS",
                {ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value: generator_mock},
            ),
        ):
            using_mock.return_value.filter.return_value.first.return_value = report
            create_mass_excel_report_task.run(report.id)

        generator_mock.assert_called_once_with(report, data_db_alias="reader")
        load_mock.assert_called_once_with(generator_mock.return_value, generator_mock.return_value._get_palvelussuhde_filter())
        store_mock.assert_called_once_with(report, json_data, mock.ANY)
        self.assertIs(generator_mock.return_value.report_data, report_data)
        generator_mock.return_value.generate.assert_called_once_with()

    def test_tyontekijatiedot_maaraaikaiset_json_snapshot_round_trip(self):
        json_data = {
            "raportti": ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value,
            "schema_version": 1,
            "tyontekijat": [],
        }
        report = SimpleNamespace(
            id=123,
            report_type=ExcelReportType.TYONTEKIJATIEDOT_MAARAAIKAISET_VOIMASSA.value,
        )
        access_data = {(10, "1.2.246.562.10.1")}

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            override_settings(EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=True, ENVIRONMENT_TYPE=None),
        ):
            store_tyontekijatiedot_json(report, json_data, access_data)

            self.assertEqual(read_tyontekijatiedot_json(report), json_data)
            self.assertEqual(read_tyontekijatiedot_json_access(report), list(access_data))

    def test_tyontekijatiedot_json_snapshot_is_uploaded_to_report_bucket(self):
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value)
        access_data = {(10, "1.2.246.562.10.1")}

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            override_settings(
                EXCEL_PATH=f"{temp_dir}/",
                PRODUCTION_ENV=False,
                QA_ENV=False,
                DEV_ENV=True,
                ENVIRONMENT_TYPE="env-varda-prod",
                S3_EXCEL_REPORTS="excel-reports",
            ),
            mock.patch("varda.excel_export.storage.S3Client") as client_class,
        ):
            client_class.return_value.upload_fileobj.return_value = True

            store_tyontekijatiedot_json(report, json_data, access_data)

            self.assertEqual(client_class.call_count, 2)
            client_class.assert_any_call("dev-excel-reports")
            client_class.return_value.upload_fileobj.assert_any_call(
                mock.ANY,
                "dev-excel-reports",
                get_tyontekijatiedot_json_nimet(report)["object"],
            )
            client_class.return_value.upload_fileobj.assert_any_call(
                mock.ANY,
                "dev-excel-reports",
                get_tyontekijatiedot_json_nimet(report)["access_object"],
            )
            self.assertFalse(os.path.exists(get_tyontekijatiedot_json_nimet(report)["local"]))

    def test_tyontekijatiedot_json_snapshot_uses_environment_report_buckets(self):
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value)
        access_data = {(10, "1.2.246.562.10.1")}

        environments = (
            ("dev", {"PRODUCTION_ENV": False, "QA_ENV": False, "DEV_ENV": True, "ENVIRONMENT_TYPE": "env-varda-prod"}),
            ("qa", {"PRODUCTION_ENV": False, "QA_ENV": True, "DEV_ENV": False, "ENVIRONMENT_TYPE": "env-varda-testing"}),
            ("prod", {"PRODUCTION_ENV": True, "QA_ENV": False, "DEV_ENV": False, "ENVIRONMENT_TYPE": "env-varda-prod"}),
        )
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch("varda.excel_export.storage.S3Client") as client_class:
            client_class.return_value.upload_fileobj.return_value = True
            for environment, settings_override in environments:
                with (
                    self.subTest(environment=environment),
                    override_settings(
                        EXCEL_PATH=f"{temp_dir}/",
                        S3_EXCEL_REPORTS="excel-reports",
                        **settings_override,
                    ),
                ):
                    store_tyontekijatiedot_json(report, json_data, access_data)

                self.assertEqual(client_class.call_args_list[-2].args, (f"{environment}-excel-reports",))
                self.assertEqual(client_class.call_args_list[-1].args, (f"{environment}-excel-reports",))

    def test_tyontekijatiedot_json_snapshot_uses_local_storage_without_s3(self):
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        report = SimpleNamespace(id=123, report_type=ExcelReportType.TYONTEKIJATIEDOT_VOIMASSA.value)
        access_data = {(10, "1.2.246.562.10.1")}

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            override_settings(
                EXCEL_PATH=f"{temp_dir}/",
                PRODUCTION_ENV=False,
                QA_ENV=False,
                DEV_ENV=True,
                ENVIRONMENT_TYPE=None,
            ),
            mock.patch("varda.excel_export.storage.S3Client") as client_class,
        ):
            store_tyontekijatiedot_json(report, json_data, access_data)

            self.assertEqual(read_tyontekijatiedot_json(report), json_data)
            self.assertEqual(read_tyontekijatiedot_json_access(report), list(access_data))
            client_class.assert_not_called()

    def test_mass_excel_report_task_does_not_generate_non_pending_report(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.FINISHED.value, report_type=REPORT_TYPE)
        generator_mock = mock.Mock()

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch.dict("varda.excel_export.REPORT_GENERATORS", {REPORT_TYPE: generator_mock}),
        ):
            using_mock.return_value.filter.return_value.first.return_value = report

            create_mass_excel_report_task.run(report_id)

        using_mock.assert_called_once_with(DEFAULT_DB_ALIAS)
        using_mock.return_value.filter.assert_called_once_with(id=report_id)
        generator_mock.assert_not_called()

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_marks_report_failed_on_database_error(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.PENDING.value, report_type=REPORT_TYPE)
        generator_mock = mock.Mock()

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch.dict("varda.excel_export.REPORT_GENERATORS", {REPORT_TYPE: generator_mock}),
        ):
            using_mock.return_value.filter.return_value.first.return_value = report
            generator_mock.return_value.generate.side_effect = DatabaseError("reader unavailable")

            with self.assertRaises(DatabaseError):
                create_mass_excel_report_task.run(report_id)

        using_mock.assert_called_once_with(DEFAULT_DB_ALIAS)
        generator_mock.assert_called_once_with(report, data_db_alias="reader")
        generator_mock.return_value.generate.assert_called_once_with()
        self.assertEqual(report.status, ReportStatus.FAILED.value)
        report.save.assert_called_once_with(using=DEFAULT_DB_ALIAS)

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_logs_database_error_without_sensitive_data(self):
        report_id = 123
        encrypted_password = "encrypted-report-password"
        report = mock.Mock(status=ReportStatus.PENDING.value, id=report_id, password=encrypted_password, report_type=REPORT_TYPE)
        generator_mock = mock.Mock()

        with (
            mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock,
            mock.patch.dict("varda.excel_export.REPORT_GENERATORS", {REPORT_TYPE: generator_mock}),
            mock.patch("varda.excel_export.logger") as logger_mock,
        ):
            using_mock.return_value.filter.return_value.first.return_value = report
            generator_mock.return_value.generate.side_effect = DatabaseError("reader unavailable")

            with self.assertRaises(DatabaseError):
                create_mass_excel_report_task.run(report_id)

        log_message = str(logger_mock.exception.call_args)
        self.assertIn(str(report_id), log_message)
        self.assertIn("Mass Excel report generation failed", log_message)
        self.assertNotIn(encrypted_password, log_message)

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_marks_unknown_report_type_failed(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.PENDING.value, id=report_id, report_type="UNKNOWN_REPORT_TYPE")

        with mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock:
            using_mock.return_value.filter.return_value.first.return_value = report

            create_mass_excel_report_task.run(report_id)

        self.assertEqual(report.status, ReportStatus.FAILED.value)
        report.save.assert_called_once_with(using=DEFAULT_DB_ALIAS)

    def test_tyontekijatiedot_primary_query_uses_data_database_alias(self):
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=SimpleNamespace(id=123),
            toimipaikka=None,
            target_date=None,
        )
        generator = TyontekijatiedotVoimassaReportGenerator(report, data_db_alias="reader")

        queryset = mock.MagicMock()
        queryset.filter.return_value = queryset
        queryset.distinct.return_value = queryset
        queryset.select_related.return_value = queryset
        queryset.prefetch_related.return_value = queryset
        queryset.order_by.return_value = queryset
        queryset.iterator.return_value = iter(())

        with (
            mock.patch(
                "varda.excel_export.reports.tyontekijatiedot.Palvelussuhde.objects.using", return_value=queryset
            ) as using_mock,
            mock.patch("varda.excel_export.reports.tyontekijatiedot.Palvelussuhde.objects.filter", return_value=queryset),
            mock.patch.object(generator, "_get_koodisto_with_translations", return_value=[]),
            mock.patch.object(generator, "_add_worksheet"),
            mock.patch.object(generator, "_write_headers"),
        ):
            generator._create_excel_report()

        using_mock.assert_called_once_with("reader")


class ReportGeneratorRegistryTests(SimpleTestCase):
    def test_every_report_type_has_generator(self):
        self.assertEqual(set(REPORT_GENERATORS), {report_type.value for report_type in ExcelReportType})
