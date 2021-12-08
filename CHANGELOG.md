# Change Log
## [v1.2.1] - 2021-11-24

### Added 
- Support for TFLite trained SSDLite MobileNet v2 models
    - TFLite compiled binary wheel files for raspberry pi devices are included in `python_wheels/tflite_runtime`
        - at present installing through pip is experimental on RPi 4 and not possible on RPi Zero W, must be built from source.
    - `animal.py` modified to run inference using tflite networks or yolov4-tiny
    - `animal.py` `run_raw` and `run` modified to produce a `human_confidence` as well as `animal_confidence`
    - configuration for human detection, fast animal detection (tflite model) and thresholds for each added to settings.

### Fixed  
    - fixed output queue length in `event_rememberer` to 1 not 10, this stops the system loading way too many motion events and exhausting memory (kswaps)
    - fixed indexing error in reading from motion buffer within `camera_to_disk.py`

### Changed
    - methods which use `animal.run` have been modified to accept human and animal values
    - changes in `setup.sh` insure tflite install is attempted 

## [v1.2.0] - 2021-10-31
### Added 
- Camera recording to disk module, modified PiCamera; DynCamera
- EventRememberer which to load events from disk into processing pipeline
- Filtermodes BY_FRAME and BY_EVENT to add functionality to process events with Filter module
- Event output added to comms.py
- modified __main__.py to support old and new pipelines depending on settings
- Modified settings to include parameters for: pipeline, bitrate, framerate divisor, buffer length, raw image format and detector fraction 

### Changed 
- Motion Queue Settings semantics changed to processing settings. To better fit other pipeline which does not use a motion queue.


## [v1.1.0] - 2021-08-15
### Added
- Check for `settings.json` version vs. DynAIkonTrap version in case settings are copied from one trap to another
- Added support for multiple output video codecs and settings to choose between them
- Pillow to requirements.txt easiest way to load raw images as far as I can tell. If this can be done with OpenCV it would be nicer. 


### Fixed
- Implementation of UrSense interface following updated documentation
- Catches pycamera `ModuleNotFoundError` when running the camera trap with emulated input on desktop

### Changed
- Video sensor logs to JSON for easier machine reading -- parsing this back to the previous VTT output is trivial
- Interface to initialise `Output` -- output mode is now handled internally
- Documentation -- including wiki -- migrated to Sphinx


### Added 
- context buffer so that clips of animals include "run in" and "trail off" frames. 
- `LabelledFrames` now include a `motion_status` label of enumerated type `MotionStatus`
- `filtering.py` adds all frames to a `motion_sequence` regardless of motion score but labels frames passing through it. 
- frames without motion are assigned a priority of -1.0 and a `MotionStatus` of `STILL` this ensures they are never returned by `get_highest_priority()` - thus never assessed for containing an animal.
- `MotionQueue` does not add motion sequences to its queue which do not contain motion. ie `end_motion_sequence()` now searches the sequence to make sure at least one frame is labelled with motion before appending to queue.  


### Changed
- `MotionSequence` class is now called `Sequence`
- `MotionQueue` class is now called `MotionLabelledQueue` 
---

## [v1.0.0] - 2021-06-12
### Added
- First release of DynAIkonTrap
