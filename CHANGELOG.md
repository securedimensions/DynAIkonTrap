# Change Log

## [v1.1.0] - 2021-08-15
### Added
- Check for `settings.json` version vs. DynAIkonTrap version in case settings are copied from one trap to another
- Added support for multiple output video codecs and settings to choose between them.

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
