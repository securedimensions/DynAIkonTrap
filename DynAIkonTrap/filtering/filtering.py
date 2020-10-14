from multiprocessing import Process, Queue
from multiprocessing.queues import Queue as QueueType
from queue import Empty

from DynAikonTrap.camera import Frame, Camera
from DynAikonTrap.filtering.animal import AnimalFilter
from DynAikonTrap.filtering.motion import MotionFilter
from DynAikonTrap.filtering.motion_queue import MotionQueue
from DynAikonTrap.logging import get_logger
from DynAikonTrap.settings import FilterSettings

logger = get_logger(__name__)


class Filter:
    def __init__(self, read_from: Camera, settings: FilterSettings):
        framerate = read_from.framerate

        self._input_queue = read_from
        self._output_queue: QueueType[Frame] = Queue()

        self._motion_filter = MotionFilter(
            settings=settings.motion, framerate=framerate
        )
        self._motion_threshold = settings.motion.sotv_threshold

        self._animal_filter = AnimalFilter(settings=settings.animal)
        self._motion_queue = MotionQueue(
            animal_detector=self._animal_filter,
            output_callback=lambda frames: [self._output_queue.put(f) for f in frames],
            settings=settings.motion_queue,
            framerate=framerate,
        )

        self._usher = Process(target=self._handle_input, daemon=True)
        self._usher.start()
        logger.debug('Filter started')

    def get(self) -> Frame:
        return self._output_queue.get()

    def close(self):
        self._usher.terminate()
        self._usher.join()

    def _handle_input(self):
        while True:

            if not self._input_queue.empty():
                try:
                    frame = self._input_queue.get()
                except Empty:
                    continue

                motion_score = self._motion_filter.run_raw(frame.motion)
                motion_detected = motion_score >= self._motion_threshold

                if motion_detected:
                    self._motion_queue.put(frame, motion_score)

                else:
                    self._motion_queue.end_motion_sequence()
