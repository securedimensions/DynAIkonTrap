"""
An interface for sending animal frames to a server. The `Sender` combines a frame with the most appropriate sensor log and sends these together via a HTTP POST request to the specified server.

The current server API is:\n
- Path: <server>/trap/capture\n
- Type: POST\n
- Files: The image frame encoded as JPEG\n
- Data: meta-data for the image reporesented in the following JSON:
```json
meta = {
            'trap_id': self._device_id,
            'time': time,
            'temperature': temp,
            'pressure': press,
            'brightness': light,
            'humidity': humidity,
        }
```
"""
from multiprocessing import Process
from typing import Dict, IO, Tuple, List
from tempfile import NamedTemporaryFile
from io import BytesIO, StringIO
from datetime import datetime, timezone
from os import listdir
from os.path import join
from json import dump

from requests import post
from requests.exceptions import HTTPError, ConnectionError
from numpy import asarray
import cv2  # pdoc3 can't handle importing individual OpenCV functions

from DynAIkonTrap.filtering import Filter
from DynAIkonTrap.sensor import SensorLogs, Reading
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import (
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
                    'start': frame_number,
                    'stop': frame_number,
                    'log': log,
                },
            )

            # Extend caption duration for a subsequent frame using the same log
            caption['stop'] += 1

            captions.update({key: caption})
        return captions

    def _video_time_to_str(self, video_time: float) -> str:
        ss = int(video_time % 60)
        ttt = (video_time % 60 - ss) * 1000
        mm = video_time // 60
        return '{:02.0f}:{:02.0f}.{:03.0f}'.format(mm, ss, ttt)

    def _reading_to_str(self, reading: Reading) -> str:
        if reading is None:
            return '?'
        return '{x.value}{x.units}'.format(x=reading)

    def _captions_dict_to_vtt(self, captions: Dict, framerate: float) -> str:
        vtt = 'WEBVTT \n'
        vtt += '\n'

        for key, caption in sorted(captions.items()):
            log = caption['log']
            if log is None:
                continue

            start_time = caption['start'] / framerate
            stop_time = caption['stop'] / framerate

            vtt += '{} --> {} - Sensor@{}\n'.format(
                self._video_time_to_str(start_time),
                self._video_time_to_str(stop_time),
                '{:%H:%M:%S}'.format(
                    datetime.fromtimestamp(log.timestamp, timezone.utc)
                ),
            )

            vtt += 'T: {} - RH: {} - L: {} - P: {}\n\n'.format(
                self._reading_to_str(log.temperature),
                self._reading_to_str(log.humidity),
                self._reading_to_str(log.brightness),
                self._reading_to_str(log.pressure),
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


class Output:
    """A base class to use for outputting captured images or videos. The `output_still()` and `output_video()` functions should be overridden with output method-specific implementations."""

    def __init__(self, settings: OutputSettings, read_from: Tuple[Filter, SensorLogs]):
        self._frame_queue = read_from[0]
        self._sensor_logs = read_from[1]
        self.framerate = self._frame_queue.framerate

        if settings.output_format == OutputFormat.VIDEO:
            self._reader = Process(target=self._read_frames_to_video, daemon=True)
        else:
            self._reader = Process(target=self._read_frames, daemon=True)
        self._reader.start()

    def close(self):
        self._reader.terminate()
        self._reader.join()

    def _read_frames(self):
        while True:
            frame = self._frame_queue.get()
            if frame is None:
                continue

            log = self._sensor_logs.get(frame.timestamp)
            if log is None:
                logger.warn('No sensor readings')
                self.output_still(image=frame.image, time=frame.timestamp)
            else:
                self.output_still(
                    image=frame.image,
                    time=frame.timestamp,
                    brightness=log.brightness,
                    humidity=log.humidity,
                    pressure=log.pressure,
                )

    def _read_frames_to_video(self):
        start_new = True
        start_time = 0
        caption_generator = VideoCaption(self._sensor_logs, self.framerate)
        while True:
            frame = self._frame_queue.get()

            # End of motion sequence
            if frame is None and not start_new:
                start_new = True
                writer.release()
                captions = caption_generator.generate_vtt_for(frame_timestamps)
                self.output_video(video=file, caption=captions, time=start_time)
                file.close()
                continue

            decoded_image = cv2.imdecode(asarray(frame.image), cv2.IMREAD_COLOR)

            # Start of motion sequence
            if start_new:
                start_new = False
                start_time = frame.timestamp
                frame_timestamps = []
                file = NamedTemporaryFile(suffix='.mp4')

                writer = cv2.VideoWriter(
                    file.name,
                    cv2.VideoWriter_fourcc(*'avc1'),
                    self.framerate,
                    (decoded_image.shape[1], decoded_image.shape[0]),
                )

            writer.write(decoded_image)
            frame_timestamps.append(frame.timestamp)

    def output_still(self, image: bytes, time: float, **kwargs):
        """Output a still image with its sensor data. The sensor data can be provided via the keyword arguments.

        Args:
            image (bytes): The JPEG image frame
            time (float): UNIX timestamp when the image was captured
            **humidity (float): Humidity at or close to capture time
            **brightness (float): Brightness at or close to capture time
            **pressure (float): Pressure at or close to capture time
            **temperature (float): Temperature at or close to capture time
            **trap_id: ID of the camera trap

        Raises:
            NotImplementedError: A subclass should implement this function for the specific use-case e.g. writing to disk.
        """
        raise NotImplementedError()

    def output_video(self, video: IO[bytes], caption: StringIO, time: float, **kwargs):
        """Output a video with its meta-data. The sensor data is provided via the video captions (`caption`).

        Args:
            video (IO[bytes]): MP4 video (codec: H264 - MPEG-4 AVC (part 10))
            caption (StringIO): WebVTT caption of sensor readings
            time (float): UNIX timestamp when the image was captured

        Raises:
            NotImplementedError: A subclass should implement this function for the specific use-case e.g. writing to disk.
        """
        raise NotImplementedError()


class Sender(Output):
    """The Sender is a simple interface for sending the desired data to a server"""

    def __init__(self, settings: SenderSettings, read_from: Tuple[Filter, SensorLogs]):
        self._server = settings.server
        self._device_id = settings.device_id
        self._path_POST = settings.POST
        super().__init__(settings, read_from)

        logger.debug('Sender started (format: {})'.format(settings.output_format))

    def output_still(self, image: bytes, time: float, **kwargs):
        meta = {
            'trap_id': kwargs.get('trap_id'),
            'time': time,
            'temperature': kwargs.get('temperature'),
            'pressure': kwargs.get('pressure'),
            'brightness': kwargs.get('brightness'),
            'humidity': kwargs.get('humidity'),
        }
        files_dict = {'file': ('image', image, 'image/jpeg')}
        logger.debug('Sending capture, meta = {}'.format(meta))
        try:
            r = post(self._server + self._path_POST, data=meta, files=files_dict)
            r.raise_for_status()
        except HTTPError as e:
            logger.error(e)
        except ConnectionError as e:
            logger.error('Connection to server failed; could not send data')

    def output_video(self, video: IO[bytes], caption: StringIO, time: float, **kwargs):
        meta = {'trap_id': self._device_id, 'time': time}
        files_dict = {
            'video': ('video', video, 'video/mp4'),
            'caption': ('caption', caption, 'text/vtt'),
        }
        logger.debug('Sending video, meta = {}'.format(meta))
        try:
            r = post(self._server + self._path_POST, data=meta, files=files_dict)
            r.raise_for_status()
        except HTTPError as e:
            logger.error(e)
        except ConnectionError as e:
            logger.error('Connection to server failed; could not send data')


class Writer(Output):
    def __init__(self, settings: WriterSettings, read_from: Tuple[Filter, SensorLogs]):
        if settings.path == '':
            from os.path import abspath, dirname

            self._path = dirname(dirname(abspath(__file__)))  # Root of cloned git repo
        else:
            self._path = settings.path

        super().__init__(settings, read_from)

    def _unique_name(self, capture_time: float) -> str:

        # Get all filenames and remove extensions
        names = map(lambda x: x[0], map(lambda x: x.split('.'), listdir(self._path)))

        # Base the new file's name on the capture time
        name = '{:%Y-%m-%d_%H-%M-%S-%f}'.format(
            datetime.fromtimestamp(capture_time, timezone.utc)
        )
        counter = 0

        # If the name is already taken try adding a number
        while '{}_{}'.format(name, counter) in list(names):
            counter += 1

        name = '{}_{}'.format(name, counter)

        return join(self._path, name)

    def output_still(self, image: bytes, time: float, **kwargs):
        meta = {
            'trap_id': kwargs.get('trap_id'),
            'time': time,
            'temperature': kwargs.get('temperature'),
            'pressure': kwargs.get('pressure'),
            'brightness': kwargs.get('brightness'),
            'humidity': kwargs.get('humidity'),
        }
        name = self._unique_name(time)

        with open(name + '.jpg', 'wb') as f:
            f.write(image)

        with open(name + '.json', 'wb') as f:
            dump(meta, f)
        logger.debug('Image and meta-data saved')

    def output_video(self, video: IO[bytes], caption: StringIO, time: float, **kwargs):
        name = self._unique_name(time)

        with open(name + '.mp4', 'wb') as f:
            f.write(video.read())

        with open(name + '.vtt', 'w') as f:
            f.write(caption.getvalue())

        logger.debug('Video and caption saved')
