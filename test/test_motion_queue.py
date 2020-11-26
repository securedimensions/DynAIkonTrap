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
from unittest import TestCase
from multiprocessing import Queue, Value
from time import time

from DynAIkonTrap.filtering.motion_queue import Label, MotionSequence, MotionQueue
from DynAIkonTrap.camera import Frame
from DynAIkonTrap.settings import MotionQueueSettings


class PutFramesMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(0)
        self._len = 5

        for i in range(self._len):
            self._sequence.put(Frame(None, None, None), 1)

    def test_len_sequence(self):
        self.assertEqual(len(self._sequence._frames), self._len)

    def test_incrementing_indices(self):
        for i, frame in enumerate(self._sequence._frames):
            self.assertEqual(frame.index, i)


class GetHighestPriorityFromMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(0)

        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 4)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 9)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 1)

    def test_correct_order(self):
        order = [4, 3, 0, 1, 2, 5, 6]
        i = 0
        current_frame = self._sequence.get_highest_priority()
        while current_frame:
            self.assertEqual(current_frame.index, order[i])

            current_frame.label = Label.ANIMAL
            current_frame.priority = -1

            current_frame = self._sequence.get_highest_priority()
            i += 1


class LabelAsAnimalMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(1)

        self._sequence.put(Frame(None, None, None), 1)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 4)  # This is the "animal"
        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 7)

        self._sequence.label_as_animal(self._sequence._frames[3])

    def test_frame_label_changed_to_animal(self):
        self.assertEqual(self._sequence._frames[3].label, Label.ANIMAL)

    def test_frames_either_side_labelled_as_animal(self):
        self.assertEqual(self._sequence._frames[2].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[4].label, Label.ANIMAL)

    def test_frames_beyond_smoothing_len_left_unlabelled(self):
        self.assertEqual(self._sequence._frames[0].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[1].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[5].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[6].label, Label.UNKNOWN)


class LabelAsEmptyMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(1)

        self._sequence.put(Frame(None, None, None), 1)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 4)  # This is the "empty"
        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 7)

        self._sequence.label_as_empty(self._sequence._frames[3])

    def test_frame_label_changed_to_empty(self):
        self.assertEqual(self._sequence._frames[3].label, Label.EMPTY)

    def test_all_frames_either_side_unlabelled(self):
        self.assertEqual(self._sequence._frames[0].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[1].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[2].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[4].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[5].label, Label.UNKNOWN)
        self.assertEqual(self._sequence._frames[6].label, Label.UNKNOWN)


class LabelAnimalOverwritesEmptyMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(1)

        self._sequence.put(Frame(None, None, None), 1)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 4)
        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 7)

        # Every frame is initially labelled as empty
        self._sequence.label_as_empty(self._sequence._frames[0])
        self._sequence.label_as_empty(self._sequence._frames[1])
        self._sequence.label_as_empty(self._sequence._frames[2])
        self._sequence.label_as_empty(self._sequence._frames[3])
        self._sequence.label_as_empty(self._sequence._frames[4])
        self._sequence.label_as_empty(self._sequence._frames[5])
        self._sequence.label_as_empty(self._sequence._frames[6])

        # But then the 3th frame is labelled "animal"
        self._sequence.label_as_animal(self._sequence._frames[3])

    def test_empty_overwitten_by_animal(self):
        self.assertEqual(self._sequence._frames[3].label, Label.ANIMAL)

    def test_animal_smoothing_overwrites_empty(self):
        self.assertEqual(self._sequence._frames[2].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[4].label, Label.ANIMAL)

    def test_other_frame_labels_not_overwritten(self):
        self.assertEqual(self._sequence._frames[0].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[1].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[5].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[6].label, Label.EMPTY)


class LabelEmptyNotOverwriteAnimalMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(1)

        self._sequence.put(Frame(None, None, None), 1)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 4)
        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 7)

        # Every frame is initially labelled as "animal"
        self._sequence.label_as_animal(self._sequence._frames[0])
        self._sequence.label_as_animal(self._sequence._frames[1])
        self._sequence.label_as_animal(self._sequence._frames[2])
        self._sequence.label_as_animal(self._sequence._frames[3])
        self._sequence.label_as_animal(self._sequence._frames[4])
        self._sequence.label_as_animal(self._sequence._frames[5])
        self._sequence.label_as_animal(self._sequence._frames[6])

        # But then the 3th frame is labelled "empty"
        self._sequence.label_as_empty(self._sequence._frames[3])

    def test_animal_frames_not_overwritten_by_empty(self):
        self.assertEqual(self._sequence._frames[0].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[1].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[2].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[4].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[5].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[6].label, Label.ANIMAL)


class CloseGapsMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(0)  # Note: no smoothing here

        self._sequence.put(Frame(None, None, None), 1)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 4)
        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 7)
        self._sequence.put(Frame(None, None, None), 8)

        self._sequence.label_as_animal(self._sequence._frames[0])
        self._sequence.label_as_empty(self._sequence._frames[1])
        self._sequence.label_as_empty(self._sequence._frames[2])
        self._sequence.label_as_animal(self._sequence._frames[3])
        self._sequence.label_as_empty(self._sequence._frames[4])
        self._sequence.label_as_empty(self._sequence._frames[5])
        self._sequence.label_as_empty(self._sequence._frames[6])
        self._sequence.label_as_animal(self._sequence._frames[7])

        self._sequence.smoothing_len = 1  # Enable smoothing
        self._sequence.close_gaps()

    def test_small_gaps_are_closed(self):
        self.assertEqual(self._sequence._frames[1].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[2].label, Label.ANIMAL)

    def test_larger_gaps_not_closed(self):
        self.assertEqual(self._sequence._frames[4].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[5].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[6].label, Label.EMPTY)


class CloseGapsLeadingEmptyMotionSequenceTestCase(TestCase):
    def setUp(self):
        self._sequence = MotionSequence(0)  # Note: no smoothing here

        self._sequence.put(Frame(None, None, None), 1)
        self._sequence.put(Frame(None, None, None), 2)
        self._sequence.put(Frame(None, None, None), 3)
        self._sequence.put(Frame(None, None, None), 4)
        self._sequence.put(Frame(None, None, None), 5)
        self._sequence.put(Frame(None, None, None), 6)
        self._sequence.put(Frame(None, None, None), 7)
        self._sequence.put(Frame(None, None, None), 8)
        self._sequence.put(Frame(None, None, None), 9)

        self._sequence.label_as_empty(self._sequence._frames[0])
        self._sequence.label_as_animal(self._sequence._frames[1])
        self._sequence.label_as_empty(self._sequence._frames[2])
        self._sequence.label_as_empty(self._sequence._frames[3])
        self._sequence.label_as_animal(self._sequence._frames[4])
        self._sequence.label_as_empty(self._sequence._frames[5])
        self._sequence.label_as_empty(self._sequence._frames[6])
        self._sequence.label_as_empty(self._sequence._frames[7])
        self._sequence.label_as_animal(self._sequence._frames[8])

        self._sequence.smoothing_len = 1  # Enable smoothing
        self._sequence.close_gaps()

    def test_leading_empties_not_made_animal(self):
        self.assertEqual(self._sequence._frames[0].label, Label.EMPTY)

    def test_small_gaps_are_closed(self):
        self.assertEqual(self._sequence._frames[2].label, Label.ANIMAL)
        self.assertEqual(self._sequence._frames[3].label, Label.ANIMAL)

    def test_larger_gaps_not_closed(self):
        self.assertEqual(self._sequence._frames[5].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[6].label, Label.EMPTY)
        self.assertEqual(self._sequence._frames[7].label, Label.EMPTY)


class KeepPuttingMotionQueueTestCase(TestCase):
    """`end_motion_sequence()` is never explicitely called"""

    def setUp(self):
        class AnimalFilterMock:
            def __init__(self):
                self.num_calls = Value('i', 0)

            def run(self, *args, **kwargs):
                with self.num_calls.get_lock():
                    self.num_calls.value += 1
                return 0.5

        self._animal_filter = AnimalFilterMock()
        self._output = Queue()

        self._mq = MotionQueue(
            settings=MotionQueueSettings(max_sequence_period_s=5, smoothing_factor=5),
            animal_detector=self._animal_filter,
            framerate=1,
        )

        self._mq.put(Frame(None, None, None), 2)  # Group 1, priority 5
        self._mq.put(Frame(None, None, None), 4)  # Group 1, priority 4
        self._mq.put(Frame(None, None, None), 6)  # Group 1, priority 3
        self._mq.put(Frame(None, None, None), 8)  # Group 1, priority 2
        self._mq.put(Frame(None, None, None), 10)  # Group 1, priority 1
        self._mq.put(Frame(None, None, None), 9)  # Group 2, priority 1
        self._mq.put(Frame(None, None, None), 7)  # Group 2, priority 2
        self._mq.put(Frame(None, None, None), 5)  # Group 2, priority 3
        self._mq.put(Frame(None, None, None), 3)  # Group 2, priority 4
        self._mq.put(Frame(None, None, None), 1)  # Group 2, priority 5

    def test_frames_are_run_and_output(self):
        t_start = time()
        while True:
            if self._mq._output_queue.qsize() == 10:
                self.assertTrue(True)
                break

            if time() - t_start > 10:
                self.fail('Timed out')

    def test_animal_filter_called_for_only_some_frames(self):
        t_start = time()
        while True:
            if self._mq._output_queue.qsize() == 10:
                break
            if time() - t_start > 10:
                self.fail('Timed out')

        self.assertEqual(self._animal_filter.num_calls.value, 4)
