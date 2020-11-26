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
import cv2
import numpy as np

from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.settings import AnimalFilterSettings


class NoAnimalTestCase(TestCase):
    def setUp(self):
        # A black image
        _, encoded_image = cv2.imencode('.jpg', np.full((640, 480, 3), 0))

        self._animal_filter = AnimalFilter(AnimalFilterSettings())
        self._run_raw = self._animal_filter.run_raw(encoded_image)
        self._run = self._animal_filter.run(encoded_image)

    def test_no_animal_gives_run_raw_zero(self):
        self.assertEqual(self._run_raw, 0)

    def test_no_animal_gives_run_false(self):
        self.assertEqual(self._run, False)
