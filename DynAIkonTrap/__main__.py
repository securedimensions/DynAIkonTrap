from signal import signal, SIGINT

from DynAIkonTrap.camera import Camera  # , MockCamera
from DynAIkonTrap.filtering import Filter
from DynAIkonTrap.comms import Sender, Writer
from DynAIkonTrap.sensor import SensorLogs
from DynAIkonTrap.settings import load_settings, OutputMode

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

if settings.output.output_mode == OutputMode.SEND:
    Sender(settings=settings.output, read_from=(filters, sensor_logs))
else:
    Writer(settings=settings.output, read_from=(filters, sensor_logs))

while True:
    pass
