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
"""
The mechanism by which the tunable settings may be loaded into the system. Whilst this may look complicated at first, it provides a simple method to access all of the settings without needing to index into/get from a dictionary. This also means IDEs are able to perform autocompletion and provide type hints as the settings are unpacked in their respective places in the system.

To load the ``settings.json`` file, just run the :func:`load_settings` function once and it returns the a :class:`Settings` object. For example:

.. code:: py

   settings = load_settings()

   camera = DynAIkonTrap.camera.Camera(settings=settings.camera)


The ``settings.json`` should ideally be generated by the provided ``tuner.py`` script, although manual modifications may be desired.

The JSON file should be structured as follows (of course the values can be changed):

.. code:: json

   {
       "camera": {
           "framerate": 20,
           "resolution": [640, 480]
       },
       "filter": {
           "motion": {
               "small_threshold": 10,
               "sotv_threshold": 300,
               "iir_cutoff_hz": 1,
               "iir_order": 8,
               "iir_attenuation": 20
           },
           "animal": {
               "threshold": 0.1
           },
           "motion_queue": {
               "smoothing_factor": 1,
               "max_sequence_period_s": 10.0
           }
       },
       "sensor": {
           "port": "/dev/ttyUSB0",
           "baud": 57600,
           "interval_s": 30.0
       },
       "sender": {
           "server": "http://10.42.0.1:8080/trap/",
           "POST": "capture/",
           "device_id": 0,
           "output_format": 0
       },
       "logging": {
           "level": "INFO"
       }
   }
"""
from json import load, JSONDecodeError
from dataclasses import dataclass
from typing import Tuple, Any, Union
from enum import Enum

from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CameraSettings:
    """Settings for a  :class:`~DynAIkonTrap.camera.Camera`"""

    framerate: int = 20
    resolution: Tuple[int, int] = (640, 480)


@dataclass
class MotionFilterSettings:
    """Settings for a :class:`~DynAIkonTrap.filtering.motion.MotionFilter`"""

    small_threshold: int = 10
    sotv_threshold: float = 300.0
    iir_cutoff_hz: float = 2.0
    iir_order: int = 3
    iir_attenuation: int = 35


@dataclass
class AnimalFilterSettings:
    """Settings for a :class:`~DynAIkonTrap.filtering.animal.AnimalFilter`"""

    threshold: float = 0.2


@dataclass
class MotionQueueSettings:
    """Settings for a :class:`~DynAIkonTrap.filtering.motion_queue.MotionQueue`"""

    smoothing_factor: float = 0.5
    max_sequence_period_s: float = 10.0


@dataclass
class SensorSettings:
    """Settings for a :class:`~DynAIkonTrap.sensor.SensorLogs`

    The `obfuscation_distance` should be kept to the range [0..`EARTH_CIRCUMFERENCE_KM/8`), otherwise it will internally be capped to this range. Note that setting to less than 1mm will be rounded down to zero.
    """

    port: str = '/dev/ttyUSB0'
    baud: int = 57600
    interval_s: float = 30.0
    obfuscation_distance_km: float = 2


class OutputFormat(Enum):
    """System output format"""

    VIDEO = 0
    STILL = 1


class OutputMode(Enum):
    """System output mode"""

    DISK = 0
    SEND = 1

class OutputVideoCodec(Enum):
    """System output video codec"""
    H264 = 0
    PIM1 = 1

@dataclass
class OutputSettings:
    device_id: Any = 0
    output_format: OutputFormat = OutputFormat.STILL
    output_mode: OutputMode = OutputMode.DISK
    output_codec: OutputVideoCodec = OutputVideoCodec.H264


@dataclass
class SenderSettings(OutputSettings):
    """Settings for a :class:`~DynAIkonTrap.comms.Sender`"""

    server: str = 'http://10.42.0.1:8080/trap/'
    POST: str = 'capture/'


@dataclass
class WriterSettings(OutputSettings):
    """Settings for a :class:`~DynAIkonTrap.comms.Writer`"""

    path: str = ''


@dataclass
class FilterSettings:
    """Settings for a :class:`~DynAIkonTrap.comms.Filter`"""

    motion: MotionFilterSettings = MotionFilterSettings()
    animal: AnimalFilterSettings = AnimalFilterSettings()
    motion_queue: MotionQueueSettings = MotionQueueSettings()


@dataclass
class LoggerSettings:
    """Settings for logging"""

    level: str = 'INFO'  # Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
    # `Literal` is not supported in Python from RPi packages, hence no proper type hint


@dataclass
class Settings:
    """Settings for the camera trap system. A class of nested classes and variables to represent all tunable parameters in the system."""

    camera: CameraSettings = CameraSettings()
    filter: FilterSettings = FilterSettings()
    sensor: SensorSettings = SensorSettings()
    output: Union[SenderSettings, WriterSettings] = WriterSettings()
    logging: LoggerSettings = LoggerSettings()


def _version_number() -> str:
    with open('VERSION', 'r') as f:
        version = f.readline().strip()
    return version


def load_settings() -> Settings:
    """Call this function once to load the settings from ``settings.json`` file. If the file is not present some defaults are loaded.

    NOTE: these defaults should not be used for anything other than a brief test. Please generate a settings.json for any full deployments (see docs for more info).

    Returns:
        Settings: The settings for all tunable parameters in the system.
    """
    try:
        with open('DynAIkonTrap/settings.json', 'rb') as f:
            try:
                settings_json = load(f)
            except JSONDecodeError:
                logger.warning(
                    'Malformed settings.json, using some defaults (JSONDecodeError)'
                )
                return Settings()

            try:
                json_version = settings_json.get('version', '0')
                system_version = _version_number()

                if json_version != system_version:
                    logger.warning(
                        'Running DynAIkonTrap v{}, but settings are for v{}, using defaults'.format(
                            system_version, json_version
                        )
                    )
                    return Settings()

                output_mode = OutputMode(settings_json['output']['output_mode'])
                if output_mode == OutputMode.SEND:
                    output = SenderSettings(
                        server=settings_json['output']['server'],
                        POST=settings_json['output']['POST'],
                        device_id=settings_json['output']['device_id'],
                        output_format=OutputFormat(
                            settings_json['output']['output_format']
                        ),
                        output_mode=output_mode,
                        output_codec=OutputVideoCodec(settings_json['output']['output_codec']),
                    )
                else:  # Default to writing to disk
                    output = WriterSettings(
                        device_id=settings_json['output']['device_id'],
                        output_format=OutputFormat(
                            settings_json['output']['output_format']
                        ),
                        output_mode=output_mode,
                        output_codec=OutputVideoCodec(settings_json['output']['output_codec']),
                        path=settings_json['output']['path'],
                    )

                return Settings(
                    CameraSettings(**settings_json['camera']),
                    FilterSettings(
                        MotionFilterSettings(**settings_json['filter']['motion']),
                        AnimalFilterSettings(**settings_json['filter']['animal']),
                        MotionQueueSettings(**settings_json['filter']['motion_queue']),
                    ),
                    SensorSettings(**settings_json['sensor']),
                    output,
                    LoggerSettings(**settings_json['logging']),
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
