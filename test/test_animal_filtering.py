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
