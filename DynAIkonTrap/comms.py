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
from requests import post
from requests.exceptions import HTTPError, ConnectionError
from multiprocessing import Process
from typing import Tuple

from DynAIkonTrap.filtering import Filter
from DynAIkonTrap.sensor import SensorLogs
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import SenderSettings

logger = get_logger(__name__)


class Sender:
    """The Sender is a simple interface for sending the desired data to a server"""

    def __init__(self, settings: SenderSettings, read_from: Tuple[Filter, SensorLogs]):
        self._server = settings.server
        self._device_id = settings.device_id
        self._send = True
        self._path_POST = settings.POST

        self._frame_queue = read_from[0]
        self._sensor_logs = read_from[1]
        self._reader = Process(target=self._read_frames, daemon=True)
        self._reader.start()
        logger.debug('Sender started')

    def close(self):
        self._reader.terminate()
        self._reader.join()

    def _read_frames(self):
        while True:
            frame = self._frame_queue.get()
            log = self._sensor_logs.get(frame.timestamp)
            if log is None:
                logger.warn('No sensor readings')
                self.send(image=frame.image, time=frame.timestamp)
            else:
                self.send(
                    image=frame.image,
                    time=frame.timestamp,
                    brightness=log.brightness,
                    humidity=log.humidity,
                    pressure=log.pressure,
                )

    def send(self, **kwargs):
        """Queue the specified data for sending. Available keyword arguments:
        `image`, `time`, `temperature`, `pressure`, `light`. Others will simply be ignored as they are not implemented. This may change in the future, so that all are sent in the metadata.
        """
        image = kwargs.get('image', None)
        time = kwargs.get('time', None)
        temp = kwargs.get('temperature', None)
        press = kwargs.get('pressure', None)
        light = kwargs.get('light', None)
        humidity = kwargs.get('humidity', None)

        meta = {
            'trap_id': self._device_id,
            'time': time,
            'temperature': temp,
            'pressure': press,
            'brightness': light,
            'humidity': humidity,
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
