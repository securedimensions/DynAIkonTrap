"""
A simple interface to the frame animal filtering pipeline is provided by this module. It encapsulates both motion- and image-based filtering as well as any smoothing of this in time. Viewed from the outside the `Filter` reads from a `DynAIkonTrap.camera.Camera`'s output and in turn outputs only frames containing animals.

Internally frames are first analysed by the `DynAIkonTrap.filtering.motion.MotionFilter` and then, if sufficient motion is detected, placed on the `DynAIkonTrap.filtering.motion_queue.MotionQueue`. Within the queue the `DynAIkonTrap.filtering.animal.AnimalFilter` stage is applied with only the animal frames being returned as the output of this pipeline.

The output is accessible via a queue, which mitigates problems due to the burstiness of this stage's output and also allows the pipeline to be run in a separate process.
"""
from multiprocessing import Process, Queue
from multiprocessing.queues import Queue as QueueType
from queue import Empty

from DynAIkonTrap.camera import Frame, Camera
from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.filtering.motion_queue import MotionQueue
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import FilterSettings

logger = get_logger(__name__)


class Filter:
    """Wrapper for the complete image filtering pipeline"""

    def __init__(self, read_from: Camera, settings: FilterSettings):
        """
        Args:
            read_from (Camera): Read frames from this camera
            settings (FilterSettings): Settings for the filter pipeline
        """
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
        """Retrieve the next animal `Frame` from the filter pipeline's output

        Returns:
            Frame: An animal frame
        """
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
