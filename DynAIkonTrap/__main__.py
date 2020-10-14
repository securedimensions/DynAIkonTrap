from signal import signal, SIGINT

from DynAikonTrap.camera import Camera  # , MockCamera
from DynAikonTrap.filtering import Filter
from DynAikonTrap.comms import Sender
from DynAikonTrap.sensor import SensorLogs
from DynAikonTrap.settings import load_settings


# Make Ctrl-C quit gracefully
def handler(signal_num, stack_frame):
    exit(0)


signal(SIGINT, handler)
print('Welcome DynAIkon\'s AI camera trap!')
print('You can halt execution with <Ctrl>+C anytime\n')


settings = load_settings()

camera = Camera(settings=settings.camera)
filters = Filter(read_from=camera, settings=settings.filter)
sensor_logs = SensorLogs(settings=settings.sensor)
sender = Sender(settings=settings.sender, read_from=(filters, sensor_logs))

while True:
    pass
