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
Provides a simplified interface to the :class:`PiCamera` library class. The :class:`Camera` class provides the :class:`Frame`\ s from the camera's stream via a queue. Initialising the :class:`Camera` takes care of setting up the necessary motion vector and image streams under the hood.

A :class:`Frame` is defined for this system as having the motion vectors, as used in H.264 encoding, a JPEG encode image, and a UNIX-style timestamp when the frame was captured.
"""
from queue import Empty
from time import sleep, time
import numpy as np
from multiprocessing import Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from typing import Tuple

try:
    from picamera import PiCamera
    from picamera.array import PiMotionAnalysis
except (OSError, ModuleNotFoundError):
    # Ignore error that occurs when running pdoc3
    class PiMotionAnalysis:
        pass


from DynAIkonTrap.settings import CameraSettings
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Frame:
    """A frame from the camera consisting of motion and image information as well as the time of capture."""

    image: bytes
    motion: np.ndarray
    timestamp: float


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


class MovementAnalyser(PiMotionAnalysis):
    def __init__(self, camera, synchroniser):
        super().__init__(camera)
        self._sync = synchroniser

    def analyse(self, motion):
        self._sync.tick_movement_frame(motion)


class ImageReader:
    def __init__(self, synchroniser):
        self._sync = synchroniser

    def write(self, buf):
        if buf.startswith(b"\xff\xd8"):
            self._sync.tick_image_frame(buf)


class Camera:
    """Acts as a wrapper class to provide a simple interface to a stream of camera frames. Each frame consists of motion vectors and a JPEG image. The frames are stored on an internal queue, ready to be read by any subsequent stage in the system."""

    def __init__(self, settings: CameraSettings):
        """Takes a :class:`~DynAIkonTrap.settings.CameraSettings` object to initialise and start the camera hardware."""

        self.resolution = settings.resolution
        self.framerate = settings.framerate
        self._camera = PiCamera(resolution=self.resolution, framerate=self.framerate)
        sleep(2)  # Camera warmup

        self._output: QueueType[Frame] = Queue()
        synchroniser = Synchroniser(self._output)
        self._camera.start_recording(
            "/dev/null",
            format="h264",
            motion_output=MovementAnalyser(self._camera, synchroniser),
        )
        self._camera.start_recording(
            ImageReader(synchroniser),
            format="mjpeg",
            splitter_port=2,
            bitrate=settings.bitrate_bps,
        )
        logger.debug("Camera started")

    def get(self) -> Frame:
        """Retrieve the next frame from the camera

        Raises:
            Empty: If the camera has not captured any frames since the last call

        Returns:
            Frame: A frame from the camera video stream
        """
        try:
            return self._output.get(1 / self.framerate)

        except Empty:
            logger.error("No frames available from Camera")
            self._no_frames = True
            raise Empty

    def empty(self) -> bool:
        """Indicates if the queue of buffered frames is empty

        Returns:
            bool: ``True`` if there are no more frames, otherwise ``False``
        """
        return self._output.empty()

    def close(self):
        self._camera.stop_recording()
