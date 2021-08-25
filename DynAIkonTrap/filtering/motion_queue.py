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
This module provides access to a :class:`~DynAIkonTrap.filtering.motion_queue.MotionLabelledQueue`, which is simply a queue for labelled consecutive sequences. The intended usage is to place frames of interest, labelled as determined by a motion filter, into the queue. The queue is ended when the maximum length is reached as determined by :class:`~DynAIkonTrap.settings.MotionQueueSettings`.

The sequence is then analysed by the animal filter, loaded into the :class:`~DynAIkonTrap.filtering.motion_queue.MotionLabelledQueue`, and a callback called with only the animal frames from the motion sequence. Within a :class:`~DynAIkonTrap.filtering.motion_queue.Sequence` there is some simplistic "smoothing" of animal detections. This means even animal detectors that provide sporadic outputs in time, are transformed to a smooth system output.

Below is a simple outline example of how this can be used to print all animal frames:
```python
camera = Camera()

mf = MotionFilter(...)

mq = MotionLabelledQueue(
    AnimalFilter(...), 
    print, 
    MotionQueueSettings(), 
    camera.framerate,
    )

while True:

    frame = camera.get() # Can raise Empty exception

    motion_score = mf.run_raw(frame.motion)
    motion_detected = motion_score >= motion_threshold
    

    if motion_detected:
        mq.put(frame, motion_score, MotionStatus.MOTION)
    else:
        mq.put(frame, -1.0, MotionStatus.STILL)
```

The modularity here means Different implementations for animal filtering and motion filtering stages can be used.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum
from multiprocessing import Event, Process, Queue, Value
from multiprocessing.queues import Queue as QueueType
from time import time

from DynAIkonTrap.camera import Frame
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import MotionQueueSettings
from DynAIkonTrap.filtering.animal import AnimalFilter

logger = get_logger(__name__)


class MotionStatus(Enum):
    """Categories for the motion status of a frame"""

    STILL = 0
    MOTION = 1
    UNKNOWN = 2

class Label(Enum):
    """Categories into which a frame can fall"""

    EMPTY = 0
    ANIMAL = 1
    UNKNOWN = 2
    CONTEXT = 3

@dataclass
class LabelledFrame:
    """A frame of motion and image data accompanied by some additional labels for the motion queue"""

    frame: Frame
    index: int
    priority: float  # Higher means more likely to be animal
    label: Label = Label.UNKNOWN
    motion_status: MotionStatus = MotionStatus.UNKNOWN

