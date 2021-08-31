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

---

## [v1.0.0] - 2021-06-12
### Added
- First release of DynAIkonTrap
