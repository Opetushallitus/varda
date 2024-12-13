import unittest
from anonymizer.python.generate_anonymized_data import get_syntymaaika


class DbAnonymizerTests(unittest.TestCase):
    def test_get_syntymaaika_century_20(self):
        hetu = '010397-1232'
        date = get_syntymaaika(hetu)
        self.assertEqual('1997-03-01', date)

    def test_get_syntymaaika_century_21(self):
        hetu = '050115A459P'
        date = get_syntymaaika(hetu)
        self.assertEqual('2015-01-05', date)
