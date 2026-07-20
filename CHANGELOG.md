# Changelog

All notable changes to Decktation are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.7] - 2026-07-20

### Changed

- Clarified that Decky users must install the `decktation.zip` release asset,
  not GitHub's automatically generated source archives.

### Fixed

- Corrected the L5 and R5 labels in the controller button-test display.
- Added one-hot raw HID mapping coverage so swapped or overlapping physical
  button definitions fail automated tests.

## [0.3.6] - 2026-07-19

### Added

- Added a Guild Wars 2 preset with game-specific chat channels and vocabulary.
- Added direct Steam Deck HID input for stable push-to-talk controls, including
  the rear L4, L5, R4, and R5 buttons and analog trigger handling.
- Added an in-plugin three-second test recording with transcription preview.
- Added marketplace metadata, third-party notices, pinned backend dependencies,
  and Decky-compatible build documentation.
- Added release tooling to keep package versions and Git tags synchronized.

### Changed

- Migrated backend calls to Decky's current callable API.
- Switched release packaging to the official Decky CLI marketplace builder.
- Bundled a CPython 3.11-compatible inference runtime, PortAudio, `ydotool`, and
  a private `ydotoold` instance for SteamOS compatibility.
- Replaced temporary WAV/PyAV transcription with direct normalized PCM input.
- Moved model loading and transcription off Decky's asynchronous request loop.
- Reduced frontend status polling and prevented overlapping backend requests.

### Fixed

- Fixed the plugin remaining indefinitely on **Initializing** with current
  Decky Loader releases.
- Fixed long transcription times and garbled output caused by resampled
  `int16` microphone samples being passed to Whisper at the wrong scale.
- Fixed test recordings typing their transcription into the active window.
- Fixed native Python modules being built for CPython 3.13 instead of Decky's
  embedded CPython 3.11 runtime.
- Fixed release tags being able to disagree with packaged plugin versions.
- Fixed the GitHub Actions Decky executable colliding with its temporary build
  directory.

### Removed

- Removed the `evdev` runtime dependency.
- Removed the PyAV/FFmpeg runtime dependency from the recording path.
- Removed reliance on a system-wide `ydotoold` service.

## [0.3.4] - 2026-07-18

### Added

- Added support for the Steam Deck's L4, L5, R4, and R5 rear buttons.

### Fixed

- Made all plugin controls focusable and usable in Game Mode.

## [0.3.3] - 2026-04-23

### Fixed

- Restored controller detection after a Steam Deck software update.

## [0.3.2] - 2026-03-24

### Added

- Added a spoken raid-warning channel.

### Fixed

- Included channel language configuration and documentation in release builds.

## [0.3.1] - 2026-03-21

### Added

- Added English and French channel trigger configuration.
- Added manual-send mode, which types a transcription without pressing Enter.

## [0.2.5] - 2026-03-06

### Fixed

- Selected the appropriate controller input device from its available buttons.

## [0.2.4] - 2026-03-04

### Fixed

- Corrected spoken channel-prefix handling.
- Restored missing game presets in packaged releases.
- Switched the controller listener to the SteamOS system Python interpreter.

## [0.2.3] - 2026-02-27

### Changed

- Bundled plugin dependencies instead of requiring system installations.
- Enabled CI builds for all branches.

## [0.2.2] - 2026-02-26

### Fixed

- Granted the release workflow permission to upload GitHub Release assets.

## [0.2.1] - 2026-02-26

### Added

- Added automatic GitHub Release creation for version tags.

## [0.2.0] - 2026-02-17

### Added

- Added configurable game presets and channel mappings.
- Added confirmation notifications before automatically sending text.
- Added automated tests and CI checks.

### Changed

- Refactored plugin modules and cleaned up the Decky interface.

## [0.1.0] - 2026-02-08

### Added

- Initial packaged release of Decktation for Decky Loader.

[Unreleased]: https://github.com/silverfoxy/decktation/compare/v0.3.6...HEAD
[0.3.6]: https://github.com/silverfoxy/decktation/compare/v0.3.4...v0.3.6
[0.3.4]: https://github.com/silverfoxy/decktation/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/silverfoxy/decktation/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/silverfoxy/decktation/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/silverfoxy/decktation/compare/v0.2.5...v0.3.1
[0.2.5]: https://github.com/silverfoxy/decktation/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/silverfoxy/decktation/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/silverfoxy/decktation/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/silverfoxy/decktation/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/silverfoxy/decktation/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/silverfoxy/decktation/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/silverfoxy/decktation/releases/tag/v0.1.0
