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
This module provides a generic interface to an animal detector. The system is fairly agnostic of the specific animal detection mechanism beings used, as the input to the :class:`AnimalFilter` is a JPEG image and the output a confidence in the image containing an animal.

A WCS-trained Tiny YOLOv4 model is used in this implementation, but any other architecture could be substituted in its place easily. Such a substitution would not require any changes to the module interface.
"""
import cv2
import numpy as np

from DynAIkonTrap.settings import AnimalFilterSettings


class AnimalFilter:
    """Animal filter stage to indicate if a frame contains an animal
    """
    def __init__(self, settings: AnimalFilterSettings):
        """
        Args:
            settings (AnimalFilterSettings): Settings for the filter
        """
        self.threshold = settings.threshold

        self.model = cv2.dnn.readNet(
            'DynAIkonTrap/filtering/yolo_animal_detector.weights',
            'DynAIkonTrap/filtering/yolo_animal_detector.cfg',
        )
        layer_names = self.model.getLayerNames()
        self.output_layers = [
            layer_names[i[0] - 1] for i in self.model.getUnconnectedOutLayers()
        ]

    def run_raw(self, image: bytes) -> float:
        """Run the animal filter on the image to give a confidence that the image frame contains an animal

        Args:
            image (bytes): The image frame to be analysed in JPEG format

        Returns:
            float: Confidence in the output containing an animal as a decimal fraction
        """
        decoded_image = cv2.resize(
            cv2.imdecode(np.asarray(image), cv2.IMREAD_COLOR), (416, 416)
        )

        blob = cv2.dnn.blobFromImage(decoded_image, 1, (416, 416), (0, 0, 0))
        blob = blob / 255  # Scale to be a float
        self.model.setInput(blob)
        output = self.model.forward(self.output_layers)

        _, _, _, _, _, confidence0 = output[0].max(axis=0)
        _, _, _, _, _, confidence1 = output[1].max(axis=0)
        return max(confidence0, confidence1)

    def run(self, image: bytes) -> bool:
        """The same as :func:`run_raw()`, but with a threshold applied. This function outputs a boolean to indicate if the confidence is at least as large as the threshold

        Args:
            image (bytes): The image frame to be analysed in JPEG format

        Returns:
            bool: `True` if the confidence in animal presence is at least the threshold, otherwise `False`
        """
        return self.run_raw(image) >= self.threshold
