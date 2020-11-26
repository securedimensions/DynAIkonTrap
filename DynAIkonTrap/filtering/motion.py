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
This module provides a general interface to a motion filtering stage. The motion filter determines if a frame contains sufficient motion to be of interest for passing on to the `DynAIkonTrap.filtering.animal.AnimalFilter` stage. This stage in the pipeline is what allows the system to operate at video framerates as it allows the removal of empty frames that do not need to be analysed by an animal detector. Any method employed in the `MotionFilter` must therefore be able to operate fast enough that it does not form a bottleneck in the system.

The implementation can be replaced with another one easily as the interface simply takes the motion vectors from a frame, performs a calculation, and returns a value corresponding to the motion. If using the `MotionFilter.run()` method (over `MotionFilter.run_raw()`), the threshold is defined internally and a simple Boolean is provided as an output.

This implementation makes use of the Sum of Thresholded Vectors (SoTV) approach. Under this approach initially a small threshold is applied to all motion vectors. This removes the smallest vectors that are more likely to be due to noise or unimportant movements. Secondly, the vectors are summed together giving a single average motion vector for the frame. This step implicitely checks for coherence in movement vectors, as well as the magnitude and size of the area of motion. Finally, the vector is smoothed in time using a Chebyshev type-2 filter to reduce frame-to-frame oscillations in movement and give an insight to the trend in motion. The magnitude of the single smoothed vector representing motion in the frame can then be thresholded to determine if sufficient movement is declared, or not.
"""
import numpy as np
import math
from scipy import signal

from DynAIkonTrap.filtering.iir import IIRFilter
from DynAIkonTrap.settings import MotionFilterSettings
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


class MotionFilter:
    """Motion filtering stage employing the Sum of Thresholded Vectors (SoTV) approach. The output of this stage is filtered in time using an IIR filter, to provide a smoothed result."""

    def __init__(
        self,
        settings: MotionFilterSettings,
        framerate: int,
    ):
        """
        This implementation of the motion-based filter makes use of a Chebyshev type-2 filter to smooth the output.

        Args:
            settings (MotionFilterSettings): Settings for the motion filter
            framerate (int): Framerate at which the frames were recorded
        """
        self.threshold_small: int = settings.small_threshold
        self.threshold_sotv: int = settings.sotv_threshold

        def wn(fc):
            fnq = framerate / 2
            return fc / fnq

        wn = wn(settings.iir_cutoff_hz)
        # Ensure wn is capped to the necessary bounds
        if wn <= 0:
            logger.error('IIR cutoff frequency too low (wn = {:.2f})'.format(wn))
            wn = 1e-10
        elif wn >= 1:
            logger.error('IIR cutoff frequency too high (wn = {:.2f})'.format(wn))
            wn = 1 - 1e-10

        sos = signal.cheby2(
            settings.iir_order,
            settings.iir_attenuation,
            wn,
            output='sos',
            btype='lowpass',
        )
        self.x_iir_filter = IIRFilter(sos)
        self.y_iir_filter = IIRFilter(sos)

    def run_raw(self, motion_frame: np.ndarray) -> float:
        """Run the motion filter using SoTV:
            1. Apply a small threshold to the motion vectors
            2. For those that exceed this, sum the vectors
            3. Apply time filtering to smooth this output

        Args:
            motion_frame (np.ndarray): Motion vectors for a frame

        Returns:
            float: SoTV for the given frame
        """
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

    def run(self, motion_frame: np.ndarray) -> bool:
        """Apply a threshold to the output of `run_raw()`

        Args:
            motion_frame (np.ndarray): Motion vectors for a frame

        Returns:
            bool: `True` if the SoTV is at least the threshold, otherwise `False`
        """
        return self.run_raw(motion_frame) >= self.threshold_sotv

    def reset(self):
        """Reset the internal IIR filter's memory to zero
        """
        self.x_iir_filter.reset()
        self.y_iir_filter.reset()
