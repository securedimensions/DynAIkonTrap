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
from unittest import TestCase
from collections import OrderedDict

from DynAIkonTrap.sensor import Reading, SensorLogs, SensorLog
import DynAIkonTrap.ursense.parser as parser

from DynAIkonTrap.settings import SensorSettings


class SensorMock:
    def __init__(self):
        self._i = 0

    def read(self) -> SensorLog:
        ret = SensorLog(self._i, {'DUMMY': self._i + 1})
        self._i += 2
        return ret


class LogNowAddsToLogsTestCase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_logs_added(self):
        self._sl._log_now()
        self._sl._log_now()
        self._sl._log_now()
        self.assertEqual(self._sl._storage[0], SensorLog(0, {'DUMMY': 1}))
        self.assertEqual(self._sl._storage[2], SensorLog(2, {'DUMMY': 3}))
        self.assertEqual(self._sl._storage[4], SensorLog(4, {'DUMMY': 5}))


class RemoveLogsTestcase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_remove_logs_when_none_exist(self):
        self._sl._storage.clear()
        with self.assertRaises(KeyError):
            self._sl._remove_logs([0])

    def test_remove_logs_with_given_timestamps(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        self._sl._log_now()
        self._sl._remove_logs([0, 2])
        self.assertEqual(len(self._sl._storage), 1)
        self.assertEqual(self._sl._storage[4], SensorLog(4, {'DUMMY': 5}))


class FindKeyTestCase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_find_exact_key(self):
        res = self._sl._find_closest_key([0.1, 1.1, 2.1], 0.1)
        self.assertEqual(res, (0.1, 0))

    def test_lookup_just_larger_than_key(self):
        res = self._sl._find_closest_key([0, 1, 2], 0.1)
        self.assertEqual(res, (0, 0))

    def test_lookup_just_smaller_than_key(self):
        res = self._sl._find_closest_key([0, 1, 2], 0.9)
        self.assertEqual(res, (1, 1))

    def test_only_one_key(self):
        res = self._sl._find_closest_key([0], 1)
        self.assertEqual(res, (0, 0))

    def test_lookup_smaller_than_smallest_entry(self):
        res = self._sl._find_closest_key([0, 1, 2], -1)
        self.assertEqual(res, (0, 0))

    def test_lookup_larger_than_largest_entry(self):
        res = self._sl._find_closest_key([0, 1, 2], 3)
        self.assertEqual(res, (2, 2))


class LookupAndDeleteTestCase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_returns_closest_log1(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        ret = self._sl._lookup(0.1)
        self.assertEqual(ret, SensorLog(0, {'DUMMY': 1}))

    def test_returns_closest_log2(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        ret = self._sl._lookup(1.9)
        self.assertEqual(ret, SensorLog(2, {'DUMMY': 3}))

    def test_returns_closest_log3(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        ret = self._sl._lookup(2.1)
        self.assertEqual(ret, SensorLog(2, {'DUMMY': 3}))

    def test_removes_only_logs_older_than_requested_time(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        self._sl._lookup(2.1)
        self.assertEqual(len(self._sl._storage), 1)
        self.assertEqual(
            self._sl._storage, OrderedDict({2: SensorLog(2, {'DUMMY': 3})})
        )


class ParseInvalidSensorTestCase(TestCase):
    def test_parse_envt_report_type(self):
        ret = parse_ursense(
            'urSense 1.28... commands:\n  e show environment sensor measurements\n  L toggle PPS on LED D5\n'
        )
        self.assertEqual(ret, None)


p = parser.UrSenseParser(obfuscation_distance_km=0)
parse_ursense = p.parse


class ParseEnvmReportTypeTestCase(TestCase):
    def test_parse_envm_report_type(self):
        self.maxDiff = None
        ret = parse_ursense(
            'selF envm 2.800 s usid 0123456789ab skwt 24.6 C brig 1.86% airr 4.69 kOhm humi 35.2% atpr 1002.8 mbar prst 25.3 C\n'
        )
        sl = {
            'UNIQUE_ID': Reading(int('0123456789ab', 16)),
            'BRIGHTNESS': Reading(1.86, '%'),
            'HUMIDITY': Reading(35.2, '%'),
            'RAW_ATMOSPHERIC_PRESSURE': Reading(1002.8, 'mbar'),
            'SKEW_TEMPERATURE': Reading(24.6, 'C'),
            'PRESSURE_TEMPERATURE': Reading(25.3, 'C'),
            'AIR_QUALITY_RESISTANCE': Reading(4.69, 'kOhm'),
        }
        self.assertEqual(ret, sl)


class ParseEnvtReportTypeTestCase(TestCase):
    def test_parse_envt_report_type(self):
        self.maxDiff = None
        ret = parse_ursense(
            'selE envt 2.800 s usid 0123456789ab skwt 24.6 C brig 1.86% airr 4.69 kOhm humi 35.2% atpr 1002.8 mbar prst 25.3 C\n'
        )
        sl = {
            'UNIQUE_ID': Reading(int('0123456789ab', 16)),
            'BRIGHTNESS': Reading(1.86, '%'),
            'HUMIDITY': Reading(35.2, '%'),
            'RAW_ATMOSPHERIC_PRESSURE': Reading(1002.8, 'mbar'),
            'SKEW_TEMPERATURE': Reading(24.6, 'C'),
            'PRESSURE_TEMPERATURE': Reading(25.3, 'C'),
            'AIR_QUALITY_RESISTANCE': Reading(4.69, 'kOhm'),
        }
        self.assertEqual(ret, sl)


class ParseEnvlReportTypeTestCase(TestCase):
    def test_parse_envl_report_type(self):
        self.maxDiff = None
        ret = parse_ursense(
            'selE envl 2.800 s usid 0123456789ab skwt 24.6 C brig 1.86% airr 4.69 kOhm humi 35.2% atpr 1002.8 mbar prst 25.3 C\n'
        )
        sl = {
            'UNIQUE_ID': Reading(int('0123456789ab', 16)),
            'BRIGHTNESS': Reading(1.86, '%'),
            'HUMIDITY': Reading(35.2, '%'),
            'RAW_ATMOSPHERIC_PRESSURE': Reading(1002.8, 'mbar'),
            'SKEW_TEMPERATURE': Reading(24.6, 'C'),
            'PRESSURE_TEMPERATURE': Reading(25.3, 'C'),
            'AIR_QUALITY_RESISTANCE': Reading(4.69, 'kOhm'),
        }
        self.assertEqual(ret, sl)


class ParseEnvsReportTypeTestCase(TestCase):
    def test_parse_envs_report_type(self):
        self.maxDiff = None
        ret = parse_ursense(
            'selE envs 114.205 s usid 0123456789ab skwt 25.2 C brig 1.27% airr 5.47 kOhm humi 35.1% atpr 1003 mbar prst 25.7 C Fri 30.04.2021 20;25;20.123 E1+0000 50.36194N 4.74472W alti 108 m sazi 116.123 WNW salt -1.123 deg\n'
        )
        sl = {
            'UNIQUE_ID': Reading(int('0123456789ab', 16)),
            'BRIGHTNESS': Reading(1.27, '%'),
            'HUMIDITY': Reading(35.1, '%'),
            'RAW_ATMOSPHERIC_PRESSURE': Reading(1003.0, 'mbar'),
            'SKEW_TEMPERATURE': Reading(25.2, 'C'),
            'PRESSURE_TEMPERATURE': Reading(25.7, 'C'),
            'AIR_QUALITY_RESISTANCE': Reading(5.47, 'kOhm'),
            'GPS_TIME': Reading('Fri 30.04.2021 20;25;20.123 E1+0000'),
            'GPS_POSITION_LATITUDE_RAW': Reading(50.36194, 'N'),
            'GPS_POSITION_LONGITUDE_RAW': Reading(4.74472, 'W'),
            'GPS_POSITION_LATITUDE_QUANTISED': Reading(50.36194, 'N'),
            'GPS_POSITION_LONGITUDE_QUANTISED': Reading(4.74472, 'W'),
            'ALTITUDE_ABOVE_SEA': Reading(108.0, 'm'),
            'SUN_AZIMUTH': Reading(116.123, 'WNW'),
            'SUN_ALTITUDE': Reading(-1.123, 'deg'),
        }
        self.assertEqual(ret, sl)


class ObfuscateGPSTestCase(TestCase):
    def setUp(self):
        p = parser.UrSenseParser(obfuscation_distance_km=2)
        self.parse = p.parse

    def test_quantise_gps(self):
        self.maxDiff = None
        ret = self.parse(
            'selE envs 114.205 s usid 0123456789ab skwt 25.2 C brig 1.27% airr 5.47 kOhm humi 35.1% atpr 1003 mbar prst 25.7 C Fri 30.04.2021 20;25;20.123 E1+0000 50.36194N 4.74472W alti 108 m sazi 116.123 WNW salt -1.123 deg\n'
        )
        sl = {
            'UNIQUE_ID': Reading(int('0123456789ab', 16)),
            'BRIGHTNESS': Reading(1.27, '%'),
            'HUMIDITY': Reading(35.1, '%'),
            'RAW_ATMOSPHERIC_PRESSURE': Reading(1003.0, 'mbar'),
            'SKEW_TEMPERATURE': Reading(25.2, 'C'),
            'PRESSURE_TEMPERATURE': Reading(25.7, 'C'),
            'AIR_QUALITY_RESISTANCE': Reading(5.47, 'kOhm'),
            'GPS_TIME': Reading('Fri 30.04.2021 20;25;20.123 E1+0000'),
            'GPS_POSITION_LATITUDE_RAW': Reading(50.36194, 'N'),
            'GPS_POSITION_LONGITUDE_RAW': Reading(4.74472, 'W'),
            'GPS_POSITION_LATITUDE_QUANTISED': Reading(50.364, 'N'),
            'GPS_POSITION_LONGITUDE_QUANTISED': Reading(4.7404955548939025, 'W'),
            'ALTITUDE_ABOVE_SEA': Reading(108.0, 'm'),
            'SUN_AZIMUTH': Reading(116.123, 'WNW'),
            'SUN_ALTITUDE': Reading(-1.123, 'deg'),
        }
        self.assertEqual(ret, sl)

    def test_quantise_close_gps_to_same_coords(self):
        self.maxDiff = None
        # Restart parser to reset any knowledge of previous results
        p = parser.UrSenseParser(obfuscation_distance_km=2)
        self.parse = p.parse
        ret = self.parse(
            'selE envs 114.205 s usid 0123456789ab skwt 25.2 C brig 1.27% airr 5.47 kOhm humi 35.1% atpr 1003 mbar prst 25.7 C Fri 30.04.2021 20;25;20.123 E1+0000 50.361945N 4.744999W alti 108 m sazi 116.123 WNW salt -1.123 deg\n'
        )
        sl = {
            'UNIQUE_ID': Reading(int('0123456789ab', 16)),
            'BRIGHTNESS': Reading(1.27, '%'),
            'HUMIDITY': Reading(35.1, '%'),
            'RAW_ATMOSPHERIC_PRESSURE': Reading(1003.0, 'mbar'),
            'SKEW_TEMPERATURE': Reading(25.2, 'C'),
            'PRESSURE_TEMPERATURE': Reading(25.7, 'C'),
            'AIR_QUALITY_RESISTANCE': Reading(5.47, 'kOhm'),
            'GPS_TIME': Reading('Fri 30.04.2021 20;25;20.123 E1+0000'),
            'GPS_POSITION_LATITUDE_RAW': Reading(50.361945, 'N'),
            'GPS_POSITION_LONGITUDE_RAW': Reading(4.744999, 'W'),
            'GPS_POSITION_LATITUDE_QUANTISED': Reading(50.364, 'N'),
            'GPS_POSITION_LONGITUDE_QUANTISED': Reading(4.7404955548939025, 'W'),
            'ALTITUDE_ABOVE_SEA': Reading(108.0, 'm'),
            'SUN_AZIMUTH': Reading(116.123, 'WNW'),
            'SUN_ALTITUDE': Reading(-1.123, 'deg'),
        }
        self.assertEqual(ret, sl)