class Sequence:
    """Sequence of consecutive labelled frames. Frames may be "still" or contain motion. Smoothing is built in to smooth any animal detections over multiple frames. This can be done as the minimum number of frames in which an animal is likely to be present, can be reasoned about."""

    def __init__(self, smoothing_len: int, context_len: int):
        """
        Args:
            smoothing_len (int): Number of frames by which to smooth animal detections in either direction
        """
        self._frames: List[LabelledFrame] = []
        self.smoothing_len = smoothing_len
        self.context_len = context_len
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
    
    def add_context(self):
        """Add context labels to either side of the animal predictions. This should only be called just before the sequence is passed out of the motion labelled queue - ie after close_gaps() """
        first_animal_frame_index = self.get_first_animal_index()
        last_animal_frame_index = self.get_last_animal_index()
        #add head context
        stop = first_animal_frame_index
        start = max(first_animal_frame_index - self.context_len, 0)
        self._label(self._frames[start:stop], Label.CONTEXT)
        #add tail context
        start = last_animal_frame_index 
        stop = min(start + self.context_len, len(self._frames))
        self._label(self._frames[start + 1: stop], Label.CONTEXT)
    


    def label_as_animal(self, frame: LabelledFrame):
        """Label a given frame as containing an animal. Intended to be called based on the output of the animal filter. Frames either side of this one in the current sequence will also be labelled as animal according to the ``smoothing_len``

        Args:
            frame (LabelledFrame): The frame to be labelled as containing an animal
        """
        frame_index = frame.index
        start = max(frame_index - self.smoothing_len, 0)
        stop = min(frame_index + self.smoothing_len, len(self._frames))
        self._label(self._frames[start : stop + 1], Label.ANIMAL)

    def label_as_empty(self, frame: LabelledFrame):
        """Label the given frame as empty. Intended to be called based on the output of the animal filter. Only this frame is labelled as empty; no smoothing is applied.

        Args:
            frame (LabelledFrame): The frame to be labelled as being empty
        """
        self._label([frame], Label.EMPTY)

    def close_gaps(self):
        """Remove small gaps of missing animal predictions in the current sequence. This function removes unlikely gaps in animal detections using the ``smoothing_len``."""
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

    def put(self, frame: Frame, motion_score: float, status: MotionStatus):
        """Append the frame to this sequence

        Args:
            frame (Frame): Frame to be put in this sequence
            motion_score (float): Output value for this frame from the motion filtering stage
            status (MotionStatus): status of motion detected in this frame
        """
        self._frames.append(
            LabelledFrame(frame=frame, index=self._next_index, priority=motion_score, motion_status=status)
        )
        self._next_index += 1

    def get_highest_priority(self) -> LabelledFrame:
        """Finds the frame with the highest priority in the sequence. This should be the next frame to be passed to the animal filtering stage.

        Returns:
            LabelledFrame: Frame to be analysed by the animal filtering stage
        """
        highest_priority_frame = max(self._frames, key=lambda frame: frame.priority)
        if highest_priority_frame.motion_status is MotionStatus.STILL:
            return None
        return highest_priority_frame

    def get_first_animal_index(self) -> int:
        """Finds and returns first index in the frame queue labelled as an animal
        
        Returns:
            Index (int) of first animal frame in this sequence.
        """
        indx: int = 0
        for i, frame in enumerate(self._frames):
            if frame.label is Label.ANIMAL:
                indx = i
                break
        return indx
    
    def get_last_animal_index(self) -> int:
        """Finds and returns last index in the frame queue labeled as an animal
        
        Returns:
            Index (int) of last animal frame in this sequence.
        """
        indx: int = len(self._frames)
        for i, frame in reversed(list(enumerate(self._frames))):
            if frame.label is Label.ANIMAL:
                indx = i
                break
        return indx

    def get_animal_frames(self) -> List[LabelledFrame]:
        """Retrieve only the animal frames from the sequence

        Returns:
            List[LabelledFrame]: List of animal frames from this sequence
        """
        return list(filter(lambda frame: frame.label == Label.ANIMAL, self._frames))
        
    def get_animal_or_context_frames(self) -> List[LabelledFrame]:
        """Retrieve only the animal or context frames from the sequence
        
        Returns:
            List[LabelledFrane]: List of animal or context frames from this sequence
        """
        return list(filter(lambda frame: frame.label in (Label.ANIMAL, Label.CONTEXT), self._frames))
    
    def has_motion(self) -> bool:
        """Check if this sequence has a frame with motion status MOTION
        
        Returns:
            Bool: True if a frame in this sequence has a status indicating motion, False otherwise"""
        for frame in self._frames:
            if frame.motion_status is MotionStatus.MOTION:
                return True
        return False

    def __len__(self):
        return len(self._frames)


