from json import dump
from types import MappingProxyType

from DynAIkonTrap.settings import (
    OutputMode,
    SenderSettings,
    Settings,
    FilterSettings,
    OutputFormat,
    WriterSettings,
)


def setter(name, setting):
    inpt = input('{} [{}]> '.format(name, setting))
    if inpt != '':
        setting = type(setting)(inpt)
    return setting


def forced_setter(name, setting, value):
    setting = type(setting)(value)
    print('{} [{}]> calculated for you'.format(name, setting))
    return setting


settings = Settings()

print('Welcome to the tuner!\n')
print('You will be asked some questions to optimise the camera for your needs.')
print(
    'For any input prompt enter a value or just hit enter to accept the default (shown in square brackets e.g. [10]).'
)
print(
    'Lastly, it is recommended not to change any parameters marked with `(ADVANCED)`\n'
)


print('Camera settings')
print('---------------')
settings.camera.framerate = setter('framerate', settings.camera.framerate)
w = setter('resolution width (ADVANCED)', settings.camera.resolution[0])
h = setter('resolution height (ADVANCED)', settings.camera.resolution[1])
settings.camera.resolution = (w, h)

# Camera settings for later
area_reality = setter('Visible animal area to trigger/m^2', 0.0064)
subject_distance = setter('Expected distance of animal from sensor/m', 1.0)
animal_speed = setter('Min. animal trigger speed/m/s', 1.0)
focal_len = setter('Camera focal length/m (ADVANCED)', 3.6e-3)
pixel_size = setter('Pixel size/m (ADVANCED)', 1.4e-6)
num_pixels = setter('Number of pixels on sensor (width) (ADVANCED)', 2592)
pixel_ratio = pixel_size * num_pixels / settings.camera.resolution[0]

print('\nFilter settings')
print('---------------')
print('----Motion filtering')
settings.filter.motion.small_threshold = setter(
    'SoTV small movement threshold', settings.filter.motion.small_threshold
)

# Calculate SoTV threshold
animal_dimension = (area_reality ** 0.5 * focal_len) / (pixel_ratio * subject_distance)
animal_area_in_motion_vectors = animal_dimension ** 2 / 16 ** 2
animal_pixel_speed = (animal_speed * 1 / settings.camera.framerate * focal_len) / (
    pixel_ratio * subject_distance
)

settings.filter.motion.sotv_threshold = forced_setter(
    'SoTV general threshold',
    settings.filter.motion.sotv_threshold,
    animal_pixel_speed * animal_area_in_motion_vectors,
)
animal_frames = settings.camera.resolution[0] / animal_pixel_speed
settings.filter.motion.iir_cutoff_hz = forced_setter(
    'SoTV smoothing cut-off frequency/Hz',
    settings.filter.motion.iir_cutoff_hz,
    settings.camera.framerate / animal_frames,
)
settings.filter.motion.iir_order = setter(
    'SoTV smoothing IIR order (ADVANCED)', settings.filter.motion.iir_order
)
settings.filter.motion.iir_attenuation = setter(
    'SoTV smoothing IIR stop-band attenuation (ADVANCED)',
    settings.filter.motion.iir_attenuation,
)

print('----Animal filtering')
settings.filter.animal.threshold = setter(
    'Animal confidence threshold (ADVANCED)', settings.filter.animal.threshold
)

print('----Motion queue')
settings.filter.motion_queue.smoothing_factor = forced_setter(
    'Smoothing factor',
    settings.filter.motion_queue.smoothing_factor,
    animal_frames / settings.camera.framerate,
)
settings.filter.motion_queue.max_sequence_period_s = setter(
    'Max. motion sequence period/s (ADVANCED)',
    settings.filter.motion_queue.max_sequence_period_s,
)

print('\nSensor settings')
print('---------------')
settings.sensor.port = setter('Sensor board port', settings.sensor.port)
settings.sensor.baud = setter('Sensor board baud rate', settings.sensor.baud)
settings.sensor.interval_s = setter(
    'Sensor reading interval/s', settings.sensor.interval_s
)

print('\nOutput settings')
print('---------------')
mode = input('Output mode: save to disk, or server? (d/s) [d]> ')
if mode == 's':
    settings.output = SenderSettings
    settings.output.output_mode = OutputMode.SEND.value
    settings.output.server = setter('Server address', settings.output.server)
else:
    settings.output = WriterSettings
    settings.output.output_mode = OutputMode.DISK.value
    settings.output.path = setter('Output path', settings.output.path)


format = input('Output format video? (y/n) [y]> ')
if format == 'n':
    if mode == 's':
        settings.output.POST = 'capture/'
    settings.output.output_format = OutputFormat.STILL.value
else:
    if mode == 's':
        settings.output.POST = 'capture_video/'
    settings.output.output_format = OutputFormat.VIDEO.value

settings.output.device_id = setter('Device ID', settings.output.device_id)

print('\nLogging level')
print('---------------')
settings.logging.level = setter(
    'Level from `DEBUG`, `INFO`, `WARNING`, `ERROR`', settings.logging.level
)


def serialise(obj):
    if isinstance(obj, Settings):
        return {k: serialise(v) for k, v in obj.__dict__.items()}

    elif isinstance(obj, FilterSettings):
        return {k: serialise(v) for k, v in obj.__dict__.items()}

    elif isinstance(obj, MappingProxyType):
        return {k: v for k, v in obj.items() if not k.startswith('__')}

    return obj.__dict__


with open('DynAIkonTrap/settings.json', 'w') as f:
    dump(settings, f, default=serialise)
