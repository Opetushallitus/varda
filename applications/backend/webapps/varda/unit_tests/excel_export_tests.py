from types import SimpleNamespace
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, DatabaseError
from django.test import SimpleTestCase, TestCase, override_settings

from varda.enums.koodistot import Koodistot
from varda.enums.reporting import ReportStatus
from varda.enums.supported_language import SupportedLanguage
from varda.excel_export import ExcelReportGenerator, create_mass_excel_report_task


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


class EmployeeReportDatabaseAliasTests(TestCase):
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

            create_mass_excel_report_task.run(report_id)

        log_message = str(logger_mock.error.call_args)
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