class MotionLabelledQueue:
    """A queue for sequences of motion to be analysed by the animal filter"""

    def __init__(
        self,
        settings: MotionQueueSettings,
        animal_detector: AnimalFilter,
        framerate: int,
    ):
        """
        Args:
            settings (MotionQueueSettings): Settings for the queue
            animal_detector (AnimalFilter): An initialised animal filter to apply to frames in the motion sequences
            output_callback (Callable[[List[Frame]], Any]): Function to call with filtered frames
            framerate (int): Framerate at which the frames were recorded
        """
        self._smoothing_len = int((settings.smoothing_factor * framerate) / 2)
        self._context_len = int((settings.context_length_s * framerate))
        self._sequence_len = framerate * settings.max_sequence_period_s
        self._current_sequence = Sequence(self._smoothing_len, self._context_len)
        self._queue: QueueType[Sequence] = Queue()
        self._animal_detector = animal_detector
        self._output_queue: QueueType[Frame] = Queue()

        self._mean_time = Value('d')
        with self._mean_time.get_lock():
            self._mean_time.value = 1 / 0.3

        self._remaining_frames = Value('L')
        with self._remaining_frames.get_lock():
            self._remaining_frames.value = 0

        self._idle = Event()
        self._idle.set()

        self._process = Process(target=self._process_queue, daemon=True)
        self._process.start()

    def put(self, frame: Frame, motion_score: float, motion_status: MotionStatus):
        """Append the given frame to the current sequence. If the sequence exceeds the length limit, a new one is automatically started. This prevents excessively long motion sequences.

        Args:
            frame (Frame): A frame of motion and image data to be analysed
            motion_score (float): Output value for this frame from the motion filtering stage
            status (MotionStatus): status of motion detected in this frame

        """
        self._idle.clear()
        self._current_sequence.put(frame, motion_score, motion_status)
        if len(self._current_sequence) >= self._sequence_len:
            self.end_motion_sequence()

    def end_motion_sequence(self):
        """End the current sequence and prepare the next one. It is safe to call this repeatedly for consecutive empty frames. Calling this releases the sequence to be processed by the animal filter."""
        current_len = len(self._current_sequence)
        if current_len > 0: 
            if self._current_sequence.has_motion():
                self._queue.put(self._current_sequence)
                logger.info(
                'End of motion ({} frames will take <=~{:.0f}s; {:.0f}s cumulative)'.format(
                    current_len,
                    current_len * self._mean_time.value,
                    self._remaining_frames.value * self._mean_time.value,
                )
            )
            self._current_sequence = Sequence(self._smoothing_len, self._context_len)

            with self._remaining_frames.get_lock():
                self._remaining_frames.value += current_len

            

    def _process_queue(self):
        while True:
            sequence = self._queue.get()
            self._idle.clear()

            # Timing full sequence
            t_start = time()

            # Timing animal detector inference
            t_actual_framerate = 0
            inference_count = 0
            t_temp = time()

            frame = sequence.get_highest_priority()
            while frame:
                is_animal = self._animal_detector.run(frame.frame.image)

                _t = time()
                t_actual_framerate += _t - t_temp
                t_temp = _t
                inference_count += 1

                if is_animal:
                    sequence.label_as_animal(frame)
                else:
                    sequence.label_as_empty(frame)
                frame = sequence.get_highest_priority()

            sequence.close_gaps()
            sequence.add_context()
            t_stop = time()
            t = t_stop - t_start

            # Update average inferencing time
            if inference_count:
                with self._mean_time.get_lock():
                    self._mean_time.value = (
                        self._mean_time.value + t_actual_framerate / inference_count
                    ) / 2

            logger.info(
                'It took {:.1f}s to process {} frames ({} animal) => ~{:.2f}FPS'.format(
                    t,
                    len(sequence),
                    len(sequence.get_animal_frames()),
                    len(sequence) / t,
                )
            )
            output = list(map(lambda frame: frame.frame, sequence.get_animal_or_context_frames()))
            output += [None] if len(output) > 0 else []
            [self._output_queue.put(f) for f in output]
            self._idle.set()

            # Update count of frames
            with self._remaining_frames.get_lock():
                self._remaining_frames.value -= len(sequence)

    def is_idle(self) -> bool:
        """Allows checking if the motion queue is currently waiting for new frames to arrive. May be removed in future."""
        return (self._queue.qsize() == 0) and self._idle.is_set()

    def get(self) -> Frame:
        """Retrieve the next animal `Frame` from the motion queue's output

        Returns:
            Frame: An animal frame
        """
        return self._output_queue.get()

    def close(self):
        self._process.terminate()
        self._process.join()
