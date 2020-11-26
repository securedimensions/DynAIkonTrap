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
The IIR filter architecture provided in this module can be used to filter/smooth "continuous" data signals in time. In particular, it is used in the motion filtering stage of the filtering pipeline.
"""


class IIR2Filter:
    """Second order IIR filter stage"""

    def __init__(self, coeffs: 'numpy.ndarray'):
        """
        Args:
            coeffs (numpy.ndarray): SOS coefficients as returned by the utility functions from scipy
        """
        self.b0 = coeffs[0]
        self.b1 = coeffs[1]
        self.b2 = coeffs[2]
        self.a0 = coeffs[3]
        self.a1 = coeffs[4]
        self.a2 = coeffs[5]
        self.tap1 = 0
        self.tap2 = 0

    def filter(self, x: float) -> float:
        """Perform time-based filtering based on the provided data sample

        Args:
            x (float): A data sample

        Returns:
            float: The filtered sample
        """

        output = self.b1 * self.tap1
        x = x - (self.a1 * self.tap1)
        output = output + (self.b2 * self.tap2)
        x = x - (self.a2 * self.tap2)
        output = output + x * self.b0
        self.tap2 = self.tap1
        self.tap1 = x
        return output

    def reset(self):
        self.tap1, self.tap2 = 0, 0


class IIRFilter(object):
    """IIR filter constructed from IIR2Filters"""

    def __init__(self, SOS: 'numpy.ndarray'):
        """
        Creates a chain of 2nd order filter instances of IIR2Filter

        Args:
            SOS (numpy.ndarray): SOS coefficients as returned by the utility functions from scipy
        """

        self.iir2filters = [IIR2Filter(coeffs) for coeffs in SOS]

    def filter(self, x: float) -> float:
        """Perform time-based filtering based on the provided data sample

        Args:
            x (float): A data sample

        Returns:
            float: The filtered sample
        """
        for filter in self.iir2filters:
            x = filter.filter(x)
        return x

    def reset(self):
        [f.reset() for f in self.iir2filters]
