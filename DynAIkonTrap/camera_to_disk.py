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
This module handles detection and recording of motion events to disk. This interfaces with :class:`~DynAIkonTrap.custom_picamera.DynCamera` to buffer streams of vectors, H264 data and a raw stream. 

Motion detection is performed within :class:`MotionRAMBuffer` by filtering each motion vectors for each frame using :class:`~DynAIkonTrap.filtering.motion.MotionFilter`. When motion is detected, the buffers are emptied to a location on disk for further processing. 

An output queue of emptied buffer directories is accessible via the output of :class:`CameraToDisk`. 
"""
from collections import deque
from logging import DEBUG, exception
from os import SEEK_CUR, nice
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
from threading import Thread

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
    """This class buffers motion vectors in RAM, runs a motion filter on each set of frame vectors and deposits buffers to disk when an event is required to be saved.

    Buffering is implemented by making use of two :class:`CircularIO` ring buffers - refered to as active and inactive streams. The active stream is being written when the camera is on and producing motion vectors. When saving is requested, the active and inactive streams are swapped, and the new inactive stream is written to disk and it's contents deleted. Motion vectors to be processed are added to an internal process queue, this ensures that the motion detector may skip over processing some vectors if filtering is taking too long per vector frame.

    Motion presence is accessible via a flag variable, is_motion.
    """

    def __init__(
        self,
        camera: DynCamera,
        settings: MotionFilterSettings,
        seconds: float,
        context_len_s: float,
    ) -> None:
        """Initialiser, creates two instances of :class:`CircularIO`. Each sized to be large enough to hold several seconds (configurable) of motion vector data.

        Args:
            camera (DynCamera): Camera instance buffering from
            settings (MotionFilterSettings): Settings for configuration of the motion filter.
            seconds (float): Number of seconds of motion vectors to buffer.
            context_len_s (float): Context and tail length for the detections.
        """
        (width, height) = camera.resolution
        (self._rows, self._cols) = MotionRAMBuffer.calc_rows_cols(width, height)
        self._element_size: int = MotionRAMBuffer.calc_motion_element_size(
            self._rows, self._cols
        )
        self._active_stream: CircularIO = CircularIO(
            self._element_size * seconds * camera.framerate
        )
        self._inactive_stream: CircularIO = CircularIO(
            self._element_size * seconds * camera.framerate
        )
        self._bytes_written: int = 0
        self._framerate = camera.framerate
        self._motion_filter = MotionFilter(settings, camera.framerate)
        self._context_len_s: float = context_len_s
        self._proc_queue = deque([], maxlen=100)
        self._target_time: float = 1.0 / (2.0 * camera.framerate)
        self.is_motion: bool = False
        self._threshold_sotv: float = settings.sotv_threshold
        super().__init__(camera)

        self._proc_thread = Thread(
            target=self._process_queue, name="motion process thread", daemon=True
        )
        self._proc_thread.start()

    def analyse(self, motion):
        """Add motion data to the internal process queue for analysis

        Args:
            motion : motion data to be added to queue
        """
        self._proc_queue.append(motion)

    def _process_queue(self):
        """This function processes vectors on the internal process queue to filter for motion. An aim is to compute motion detection within half a frame interval, as defined by the field _target_time. On some hardware platforms and some resolutions, detection time may go over this budget. In these cases, this function skips computing the next few vector frames to make up for lost time.
        In any case, this function writes a timestamp, motion score and motion vector data to the active stream. If the motion score has not been computed, a value of -1 is written instead.
        """
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
                    self.is_motion = motion_score > self._threshold_sotv
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

            except IndexError:
                sleep(0.1)
                pass

    def write_inactive_stream(self, filename: Path, is_start=False):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        Args:
            filename (Path): path to file
            is_start (bool): indicates if this buffer starts a new motion event
        """
        if is_start:

            current_pos = self._inactive_stream.tell()
            context_pos = max(
                0,
                int(current_pos
                    - (self._element_size * self._context_len_s * self._framerate)),
            )
            try:
                self._inactive_stream.seek(context_pos)
            except ValueError:
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
        """Deletes data in the inactive stream, sets stream position to 0."""
        self._inactive_stream.seek(0)
        self._inactive_stream.truncate()

    def switch_stream(self):
        """switch the active and inactive streams"""
        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )

    def calc_rows_cols(width: int, height: int) -> Tuple[int, int]:
        """Calculates the dimensions of motion vectors given a resolution

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
        """Calculates the size of a single motion element in the ring buffer

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
    """Class for storing video frames in RAM while motion detection is evaluated.

    Buffering is implemented by making use of two :class:`PiCameraCircularIO` ring buffers - refered to as active and inactive streams. The active stream is being written when the camera is on and producing frames. When saving is requested, the active and inactive streams are swapped, and the new inactive stream is written to disk and it's contents deleted.
    """

    def __init__(self, camera: DynCamera, splitter_port: int, size: int) -> None:
        """Initialise stream object.

        Args:
            camera (DynCamera): Camera instance
            splitter_port (int): Splitter port number, range [1-3], indicates PiCamera port for connection to underlying stream
            size (int): Maximum size of a ring buffer, measured in bytes

        """
        self._active_stream: PiCameraCircularIO = PiCameraCircularIO(
            camera, size=size, splitter_port=splitter_port
        )
        self._inactive_stream: PiCameraCircularIO = PiCameraCircularIO(
            camera, size=size, splitter_port=splitter_port
        )
        self._bytes_written: int = 0
        self._framerate = camera.framerate
        self._frac_full: float = 0.0

    def write(self, buf):
        """Write a frame buffer to the active stream

        Args:
            buf : frame buffer
        """
        self._bytes_written += self._active_stream.write(buf)

    def switch_stream(self):
        """switch the active and inactive streams"""

        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )

    def write_inactive_stream(self, filename: Path):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        Args:
            filename (Path): path to file
        """
        with open(filename, "ab") as output:
            while True:
                buf = self._inactive_stream.read1()
                if not buf:
                    break
                output.write(buf)
        self.clear_inactive_stream()

    def clear_inactive_stream(self):
        """Deletes the inactive stream"""
        self._inactive_stream.seek(0)
        self._inactive_stream.clear()


class H264RAMBuffer(VideoRAMBuffer):
    """This class inherits from :class:`~DynAIkonTrap.camera_to_disk.VideoRAMBuffer` to specialise for H264 image encoded frames."""

    def __init__(self, context_length_s, *args, **kwargs) -> None:
        self._context_length_s = context_length_s
        super(H264RAMBuffer, self).__init__(*args, **kwargs)

    def write_inactive_stream(self, filename: Path, is_start=False):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        May be used to start an event stream if is_start is set True. In this case, this function will recall frames from the buffer which occupy the context time. When a stream is started, this function searches for the nearest SPS header to start the H264 encoded stream. As a result, the start index may not be exactly equal to context start time index. The affect of this can be limited by increasing intra-frame frequency - at the expense of stream compression ratio.

        Args:
            filename (Path): path to write the stream to
            is_start (bool, optional): Indicates if this should start a new event stream on disk. Defaults to False.
        """
        if is_start:
            try:
                lst_frames = list(self._inactive_stream.frames)
                # get context index
                context_index = int(
                    round(
                        max(
                            0,
                            len(lst_frames)
                            - (self._context_length_s * self._framerate),
                        )
                    )
                )
                # get sps frame indexes
                sps_frames = list(
                    filter(
                        lambda element: element[1].frame_type
                        == PiVideoFrameType.sps_header,
                        enumerate(lst_frames),
                    )
                )
                if len(sps_frames) > 0:
                    def get_closest_frame(frame_idx, sps_frames): return min(
                        sps_frames, key=lambda element: abs(
                            element[0] - context_index)
                    )[1]
                    # scroll to start frame, sps frame closest to context index
                    start_frame = get_closest_frame(context_index, sps_frames)
                    self._inactive_stream.seek(start_frame.position)
                    return super().write_inactive_stream(filename)
                else:
                    # if no sps frames, discard the stream
                    self.clear_inactive_stream()
            except (IndexError, ValueError) as e:
                print(e)
                logger.error(
                    "Problem writing the first H264 frame, buffer abandoned")
                self.clear_inactive_stream()
        else:
            self._inactive_stream.seek(0)
            return super().write_inactive_stream(filename)


