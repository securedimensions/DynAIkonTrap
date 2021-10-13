# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2021 Ross Gardiner

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
Provides a simplified interface to the :class:`PiCamera` library class. The :class:`Camera` class provides the :class:`Frame`\ s from the camera's stream via a queue. Initialising the :class:`Camera` takes care of setting up the necessary motion vector and image streams under the hood.

A :class:`Frame` is defined for this system as having the motion vectors, as used in H.264 encoding, a JPEG encode image, and a UNIX-style timestamp when the frame was captured.
"""
from os import write
from queue import Empty
from pathlib import Path
from time import sleep, time
import numpy as np
from multiprocessing import Event, Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from typing import Tuple

try:
    from picamera import PiCamera
    from picamera.array import PiMotionAnalysis
    from picamera.streams import PiCameraCircularIO, CircularIO
except (OSError, ModuleNotFoundError):
    # Ignore error that occurs when running pdoc3
    class PiMotionAnalysis:
        pass


from DynAIkonTrap.settings import CameraSettings, WriterSettings
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EventData:
    """Data for a saved motion event on disk."""

    path: Path

class VideoRAMBuffer():
    """class for storing video frames on RAM while motion detection is evaluated. Frame storage is alternated between two ring-buffers of type `PiCameraCircularIO`. """

    def __init__(self, camera, splitter_port, size) -> None:
        """Initialise stream object.

        Args:
            camera (PiCamera): Picamera instance, used to initialise underlying buffers 
            splitter_port (int): Splitter port number, range [0-3], indicates port for connection to underlying stream
            size (int): [description]. Maximum size of a ring buffer, measured in bytes

        """
        self._active_stream = PiCameraCircularIO(camera, size=size, splitter_port=splitter_port)
        self._inactive_stream = PiCameraCircularIO(camera, size=size, splitter_port=splitter_port)
        self._bytes_written :int = 0
        self._frac_full :float = 0.0
        self.compute_used_space()

    def write(self, buf):
        """Write a frame buffer to the active stream 

        Args:
            buf ([type]): frame buffer
        """
        self._bytes_written += self._active_stream.write(buf)


    def compute_used_space(self) -> float:
        """compute the fraction of the ring buffer filled up thus far

        Returns:
            float: fraction representing full space in ring buffer
        """
        self._frac_full = self._bytes_written / self._active_stream.size
        return self._frac_full
    
    def switch_stream(self):
        self._active_stream, self._inactive_stream = self._inactive_stream, self._active_stream
        self._bytes_written = 0
        
class Synchroniser:
    def __init__(self, output: QueueType):
        self._last_image = None
        self._output = output

    def tick_movement_frame(self, motion):
        if self._last_image is not None:
            image = np.asarray(bytearray(self._last_image), dtype="uint8")
        else:
            return
        self._output.put_nowait(Frame(image, motion, time()))

    def tick_image_frame(self, image):
        self._last_image = image

class DirectoryFactory:
    """Creates new directories for storing motion events."""

    def __init__(self, base_dir: Path):
        """Takes a base Path object and initialises a directory factory for motion events.

        Args:
            base_dir (Path): base directory for storing motion event folders.
        """
        self._base_dir = base_dir
        self._event_counter = 0

    def new_event(self) -> Tuple(Path, str):
        """Gives string name and directory path for a new motion event on disk"""

        ret_str = "event_" + str(self._event_counter)
        self._event_counter += 1
        ret_path = self._base_dir.joinpath(ret_str)
        return Tuple(ret_path, ret_str)


class CameraToDisk:
    """Wraps picamera functionality to stream motion events to disk."""

    def __init__(self, camera_settings: CameraSettings, writer_settings: WriterSettings):
        """Takes a :class:`~DynAIkonTrap.settings.CameraSettings` object to initialise and start the camera hardware.

        Args:
            camera_settings (CameraSettings): settings object for camera construction
            writer_settings (WriterSettings): settings object for writing out events
        """
        self.resolution = camera_settings.resolution
        self.framerate = camera_settings.framerate
        self._camera = PiCamera(resolution=self.resolution, framerate=self.framerate)
        sleep(2)  # Camera warmup

        self._output: QueueType[EventData] = Queue()
        self._synchroniser = Synchroniser(self._output)
        self._directory_factory = DirectoryFactory(writer_settings.path)
        
