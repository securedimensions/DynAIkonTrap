
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
A simple interface to the frame animal filtering pipeline is provided by this module. It encapsulates both motion- and image-based filtering as well as any smoothing of this in time. Viewed from the outside the :class:`Filter` reads from a :class:`~DynAIkonTrap.camera.Camera`'s output and in turn outputs only frames containing animals.

Internally frames are first analysed by the :class:`~DynAIkonTrap.filtering.motion.MotionFilter`. Frames with motion score and label indicating motion, are added to a :class:`~DynAIkonTrap.filtering.motion_queue.MotionLabelledQueue`. Within the queue the :class:`~DynAIkonTrap.filtering.animal.AnimalFilter` stage is applied with only the animal frames being returned as the output of this pipeline.

The output is accessible via a queue, which mitigates problems due to the burstiness of this stage's output and also allows the pipeline to be run in a separate process.
"""
from multiprocessing import Process, Queue
from multiprocessing.queues import Queue as QueueType
from queue import Empty
from time import sleep

from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.filtering.motion_queue import MotionLabelledQueue
from DynAIkonTrap.filtering.remember_from_disk import EventData, EventRememberer
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import FilterSettings




class FilterFromDisk:

    def __init__(self, read_from: EventRememberer, settings: FilterSettings):
        self._input_queue = read_from
        self._output_queue: QueueType[EventData] = Queue()
        self._animal_filter = AnimalFilter(settings.animal)
        self._motion_labelled_queue = MotionLabelledQueue(
            animal_detector=self._animal_filter,
            settings=settings.motion_queue,
            framerate=read_from._framerate
        )

        self._usher = Process(target=self._handle_input, daemon=True)
        self._usher.start()

    def _handle_input(self):
        while True:
            try:
                event = self._input_queue.get()
            except Empty:
                sleep(1)
                continue

    def motion_labelled_queue_from_event(self, event) -> MotionLabelledQueue:
        print(event.dir)
