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
from os import listdir, replace, remove
from json import dump

from DynAIkonTrap.settings import (
    LoggerSettings,
    OutputMode,
    _version_number,
    load_settings,
    Settings,
    CameraSettings,
    FilterSettings,
    MotionFilterSettings,
    AnimalFilterSettings,
    MotionQueueSettings,
    SensorSettings,
    SenderSettings,
    OutputFormat,
)


class SettingsDoesNotExistTestCase(TestCase):
    def setUp(self) -> None:
        self._prev_existed = False

        # Ensure a settings.py file does not exist
        if 'settings.json' in listdir('DynAIkonTrap'):
            replace('DynAIkonTrap/settings.json', 'DynAIkonTrap/settings.json.old')
            self._prev_existed = True

    def test_return_default_settings(self):
        loaded_settings = load_settings()
        self.assertEqual(loaded_settings, Settings())

    def tearDown(self) -> None:
        # Recreate a settings file if it existed previously
        if self._prev_existed:
            replace('DynAIkonTrap/settings.json.old', 'DynAIkonTrap/settings.json')


class SettingsDoesExistMalformedTestCase(TestCase):
    def setUp(self) -> None:
        self._prev_existed = False

        # Ensure settings exist
        if 'settings.json' in listdir('DynAIkonTrap'):
            replace('DynAIkonTrap/settings.json', 'DynAIkonTrap/settings.json.old')
            self._prev_existed = True

        with open('DynAIkonTrap/settings.json', 'w') as f:
            f.write('nonesense')

    def test_malformed_json_returns_default(self):
        loaded_settings = load_settings()
        self.assertEqual(loaded_settings, Settings())

    def tearDown(self) -> None:
        if self._prev_existed:
            replace('DynAIkonTrap/settings.json.old', 'DynAIkonTrap/settings.json')
        else:
            remove('DynAIkonTrap/settings.json')


class SettingsDoesExistTestCase(TestCase):
    def setUp(self) -> None:
        # Ensure settings exist
        # Ensure it contains different data to the defaults
        # E.g. all unique negative numbers (-ve nos. aren't default for anything)
        self._prev_existed = False

        # Ensure settings exist
        if 'settings.json' in listdir('DynAIkonTrap'):
            replace('DynAIkonTrap/settings.json', 'DynAIkonTrap/settings.json.old')
            self._prev_existed = True

        settings_json = {
            "camera": {"framerate": -1, "resolution": [-2, -3]},
            "filter": {
                "motion": {
                    "small_threshold": -4,
                    "sotv_threshold": -5,
                    "iir_cutoff_hz": -6,
                    "iir_order": -7,
                    "iir_attenuation": -8,
                },
                "animal": {"threshold": -9},
                "motion_queue": {
                    "smoothing_factor": -10,
                    "max_sequence_period_s": -11,
                },
            },
            "sensor": {
                "port": -12,
                "baud": -13,
                "interval_s": -14,
                "obfuscation_distance_km": -1,
            },
            "output": {
                "output_mode": 1,
                "server": -15,
                "POST": -16,
                "device_id": -17,
                "output_format": 0,
            },
            "logging": {"level": "DEBUG"},
            "version": _version_number(),
        }
        self._settings = Settings(
            CameraSettings(-1, [-2, -3]),
            FilterSettings(
                MotionFilterSettings(-4, -5, -6, -7, -8),
                AnimalFilterSettings(-9),
                MotionQueueSettings(-10, -11),
            ),
            SensorSettings(-12, -13, -14, -1),
            SenderSettings(-17, OutputFormat(0), OutputMode(1), -15, -16),
            LoggerSettings('DEBUG'),
        )

        with open('DynAIkonTrap/settings.json', 'w') as f:
            dump(settings_json, f)

    def test_returns_loaded_settings(self):
        loaded_settings = load_settings()
        print(loaded_settings)
        self.assertEqual(loaded_settings, self._settings)

    def tearDown(self) -> None:
        if self._prev_existed:
            replace('DynAIkonTrap/settings.json.old', 'DynAIkonTrap/settings.json')
        else:
            remove('DynAIkonTrap/settings.json')
