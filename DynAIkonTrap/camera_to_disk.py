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
from collections import deque
from ctypes import resize, sizeof
from logging import DEBUG, exception
from math import ceil
from os import nice
from io import open
from queue import Empty
from pathlib import Path
from time import sleep, time
import numpy as np
from struct import pack, unpack
from multiprocessing import Event, Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from typing import Tuple
from random import randint
from threading import Thread
import picamera
from picamera import camera

from DynAIkonTrap.filtering.animal import AnimalFilter


try:
    from picamera import PiCamera
    from picamera.array import PiMotionAnalysis
    from picamera.streams import PiCameraCircularIO, CircularIO
    from picamera.frames import PiVideoFrame, PiVideoFrameType
except (OSError, ModuleNotFoundError):
    # Ignore error that occurs when running pdoc3
    class PiMotionAnalysis:
        pass


from DynAIkonTrap.custom_picamera import DynCamera
from DynAIkonTrap.filtering.animal import NetworkInputSizes
from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.settings import (
    CameraSettings,
    FilterSettings,
    RawImageFormat,
    WriterSettings,
    MotionFilterSettings,
)
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MotionData:
    """Class for holding a motion vector data type"""

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
        camera: DynCamera,
        settings: MotionFilterSettings,
        seconds: float,
        context_len_s: float,
    ) -> None:
        (width, height) = camera.resolution
        (self._rows, self._cols) = MotionRAMBuffer.calc_rows_cols(width, height)
        self._element_size = MotionRAMBuffer.calc_motion_element_size(
            self._rows, self._cols
        )
        buff_len = seconds * camera.framerate
        self._active_stream = CircularIO(self._element_size * buff_len)
        self._inactive_stream = CircularIO(self._element_size * buff_len)
        self._bytes_written = 0
        self._framerate = camera.framerate
        self._motion_filter = MotionFilter(settings, camera.framerate)
        self._context_len_s = context_len_s
        self._proc_queue = deque([], maxlen=100)
        self._target_time: float = 1.0 / (2.0 * camera.framerate)
        self._is_motion = False
        self._threshold_sotv = settings.sotv_threshold
        super().__init__(camera)

        self._proc_thread = Thread(
            target=self.process_queue, name="motion process thread", daemon=True
        )
        self._proc_thread.start()

    def analyse(self, motion):
        """Add motion data to the internal process queue for analysis

        Args:
            motion : motion data to be added to queue
        """
        self._proc_queue.append(motion)

    def process_queue(self):
        nice(0)
        skip_frames = 0
        count_frames = 0
        while True:
            try:
                buf = self._proc_queue.popleft()
                motion_frame = np.frombuffer(buf, MotionData.motion_dtype)
                motion_frame = motion_frame.reshape((self.rows, self.cols))
                motion_score: float = -1.0
                if count_frames >= skip_frames:
                    start = time()
                    motion_score = self._motion_filter.run_raw(motion_frame)
                    self._is_motion = motion_score > self._threshold_sotv
                    end = time()
                    skip_frames = round((end - start) / self._target_time)
                    count_frames = 0
                count_frames += 1
                motion_bytes = (
                    pack("d", float(time()))
                    + pack("d", float(motion_score))
                    + bytearray(motion_frame)
                )
                self._bytes_written += self._active_stream.write(motion_bytes)

            except:
                sleep(0.1)
                pass

    def compute_used_space(self) -> float:
        """computes the fraction of the active ring buffer filled up thus far

        Returns:
            float: fraction representing full space in ring buffer
        """
        return float(self._bytes_written / self._active_stream.size)

    def write_inactive_stream(self, filename: Path, is_start=False):
        """write the inactive buffer to file

        Args:
            filename (Path): path to file
        """
        if is_start:
            current_pos = self._inactive_stream.seek(1)
            context_pos = max(
                0,
                current_pos
                - (self._element_size * self._context_len_s * self._framerate),
            )
            try:
                self._inactive_stream.seek(context_pos)
            except:
                logger.error(
                    "cannot seek to context position for motion vector buffer, buffer abandoned"
                )
                return self.clear_inactive_stream()
        else:
            self._inactive_stream.seek(0)

        with open(filename, "ab") as output:
            while True:
                buf = self._inactive_stream.read1()
                if not buf:
                    break
                output.write(buf)
        self.clear_inactive_stream()

    def clear_inactive_stream(self):
        self._inactive_stream.seek(0)
        self._inactive_stream.truncate()

    def switch_stream(self):
        """switch the active and inactive streams"""
        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )
        self._bytes_written = 0

    def get_motion_flag(self) -> bool:
        """poll the observed motion flag, resets flag to false after polling

        Returns:
            bool: motion flag, true if motion observed
        """
        ret = self._is_motion
        self._is_motion = False
        return ret

    def calc_rows_cols(width: int, height: int) -> Tuple[int, int]:
        """calculate the dimensions of motion vectors given a resolution

        Args:
            width (int): resolution width in pixels
            height (int):  resolution height in pixels

        Returns:
            Tuple[int, int]: motion vector row, column dimensions
        """
        cols = ((width + 15) // 16) + 1
        rows = (height + 15) // 16
        return (rows, cols)

    def calc_motion_element_size(rows: int, cols: int) -> int:
        """calculates the size of a single motion element in the ring buffer

        Args:
            rows (int): motion vector row dimension
            cols (int): motion vector column dimension

        Returns:
            int: size (in bytes) of a single motion element. Computed as size of 2 floats (16 bytes) plus size of all motion vectors to fit input dimensions
        """
        return (len(pack("d", float(0.0))) * 2) + (
            rows * cols * MotionData.motion_dtype.itemsize
        )


class VideoRAMBuffer:
    """class for storing video frames in RAM while motion detection is evaluated. Frame storage is alternated between two ring-buffers of type `PiCameraCircularIO`."""

    def __init__(self, camera: DynCamera, splitter_port: int, size: int) -> None:
        """Initialise stream object.

        Args:
            camera (DynCamera): Picamera instance, used to initialise underlying buffers
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
        self._framerate = camera.framerate
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
        self.compute_used_space()

    def write_inactive_stream(self, filename: Path):
        with open(filename, "ab") as output:
            while True:
                buf = self._inactive_stream.read1()
                if not buf:
                    break
                output.write(buf)
        self.clear_inactive_stream()

    def clear_inactive_stream(self):
        self._inactive_stream.seek(0)
        self._inactive_stream.clear()


class H264RAMBuffer(VideoRAMBuffer):
    def __init__(self, context_length_s, *args, **kwargs) -> None:
        self._context_length_s = context_length_s
        super(H264RAMBuffer, self).__init__(*args, **kwargs)

    def write_inactive_stream(self, filename: Path, is_start=False):
        if is_start:
            try:
                lst_frames = list(self._inactive_stream.frames)
                context_index = int(
                    round(
                        max(
                            0,
                            len(lst_frames)
                            - (self._context_length_s * self._framerate),
                        )
                    )
                )
                sps_frames = list(
                    filter(
                        lambda element: element[1].frame_type
                        == PiVideoFrameType.sps_header,
                        enumerate(lst_frames),
                    )
                )
                if len(sps_frames) > 0:
                    get_closest_frame = lambda frame_idx, sps_frames: min(
                        sps_frames, key=lambda element: abs(element[0] - context_index)
                    )[1]
                    start_frame = get_closest_frame(context_index, sps_frames)
                    self._inactive_stream.seek(start_frame.position)
                    return super().write_inactive_stream(filename)
                else:
                    self.clear_inactive_stream()
            except Exception as e:
                print(e)
                logger.error("Problem writing the first H264 frame, buffer abandoned")
                self.clear_inactive_stream()
        else:
            self._inactive_stream.seek(0)
            return super().write_inactive_stream(filename)


class RawRAMBuffer(VideoRAMBuffer):
    def __init__(self, context_length_s, camera: DynCamera, *args, **kwargs) -> None:
        self._context_length_s = context_length_s

        super(RawRAMBuffer, self).__init__(camera, *args, **kwargs)
        self._raw_framerate = self._framerate // camera.raw_divisor

    def write_inactive_stream(self, filename: Path, is_start=False):
        if is_start:
            lst_frames = list(self._inactive_stream.frames)
            context_index = int(
                round(
                    max(
                        0,
                        len(lst_frames)
                        - (self._context_length_s * self._raw_framerate),
                    )
                )
            )
            start_frame = lst_frames[context_index]
            self._inactive_stream.seek(start_frame.position)
            return super().write_inactive_stream(filename)

        else:
            self._inactive_stream.seek(0)
            return super().write_inactive_stream(filename)


class DirectoryMaker:
    """Creates new directories for storing motion events."""

    def __init__(self, base_dir: Path):
        """Takes a base Path object and initialises a directory factory for motion events.

        Args:
            base_dir (Path): base directory for storing motion event folders.
        """
        self._base_dir = base_dir
        self._event_counter = 0

    def get_event(self) -> Tuple[Path, str]:
        """Searches for a new directory path for motion event until a new one is found"""

        ret_path, ret_str = self.new_event()
        while ret_path.exists():
            ret_path, ret_str = self.new_event()
        ret_path.mkdir(parents=True, exist_ok=True)
        return (ret_path, ret_str)

    def new_event(self) -> Tuple[Path, str]:
        """Gives string name and directory path for a new motion event on disk"""

        ret_str = "event_" + str(self._event_counter)
        self._event_counter += 1
        ret_path = self._base_dir.joinpath(ret_str)
        return (ret_path, ret_str)


class CameraToDisk:
    """Wraps picamera functionality to stream motion events to disk."""

    def __init__(
        self,
        camera_settings: CameraSettings,
        writer_settings: WriterSettings,
        filter_settings: FilterSettings,
    ):
        """Takes a :class:`~DynAIkonTrap.settings.CameraSettings` object to initialise and start the camera hardware.

        Args:
            camera_settings (CameraSettings): settings object for camera construction
            writer_settings (WriterSettings): settings object for writing out events
        """
        self.resolution = camera_settings.resolution
        self._buffer_secs = camera_settings.io_buffer_size_s
        self.bitrate = camera_settings.bitrate_bps
        self._raw_stream_image_format = camera_settings.raw_stream_image_format
        self.bits_per_pixel_raw = 0
        if camera_settings.raw_stream_image_format == RawImageFormat.RGBA.value:
            self.bits_per_pixel_raw = 4
        elif camera_settings.raw_stream_image_format == RawImageFormat.RGB.value:
            self.bits_per_pixel_raw = 3
        self.raw_frame_dims = NetworkInputSizes.YOLOv4_TINY
        self.framerate = camera_settings.framerate
        self._camera = DynCamera(
            raw_divisor=camera_settings.raw_framerate_divisor,
            resolution=camera_settings.resolution,
            framerate=camera_settings.framerate,
        )

        self._on = True
        self._context_length_s = filter_settings.motion_queue.context_length_s

        self._maximum_event_length_s: float = (
            filter_settings.motion_queue.max_sequence_period_s
        )

        self._output_queue: QueueType[str] = Queue()
        self._h264_buffer: H264RAMBuffer = H264RAMBuffer(
            filter_settings.motion_queue.context_length_s,
            self._camera,
            splitter_port=1,
            size=(camera_settings.bitrate_bps * camera_settings.io_buffer_size_s) // 8,
        )
        self._raw_buffer: RawRAMBuffer = RawRAMBuffer(
            filter_settings.motion_queue.context_length_s,
            self._camera,
            splitter_port=2,
            size=(
                (
                    self.raw_frame_dims[0]
                    * self.raw_frame_dims[1]
                    * self.bits_per_pixel_raw
                )
                * (camera_settings.framerate // camera_settings.raw_framerate_divisor)
                * camera_settings.io_buffer_size_s
            ),
        )

        self._motion_buffer: MotionRAMBuffer = MotionRAMBuffer(
            self._camera,
            filter_settings.motion,
            self._buffer_secs,
            filter_settings.motion_queue.context_length_s,
        )
        self._directory_maker: DirectoryMaker = DirectoryMaker(
            Path(writer_settings.path)
        )
        self._record_proc = Thread(
            target=self.record, name="camera recording process", daemon=True
        )
        self._record_proc.start()

    def record(self):
        nice(0)
        current_path = self._directory_maker.get_event()[0]
        self._camera.start_recording(
            self._h264_buffer,
            format="h264",
            splitter_port=1,
            motion_output=self._motion_buffer,
            bitrate=self.bitrate,
            intra_period=int((self._context_length_s / 2) * self.framerate),
        )
        self._camera.start_recording(
            self._raw_buffer,
            format="rgba",
            splitter_port=2,
            resize=self.raw_frame_dims,
        )
        self._camera.wait_recording(5)  # camera warm-up

        try:
            while self._on:
                self._camera.wait_recording(1)

                if self._motion_buffer._is_motion:  # motion is detected!
                    print("motion detected!")
                    event_dir = current_path
                    motion_start_time = time()
                    last_buffer_empty_t = time()
                    self.empty_all_buffers(current_path, start=True)

                    # continue writing to buffers while motion
                    while (
                        self._motion_buffer._is_motion
                        and (time() - motion_start_time) < self._maximum_event_length_s
                    ):
                        # check if buffers are getting near-full
                        if (time() - last_buffer_empty_t) > (0.75 * self._buffer_secs):
                            last_buffer_empty_t = time()
                            self.empty_all_buffers(current_path, start=False)
                        self._camera.wait_recording(1)
                    # motion finished, wait for trail-off period
                    self._camera.wait_recording(self._context_length_s)
                    # empty buffers
                    self.empty_all_buffers(current_path, start=False)
                    self._output_queue.put(event_dir)

                    current_path = self._directory_maker.get_event()[0]
        finally:
            self._camera.stop_recording()

    def get(self) -> str:
        try:
            return self._output_queue.get()

        except Empty:
            logger.error("No events available from Camera")
            raise Empty

    def empty_all_buffers(self, current_path: Path, start: bool):
        # switch all buffers first
        self._h264_buffer.switch_stream()
        self._raw_buffer.switch_stream()
        self._motion_buffer.switch_stream()

        self._h264_buffer.write_inactive_stream(
            filename=current_path.joinpath("clip.h264"), is_start=start
        )
        self._raw_buffer.write_inactive_stream(
            filename=current_path.joinpath("clip.dat"), is_start=start
        )
        self._motion_buffer.write_inactive_stream(
            filename=current_path.joinpath("clip_vect.dat"), is_start=start
        )

    def empty_h264_buffer(self, current_path: Path, start: bool):
        if start:
            print("----looking for sps----")
            self._h264_buffer.write_inactive_stream(
                current_path.joinpath("clip.h264"),
                frametype=PiVideoFrameType.sps_header,
            )
        else:
            self._h264_buffer.write_inactive_stream(
                current_path.joinpath("clip.h264"), frametype=PiVideoFrameType.frame
            )

    def empty_raw_buffer(self, current_path: Path):
        self._raw_buffer.write_inactive_stream(
            current_path.joinpath("clip.dat"), frametype=PiVideoFrameType.frame
        )

    def empty_motion_buffer(self, current_path: Path):
        self._motion_buffer.write_inactive_stream(
            current_path.joinpath("clip_vect.dat")
        )
