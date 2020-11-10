from os.path import abspath, dirname, join
from unittest import TestCase
from unittest.mock import patch

from DynAIkonTrap.settings import WriterSettings
from DynAIkonTrap.filtering.filtering import Filter


class MockFilter(Filter):
    def __init__(self):
        self.framerate = 1

PATH = dirname(abspath(__file__))

class CreateValidNamesTestCase(TestCase):
    def test_filename_correctly_formatted(self):
        self._mock_listdir = lambda _: []

        with patch('DynAIkonTrap.comms.listdir', self._mock_listdir):
            from DynAIkonTrap.comms import Writer

            settings = WriterSettings()
            settings.path = PATH

            writer = Writer(settings, (MockFilter(), None))
            writer._reader.terminate()
            ts = 2274139425.678910
            res = writer._unique_name(ts)
            self.assertEqual(res, join(PATH, '2042-01-24_01-23-45-678910_0'))


class CreateValidNamesFileExistsTestCase(TestCase):
    def test_filename_correctly_formatted(self):
        self._mock_listdir = lambda _: ['2042-01-24_01-23-45-678910_0']

        with patch('DynAIkonTrap.comms.listdir', self._mock_listdir):
            from DynAIkonTrap.comms import Writer

            settings = WriterSettings()
            settings.path = PATH

            writer = Writer(settings, (MockFilter(), None))
            writer._reader.terminate()
            ts = 2274139425.678910
            res = writer._unique_name(ts)
            self.assertEqual(res, join(PATH, '2042-01-24_01-23-45-678910_1'))
