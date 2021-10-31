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
from json import dump
from types import MappingProxyType

from DynAIkonTrap.settings import (
    OutputMode,
    OutputVideoCodec,
    PipelineVariant,
    RawImageFormat,
    SenderSettings,
    Settings,
    FilterSettings,
    OutputFormat,
    WriterSettings,
)


def setter(name, setting):
    inpt = input("{} [{}]> ".format(name, setting))
    if inpt != "":
        setting = type(setting)(inpt)
    return setting


def forced_setter(name, setting, value):
    setting = type(setting)(value)
    print("{} [{}]> calculated for you".format(name, setting))
    return setting


def _version_number() -> str:
    with open("VERSION", "r") as f:
        version = f.readline().strip()
    return version


settings = Settings()
settings.version = _version_number()

print(
    """
DynAIkonTrap Copyright (C) 2020 Miklas Riechmann
This program comes with ABSOLUTELY NO WARRANTY. This is free software, and
you are welcome to redistribute it under certain conditions. See the
LICENSE file or <https://www.gnu.org/licenses/> for details.
"""
)

print("Welcome to the tuner!\n")
print("You will be asked some questions to optimise the camera for your needs.")
print(
    "For any input prompt enter a value or just hit enter to accept the default (shown in square brackets e.g. [10])."
)
print(
    "Lastly, it is recommended not to change any parameters marked with `(ADVANCED)`\n"
)

print("Pipeline settings")
print("---------------")
pipeline_variant = input(
    "Indicate which pipeline to use LEGACY or LOW_POWER [LOW_POWER]> "
)
if pipeline_variant == "LEGACY":
    settings.pipeline.pipeline_variant = PipelineVariant.LEGACY.value
else:
    settings.pipeline.pipeline_variant = PipelineVariant.LOW_POWER.value

print("Camera settings")
print("---------------")
settings.camera.framerate = setter("framerate", settings.camera.framerate)
w = setter("Resolution width (ADVANCED)", settings.camera.resolution[0])
h = setter("Resolution height (ADVANCED)", settings.camera.resolution[1])
settings.camera.resolution = (w, h)
settings.camera.bitrate_bps = setter(
    "Encoding bitrate bits/s (ADVANCED)", settings.camera.bitrate_bps
)
if settings.pipeline.pipeline_variant == PipelineVariant.LOW_POWER.value:
    settings.camera.raw_framerate_divisor = setter(
        "Raw framerate divisor (ADVANCED)", settings.camera.raw_framerate_divisor
    )
    settings.camera.io_buffer_size_s = setter(
        "Nr. seconds to buffer stream IO access (ADVANCED)",
        settings.camera.io_buffer_size_s,
    )
    raw_fmt = input("Raw stream image format: RGBA, or RGB (ADVANCED) [RGBA]> ")
    if raw_fmt == "RGB":
        settings.camera.raw_stream_image_format = RawImageFormat.RGB.value
    else:
        settings.camera.raw_stream_image_format = RawImageFormat.RGBA.value
else:
    settings.camera.raw_stream_image_format = RawImageFormat.RGBA.value
# Camera settings for later
area_reality = setter("Visible animal area to trigger/m^2", 0.0064)
subject_distance = setter("Expected distance of animal from sensor/m", 1.0)
animal_speed = setter("Min. animal trigger speed/m/s", 1.0)
focal_len = setter("Camera focal length/m (ADVANCED)", 3.6e-3)
pixel_size = setter("Pixel size/m (ADVANCED)", 1.4e-6)
num_pixels = setter("Number of pixels on sensor (width) (ADVANCED)", 2592)
pixel_ratio = pixel_size * num_pixels / settings.camera.resolution[0]

print("\nFilter settings")
print("---------------")
print("----Motion filtering")
settings.filter.motion.small_threshold = setter(
    "SoTV small movement threshold", settings.filter.motion.small_threshold
)

# Calculate SoTV threshold
animal_dimension = (area_reality ** 0.5 * focal_len) / (pixel_ratio * subject_distance)
animal_area_in_motion_vectors = animal_dimension ** 2 / 16 ** 2
animal_pixel_speed = (animal_speed * 1 / settings.camera.framerate * focal_len) / (
    pixel_ratio * subject_distance
)

