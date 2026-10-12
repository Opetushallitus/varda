import datetime
import os
import tempfile

from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, DatabaseError, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings

from varda.clients.aws_s3_client import Client as S3Client
from varda.enums.koodistot import Koodistot
from varda.enums.reporting import ReportStatus
from varda.enums.supported_language import SupportedLanguage
from varda.excel_export import (
    ExcelReportGenerator,
    _delete_tyontekijatiedot_voimassa_s3_artifacts,
    _tyontekijatiedot_voimassa_snapshot,
    create_mass_excel_report_task,
    create_tyontekijatiedot_voimassa_json_from_data,
    delete_excel_reports_earlier_than,
    get_excel_local_file_path,
    get_tyontekijatiedot_voimassa_json_access_local_file_path,
    get_tyontekijatiedot_voimassa_json_access_object_name,
    get_tyontekijatiedot_voimassa_json_local_file_path,
    get_tyontekijatiedot_voimassa_json_object_name,
    load_tyontekijatiedot_voimassa_data,
    read_tyontekijatiedot_voimassa_json,
    read_tyontekijatiedot_voimassa_json_access,
    store_tyontekijatiedot_voimassa_json,
)


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

        generator = ExcelReportGenerator(report)

        self.assertEqual(generator.data_db_alias, DEFAULT_DB_ALIAS)

    def test_excel_report_generator_uses_explicit_database_alias(self):
        report = self._report()

        generator = ExcelReportGenerator(
            report,
            data_db_alias="reader",
        )

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
        generator = ExcelReportGenerator(report)
        with mock.patch.object(generator, "_get_tyontekijatiedot_queryset", side_effect=AssertionError), mock.patch.object(
            generator, "_add_worksheet"
        ) as add_worksheet, mock.patch.object(generator, "_write_headers"):
            generator._create_tyontekijatiedot_voimassa_report(report_data=report_data)

        add_worksheet.assert_called_once()


class S3UploadTests(SimpleTestCase):
    def test_shared_upload_does_not_override_bucket_encryption(self):
        client = S3Client.__new__(S3Client)
        client.client = mock.Mock()

        with tempfile.NamedTemporaryFile() as file:
            client.upload_fileobj(file.name, "reports", "report.json.gz")

        client.client.upload_fileobj.assert_called_once_with(mock.ANY, "reports", "report.json.gz")

    def test_tyontekijatiedot_s3_cleanup_attempts_both_json_artifacts(self):
        report = SimpleNamespace(id=123, report_type="TYONTEKIJATIEDOT_VOIMASSA")
        client = mock.Mock()
        client.delete_file.side_effect = [False, True]

        self.assertFalse(_delete_tyontekijatiedot_voimassa_s3_artifacts(client, report))

        self.assertEqual(client.delete_file.call_count, 2)


