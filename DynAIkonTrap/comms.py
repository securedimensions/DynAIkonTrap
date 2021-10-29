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
An interface for writing animal frames to disk or sending them to a server. The ``AbstractOutput`` combines a frame(s) with the most appropriate sensor log(s) and outputs these.
"""
from abc import ABCMeta, abstractmethod
from multiprocessing import Process
from typing import Dict, IO, Tuple, List, Union
from tempfile import NamedTemporaryFile
from io import StringIO
from datetime import datetime, timezone
from pathlib import Path
from os import listdir, nice
from os.path import join
from json import dump, dumps
from subprocess import call

from requests import post
from requests.exceptions import HTTPError, ConnectionError
from numpy import asarray
import cv2  # pdoc3 can't handle importing individual OpenCV functions

from DynAIkonTrap.filtering.filtering import Filter, FilterMode
from DynAIkonTrap.sensor import SensorLog, SensorLogs, Reading
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import (
    OutputVideoCodec,
    OutputMode,
    SenderSettings,
    OutputFormat,
    OutputSettings,
    WriterSettings,
)

logger = get_logger(__name__)


class VideoCaption:
    """Class to aid in generating captions for video output. The captions are based on the logged sensor readings."""

    def __init__(self, sensor_logs: SensorLogs, framerate: float):
        """
        Args:
            sensor_logs (SensorLogs): The object containing the log of sensor readings
            framerate (float): Camera framerate
        """
        self._sensor_logs = sensor_logs
        self._framerate = framerate

    def _generate_captions_dict(self, timestamps: List[float]) -> Dict:
        """NOTE: If sensor readings do not line up with frame capturing, there may be slight off-by-one style errors."""
        captions = {}
        for frame_number, timestamp in enumerate(timestamps):
            # Retrieve the corresponding log
            log = self._sensor_logs.get(timestamp)

            # Get existing or create new caption with this log
            key = int(
                frame_number // (self._framerate * self._sensor_logs.read_interval)
            )
            caption = captions.get(
                key,
                {
                    "start": frame_number,
                    "stop": frame_number,
                    "log": log,
                },
            )

            # Extend caption duration for a subsequent frame using the same log
            caption["stop"] += 1

            captions.update({key: caption})
        return captions

    def _video_time_to_str(self, video_time: float) -> str:
        ss = int(video_time % 60)
        ttt = (video_time % 60 - ss) * 1000
        mm = video_time // 60
        return "{:02.0f}:{:02.0f}.{:03.0f}".format(mm, ss, ttt)

    def _reading_to_str(self, reading: Reading) -> str:
        if reading is None:
            return "?"
        return "{x.value}{x.units}".format(x=reading)

    def _captions_dict_to_vtt(self, captions: Dict, framerate: float) -> str:
        vtt = "WEBVTT \n"
        vtt += "\n"

        for key, caption in sorted(captions.items()):
            log: SensorLog = caption["log"]
            if log is None:
                continue

            start_time = caption["start"] / framerate
            stop_time = caption["stop"] / framerate

            vtt += "{} --> {} - Sensor@{}\n".format(
                self._video_time_to_str(start_time),
                self._video_time_to_str(stop_time),
                "{:%H:%M:%S}".format(
                    datetime.fromtimestamp(log.system_time, timezone.utc)
                ),
            )

            vtt += "T: {} - RH: {} - L: {} - P: {}\n\n".format(
                self._reading_to_str(log.readings.get("SKEW_TEMPERATURE")),
                self._reading_to_str(log.readings.get("HUMIDITY")),
                self._reading_to_str(log.readings.get("BRIGHTNESS")),
                self._reading_to_str(log.readings.get("ATMOSPHERIC_PRESSURE")),
            )
        return vtt

    def generate_vtt_for(self, timestamps: List[float]) -> StringIO:
        """Generate WebVTT captions containing the sensor readings at given moments in time.

        Args:
            timestamps (List[float]): Timestamps for every frame in the motion/animal sequence

        Returns:
            StringIO: The WebVTT captions ready to be sent to a server
        """
        captions = self._generate_captions_dict(timestamps)
        return StringIO(self._captions_dict_to_vtt(captions, self._framerate))

    def generate_sensor_json(self, timestamps: List[float]) -> StringIO:
        """Generate JSON captions containing the sensor readings at given moments in time.

        The format is as follows:

        .. code:: json

           [
               {
                   "start": 0,
                   "end": 1,
                   "log": {
                       "EXAMPLE_SENSOR_1": {
                           "value": 0.0,
                           "units": "x"
                       },
                       "EXAMPLE_SENSOR_2": {
                           "value": 0.0,
                           "units": "x"
                       }
                   }
               },
               {
                   "start": 1,
                   "end": 5,
                   "logs": {}
               }
           ]


        The ``"start"`` and ``"end"`` correspond to the frame numbers in which the sensor logs are valid. The frame numbers are inclusive. It is not guaranteed that all frames are covered by logs. There may also be also be overlaps between entries if the exact timestamp where a new set of sensor readings becomes valid occurs during a frame.

        Args:
            timestamps (List[float]): Timestamps for every frame in the motion/animal sequence

        Returns:
            StringIO: The JSON captions wrapped in a :class:`StringIO`, ready for writing to file
        """
        captions = self._generate_captions_dict(timestamps)
        logger.debug(captions)

        json_captions = []
        for c in captions.values():
            log = c["log"]
            if log != None:
                json_captions.append(
                    {"start": c["start"], "end": c["stop"], "log": log.serialise()}
                )
        return StringIO(dumps(json_captions))


class AbstractOutput(metaclass=ABCMeta):
    """A base class to use for outputting captured images or videos. The :func:`output_still` and :func:`output_video` functions should be overridden with output method-specific implementations."""

    def __init__(self, settings: OutputSettings, read_from: Tuple[Filter, SensorLogs]):
        self._animal_queue = read_from[0]
        self._sensor_logs = read_from[1]
        self.framerate = self._animal_queue.framerate
        self._video_codec = settings.output_codec.name
        if settings.output_codec == OutputVideoCodec.H264:
            self._video_suffix = ".mp4"
        elif settings.output_codec == OutputVideoCodec.PIM1:
            self._video_suffix = ".avi"
        else:
            logger.error(
                "Invalid video codec (codec: {}); cannot form output suffix".format(
                    settings.output_codec.name
                )
            )

        if settings.output_format == OutputFormat.VIDEO:
            if self._animal_queue.mode == FilterMode.BY_FRAME:
                self._reader = Process(target=self._read_frames_to_video, daemon=True)
            elif self._animal_queue.mode == FilterMode.BY_EVENT:
                self._reader = Process(target=self._read_events_to_video, daemon=True)

        elif settings.output_format == OutputFormat.STILL:
            if self._animal_queue.mode == FilterMode.BY_FRAME:
                self._reader = Process(target=self._read_frames_to_image, daemon=True)
            elif self._animal_queue.mode == FilterMode.BY_EVENT:
                self._reader = Process(target=self._read_events_to_image, daemon=True)

        self._reader.start()

    def close(self):
        self._reader.terminate()
        self._reader.join()

    def _read_frames_to_image(self):
        while True:
            frame = self._animal_queue.get()
            if frame is None:
                continue

            log = self._sensor_logs.get(frame.timestamp)
            if log is None:
                logger.warning("No sensor readings")
                self.output_still(image=frame.image, time=frame.timestamp)
            else:
                self.output_still(
                    image=frame.image, time=frame.timestamp, sensor_log=log
                )

    def _read_frames_to_video(self):
        start_new = True
        start_time = 0
        caption_generator = VideoCaption(self._sensor_logs, self.framerate)
        while True:
            frame = self._animal_queue.get()

            # End of motion sequence
            if frame is None and not start_new:
                start_new = True
                writer.release()
                captions = caption_generator.generate_sensor_json(frame_timestamps)
                self.output_video(video=file, caption=captions, time=start_time)
                file.close()
                continue

            decoded_image = cv2.imdecode(asarray(frame.image), cv2.IMREAD_COLOR)

            # Start of motion sequence
            if start_new:
                start_new = False
                start_time = frame.timestamp
                frame_timestamps = []

                file = NamedTemporaryFile(suffix=self._video_suffix)

                writer = cv2.VideoWriter(
                    file.name,
                    cv2.VideoWriter_fourcc(*self._video_codec),
                    self.framerate,
                    (decoded_image.shape[1], decoded_image.shape[0]),
                )

            writer.write(decoded_image)
            frame_timestamps.append(frame.timestamp)

    def _read_events_to_video(self):
        nice(4)
        caption_generator = VideoCaption(self._sensor_logs, self.framerate)
        while True:
            try:
                event = self._animal_queue.get()

                start_time = event.start_timestamp
                file = NamedTemporaryFile(suffix=self._video_suffix)
                call(
                    [
                        "nice -n 5 ffmpeg -framerate {} -i {} -c copy {} -y".format(
                            self.framerate, join(event.dir, "clip.h264"), file.name
                        )
                    ],
                    shell=True,
                )
                caption = caption_generator.generate_sensor_json(
                    [event.start_timestamp]
                )
                self.output_video(
                    video=file, caption=caption, time=event.start_timestamp
                )
                file.close()
            except Exception as e:
                pass

    def _read_events_to_image(self):
        while True:
            try:
                event = self._animal_queue.get()
                vidcap = cv2.VideoCapture(join(event.dir, "clip.h264"))
                success, image = vidcap.read()
                log = self._sensor_logs.get(event.start_timestamp)
                while success:
                    if log is None:
                        logger.warning("No sensor readings")
                        self.output_still(image=image, time=event.start_timestamp)
                    else:
                        self.output_still(
                            image=image, time=event.start_timestamp, sensor_log=log
                        )
                    success, image = vidcap.read()
            except Exception as e:
                pass

    @abstractmethod
    def output_still(self, image: bytes, time: float, sensor_log: SensorLog):
        """Output a still image with its sensor data. The sensor data can be provided via the keyword arguments.

        Args:
            image (bytes): The JPEG image frame
            time (float): UNIX timestamp when the image was captured
            sensor_log (SensorLog): Log of sensor values at time frame was captured
        """
        pass

    @abstractmethod
    def output_video(self, video: IO[bytes], caption: StringIO, time: float, **kwargs):
        """Output a video with its meta-data. The sensor data is provided via the video captions (``caption``).

        Args:
            video (IO[bytes]): MP4 video (codec: H264 - MPEG-4 AVC (part 10))
            caption (StringIO): Caption of sensor readings as produced by :func:`VideoCaption.generate_sensor_json()`
            time (float): UNIX timestamp when the image was captured
        """
        pass


class Sender(AbstractOutput):
    """The Sender is a simple interface for sending the desired data to a server"""

    def __init__(self, settings: SenderSettings, read_from: Tuple[Filter, SensorLogs]):
        self._server = settings.server
        self._device_id = settings.device_id
        self._path_POST = settings.POST
        super().__init__(settings, read_from)

        logger.debug("Sender started (format: {})".format(settings.output_format))

    def output_still(self, image: bytes, time: float, sensor_log: SensorLog):

        files_dict = {"file": ("image", image, "image/jpeg")}
        logger.debug("Sending capture, meta = {}".format(sensor_log))
        try:
            r = post(self._server + self._path_POST, data=sensor_log, files=files_dict)
            r.raise_for_status()
            logger.info("Image sent")
        except HTTPError as e:
            logger.error(e)
        except ConnectionError as e:
            logger.error("Connection to server failed; could not send data")

    def output_video(self, video: IO[bytes], caption: StringIO, time: float, **kwargs):
        meta = {"trap_id": self._device_id, "time": time}
        files_dict = {
            "video": ("video", video, "video/mp4"),
            "caption": ("caption", caption, "text/vtt"),
        }
        try:
            r = post(self._server + self._path_POST, data=meta, files=files_dict)
            r.raise_for_status()
            logger.info("Video sent")
        except HTTPError as e:
            logger.error(e)
        except ConnectionError as e:
            logger.error("Connection to server failed; could not send data")


class Writer(AbstractOutput):
    def __init__(self, settings: WriterSettings, read_from: Tuple[Filter, SensorLogs]):

        path = Path(settings.path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        self._path = path.resolve()
        super().__init__(settings, read_from)
        logger.debug("Writer started (format: {})".format(settings.output_format))

    def _unique_name(self, capture_time: float) -> str:

        # Get all filenames and remove extensions
        names = map(lambda x: x[0], map(lambda x: x.split("."), listdir(self._path)))

        # Base the new file's name on the capture time
        name = "{:%Y-%m-%d_%H-%M-%S-%f}".format(
            datetime.fromtimestamp(capture_time, timezone.utc)
        )
        counter = 0

        # If the name is already taken try adding a number
        while "{}_{}".format(name, counter) in list(names):
            counter += 1

        name = "{}_{}".format(name, counter)

        return join(self._path, name)

    def output_still(self, image: bytes, time: float, sensor_log: SensorLog):

        name = self._unique_name(time)

        with open(name + ".jpg", "wb") as f:
            f.write(image)

        with open(name + ".json", "w") as f:
            dump(sensor_log.serialise(), f)
        logger.info("Image and meta-data saved")

    def output_video(self, video: IO[bytes], caption: StringIO, time: float, **kwargs):
        name = self._unique_name(time)

        with open(name + self._video_suffix, "wb") as f:
            f.write(video.read())

        with open(name + ".json", "w") as f:
            f.write(caption.getvalue())

        logger.info("Video and caption saved")


def Output(
    settings: OutputSettings, read_from: Tuple[Filter, SensorLogs]
) -> Union[Sender, Writer]:
    """Generator function to provide an implementation of the :class:`~AbstractOutput` based on the :class:`~DynAIkonTrap.settings.OutputMode` of the ``settings`` argument."""
    if settings.output_mode == OutputMode.SEND:
        Sender(settings=settings, read_from=read_from)
    else:
        Writer(settings=settings, read_from=read_from)
