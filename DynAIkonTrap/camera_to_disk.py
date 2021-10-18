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
from ctypes import resize, sizeof
from math import ceil
from os import write
from io import open
from queue import Empty
from pathlib import Path
from time import sleep, time
import numpy as np
import struct
from multiprocessing import Event, Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from typing import Tuple
from random import randint
from DynAIkonTrap.filtering import motion

try:
    from picamera import PiCamera
    from picamera.array import PiMotionAnalysis
    from picamera.streams import PiCameraCircularIO, CircularIO
except (OSError, ModuleNotFoundError):
    # Ignore error that occurs when running pdoc3
    class PiMotionAnalysis:
        pass


from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.settings import CameraSettings, FilterSettings, WriterSettings
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EventData:
    """Data for a saved motion event on disk."""

    path: Path


@dataclass
class MotionData:
    """Data class for holding a motion frame"""

    motion_dtype = np.dtype(
        [
            ("x", "i1"),
            ("y", "i1"),
            ("sad", "u2"),
        ]
    )


class MotionRAMBuffer(PiMotionAnalysis):
    """A class for ushering motion vectors to the motion detector and into RAM and disk storage."""

    def __init__(
        self,
        camera: PiCamera,
        settings: MotionFilterSettings,
        seconds: float,
        divisor: int,
    ) -> None:
        width, height = camera.resolution
        self._cols = ((width + 15) // 16) + 1
        self._rows = (height + 15) // 16

        element_size = sizeof(float) + sizeof(float)(
            self._rows * self._cols * MotionData.motion_dtype.itemsize
        )
        buff_len = seconds * camera.framerate
        self._active_stream = CircularIO(element_size * buff_len)
        self._inactive_stream = CircularIO(element_size * buff_len)

        self._motion_filter = MotionFilter(settings, camera.framerate)

        self._proc_queue = Queue()
        self._target_time: float = 1.0 / 2.0 * self.camera.framerate

        super().__init__()

    def analyse(self, motion):
        """Add motion data to the internal process queue for analysis

        Args:
            motion : motion data to be added to queue
        """
        self._proc_queue.put_nowait(motion)

    def process_queue(self):
        skip_frames = 0
        count_frames = 0
        while True:
            try:
                buf = self._proc_queue.get()
                motion_frame = np.frombuffer(buf, MotionData.motion_dtype)
                motion_score: float = -1.0
                if count_frames >= skip_frames:
                    start = time()
                    motion_score = self._motion_filter.run_raw(motion_frame)
                    end = time()
                    skip_frames = ceil((end - start) / self._target_time)
                count_frames += 1
                motion_bytes = (
                    struct.pack("f", float(time()))
                    + struct.pack("f", motion_score)
                    + bytearray(motion_frame)
                )
                self._active_stream.write(motion_bytes)
            except Empty:
                pass

    def write_inactive_buffer(self, filename: Path):
        """write the inactive buffer to file

        Args:
            filename (Path): path to file
        """
        with open(filename, "ab") as output:
            self._inactive_stream.seek(0)
            while True:
                buf = self._inactive_stream.read1()
                if not buf:
                    break
                output.write(buf)
        self._inactive_stream.seek(0)
        self._inactive_stream.truncate()

    def switch_stream(self):
        """switch the active and inactive streams"""
        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )


