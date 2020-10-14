import cv2
import numpy as np

from DynAikonTrap.settings import AnimalFilterSettings


class AnimalFilter:
    def __init__(self, settings: AnimalFilterSettings):
        self.threshold = settings.threshold

        self.model = cv2.dnn.readNet(
            'DynAikonTrap/filtering/yolo_animal_detector.weights',
            'DynAikonTrap/filtering/yolo_animal_detector.cfg',
        )
        layer_names = self.model.getLayerNames()
        self.output_layers = [
            layer_names[i[0] - 1] for i in self.model.getUnconnectedOutLayers()
        ]

    def run_raw(self, image: np.ndarray) -> float:
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

    def run(self, image: np.ndarray) -> bool:
        return self.run_raw(image) >= self.threshold
