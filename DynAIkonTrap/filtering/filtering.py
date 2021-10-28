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
from multiprocessing.context import set_spawning_popen
from multiprocessing.queues import Queue as QueueType
from queue import Empty
from os import nice
from subprocess import call
from time import sleep
from enum import Enum
from typing import Union

from DynAIkonTrap.camera import Frame, Camera
from DynAIkonTrap.filtering import motion_queue
from DynAIkonTrap.filtering.animal import AnimalFilter, ImageFormat
from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.filtering.motion_queue import MotionLabelledQueue
from DynAIkonTrap.filtering.motion_queue import MotionStatus
from DynAIkonTrap.filtering.remember_from_disk import EventData, EventRememberer
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import FilterSettings

logger = get_logger(__name__)


class FilterMode(Enum):
    BY_FRAME = 0
    BY_EVENT = 1


class Filter:
    """Wrapper for the complete image filtering pipeline"""

    def __init__(
        self, read_from: Union[Camera, EventRememberer], settings: FilterSettings
    ):
        """
        Args:
            read_from (Camera): Read frames from this camera
            settings (FilterSettings): Settings for the filter pipeline
        """

        self._input_queue = read_from
        self.framerate = read_from.framerate

        self._animal_filter = AnimalFilter(settings=settings.animal)

        if isinstance(read_from, Camera):
            self.mode = FilterMode.BY_FRAME
            self._output_queue: QueueType[Frame] = Queue()
            self._motion_filter = MotionFilter(
                settings=settings.motion, framerate=self.framerate
            )
            self._motion_threshold = settings.motion.sotv_threshold
            self._motion_labelled_queue = MotionLabelledQueue(
                animal_detector=self._animal_filter,
                settings=settings.motion_queue,
                framerate=self.framerate,
            )

            self._usher = Process(target=self._handle_input_frames, daemon=True)
            self._usher.start()

        elif isinstance(read_from, EventRememberer):
            self.mode = FilterMode.BY_EVENT
            self._output_queue: QueueType[EventData] = Queue()
            self._usher = Process(target=self._handle_input_events, daemon=True)
            self._usher.start()

        logger.debug("Filter started")

    def get(self):
        """Retrieve the next animal `Frame` from the filter pipeline's output

        Returns:
            Frame: An animal frame
        """
        if self.mode == FilterMode.BY_FRAME:
            return self._motion_labelled_queue.get()
        elif self.mode == FilterMode.BY_EVENT:
            return self._output_queue.get()

    def close(self):
        self._usher.terminate()
        self._usher.join()

    def _handle_input_frames(self):
        while True:

            try:
                frame = self._input_queue.get()
            except Empty:
                # An unexpected event; finish processing motion so far
                self._motion_labelled_queue.end_motion_sequence()
                self._motion_filter.reset()
                continue

            motion_score = self._motion_filter.run_raw(frame.motion)
            motion_detected = motion_score >= self._motion_threshold

            if motion_detected:
                self._motion_labelled_queue.put(
                    frame, motion_score, MotionStatus.MOTION
                )

            else:
                self._motion_labelled_queue.put(frame, -1.0, MotionStatus.STILL)

    def _handle_input_events(self):
        nice(4)
        while True:
            try:
                event = self._input_queue.get()
                # result = self._process_event(event)
                self._output_queue.put(event)
                # if not result:
                #     self._delete_event(event)
                # else:
                #     self._output_queue.put(event)

            except Exception as e:
                print(e)
                sleep(1)
                continue

    def _process_event(self, event: EventData) -> bool:
        lst_indx_frames = list(enumerate(event.raw_raster_frames))
        middle_idx = len(lst_indx_frames) // 2
        lst_indx_frames.sort(key=lambda x: abs(middle_idx - x[0]))
        for index, frame in lst_indx_frames:
            is_animal = self._animal_filter.run(frame, format=ImageFormat.RGBA)
            if is_animal:
                return True
        return False

    def _delete_event(self, event: EventData):
        call(["rm -r {}".format(event.dir)], shell=True)
