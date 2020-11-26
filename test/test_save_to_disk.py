# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2020 Miklas Riechmann

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
