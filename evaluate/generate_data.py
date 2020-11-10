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
