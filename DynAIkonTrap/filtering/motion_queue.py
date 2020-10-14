from dataclasses import dataclass
from typing import Any, List
from enum import Enum
from multiprocessing import Process, Queue, Semaphore
from multiprocessing.queues import Queue as QueueType
from time import time

from DynAikonTrap.camera import Frame
from DynAikonTrap.logging import get_logger
from DynAikonTrap.settings import MotionQueueSettings

logger = get_logger(__name__)


class Label(Enum):
    EMPTY = 0
    ANIMAL = 1
    UNKNOWN = 2


@dataclass
class LabelledFrame:
    frame: Frame
    index: int
    priority: float  # Higher means more likely to be animal
    label: Label = Label.UNKNOWN


class MotionSequence:
    _frames: List[LabelledFrame]

    def __init__(self, smoothing_len):
        self._frames = []
        self.smoothing_len = smoothing_len
        self.complete = False
        self.labelled = False
        self._next_index = 0

    def _label(self, frames, val):
        for frame in frames:
            frame.label = val
            frame.priority = -1

        for frame in self._frames:
            if frame.label is Label.UNKNOWN:
                break
        else:
            self.labelled = True

    def label_as_animal(self, frame: LabelledFrame):
        frame_index = frame.index
        start = max(frame_index - self.smoothing_len, 0)
        stop = min(frame_index + self.smoothing_len, len(self._frames))
        self._label(self._frames[start : stop + 1], Label.ANIMAL)

    def label_as_empty(self, frame):
        self._label([frame], Label.EMPTY)

    def close_gaps(self):
        last_animal = None
        current_gap = 0
        for i, frame in enumerate(self._frames):

            if frame.label == Label.ANIMAL:

                if current_gap <= self.smoothing_len * 2:
                    self._label(self._frames[i - current_gap : i], Label.ANIMAL)

                last_animal = i
                current_gap = 0

            elif frame.label == Label.EMPTY or frame.label == Label.UNKNOWN:
                if last_animal is not None:
                    current_gap += 1

    def put(self, frame, motion_score):
        self._frames.append(
            LabelledFrame(frame=frame, index=self._next_index, priority=motion_score)
        )
        self._next_index += 1

    def get_highest_priority(self):
        highest_priority_frame = max(self._frames, key=lambda frame: frame.priority)
        if highest_priority_frame.priority < 0:
            return None
        return highest_priority_frame

    def get_animal_frames(self) -> List[LabelledFrame]:
        return list(filter(lambda frame: frame.label == Label.ANIMAL, self._frames))

    def __len__(self):
        return len(self._frames)


class MotionQueue:
    def __init__(
        self, settings: MotionQueueSettings, animal_detector, output_callback, framerate
    ):
        self._smoothing_len = int((settings.max_sequence_period_s * framerate) / 2)
        self._sequence_len = framerate * settings.max_sequence_period_s
        self._current_sequence = MotionSequence(self._smoothing_len)
        self._queue: QueueType[MotionSequence] = Queue()
        self._animal_detector = animal_detector
        self._output_callback = output_callback

        self._sem = Semaphore(0)
        self._process = Process(target=self._process_queue, daemon=True)
        self._process.start()

    def put(self, frame, motion_score):
        if len(self._current_sequence) >= self._sequence_len:
            self.end_motion_sequence()
        self._current_sequence.put(frame, motion_score)

    def end_motion_sequence(self):
        current_len = len(self._current_sequence)
        if current_len > 0:
            self._queue.put(self._current_sequence)
            self._current_sequence = MotionSequence(self._smoothing_len)
            self._sem.release()
            logger.info(
                'End of motion; motion sequence queued ({} frames will take <=~{:.0f}s)'.format(
                    current_len,
                    current_len / 0.5,  # 0.5 FPS
                )
            )

    def _process_queue(self):
        while True:

            self._sem.acquire()

            sequence = self._queue.get()

            t_start = time()
            frame = sequence.get_highest_priority()
            while frame:
                is_animal = self._animal_detector.run(frame.frame.image)
                if is_animal:
                    sequence.label_as_animal(frame)
                else:
                    sequence.label_as_empty(frame)
                frame = sequence.get_highest_priority()

            sequence.close_gaps()
            t_stop = time()
            t = t_stop - t_start
            logger.info(
                'It took {:.1f}s to process {} frames ({} animal) => ~{:.2f}FPS'.format(
                    t,
                    len(sequence),
                    len(sequence.get_animal_frames()),
                    len(sequence) / t,
                )
            )

            self._output_callback(
                list(map(lambda frame: frame.frame, sequence.get_animal_frames()))
            )

    def is_idle(self) -> bool:
        return self._queue.empty()

    def close(self):
        self._process.terminate()
        self._process.join()
