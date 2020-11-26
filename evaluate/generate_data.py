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
from queue import Empty
from typing import List
from pickle import dump
from sys import path

path.append('./')
from DynAIkonTrap.camera import Camera, Frame
from DynAIkonTrap.settings import load_settings


print('This program records data to be used for evaluating the system')
print('You can halt execution with <Ctrl>+C anytime\n')

settings = load_settings()
camera = Camera(settings.camera)
print('Recording started')

## Record the data
try:
    while True:
        pass
except KeyboardInterrupt:
    print('Stopping recording and saving data')
    camera.close()


## Convert the recorded frames to dictionary fromat
frames: List[Frame] = []
try:
    while True:
        frames.append(camera._output.get_nowait())
except Empty:
    pass

frames = list(map(lambda f: {'image': f.image, 'motion': f.motion}, frames))


## Save the results to disk
with open('data.pk', 'wb') as f:
    dump(
        {
            'frames': frames,
            'framerate': settings.camera.framerate,
            'resolution': settings.camera.resolution,
        },
        f,
    )

print('The data has been pickled and saved to `data.pk`')
