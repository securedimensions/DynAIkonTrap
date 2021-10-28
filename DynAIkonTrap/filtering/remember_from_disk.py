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
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from os import nice
from multiprocessing import Array, Process, Queue
from multiprocessing.queues import Queue as QueueType
from pathlib import Path
from struct import unpack, pack
from numpy import e, finfo
from queue import Empty
from enum import Enum
from numpy import ndarray
from time import sleep, time
from typing import List
from io import open

from DynAIkonTrap.camera import Frame
from DynAIkonTrap.camera_to_disk import CameraToDisk, MotionData, MotionRAMBuffer
from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.filtering.motion_queue import MotionLabelledQueue
from DynAIkonTrap.filtering.motion_queue import MotionStatus
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import CameraSettings, FilterSettings, WriterSettings

logger = get_logger(__name__)


@dataclass
class EventData:
    """A class for storing motion event data for further processing."""
    motion_vector_frames: List[bytes]
    raw_raster_frames: List[bytes]
    dir: str
    start_timestamp: float


class EventRememberer:
    """This object reads new event directories from an instance of :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk`. Outputs a Queue of EventData objects for further processing.
    """
    def __init__(self, read_from: CameraToDisk):
        """Initialises EventRememberer. Starts events processing thread.

        Args:
            read_from (CameraToDisk): The :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk` object creating event directories on disk.
        """
        self._output_queue: QueueType[EventData] = Queue(
            maxsize=10
        )  
        self._input_queue = read_from
        self._raw_dims = read_from.raw_frame_dims
        self._raw_bpp = read_from.bits_per_pixel_raw
        self.framerate = read_from.framerate
        width, height = read_from.resolution

        self._rows, self._cols = MotionRAMBuffer.calc_rows_cols(width, height)
        self._motion_element_size = MotionRAMBuffer.calc_motion_element_size(self._rows, self._cols)

        self._usher = Process(target=self.proc_events, daemon=True)
        self._usher.start()

    def proc_events(self):
        """Process input queue of event directories
        """
        nice(4)
        while True:
            try:
                event_dir = self._input_queue.get()
                self._output_queue.put(self.dir_to_event(event_dir))
            except Empty:
                logger.error("Trying to read from empty event directory queue")
                pass

    def dir_to_event(self, dir:str) -> EventData:
        """converts an event directory to an instance of EventData

        Args:
            dir (str): event directory

        Returns:
            EventData: populated instance of event data.
        """
        raw_path = Path(dir).joinpath("clip.dat")
        vect_path = Path(dir).joinpath("clip_vect.dat")
        raw_raster_frames = []
        try:
            with open(raw_path, "rb") as file:
                while True:
                    buf = file.read1(self._raw_dims[0] * self._raw_dims[1] * self._raw_bpp)
                    if not buf:
                        break
                    raw_raster_frames.append(buf)

            motion_vector_frames = []
            event_time = time()  # by default event time set to now

            with open(vect_path, "rb") as file:
                start = True
                while True:
                    buf = file.read(self._motion_element_size)
                    if not buf:
                        break
                    if start:
                        arr_timestamp = bytearray(buf)[0:8]  # index the timestamp
                        event_time = unpack("<d", arr_timestamp)[0]
                        start = False
                    motion_vector_frames.append(buf)

        except IOError as e:
            logger.error("Problem opening or reading file: {}".format(e.filename))

        return EventData(
            motion_vector_frames=motion_vector_frames,
            raw_raster_frames=raw_raster_frames,
            dir=dir,
            start_timestamp=event_time,
        )

    def get(self) -> EventData:
        """Get next EventData object in the output queue

        Returns:
            EventData: Next EventData object
        """
        return self._output_queue.get()
