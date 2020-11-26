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
from time import time
from pickle import load
from multiprocessing import Queue, Value
from unittest import TestCase

from DynAIkonTrap.camera import Frame
from DynAIkonTrap.filtering import Filter
from DynAIkonTrap.comms import Sender
from DynAIkonTrap.sensor import SensorLogs
from DynAIkonTrap.settings import (
    OutputMode,
    SenderSettings,
    load_settings,
    OutputFormat,
)


def load_pickle(filename):
    with open(filename, 'rb') as f:
        data = load(f)
    return data


class MockCamera:
    def __init__(self, settings, data):
        self.framerate = settings.framerate
        self._data = data
        self._queue = Queue()
        for i, d in enumerate(self._data):
            self._queue.put(Frame(d['image'], d['motion'], i))

    def get(self):
        return self._queue.get(1)


class SenderMock(Sender):
    def __init__(self, settings, read_from):
        self.call_count = Value('i', 0)
        super().__init__(settings, read_from)

    def output_still(self, **kwargs):
        with self.call_count.get_lock():
            self.call_count.value += 1


class IntegrationSendStillsOutTestCase(TestCase):
    def test_integration_at_least_one_animal_frame(self):

        data = load_pickle('test/data/data.pk')

        settings = load_settings()
        settings.camera.framerate = data['framerate']
        settings.camera.resolution = data['resolution']
        settings.output = SenderSettings(0, OutputFormat.STILL, OutputMode.SEND, '', '')

        self.camera = MockCamera(settings.camera, data['frames'])
        self.filters = Filter(read_from=self.camera, settings=settings.filter)
        self.sensor_logs = SensorLogs(settings=settings.sensor)
        self.sender = SenderMock(
            settings=settings.output, read_from=(self.filters, self.sensor_logs)
        )


        t_start = time()

        while True:

            if self.sender.call_count.value >= 1:
                break

            if time() - t_start >= 50:
                self.fail('Timed out')

    def tearDown(self):
        self.sender.close()
        self.sensor_logs.close()
        self.filters.close()
