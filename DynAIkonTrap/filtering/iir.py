class IIR2Filter:
    """Second order IIR filter stage
    """
    def __init__(self, coeffs):
        """Second order IIR filter stage

        :param coeffs: Coefficients for the branches in the filter
        :type coeffs: List of floats
        """
        self.b0 = coeffs[0]
        self.b1 = coeffs[1]
        self.b2 = coeffs[2]
        self.a0 = coeffs[3]
        self.a1 = coeffs[4]
        self.a2 = coeffs[5]
        self.tap1 = 0
        self.tap2 = 0

    def filter(self, x):
        """Perform filtering based on the sample of data, `x`

        :param x: Next data sample
        :type x: Number
        :return: Filtered sample
        :rtype: Number
        """
        output = self.b1 * self.tap1
        x = x - (self.a1 * self.tap1)
        output = output + (self.b2 * self.tap2)
        x = x - (self.a2 * self.tap2)
        output = output + x * self.b0
        self.tap2 = self.tap1
        self.tap1 = x
        return output


class IIRFilter(object):
    """IIR filter constructed from IIR2Filters"""

    def __init__(self, SOS):
        """Takes `SOS` array from high-level design commands
        Creates a chain of 2nd order filter instances of IIR2Filter.
        """
        self.iir2filters = [IIR2Filter(coeffs) for coeffs in SOS]

    def filter(self, x):
        for filter in self.iir2filters:
            x = filter.filter(x)
        return x
