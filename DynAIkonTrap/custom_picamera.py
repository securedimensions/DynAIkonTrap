# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2021 Ross Gardiner

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
Provides a interface to customisations on classes in the :class:`PiCamera` library. The :class:`Camera` class provides the :class:`Frame`\ s from the camera's stream via a queue. 
"""

from picamera import PiCamera, PiRawVideoEncoder, PiVideoFrameType, PiCookedVideoEncoder

from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


class DynRawEncoder(PiRawVideoEncoder):
    """A custom raw video encoder which outputs a divided number of frames. This class inherits from PiRawVideoEncoder."""

    def __init__(self, *args, **kwargs):
        """Initalise DynRawEncoder, by default the divisor is set to 1"""
        self.divisor = 1
        self._count = 0
        super(DynRawEncoder, self).__init__(*args, **kwargs)

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """Override _callback_write() function to not encode frames which do not land on a divisor index."""
        self._count += 1
        if (self._count % self.divisor) == 0:
            return super()._callback_write(buf, key=key)


class DynCamera(PiCamera):
    """Extension of PiCamera class which makes use of DynRawEncoder for raw encoder formats"""

    def __init__(self, raw_divisor=1, *args, **kwargs):
        self.raw_divisor = raw_divisor
        super(DynCamera, self).__init__(*args, **kwargs)

    def _get_video_encoder(self, camera_port, output_port, format, resize, **options):
        encoder_class = (
            DynRawEncoder if format in self.RAW_FORMATS else PiCookedVideoEncoder
        )
        ret = encoder_class(self, camera_port, output_port, format, resize, **options)
        if isinstance(ret, DynRawEncoder):
            ret.divisor = self.raw_divisor
        return ret
