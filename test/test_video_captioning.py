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
from json import loads
from unittest import TestCase
from io import StringIO

from DynAIkonTrap.comms import VideoCaption
from DynAIkonTrap.sensor import SensorLog, Reading


class VideoTimeToStringTestCase(TestCase):
    def setUp(self):
        class MockSensorLogs:
            pass

        self.vc = VideoCaption(MockSensorLogs(), 20)

    def test_time_zero(self):
        res = self.vc._video_time_to_str(0)
        self.assertEqual(res, '00:00.000')

    def test_time_fraction1(self):
        res = self.vc._video_time_to_str(0.01)
        self.assertEqual(res, '00:00.010')

    def test_time_fraction2(self):
        res = self.vc._video_time_to_str(0.1)
        self.assertEqual(res, '00:00.100')

    def test_time_fraction3(self):
        res = self.vc._video_time_to_str(0.001)
        self.assertEqual(res, '00:00.001')

    def test_time_minute_wrapping(self):
        res = self.vc._video_time_to_str(60)
        self.assertEqual(res, '01:00.000')

    def test_time_all_positions(self):
        res = self.vc._video_time_to_str(4242.42)
        self.assertEqual(res, '70:42.420')


class ConvertReadingToStringTestCas(TestCase):
    def setUp(self):
        class MockSensorLogs:
            pass

        self.vc = VideoCaption(MockSensorLogs(), 20)

    def test_reading_convert(self):
        res = self.vc._reading_to_str(Reading(1.1, '%'))
        self.assertEqual(res, '1.1%')

    def test_none_reading_convert(self):
        res = self.vc._reading_to_str(None)
        self.assertEqual(res, '?')


class CaptionsDictToVTTTestCase(TestCase):
    def setUp(self):
        class MockSensorLogs:
            pass

        self.vc = VideoCaption(MockSensorLogs(), 20)

    def test_empty_dict(self):
        res = self.vc._captions_dict_to_vtt({}, 1)
        self.assertEqual(res, 'WEBVTT \n\n')

    def test_single_caption(self):
        d = {
            0: {
                'start': 0,
                'stop': 20,
                'log': SensorLog(
                    system_time=0,
                    readings={
                        'BRIGHTNESS': Reading(1.1, '%'),
                        'HUMIDITY': Reading(2.2, '%'),
                        'ATMOSPHERIC_PRESSURE': Reading(3.3, 'mbar'),
                    },
                ),
            }
        }
        res = self.vc._captions_dict_to_vtt(d, 20)
        self.assertEqual(
            res,
            'WEBVTT \n\n00:00.000 --> 00:01.000 - Sensor@00:00:00\nT: ? - RH: 2.2% - L: 1.1% - P: 3.3mbar\n\n',
        )

    def test_multiple_captions(self):
        d = {
            0: {
                'start': 0,
                'stop': 20,
                'log': SensorLog(
                    system_time=0,
                    readings={
                        'BRIGHTNESS': Reading(1.1, '%'),
                        'HUMIDITY': Reading(2.2, '%'),
                        'ATMOSPHERIC_PRESSURE': Reading(3.3, 'mbar'),
                    },
                ),
            },
            1: {
                'start': 20,
                'stop': 42,
                'log': SensorLog(
                    system_time=60,
                    readings={
                        'BRIGHTNESS': Reading(4.4, '%'),
                        'HUMIDITY': Reading(5.5, '%'),
                        'ATMOSPHERIC_PRESSURE': Reading(6.6, 'mbar'),
                    },
                ),
            },
        }
        res = self.vc._captions_dict_to_vtt(d, 20)
        self.assertEqual(
            res,
            'WEBVTT \n\n00:00.000 --> 00:01.000 - Sensor@00:00:00\nT: ? - RH: 2.2% - L: 1.1% - P: 3.3mbar\n\n00:01.000 --> 00:02.100 - Sensor@00:01:00\nT: ? - RH: 5.5% - L: 4.4% - P: 6.6mbar\n\n',
        )


