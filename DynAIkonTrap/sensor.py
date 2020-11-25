"""
An interface to the sensor board. The logs from sensor readings are taken by the `SensorLogs` and can be accessed via the `SensorLogger.get()` function, by timestamp. The intended usage is to retrieve a sensor log taken at a similar time to a frame.
"""
from typing import List, Tuple, Union
from typing import OrderedDict as OrderedDictType
from multiprocessing import Process, Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from time import time
from serial import Serial, SerialException
from collections import OrderedDict
from signal import signal, setitimer, ITIMER_REAL, SIGALRM

from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import SensorSettings

logger = get_logger(__name__)


@dataclass
class Reading:
    """Representation of a sensor reading, which has a value and units of measurement"""

    value: float
    units: str


@dataclass
class SensorLog:
    """A log of sensor readings taken at a given moment in time. Time is represented as a UNIX-style timestamp. If a reading could not be taken for any of the attached sensors, the sensor may be represented by `None` in the log."""

    timestamp: float
    brightness: 'Union[Reading, type(None)]'
    humidity: 'Union[Reading, type(None)]'
    pressure: 'Union[Reading, type(None)]'
    temperature: 'type(None)' = None  # Not yet supported by the sensor


class Sensor:
    """Provides an interface to the weather sensor board"""

    def __init__(self, port: str, baud: int):
        """
        Args:
            port (str): The path to the port to which the sensor is attached, most likely `'/dev/ttyUSB0'`
            baud (int): Baudrate to use in communication with the sensor board
        Raises:
            SerialException: If the sensor board could not be found
        """
        try:
            self._ser = Serial(port, baud, timeout=0)
        except SerialException:
            logger.warning('Sensor board not found on {}, baud {}'.format(port, baud))
            self._ser = None
            raise

        self._brightness = None
        self._humidity = None
        self._pressure = None

    def _retrieve_latest_data(self):

        data = None

        if not self._ser:
            return

        while self._ser.in_waiting:
            data = self._ser.readline()

        if not data:
            return

        split_raw_data = str(data).split(' ')
        if len(split_raw_data) != 40:
            return

        self._brightness = Reading(float(split_raw_data[16][:-1]), '%')
        self._humidity = Reading(float(split_raw_data[18][:-1]), 'RH%')
        self._pressure = Reading(float(split_raw_data[20]), 'mbar')

    def read(self) -> SensorLog:
        """Triggers the taking and logging of sensor readings

        Returns:
            SensorLog: Readings for all sensors
        """
        self._retrieve_latest_data()
        return SensorLog(time(), self._brightness, self._humidity, self._pressure)


class SensorLogs:
    """A data structure to hold all sensor logs. The class includes a dedicated process to perform the sensor logging and handle sensor log lookup requests."""

    def __init__(self, settings: SensorSettings):
        """
        Args:
            settings (SensorSettings): Settings for the sensor logger
        Raises:
            SerialException: If the sensor board could not be found
        """
        self._storage: OrderedDictType[float, SensorLog] = OrderedDict()
        self._query_queue: QueueType[float] = Queue()
        self._results_queue: QueueType[SensorLog] = Queue()

        try:
            self._sensor = Sensor(settings.port, settings.baud)
        except SerialException:
            self._sensor = None

        self._read_interval = settings.interval_s
        self._last_logged = 0

        self._logger = Process(target=self._log, daemon=True)
        self._logger.start()
        logger.debug('SensorLogs started')

    @property
    def read_interval(self):
        return self._read_interval

    def _log_now(self, delay=None, interval=None):
        if self._sensor is None:
            return
        sensor_log = self._sensor.read()
        logger.debug(sensor_log)
        self._storage[sensor_log.timestamp] = sensor_log

    def _find_closest_key(
        self, sorted_keys: List[float], ts: float, index: int = 0
    ) -> Tuple[float, int]:

        if len(sorted_keys) == 1:
            return (sorted_keys[0], index)

        # Find numerically closest key of two
        if len(sorted_keys) == 2:
            mean_ts = sum(sorted_keys) / 2
            if ts >= mean_ts:
                return (sorted_keys[1], index + 1)
            else:
                return (sorted_keys[0], index)

        halfway = int(len(sorted_keys) // 2)
        halfway_ts = sorted_keys[halfway]

        # Normal bisecting
        if ts == halfway_ts:
            return (ts, halfway)
        elif ts > halfway_ts:
            return self._find_closest_key(sorted_keys[halfway:], ts, halfway)
        else:
            return self._find_closest_key(sorted_keys[: halfway + 1], ts, 0)

    def _lookup(self, timestamp: float) -> SensorLog:
        if self._sensor is None:
            return None

        keys = list(self._storage.keys())
        if len(keys) == 0:
            return None

        key, index = self._find_closest_key(keys, timestamp)

        # Delete all except current log as subsequent frames may still need this
        try:
            self._remove_logs(keys[:index])
        except KeyError as e:
            logger.error('Attempted to delete nonexistent log(s): {}'.format(e))
        return self._storage.get(key, None)

    def _remove_logs(self, timestamps: List[float]):
        """Removes all logs with the given `timestamp` keys."""
        for t in timestamps:
            del self._storage[t]

        if timestamps:
            logger.debug(
                'Deleted logs for {}\nRemaining: {}'.format(
                    timestamps, self._storage.keys()
                )
            )

    def _log(self):
        # Set up periodic temperature logging
        signal(SIGALRM, self._log_now)
        setitimer(ITIMER_REAL, 0.1, self._read_interval)

        while True:
            query = self._query_queue.get()
            self._results_queue.put_nowait(self._lookup(query))

    def get(self, timestamp: float) -> Union[SensorLog, type(None)]:
        """Get the log closest to the given timestamp and return it.

        Also deletes logs older than this timestamp.

        Args:
            timestamp (float): Timestamp of the image for which sensor readings are to be retrieved

        Returns:
            Union[SensorLog, None]: The retrieved log of sensor readings or `None` if none could be retrieved.
        """

        self._query_queue.put(timestamp)
        return self._results_queue.get()

    def close(self):
        self._logger.terminate()
        self._logger.join()
