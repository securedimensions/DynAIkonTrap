from typing import Union
from typing import OrderedDict as OrderedDictType
from multiprocessing import Process, Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from time import time, sleep
from serial import Serial, SerialException
from collections import OrderedDict
from bisect import bisect_left

from DynAikonTrap.logging import get_logger
from DynAikonTrap.settings import SensorSettings

logger = get_logger(__name__)


@dataclass
class Reading:
    value: float
    units: str


@dataclass
class SensorLog:
    timestamp: float
    brightness: 'Union[Reading, type(None)]'
    humidity: 'Reading[Reading, type(None)]'
    pressure: 'Reading[Reading, type(None)]'


class Sensor:
    """Provides simple interface to the weather sensor board"""

    def __init__(self, port: str, baud: int):
        try:
            self._ser = Serial(port, baud, timeout=0)
        except SerialException:
            logger.error('Sensor board not found on {}, baud {}'.format(port, baud))
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

    def read(self):
        self._retrieve_latest_data()
        return SensorLog(time(), self._brightness, self._humidity, self._pressure)


class SensorLogs:
    def __init__(self, settings: SensorSettings):
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

    def _log_now(self):
        if self._sensor is None:
            return
        sensor_log = self._sensor.read()
        logger.debug(sensor_log)
        self._storage[sensor_log.timestamp] = sensor_log

    def _lookup(self, timestamp: float) -> SensorLog:
        if self._sensor is None:
            return None
        
        keys = list(self._storage.keys())
        i = bisect_left(keys, timestamp) - 1

        try:
            key = keys[i]
        except KeyError:
            logger.error('Sensor log lookup failed with KeyError')

        # Delete all except current log as subsequent frames may still need this
        self._remove_logs(keys[:i])
        return self._storage.get(key, None)

    def _remove_logs(self, timestamps: float):
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
        while True:
            if not self._query_queue.empty():
                query = self._query_queue.get_nowait()
                self._results_queue.put_nowait(self._lookup(query))

            if time() - self._last_logged >= self._read_interval:
                self._log_now()
                self._last_logged = time()

    def get(self, timestamp: float) -> SensorLog:
        """Get the log closest to the given timestamp and return it.
        Also deletes logs older than this timestamp."""
        self._query_queue.put(timestamp)
        return self._results_queue.get()
