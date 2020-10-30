from unittest import TestCase
from os import listdir, replace, remove
from json import dump

from DynAIkonTrap.settings import (
    load_settings,
    Settings,
    CameraSettings,
    FilterSettings,
    MotionFilterSettings,
    AnimalFilterSettings,
    MotionQueueSettings,
    SensorSettings,
    SenderSettings,
    OutputMode
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
            "sensor": {"port": -12, "baud": -13, "interval_s": -14},
            "sender": {
                "server": -15,
                "POST": -16,
                "device_id": -17,
                "output_mode": 0
            },
        }
        self._settings = Settings(
            CameraSettings(-1, [-2, -3]),
            FilterSettings(
                MotionFilterSettings(-4, -5, -6, -7, -8),
                AnimalFilterSettings(-9),
                MotionQueueSettings(-10, -11),
            ),
            SensorSettings(-12, -13, -14),
            SenderSettings(-15, -16, -17, OutputMode(0)),
        )

        with open('DynAIkonTrap/settings.json', 'w') as f:
            dump(settings_json, f)

    def test_returns_loaded_settings(self):
        loaded_settings = load_settings()
        self.assertEqual(loaded_settings, self._settings)

    def tearDown(self) -> None:
        if self._prev_existed:
            replace('DynAIkonTrap/settings.json.old', 'DynAIkonTrap/settings.json')
        else:
            remove('DynAIkonTrap/settings.json')
