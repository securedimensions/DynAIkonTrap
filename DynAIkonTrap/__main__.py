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
from time import sleep


def get_version_number() -> str:
    with open("VERSION", "r") as f:
        version = f.readline().strip()
    return version


argparse = ArgumentParser(
    prog="DynAIkonTrap",
    description="An AI-enabled camera trap design targeted at the Raspberry Pi platform",
)
argparse.add_argument(
    "--version", action="version", version="%(prog)s " + get_version_number()
)
args = argparse.parse_args()

from DynAIkonTrap.camera import Camera
from DynAIkonTrap.filtering.filtering import Filter
from DynAIkonTrap.camera_to_disk import CameraToDisk
from DynAIkonTrap.filtering.remember_from_disk import EventRememberer
from DynAIkonTrap.comms import Output
from DynAIkonTrap.sensor import SensorLogs
from DynAIkonTrap.settings import PipelineVariant, load_settings

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

print("Welcome to DynAIkon's AI camera trap!")
print("You can halt execution with <Ctrl>+C anytime\n")


settings = load_settings()
getLogger().setLevel(settings.logging.level)
if settings.pipeline.pipeline_variant == PipelineVariant.LEGACY.value:
    # Legacy pipeline mode
    source = Camera(settings=settings.camera)

else:
    # Low-powered pipeline mode
    camera = CameraToDisk(
        camera_settings=settings.camera,
        writer_settings=settings.output,
        filter_settings=settings.filter,
    )
    source = EventRememberer(read_from=camera)

filters = Filter(read_from=source, settings=settings.filter)


sensor_logs = SensorLogs(settings=settings.sensor)
Output(settings=settings.output, read_from=(filters, sensor_logs))

while True:
    sleep(0.5)
    pass