class RawRAMBuffer(VideoRAMBuffer):
    """This class inherits from :class:`~DynAIkonTrap.camera_to_disk.VideoRAMBuffer` to specialise for raw format image frames."""

    def __init__(self, context_length_s, camera: DynCamera, *args, **kwargs) -> None:
        self._context_length_s = context_length_s

        super(RawRAMBuffer, self).__init__(camera, *args, **kwargs)
        self._raw_framerate = self._framerate // camera.raw_divisor

    def write_inactive_stream(self, filename: Path, is_start=False):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        May be used to start an event stream if is_start is set True. In this case, this function will recall frames from the buffer which occupy the context time.

        Args:
            filename (Path): path to write the stream to
            is_start (bool, optional): Indicates if this should start a new event stream on disk. Defaults to False.
        """
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
        """Searches for a new directory path for motion event until an unoccupied one is found


        Returns:
            Tuple[Path, str]: Event directory
        """

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
    """Wraps :class:`~DynAIkonTrap.custom_picamera.DynCamera` functionality to stream motion events to disk."""

    def __init__(
        self,
        camera_settings: CameraSettings,
        writer_settings: WriterSettings,
        filter_settings: FilterSettings,
    ):
        """Initialiser, creates instance of camera and buffers for catching it's output.

        Args:
            camera_settings (CameraSettings): settings object for camera construction
            writer_settings (WriterSettings): settings object for writing out events
            filter_settings (FilterSettings): settings object for filter parameters
        """
        self.resolution = camera_settings.resolution
        self._buffer_secs = camera_settings.io_buffer_size_s
        self.bitrate = camera_settings.bitrate_bps
        self._raw_stream_image_format = camera_settings.raw_stream_image_format
        self.bits_per_pixel_raw = 0
        self.raw_image_format = RawImageFormat(
            camera_settings.raw_stream_image_format)
        if self.raw_image_format is RawImageFormat.RGBA:
            self.bits_per_pixel_raw = 4
        elif self.raw_image_format is RawImageFormat.RGB:
            self.bits_per_pixel_raw = 3
        self.raw_frame_dims = NetworkInputSizes.YOLOv4_TINY
        self.framerate = camera_settings.framerate
        self._camera = DynCamera(
            raw_divisor=camera_settings.raw_framerate_divisor,
            resolution=camera_settings.resolution,
            framerate=camera_settings.framerate,
        )

        self._on = True
        self._context_length_s = filter_settings.processing.context_length_s

        self._maximum_event_length_s: float = (
            filter_settings.processing.max_sequence_period_s
        )

        self._output_queue: QueueType[str] = Queue()
        self._h264_buffer: H264RAMBuffer = H264RAMBuffer(
            filter_settings.processing.context_length_s,
            self._camera,
            splitter_port=1,
            size=(camera_settings.bitrate_bps *
                  camera_settings.io_buffer_size_s) // 8,
        )
        self._raw_buffer: RawRAMBuffer = RawRAMBuffer(
            filter_settings.processing.context_length_s,
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
            filter_settings.processing.context_length_s,
        )
        self._directory_maker: DirectoryMaker = DirectoryMaker(
            Path(writer_settings.path)
        )
        self._record_proc = Thread(
            target=self.record, name="camera recording process", daemon=True
        )
        self._record_proc.start()

    def record(self):
        """Function records streams from the camera to RAM buffers. When motion is detected, buffers are emptied in three stages. 1) motion occurs, initial buffers are emptied to fill context time. Here an event is started on disk. 2) while motion continues and the length of the event is smaller than the max. event length continue writing to disk and swapping buffers as they become full. 3) motion has ended, continue recording for a trail-off period equal to the context length. Finally switch buffers and empty one last time.

        When a motion event finishes, it's saved directory is added to the output queue.
        """
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

                if self._motion_buffer.is_motion:  # motion is detected!
                    logger.info("Motion detected, emptying buffers to disk.")
                    event_dir = current_path
                    motion_start_time = time()
                    last_buffer_empty_t = time()
                    self.empty_all_buffers(current_path, start=True)

                    # continue writing to buffers while motion
                    while (
                        self._motion_buffer.is_motion
                        and (time() - motion_start_time) < self._maximum_event_length_s
                    ):
                        # check if buffers are getting near-full, to keep all three buffers in sync this is done by simply checking the time.
                        if (time() - last_buffer_empty_t) > (0.75 * self._buffer_secs):
                            last_buffer_empty_t = time()
                            self.empty_all_buffers(current_path, start=False)
                        self._camera.wait_recording(1)
                    # motion finished, wait for trail-off period
                    self._camera.wait_recording(self._context_length_s)
                    # empty buffers
                    self.empty_all_buffers(current_path, start=False)
                    self._output_queue.put(event_dir)
                    logger.info(
                        "Motion ended, total event length: {:.2f}secs".format(
                            time() - motion_start_time
                        )
                    )

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
        """Switches and empties all three buffers. Switching is performed near-simultaneously. Writing may take longer.

        Args:
            current_path (Path): directory to write events
            start (bool): True if start of a new motion event, False otherwise.
        """
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
