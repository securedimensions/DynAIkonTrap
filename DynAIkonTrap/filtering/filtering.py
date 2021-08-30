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
from enum import Enum

from DynAIkonTrap.camera import Frame, Camera
from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.filtering.motion_queue import MotionLabelledQueue
from DynAIkonTrap.filtering.motion_queue import MotionStatus
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import FilterSettings

logger = get_logger(__name__)


class Filter:
    """Wrapper for the complete image filtering pipeline"""

    def __init__(self, read_from: Camera, settings: FilterSettings):
        """
        Args:
            read_from (Camera): Read frames from this camera
            settings (FilterSettings): Settings for the filter pipeline
        """
        self.framerate = read_from.framerate

        self._input_queue = read_from
        self._output_queue: QueueType[Frame] = Queue()

        self._motion_filter = MotionFilter(
            settings=settings.motion, framerate=self.framerate
        )
        self._motion_threshold = settings.motion.sotv_threshold

        self._animal_filter = AnimalFilter(settings=settings.animal)
        self._motion_labelled_queue = MotionLabelledQueue(
            animal_detector=self._animal_filter,
            settings=settings.motion_queue,
            framerate=self.framerate,
        )

        self._usher = Process(target=self._handle_input, daemon=True)
        self._usher.start()
        logger.debug('Filter started')

    def get(self) -> Frame:
        """Retrieve the next animal `Frame` from the filter pipeline's output

        Returns:
            Frame: An animal frame
        """
        return self._motion_labelled_queue.get()

    def close(self):
        self._usher.terminate()
        self._usher.join()

    def _handle_input(self):
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
                self._motion_labelled_queue.put(frame, motion_score, MotionStatus.MOTION)

            else:
                self._motion_labelled_queue.put(frame, -1.0, MotionStatus.STILL)
