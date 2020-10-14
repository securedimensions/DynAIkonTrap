from time import sleep, time
import numpy as np
from multiprocessing import Queue
from multiprocessing.queues import Queue as QueueType
from dataclasses import dataclass
from typing import Tuple
from picamera import PiCamera
from picamera.array import PiMotionAnalysis

from DynAikonTrap.settings import CameraSettings
from DynAikonTrap.logging import get_logger

logger = get_logger(__name__)

@dataclass
class Frame:
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
        if buf.startswith(b'\xff\xd8'):
            self._sync.tick_image_frame(buf)


class Camera:
    def __init__(self, settings: CameraSettings):
        self.resolution = settings.resolution
        self.framerate = settings.framerate
        self._camera = PiCamera(resolution=self.resolution, framerate=self.framerate)
        sleep(2)  # Camera warmup

        self._output: QueueType[Frame] = Queue()
        synchroniser = Synchroniser(self._output)
        self._camera.start_recording(
            '/dev/null',
            format='h264',
            motion_output=MovementAnalyser(self._camera, synchroniser),
        )
        self._camera.start_recording(
            ImageReader(synchroniser), format='mjpeg', splitter_port=2
        )
        logger.debug('Camera started')

    def get(self) -> Frame:
        return self._output.get_nowait()

    def empty(self) -> bool:
        return self._output.empty()

    def close(self):
        self._camera.stop_recording()


class MockCamera(Camera):
    def __init__(self, **kwargs):
        self.resolution = (640, 480)
        self.framerate = 20
        self._output: QueueType[Frame] = Queue()
        from DynAikonTrap.tester import Tester, load_pickle
        from multiprocessing import Process
        from queue import Full

        data = load_pickle('DynAikonTrap/dog2.pk')
        truth = load_pickle('DynAikonTrap/dog2.pk.truth')

        # tester = Tester(data, truth)

        def runner(frame):
            if frame is None:
                return False
            self._output.put(Frame(frame['image'], frame['motion'], time()))
            return False

        def proc():
            # sleep(30)
            # while True:
            # print('{} frames on queue'.format(self._output.qsize()))
            tester = Tester(data, truth)
            try:
                tester.test(runner)
            except Full:
                print('Queue full: {} frames on queue'.format(self._output.qsize()))
                quit(-1)

        process = Process(target=proc, daemon=True)
        process.start()