class LocalReportCleanupTests(SimpleTestCase):
    @staticmethod
    def _report():
        return mock.Mock(id=123, report_type="TYONTEKIJATIEDOT_VOIMASSA")

    def _delete_report(self, report, temp_dir):
        with override_settings(EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=False), mock.patch(
            "varda.excel_export.S3Client", return_value=None
        ), mock.patch("varda.excel_export.Z8_ExcelReport.objects.filter", return_value=[report]):
            delete_excel_reports_earlier_than(datetime.datetime.now())

    def test_missing_excel_still_deletes_json_artifacts(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            for path in (
                get_tyontekijatiedot_voimassa_json_local_file_path(report),
                get_tyontekijatiedot_voimassa_json_access_local_file_path(report),
            ):
                open(path, "w").close()

            self._delete_report(report, temp_dir)

            self.assertFalse(os.path.exists(get_tyontekijatiedot_voimassa_json_local_file_path(report)))
            self.assertFalse(os.path.exists(get_tyontekijatiedot_voimassa_json_access_local_file_path(report)))
            report.delete.assert_not_called()

    def test_missing_json_artifact_does_not_prevent_other_json_cleanup(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            access_path = get_tyontekijatiedot_voimassa_json_access_local_file_path(report)
            open(access_path, "w").close()

            self._delete_report(report, temp_dir)

            self.assertFalse(os.path.exists(access_path))

    def test_successful_cleanup_deletes_report_record(self):
        report = self._report()
        with tempfile.TemporaryDirectory() as temp_dir, override_settings(EXCEL_PATH=f"{temp_dir}/"):
            for path in (
                get_excel_local_file_path(report),
                get_tyontekijatiedot_voimassa_json_local_file_path(report),
                get_tyontekijatiedot_voimassa_json_access_local_file_path(report),
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
        generator = ExcelReportGenerator(report, data_db_alias="reader")

        queryset = mock.MagicMock()
        queryset.filter.return_value = queryset
        queryset.annotate.return_value = queryset
        queryset.values.return_value = queryset
        queryset.__iter__.return_value = iter(())

        with mock.patch("varda.excel_export.Z2_Code.objects.using", return_value=queryset) as using_mock, mock.patch(
            "varda.excel_export.Z2_Code.objects.filter", return_value=queryset
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
        generator = ExcelReportGenerator(report, data_db_alias="reader")
        queryset = mock.MagicMock()
        queryset.filter.return_value = queryset
        queryset.distinct.return_value = queryset
        queryset.select_related.return_value = queryset
        queryset.prefetch_related.return_value = queryset
        queryset.order_by.return_value = queryset

        with mock.patch("varda.excel_export.Palvelussuhde.objects.using", return_value=queryset):
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
            mock.patch.object(ExcelReportGenerator, "_get_tyontekijatiedot_queryset", return_value=query),
            mock.patch.object(
                ExcelReportGenerator,
                "_get_koodisto_with_translations",
                side_effect=lambda koodisto: koodistot[koodisto],
            ),
            mock.patch("varda.excel_export.decrypt_henkilotunnus", return_value="090593-6006"),
        ):
            report_data = load_tyontekijatiedot_voimassa_data(report)
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
        with _tyontekijatiedot_voimassa_snapshot(DEFAULT_DB_ALIAS):
            with connection.cursor() as cursor:
                cursor.execute("SHOW TRANSACTION ISOLATION LEVEL")
                isolation_level = cursor.fetchone()[0]

        self.assertEqual(isolation_level, "repeatable read")


class MassExcelReportTaskTests(TestCase):
    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_uses_writer_control_record_and_reader_generator(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.PENDING.value)

        with mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock, mock.patch(
            "varda.excel_export.ExcelReportGenerator"
        ) as generator_mock:
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
        report = SimpleNamespace(
            id=report_id,
            status=ReportStatus.PENDING.value,
            report_type="TYONTEKIJATIEDOT_VOIMASSA",
            save=mock.Mock(side_effect=lambda **kwargs: events.append(f"status -> {report.status}")),
        )
        report_data = {
            "tyontekijat": [],
            "koodistot": {koodisto.value: [] for koodisto in Koodistot},
            "henkilo_id_oid_set": set(),
        }
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        events = []

        @mock.patch("varda.excel_export._tyontekijatiedot_voimassa_snapshot")
        def run_task(snapshot_mock):
            snapshot_mock.return_value.__enter__.side_effect = lambda: events.append("begin")
            snapshot_mock.return_value.__exit__.side_effect = lambda *args: events.append("commit")
            return create_mass_excel_report_task.run(report_id)

        with mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock, mock.patch(
            "varda.excel_export.load_tyontekijatiedot_voimassa_data", return_value=report_data
        ) as json_mock, mock.patch("varda.excel_export.store_tyontekijatiedot_voimassa_json") as store_mock, mock.patch(
            "varda.excel_export.ExcelReportGenerator"
        ) as generator_mock:
            using_mock.return_value.filter.return_value.first.return_value = report
            json_mock.side_effect = lambda *args, **kwargs: (events.append("load") or report_data)
            store_mock.side_effect = lambda *args, **kwargs: events.append("store")
            generator_mock.return_value.generate.side_effect = lambda *args, **kwargs: events.append("render")

            run_task()

        json_mock.assert_called_once_with(report, data_db_alias="reader")
        store_mock.assert_called_once_with(report, json_data, mock.ANY)
        self.assertFalse(hasattr(report, "json_data"))
        generator_mock.return_value.generate.assert_called_once_with(report_data=report_data)
        self.assertEqual(events, ["status -> CREATING", "begin", "load", "commit", "store", "render"])

    def test_tyontekijatiedot_json_snapshot_is_gzip_artifact_not_database_data(self):
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        report = SimpleNamespace(id=123)
        access_data = {(10, "1.2.246.562.10.1")}

        with tempfile.TemporaryDirectory() as temp_dir, override_settings(
            EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=False
        ):
            store_tyontekijatiedot_voimassa_json(report, json_data, access_data)

            artifact_path = get_tyontekijatiedot_voimassa_json_local_file_path(report)
            self.assertTrue(os.path.exists(artifact_path))
            self.assertEqual(os.stat(artifact_path).st_mode & 0o777, 0o600)
            self.assertEqual(read_tyontekijatiedot_voimassa_json(report), json_data)
            self.assertEqual(read_tyontekijatiedot_voimassa_json_access(report), list(access_data))
            self.assertTrue(os.path.exists(get_tyontekijatiedot_voimassa_json_access_local_file_path(report)))

    def test_tyontekijatiedot_json_snapshot_is_uploaded_to_report_bucket(self):
        json_data = {"raportti": "TYONTEKIJATIEDOT_VOIMASSA", "schema_version": 1, "tyontekijat": []}
        report = SimpleNamespace(id=123)
        access_data = {(10, "1.2.246.562.10.1")}

        with tempfile.TemporaryDirectory() as temp_dir, override_settings(
            EXCEL_PATH=f"{temp_dir}/", PRODUCTION_ENV=False, QA_ENV=False, DEV_ENV=True, S3_EXCEL_REPORTS="excel-reports"
        ), mock.patch("varda.excel_export.S3Client") as client_class:
            client_class.return_value.upload_fileobj.return_value = True

            store_tyontekijatiedot_voimassa_json(report, json_data, access_data)

            self.assertEqual(client_class.call_count, 2)
            client_class.assert_any_call("dev-excel-reports")
            client_class.return_value.upload_fileobj.assert_any_call(
                mock.ANY,
                "dev-excel-reports",
                get_tyontekijatiedot_voimassa_json_object_name(report),
            )
            client_class.return_value.upload_fileobj.assert_any_call(
                mock.ANY,
                "dev-excel-reports",
                get_tyontekijatiedot_voimassa_json_access_object_name(report),
            )
            self.assertFalse(os.path.exists(get_tyontekijatiedot_voimassa_json_local_file_path(report)))

    def test_mass_excel_report_task_does_not_generate_non_pending_report(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.FINISHED.value)

        with mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock, mock.patch(
            "varda.excel_export.ExcelReportGenerator"
        ) as generator_mock:
            using_mock.return_value.filter.return_value.first.return_value = report

            create_mass_excel_report_task.run(report_id)

        using_mock.assert_called_once_with(DEFAULT_DB_ALIAS)
        using_mock.return_value.filter.assert_called_once_with(id=report_id)
        generator_mock.assert_not_called()

    @override_settings(READER_DB="reader")
    def test_mass_excel_report_task_marks_report_failed_on_database_error(self):
        report_id = 123
        report = mock.Mock(status=ReportStatus.PENDING.value)

        with mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock, mock.patch(
            "varda.excel_export.ExcelReportGenerator"
        ) as generator_mock:
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
        report = mock.Mock(status=ReportStatus.PENDING.value, id=report_id, password=encrypted_password)

        with mock.patch("varda.excel_export.Z8_ExcelReport.objects.using") as using_mock, mock.patch(
            "varda.excel_export.ExcelReportGenerator"
        ) as generator_mock, mock.patch("varda.excel_export.logger") as logger_mock:
            using_mock.return_value.filter.return_value.first.return_value = report
            generator_mock.return_value.generate.side_effect = DatabaseError("reader unavailable")

            with self.assertRaises(DatabaseError):
                create_mass_excel_report_task.run(report_id)

        log_message = str(logger_mock.exception.call_args)
        self.assertIn(str(report_id), log_message)
        self.assertIn("Mass Excel report generation failed", log_message)
        self.assertNotIn(encrypted_password, log_message)

    def test_tyontekijatiedot_primary_query_uses_data_database_alias(self):
        report = SimpleNamespace(
            language=SupportedLanguage.FI.value,
            admin_user_all_organizations=False,
            organisaatio=SimpleNamespace(id=123),
            toimipaikka=None,
        )
        generator = ExcelReportGenerator(report, data_db_alias="reader")

        queryset = mock.MagicMock()
        queryset.filter.return_value = queryset
        queryset.distinct.return_value = queryset
        queryset.select_related.return_value = queryset
        queryset.prefetch_related.return_value = queryset
        queryset.order_by.return_value = queryset
        queryset.iterator.return_value = iter(())

        with mock.patch("varda.excel_export.Palvelussuhde.objects.using", return_value=queryset) as using_mock, mock.patch(
            "varda.excel_export.Palvelussuhde.objects.filter", return_value=queryset
        ), mock.patch.object(generator, "_get_koodisto_with_translations", return_value=[]), mock.patch.object(
            generator, "_add_worksheet"
        ), mock.patch.object(
            generator, "_write_headers"
        ):
            generator._create_tyontekijatiedot_report()

        using_mock.assert_called_once_with("reader")
