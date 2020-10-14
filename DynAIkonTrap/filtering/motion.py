import numpy as np
import math
from scipy import signal

from DynAikonTrap.filtering.iir import IIRFilter
from DynAikonTrap.settings import MotionFilterSettings


class MotionFilter:
    def __init__(
        self,
        settings: MotionFilterSettings,
        framerate,
    ):
        self.threshold_small: int = settings.small_threshold
        self.threshold_sotv: int = settings.sotv_threshold

        def wn(fc):
            fnq = framerate / 2
            return fc / fnq

        sos = signal.cheby2(
            settings.iir_order,
            settings.iir_attenuation,
            wn(settings.iir_cutoff_hz),
            output='sos',
            btype='lowpass',
        )
        self.x_iir_filter = IIRFilter(sos)
        self.y_iir_filter = IIRFilter(sos)

    def run_raw(self, motion_frame):
        magnitudes = np.sqrt(
            np.square(motion_frame['x'].astype(np.float))
            + np.square(motion_frame['y'].astype(np.float))
        )
        filtered = np.where(
            magnitudes > self.threshold_small,
            motion_frame,
            np.array(
                (0, 0, 0),
                dtype=[
                    ('x', 'i1'),
                    ('y', 'i1'),
                    ('sad', 'u2'),
                ],
            ),
        )

        x_sum = sum(sum(filtered['x'].astype(int)))
        y_sum = sum(sum(filtered['y'].astype(int)))

        x_sum = self.x_iir_filter.filter(x_sum)
        y_sum = self.y_iir_filter.filter(y_sum)

        return math.sqrt(x_sum ** 2 + y_sum ** 2)

    def run(self, frame):
        return self.run_raw(frame) >= self.threshold_sotv