class LogsToCaptionsTestCase(TestCase):
    def setUp(self):
        class MockSensorLogs:
            def __init__(self):
                self._results = [
                    SensorLog(
                        system_time=0,
                        readings={
                            'BRIGHTNESS': Reading(1.2, '%'),
                            'HUMIDITY': Reading(3.4, '%'),
                            'ATMOSPHERIC_PRESSURE': Reading(5.6, 'mbar'),
                        },
                    ),
                    SensorLog(
                        system_time=1,
                        readings={
                            'BRIGHTNESS': Reading(7.8, '%'),
                            'HUMIDITY': Reading(9.10, '%'),
                            'ATMOSPHERIC_PRESSURE': Reading(11.12, 'mbar'),
                        },
                    ),
                    None,
                ]
                self.read_interval = 1

            def get(self, _):
                return self._results.pop(0)

        self.vc = VideoCaption(MockSensorLogs(), 1)

    def test_dict_generation(self):
        self.maxDiff = None
        captions = {
            0: {
                'start': 0,
                'stop': 1,
                'log': SensorLog(
                    system_time=0,
                    readings={
                        'BRIGHTNESS': Reading(1.2, '%'),
                        'HUMIDITY': Reading(3.4, '%'),
                        'ATMOSPHERIC_PRESSURE': Reading(5.6, 'mbar'),
                    },
                ),
            },
            1: {
                'start': 1,
                'stop': 2,
                'log': SensorLog(
                    system_time=1,
                    readings={
                        'BRIGHTNESS': Reading(7.8, '%'),
                        'HUMIDITY': Reading(9.10, '%'),
                        'ATMOSPHERIC_PRESSURE': Reading(11.12, 'mbar'),
                    },
                ),
            },
            2: {'start': 2, 'stop': 3, 'log': None},
        }
        # As logs older than a requested timestamp are deleted requesting zeros will
        # give the oldest logs (none are left for the third call)
        res = self.vc._generate_captions_dict([0, 0, 0])
        self.assertEqual(res, captions)


class GenerateVTTTestCase(TestCase):
    def setUp(self):
        class MockSensorLogs:
            def __init__(self):
                self._results = [
                    SensorLog(
                        system_time=0,
                        readings={
                            'BRIGHTNESS': Reading(1.2, '%'),
                            'HUMIDITY': Reading(3.4, '%'),
                            'ATMOSPHERIC_PRESSURE': Reading(5.6, 'mbar'),
                        },
                    ),
                    SensorLog(
                        system_time=1,
                        readings={
                            'BRIGHTNESS': Reading(7.8, '%'),
                            'HUMIDITY': Reading(9.10, '%'),
                            'ATMOSPHERIC_PRESSURE': Reading(11.12, 'mbar'),
                        },
                    ),
                    None,
                ]
                self.read_interval = 1

            def get(self, _):
                return self._results.pop(0)

        self.vc = VideoCaption(MockSensorLogs(), 1)

    def test_VTT_generation(self):
        res = self.vc.generate_vtt_for([0, 0, 0])
        self.assertEqual(
            res.getvalue(),
            StringIO(
                'WEBVTT \n\n00:00.000 --> 00:01.000 - Sensor@00:00:00\nT: ? - RH: 3.4% - L: 1.2% - P: 5.6mbar\n\n00:01.000 --> 00:02.000 - Sensor@00:00:01\nT: ? - RH: 9.1% - L: 7.8% - P: 11.12mbar\n\n'
            ).getvalue(),
        )


class GenerateJSONTestCase(TestCase):
    def setUp(self):
        class MockSensorLogs:
            def __init__(self):
                self._results = [
                    SensorLog(
                        system_time=0,
                        readings={
                            'BRIGHTNESS': Reading(1.2, '%'),
                            'HUMIDITY': Reading(3.4, '%'),
                            'ATMOSPHERIC_PRESSURE': Reading(5.6, 'mbar'),
                        },
                    ),
                    SensorLog(
                        system_time=1,
                        readings={
                            'BRIGHTNESS': Reading(7.8, '%'),
                            'HUMIDITY': Reading(9.10, '%'),
                            'ATMOSPHERIC_PRESSURE': Reading(11.12, 'mbar'),
                        },
                    ),
                    None,
                ]
                self.read_interval = 1

            def get(self, _):
                return self._results.pop(0)

        self.vc = VideoCaption(MockSensorLogs(), 1)

    def test_JSON_generation(self):
        res = self.vc.generate_sensor_json([0, 0, 0])
        self.assertEqual(
            loads(res.getvalue()),
            [
                {
                    "start": 0,
                    "end": 1,
                    "log": {
                        "BRIGHTNESS": {"value": 1.2, "units": "%"},
                        "HUMIDITY": {"value": 3.4, "units": "%"},
                        "ATMOSPHERIC_PRESSURE": {
                            "value": 5.6,
                            "units": "mbar",
                        },
                        "system_time": {"value": 0, "units": "s"},
                    },
                },
                {
                    "start": 1,
                    "end": 2,
                    "log": {
                        "BRIGHTNESS": {"value": 7.8, "units": "%"},
                        "HUMIDITY": {"value": 9.1, "units": "%"},
                        "ATMOSPHERIC_PRESSURE": {
                            "value": 11.12,
                            "units": "mbar",
                        },
                        "system_time": {"value": 1, "units": "s"},
                    },
                },
            ],
        )
