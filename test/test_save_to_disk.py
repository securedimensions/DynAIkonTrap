from unittest import TestCase
from unittest.mock import patch

from DynAIkonTrap.settings import WriterSettings
from DynAIkonTrap.filtering.filtering import Filter


class MockFilter(Filter):
    def __init__(self):
        self.framerate = 1


class CreateValidNamesTestCase(TestCase):
    def setUp(self):
        self._mock_listdir = lambda _: []

        with patch('os.listdir', self._mock_listdir):
            from DynAIkonTrap.comms import Writer

            settings = WriterSettings()
            settings.path = 'x/'

            self._writer = Writer(settings, (MockFilter(), None))
            self._writer._reader.terminate()

    def test_filename_correctly_formatted(self):
        ts = 2274139425.678910
        res = self._writer._unique_name(ts)
        self.assertEqual(res, 'x/2042-01-24_01-23-45-678910_0')


class CreateValidNamesFileExistsTestCase(TestCase):
    def setUp(self):
        self._mock_listdir = lambda _: ['2042-01-24_01-23-45-678910_0']

        with patch('os.listdir', self._mock_listdir):
            from DynAIkonTrap.comms import Writer

            settings = WriterSettings()
            settings.path = 'x/'

            self._writer = Writer(settings, (MockFilter(), None))
            self._writer._reader.terminate()

    def test_filename_correctly_formatted(self):
        ts = 2274139425.678910
        res = self._writer._unique_name(ts)
        self.assertEqual(res, 'x/2042-01-24_01-23-45-678910_1')
