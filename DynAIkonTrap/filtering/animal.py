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
from typing import Tuple, Union
import cv2
import numpy as np
from PIL import Image

from DynAIkonTrap.settings import AnimalFilterSettings, RawImageFormat
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


TFL = True
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    logger.error(
        "Cannot import TFLite runtime, execution will fall back to default animal detector, no human filtering"
    )
    TFL = False


@dataclass
class CompressedImageFormat(Enum):
    """Class to store supported compressed image formats"""

    JPEG = 0


@dataclass
class NetworkInputSizes:
    """A class to hold data for neural network input buffer sizes. Sizes are in (width, height) format"""

    YOLOv4_TINY = (416, 416)
    SSDLITE_MOBILENET_V2 = (300, 300)


class AnimalFilter:
    """Animal filter stage to indicate if a frame contains an animal"""

    def __init__(self, settings: AnimalFilterSettings):
        """
        Args:
            settings (AnimalFilterSettings): Settings for the filter
        """
        self.animal_threshold = settings.animal_threshold
        self.human_threshold = settings.human_threshold
        self.detect_humans = settings.detect_humans
        self.fast_animal_detect = settings.fast_animal_detect

        if settings.detect_humans or settings.fast_animal_detect:
            self.input_size = NetworkInputSizes.SSDLITE_MOBILENET_V2
            if settings.detect_humans:
                self.model = tflite.Interpreter(
                    model_path="DynAIkonTrap/filtering/ssdlite_mobilenet_v2_animal_human/model.tflite"
                )
            elif settings.fast_animal_detect:
                self.model = tflite.Interpreter(
                    model_path="DynAIkonTrap/filtering/models/ssdlite_mobilenet_v2_animal_only/model.tflite"
                )
            self.model.resize_tensor_input(
                0, [1, self.input_size[0], self.input_size[1], 3], strict=True)
            self.model.allocate_tensors()
            self.tfl_input_details = self.model.get_input_details()
            self.tfl_output_details = self.model.get_output_details()

        else:
            # use YOLOv4-tiny 416 animal-only detector
            self.input_size = NetworkInputSizes.YOLOv4_TINY
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
    ) -> Tuple[float, float]:
        """Run the animal filter on the image to give a confidence that the image frame contains an animal and/or a human. For configurations where an animal-only detector is initialised, human confidence will always equal 0.0.

        Args:
            image (bytes): The image frame to be analysed, can be in JPEG compressed format or RGBA, RGB raw format
            img_format (Union[RawImageFormat, CompressedImageFormat], optional): Enum indicating which image format has been passed. Defaults to CompressedImageFormat.JPEG.

        Returns:
            Tuple(float, float): Confidences in the output containing an animal and a human as a decimal fraction
        """
        decoded_image = []
        if img_format is CompressedImageFormat.JPEG:
            decoded_image = cv2.resize(
                cv2.imdecode(np.asarray(
                    image), cv2.IMREAD_COLOR), (self.input_size)
            )
        elif img_format is RawImageFormat.RGBA:
            decoded_image = np.asarray(
                Image.frombytes(
                    "RGBA", self.input_size, image, "raw", "RGBA"
                )
            )
            decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_RGBA2RGB)
        elif img_format is RawImageFormat.RGB:
            decoded_image = np.asarray(
                Image.frombytes(
                    "RGB", self.input_size, image, "raw", "RGB"
                )
            )
        animal_confidence = 0.0
        human_confidence = 0.0
        if self.detect_humans or self.fast_animal_detect:

            # convert to floating point input
            # in future, tflite conversion process should be modified to accept int input, it's not clear how that's done yet
            decoded_image = decoded_image.astype('float32')
            decoded_image = decoded_image / decoded_image.max()
            model_input = [decoded_image]
            self.model.set_tensor(
                self.tfl_input_details[0]['index'], model_input)
            self.model.invoke()
            output_confidences = self.model.get_tensor(
                self.tfl_output_details[0]['index'])[0]
            if self.detect_humans:
                output_classes = self.model.get_tensor(
                    self.tfl_output_details[3]['index'])[0].astype(int)
                human_indexes = [i for (i, label) in enumerate(
                    output_classes) if label == 0]
                animal_indexes = [i for (i, label) in enumerate(
                    output_classes) if label == 1]
                human_confidence = max([output_confidences[i]
                                       for i in human_indexes])
                animal_confidence = max([output_confidences[i]
                                        for i in animal_indexes])
            else:
                animal_confidence = max(output_confidences)

        else:
            blob = cv2.dnn.blobFromImage(
                decoded_image, 1, NetworkInputSizes.YOLOv4_TINY, (0, 0, 0)
            )
            blob = blob / 255  # Scale to be a float
            self.model.setInput(blob)
            output = self.model.forward(self.output_layers)

            _, _, _, _, _, confidence0 = output[0].max(axis=0)
            _, _, _, _, _, confidence1 = output[1].max(axis=0)
            animal_confidence = max(confidence0, confidence1)
        return animal_confidence, human_confidence

    def run(
        self,
        image: bytes,
        img_format: Union[
            RawImageFormat, CompressedImageFormat
        ] = CompressedImageFormat.JPEG,
    ) -> Tuple[bool, bool]:
        """The same as :func:`run_raw()`, but with a threshold applied. This function outputs a boolean to indicate if the confidences are at least as large as the threshold

        Args:
            image (bytes): The image frame to be analysed, can be in JPEG compressed format or RGBA, RGB raw format
            img_format (Union[RawImageFormat, CompressedImageFormat], optional): Enum indicating which image format has been passed. Defaults to CompressedImageFormat.JPEG.

        Returns:
            Tuple(bool, bool): Each element is `True` if the confidence is at least the threshold, otherwise `False`. Elements represent detections for animal and human class.
        """
        animal_confidence, human_confidence = self.run_raw(image, img_format)
        return animal_confidence >= self.animal_threshold, human_confidence >= self.human_threshold
