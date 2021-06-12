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
from logging import getLogger
from signal import signal, SIGINT
from argparse import ArgumentParser


def get_version_number() -> str:
    with open('VERSION', 'r') as f:
        version = f.readline().strip()
    return version


argparse = ArgumentParser(
    prog='DynAIkonTrap',
    description='An AI-enabled camera trap design targeted at the Raspberry Pi platform',
)
argparse.add_argument(
    '--version', action='version', version='%(prog)s ' + get_version_number()
)
args = argparse.parse_args()

from DynAIkonTrap.camera import Camera  # , MockCamera
from DynAIkonTrap.filtering import Filter
from DynAIkonTrap.comms import Sender, Writer
from DynAIkonTrap.sensor import SensorLogs
from DynAIkonTrap.settings import load_settings, OutputMode

# Make Ctrl-C quit gracefully
def handler(signal_num, stack_frame):
    exit(0)


signal(SIGINT, handler)

print(
    """
DynAIkonTrap Copyright (C) 2020 Miklas Riechmann
This program comes with ABSOLUTELY NO WARRANTY. This is free software, and
you are welcome to redistribute it under certain conditions. See the
LICENSE file or <https://www.gnu.org/licenses/> for details.
"""
)

print('Welcome to DynAIkon\'s AI camera trap!')
print('You can halt execution with <Ctrl>+C anytime\n')


settings = load_settings()
getLogger().setLevel(settings.logging.level)

camera = Camera(settings=settings.camera)
filters = Filter(read_from=camera, settings=settings.filter)
sensor_logs = SensorLogs(settings=settings.sensor)

if settings.output.output_mode == OutputMode.SEND:
    Sender(settings=settings.output, read_from=(filters, sensor_logs))
else:
    Writer(settings=settings.output, read_from=(filters, sensor_logs))

while True:
    pass