class VideoRAMBuffer:
    """class for storing video frames in RAM while motion detection is evaluated. Frame storage is alternated between two ring-buffers of type `PiCameraCircularIO`."""

    def __init__(self, camera: PiCamera, splitter_port: int, size: int) -> None:
        """Initialise stream object.

        Args:
            camera (PiCamera): Picamera instance, used to initialise underlying buffers
            splitter_port (int): Splitter port number, range [0-3], indicates port for connection to underlying stream
            size (int): [description]. Maximum size of a ring buffer, measured in bytes

        """
        self._active_stream = PiCameraCircularIO(
            camera, size=size, splitter_port=splitter_port
        )
        self._inactive_stream = PiCameraCircularIO(
            camera, size=size, splitter_port=splitter_port
        )
        self._bytes_written: int = 0
        self._frac_full: float = 0.0
        self.compute_used_space()

    def write(self, buf):
        """Write a frame buffer to the active stream

        Args:
            buf ([type]): frame buffer
        """
        self._bytes_written += self._active_stream.write(buf)

    def compute_used_space(self) -> float:
        """computes the fraction of the active ring buffer filled up thus far

        Returns:
            float: fraction representing full space in ring buffer
        """
        self._frac_full = self._bytes_written / self._active_stream.size
        return self._frac_full

    def switch_stream(self):
        """switch the active and inactive streams"""

        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )
        self._bytes_written = 0

    def write_inactive_stream(self, filename: Path):
        pass


# class Synchroniser:
#     def __init__(self, output: QueueType):
#         self._last_image = None
#         self._output = output

#     def tick_movement_frame(self, motion):
#         if self._last_image is not None:
#             image = np.asarray(bytearray(self._last_image), dtype="uint8")
#         else:
#             return
#         self._output.put_nowait(Frame(image, motion, time()))

#     def tick_image_frame(self, image):
#         self._last_image = image


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

    def __init__(
        self, camera_settings: CameraSettings, writer_settings: WriterSettings, filter_settings: FilterSettings
    ):
        """Takes a :class:`~DynAIkonTrap.settings.CameraSettings` object to initialise and start the camera hardware.

        Args:
            camera_settings (CameraSettings): settings object for camera construction
            writer_settings (WriterSettings): settings object for writing out events
        """
        self._bitrate_bps = 10e6
        self._buffer_secs = 10
        self._raw_frame_wdt = 416
        self._raw_frame_hgt = 416
        self._raw_divisor = 5  # these concrete settings will go later.
        self._resolution = camera_settings.resolution
        self._framerate = camera_settings.framerate
        self._camera = PiCamera(resolution=self.resolution, framerate=self.framerate)
        self._on = True
        self._minimum_event_length_s: float = filter_settings.motion_queue.context_length_s
        self._maximum_event_length_s: float = filter_settings.motion_queue.max_sequence_period_s
        sleep(2)  # Camera warmup

        self._output: QueueType[EventData] = Queue()
        self._h264_buffer: VideoRAMBuffer = VideoRAMBuffer(
            self._camera,
            splitter_port=0,
            size=(self._bitrate_bps * self._buffer_secs) // 8,
        )
        self._raw_buffer: VideoRAMBuffer = VideoRAMBuffer(
            self._camera,
            splitter_port=1,
            size=(self._raw_frame_wdt * self._raw_frame_hgt * 4) // self._raw_divisor,
        )

        self._motion_buffer: MotionRAMBuffer = MotionRAMBuffer(self._camera, filter_settings.motion, self._buffer_secs)
    
        # self._synchroniser = Synchroniser(self._output)
        self._directory_factory = DirectoryFactory(writer_settings.path)

    def record(self):
        self._camera.start_recording(self._h264_buffer, format='h264', splitter_port=0, motion_output=self._motion_buffer, bitrate = self._bitrate_bps)
        self._camera.start_recording(self._raw_buffer, format='rgba', splitter_port=1, resize=(self._raw_frame_hgt, self._raw_frame_wdt))
        self._camera.wait_recording(5) #camera warm-up
        
        event_path, event_name  = self._directory_factory.new_event()
        try:
            while self._on:
                self._camera.wait_recording(self._minimum_event_length_s/2.0)
                
                if randint(0, 5) == 1: #motion is detected!
                    event_len_s = float(randint(0, self._maximum_event_length_s))
                    self._camera.wait_recording(self._minimum_event_length_s/2.0)
                    motion_start_time = time() - self._minimum_event_length_s/2

                    while time() - motion_start_time < event_len_s:
                        if self._h264_buffer.compute_used_space() > 0.75:
                            self._h264_buffer.switch_stream()
                            self._h264_buffer.write_inactive_stream()
        except:
            pass
