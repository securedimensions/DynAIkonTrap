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
This module provides a generic interface to an animal detector. The system is fairly agnostic of the specific animal detection mechanism beings used, as the input to the :class:`AnimalFilter` is a JPEG, RGB or RGBA image and the output a confidence in the image containing an animal.

A WCS-trained Tiny YOLOv4 model is used in this implementation, but any other architecture could be substituted in its place easily. Such a substitution would not require any changes to the module interface.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Union
import cv2
import numpy as np
from PIL import Image

from DynAIkonTrap.settings import AnimalFilterSettings, RawImageFormat


@dataclass
class CompressedImageFormat(Enum):
    """Class to store supported compressed image formats"""

    JPEG = 0


@dataclass
class NetworkInputSizes:
    """A class to hold data for neural network input buffer sizes. Sizes are in (width, height) format"""

    YOLOv4_TINY = (416, 416)


class AnimalFilter:
    """Animal filter stage to indicate if a frame contains an animal"""

    def __init__(self, settings: AnimalFilterSettings):
        """
        Args:
            settings (AnimalFilterSettings): Settings for the filter
        """
        self.threshold = settings.threshold

        self.model = cv2.dnn.readNet(
            "DynAIkonTrap/filtering/yolo_animal_detector.weights",
            "DynAIkonTrap/filtering/yolo_animal_detector.cfg",
        )
        layer_names = self.model.getLayerNames()
        self.output_layers = [
            layer_names[i[0] - 1] for i in self.model.getUnconnectedOutLayers()
        ]

    def run_raw(
        self,
        image: bytes,
        img_format: Union[
            RawImageFormat, CompressedImageFormat
        ] = CompressedImageFormat.JPEG,
    ) -> float:
        """Run the animal filter on the image to give a confidence that the image frame contains an animal

        Args:
            image (bytes): The image frame to be analysed, can be in JPEG compressed format or RGBA, RGB raw format
            img_format (Union[RawImageFormat, CompressedImageFormat], optional): Enum indicating which image format has been passed. Defaults to CompressedImageFormat.JPEG.

        Returns:
            float: Confidence in the output containing an animal as a decimal fraction
        """
        decoded_image = []
        if img_format is CompressedImageFormat.JPEG:
            decoded_image = cv2.resize(
                cv2.imdecode(np.asarray(image), cv2.IMREAD_COLOR), (416, 416)
            )
        elif img_format is RawImageFormat.RGBA:
            decoded_image = np.asarray(
                Image.frombytes(
                    "RGBA", NetworkInputSizes.YOLOv4_TINY, image, "raw", "RGBA"
                )
            )
            decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_RGBA2RGB)
        elif img_format is RawImageFormat.RGB:
            decoded_image = np.asarray(
                Image.frombytes(
                    "RGB", NetworkInputSizes.YOLOv4_TINY, image, "raw", "RGB"
                )
            )

        blob = cv2.dnn.blobFromImage(
            decoded_image, 1, NetworkInputSizes.YOLOv4_TINY, (0, 0, 0)
        )
        blob = blob / 255  # Scale to be a float
        self.model.setInput(blob)
        output = self.model.forward(self.output_layers)

        _, _, _, _, _, confidence0 = output[0].max(axis=0)
        _, _, _, _, _, confidence1 = output[1].max(axis=0)
        return max(confidence0, confidence1)

    def run(
        self,
        image: bytes,
        img_format: Union[
            RawImageFormat, CompressedImageFormat
        ] = CompressedImageFormat.JPEG,
    ) -> bool:
        """The same as :func:`run_raw()`, but with a threshold applied. This function outputs a boolean to indicate if the confidence is at least as large as the threshold

        Args:
            image (bytes): The image frame to be analysed, can be in JPEG compressed format or RGBA, RGB raw format
            img_format (Union[RawImageFormat, CompressedImageFormat], optional): Enum indicating which image format has been passed. Defaults to CompressedImageFormat.JPEG.

        Returns:
            bool: `True` if the confidence in animal presence is at least the threshold, otherwise `False`
        """
        return self.run_raw(image, img_format) >= self.threshold