settings.filter.motion.sotv_threshold = forced_setter(
    "SoTV general threshold",
    settings.filter.motion.sotv_threshold,
    animal_pixel_speed * animal_area_in_motion_vectors,
)
animal_frames = settings.camera.resolution[0] / animal_pixel_speed
settings.filter.motion.iir_cutoff_hz = forced_setter(
    "SoTV smoothing cut-off frequency/Hz",
    settings.filter.motion.iir_cutoff_hz,
    settings.camera.framerate / animal_frames,
)
settings.filter.motion.iir_order = setter(
    "SoTV smoothing IIR order (ADVANCED)", settings.filter.motion.iir_order
)
settings.filter.motion.iir_attenuation = setter(
    "SoTV smoothing IIR stop-band attenuation (ADVANCED)",
    settings.filter.motion.iir_attenuation,
)

print("----Animal filtering")
settings.filter.animal.threshold = setter(
    "Animal confidence threshold (ADVANCED)", settings.filter.animal.threshold
)

print("----Processing settings")
if settings.pipeline.pipeline_variant == PipelineVariant.LEGACY.value:
    settings.filter.processing.smoothing_factor = forced_setter(
        "Smoothing factor",
        settings.filter.processing.smoothing_factor,
        animal_frames / settings.camera.framerate,
    )
settings.filter.processing.max_sequence_period_s = setter(
    "Max. motion sequence period/s (ADVANCED)",
    settings.filter.processing.max_sequence_period_s,
)
settings.filter.processing.context_length_s = setter(
    "Motion context buffer length/s",
    settings.filter.processing.context_length_s,
)
if settings.pipeline.pipeline_variant == PipelineVariant.LOW_POWER.value:
    settings.filter.processing.detector_fraction = setter(
        "Fraction of event to process with neural network, range: [0-1]",
        settings.filter.processing.detector_fraction,
    )

print("\nSensor settings")
print("---------------")
settings.sensor.port = setter("Sensor board port", settings.sensor.port)
settings.sensor.baud = setter("Sensor board baud rate", settings.sensor.baud)
settings.sensor.interval_s = setter(
    "Sensor reading interval/s", settings.sensor.interval_s
)
settings.sensor.obfuscation_distance_km = setter(
    "GPS obfuscation distance/km", settings.sensor.obfuscation_distance_km
)

print("\nOutput settings")
print("---------------")
mode = input("Output mode: save to disk, or server? (d/s) [d]> ")
if mode == "s":
    settings.output = SenderSettings
    settings.output.output_mode = OutputMode.SEND.value
    settings.output.server = setter("Server address", settings.output.server)
else:
    settings.output = WriterSettings
    settings.output.output_mode = OutputMode.DISK.value
    settings.output.path = setter("Output path", settings.output.path)


format = input("Output format video? (y/n) [y]> ")
if format == "n":
    if mode == "s":
        settings.output.POST = "capture/"
    settings.output.output_format = OutputFormat.STILL.value
else:

    if mode == "s":
        settings.output.POST = "capture_video/"
    settings.output.output_format = OutputFormat.VIDEO.value
    codec = input("Codec: H264, or PIM1 [H264]> ")
    if codec == "PIM1":
        settings.output.output_codec = OutputVideoCodec.PIM1.value
    else:
        settings.output.output_codec = OutputVideoCodec.H264.value

settings.output.device_id = setter("Device ID", settings.output.device_id)

print("\nLogging level")
print("---------------")
settings.logging.level = setter(
    "Level from `DEBUG`, `INFO`, `WARNING`, `ERROR`", settings.logging.level
)


def serialise(obj):
    if isinstance(obj, Settings):
        return {k: serialise(v) for k, v in obj.__dict__.items()}

    elif isinstance(obj, FilterSettings):
        return {k: serialise(v) for k, v in obj.__dict__.items()}

    elif isinstance(obj, MappingProxyType):
        return {k: v for k, v in obj.items() if not k.startswith("__")}

    elif isinstance(obj, str):
        return obj

    return obj.__dict__


with open("DynAIkonTrap/settings.json", "w") as f:
    dump(settings, f, default=serialise)
