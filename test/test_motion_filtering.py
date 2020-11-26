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
from numpy import array, full

from DynAIkonTrap.filtering.motion import MotionFilter, logger
from DynAIkonTrap.settings import MotionFilterSettings


class NoMotionTestCase(TestCase):
    def setUp(self):
        element = array((0, 0, 0), dtype=[('x', 'i1'), ('y', 'i1'), ('sad', 'u2')])
        no_motion_input = full((640, 480), element)

        self._motion_filter = MotionFilter(MotionFilterSettings(), 20)
        self._run_raw = self._motion_filter.run_raw(no_motion_input)
        self._run = self._motion_filter.run(no_motion_input)

    def test_no_motion_gives_run_raw_zero(self):
        self.assertTrue(type(self._run_raw) is float)
        self.assertEqual(self._run_raw, 0)

    def test_no_motion_gives_run_false(self):
        self.assertTrue(type(self._run) is bool)
        self.assertEqual(self._run, False)


class MotionTestCase(TestCase):
    def setUp(self):
        element = array((640, 480, 0), dtype=[('x', 'i1'), ('y', 'i1'), ('sad', 'u2')])
        motion_input = full((640, 480), element)

        self._motion_filter = MotionFilter(MotionFilterSettings(), 20)
        self._run_raw = self._motion_filter.run_raw(motion_input)
        self._run = self._motion_filter.run(motion_input)

    def test_motion_gives_run_raw_non_zero(self):
        self.assertTrue(type(self._run_raw) is float)
        self.assertGreater(self._run_raw, 0)

    def test_motion_gives_run_true(self):
        self.assertTrue(type(self._run) is bool)
        self.assertEqual(self._run, True)


class SmallMotionIgnoredThresholdTestCase(TestCase):
    def setUp(self):
        element = array((5, 5, 0), dtype=[('x', 'i1'), ('y', 'i1'), ('sad', 'u2')])
        motion_input = full((640, 480), element)

        self._motion_filter = MotionFilter(MotionFilterSettings(small_threshold=10), 20)
        self._run_raw = self._motion_filter.run_raw(motion_input)
        self._run = self._motion_filter.run(motion_input)

    def test_small_motion_ignored_run_raw(self):
        self.assertEqual(self._run_raw, 0)

    def test_small_motion_ignored_run(self):
        self.assertEqual(self._run, False)


class InvalidFrequencyTestCase(TestCase):
    def test_cutoff_at_nyquist_fails(self):
        with self.assertLogs(logger, 'ERROR'):
            MotionFilter(MotionFilterSettings(iir_cutoff_hz=10), framerate=20)

    def test_cutoff_above_nyquist_fails(self):
        with self.assertLogs(logger, 'ERROR'):
            MotionFilter(MotionFilterSettings(iir_cutoff_hz=15), framerate=20)

    def test_cutoff_below_zero_fails(self):
        with self.assertLogs(logger, 'ERROR'):
            MotionFilter(MotionFilterSettings(iir_cutoff_hz=-1), framerate=20)

    def test_cutoff_at_zero_fails(self):
        with self.assertLogs(logger, 'ERROR'):
            MotionFilter(MotionFilterSettings(iir_cutoff_hz=0), framerate=20)
