import datetime
import unittest

from anonymizer.python.db_anonymizer import delete_orphan_history_rows
from anonymizer.python.generate_anonymized_data import get_syntymaaika
from anonymizer.python.validate_anonymization import (
    validate_hetut_are_test_hetut,
    validate_logs_are_empty,
    validate_no_orphan_history_rows,
)
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from django.test import TestCase
from django_celery_results.models import TaskResult

from varda.misc import create_hetu_from_birthday, encrypt_string
from varda.models import Henkilo, Toimipaikka
from varda.validators import validate_henkilotunnus


class DbAnonymizerTests(unittest.TestCase):
    def test_get_syntymaaika_century_20(self):
        hetu = "010397-1232"
        date = get_syntymaaika(hetu)
        self.assertEqual("1997-03-01", date)

    def test_get_syntymaaika_century_21(self):
        hetu = "050115A459P"
        date = get_syntymaaika(hetu)
        self.assertEqual("2015-01-05", date)

    def test_get_syntymaaika_all_century_signs(self):
        for sign, century in [("+", "18"), *[(s, "19") for s in "-UVWXY"], *[(s, "20") for s in "ABCDEF"]]:
            with self.subTest(sign=sign):
                self.assertEqual(f"{century}15-01-05", get_syntymaaika(f"050115{sign}9000"))

    def test_create_hetu_from_birthday_uses_test_range(self):
        for year in (1890, 1965, 2015):
            for sukupuoli_koodi in (1, 2):
                for _ in range(500):
                    hetu = create_hetu_from_birthday(datetime.date(year, 6, 1), sukupuoli_koodi)
                    with self.subTest(hetu=hetu):
                        individual_number = int(hetu[7:10])
                        self.assertGreaterEqual(individual_number, 900)
                        self.assertEqual(individual_number % 2, sukupuoli_koodi % 2)
                        self.assertTrue(get_syntymaaika(hetu).startswith(str(year)))
                        # Raises ValidationError if date, century sign or control character is invalid
                        validate_henkilotunnus(hetu)


class DbAnonymizerDatabaseTests(TestCase):
    fixtures = ["fixture_basics"]

    def test_orphan_history_rows(self):
        history_model = Toimipaikka.history.model
        self.assertTrue(history_model.objects.exists())
        live_history_count = history_model.objects.count()
        validate_no_orphan_history_rows()

        # Make one history row look like a row of a deleted Toimipaikka
        orphan_id = Toimipaikka.objects.aggregate(Max("id"))["id__max"] + 1000
        history_model.objects.filter(history_id=history_model.objects.first().history_id).update(id=orphan_id)
        with self.assertRaises(SystemExit) as context:
            validate_no_orphan_history_rows()
        self.assertEqual(context.exception.code, 8)

        delete_orphan_history_rows()
        self.assertFalse(history_model.objects.filter(id=orphan_id).exists())
        self.assertEqual(history_model.objects.count(), live_history_count - 1)
        validate_no_orphan_history_rows()

    def test_hetut_must_be_test_hetut(self):
        Henkilo.objects.exclude(henkilotunnus="").update(henkilotunnus=encrypt_string("120386-109V"))
        with self.assertRaises(SystemExit) as context:
            validate_hetut_are_test_hetut()
        self.assertEqual(context.exception.code, 7)

        Henkilo.objects.exclude(henkilotunnus="").update(henkilotunnus=encrypt_string("120386-909D"))
        validate_hetut_are_test_hetut()

    def test_logs_must_be_empty(self):
        TaskResult.objects.all().delete()
        LogEntry.objects.all().delete()
        validate_logs_are_empty()

        TaskResult.objects.create(task_id="test-task")
        with self.assertRaises(SystemExit) as context:
            validate_logs_are_empty()
        self.assertEqual(context.exception.code, 9)

        TaskResult.objects.all().delete()
        LogEntry.objects.create(
            user=User.objects.first(),
            content_type=ContentType.objects.get_for_model(User),
            object_repr="test",
            action_flag=1,
        )
        with self.assertRaises(SystemExit) as context:
            validate_logs_are_empty()
        self.assertEqual(context.exception.code, 9)
