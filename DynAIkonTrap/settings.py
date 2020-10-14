from json import load, JSONDecodeError
from dataclasses import dataclass
from typing import Tuple, Any

from DynAikonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CameraSettings:
    framerate: int = 20
    resolution: Tuple[int, int] = (640, 480)


@dataclass
class MotionFilterSettings:
    small_threshold: int = 10
    sotv_threshold: float = 300.
    iir_cutoff_hz: float = 2.
    iir_order: int = 8
    iir_attenuation: int = 20


@dataclass
class AnimalFilterSettings:
    threshold: float = 0.1


@dataclass
class MotionQueueSettings:
    smoothing_factor: float = 0.5
    max_sequence_period_s: float = 10.


@dataclass
class SensorSettings:
    port: str = '/dev/ttyUSB0'
    baud: int = 57600
    interval_s: float = 30.


@dataclass
class SenderSettings:
    server: str = 'http://10.42.0.1:8080/trap/'
    POST: str = 'capture/'
    device_id: Any = 0


@dataclass
class FilterSettings:
    motion: MotionFilterSettings = MotionFilterSettings()
    animal: AnimalFilterSettings = AnimalFilterSettings()
    motion_queue: MotionQueueSettings = MotionQueueSettings()


@dataclass
class Settings:
    camera: CameraSettings = CameraSettings()
    filter: FilterSettings = FilterSettings()
    sensor: SensorSettings = SensorSettings()
    sender: SenderSettings = SenderSettings()


def load_settings() -> Settings:
    try:
        with open('DynAikonTrap/settings.json', 'rb') as f:
            try:
                settings_json = load(f)
            except JSONDecodeError:
                logger.warning(
                    'Malformed settings.json, using some defaults (JSONDecodeError)'
                )
                return Settings()

            try:
                return Settings(
                    CameraSettings(**settings_json['camera']),
                    FilterSettings(
                        MotionFilterSettings(**settings_json['filter']['motion']),
                        AnimalFilterSettings(**settings_json['filter']['animal']),
                        MotionQueueSettings(**settings_json['filter']['motion_queue']),
                    ),
                    SensorSettings(**settings_json['sensor']),
                    SenderSettings(**settings_json['sender']),
                )
            except KeyError as e:
                logger.warning(
                    'Badly formatted settings.json, using defaults (KeyError `{}`)'.format(
                        e
                    )
                )
                return Settings()

    except FileNotFoundError:
        logger.warning(
            'The settings.json file could not be found, starting with defaults'
        )
        return Settings()
