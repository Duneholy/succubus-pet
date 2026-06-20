# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-21

### Added
- **Cursor IDE Integration**: Real-time background token parsing to track AI API limits and Composer usage.
- **Regular Reminders**: Support for up to 3 repeating interval timers (e.g. every 1 hr 15 mins).
- Double-click action to manually trigger Cursor AI stats overlay.
- Text accumulation bug fix and anti-bounce filtering for fast mouse clicks.

## [1.0.0] - 2026-06-21
### Added
- Complete rewrite and rebranding to Succubus Pet.
- Setup script `Run Succubus.bat` with automatic Python dependency checks and installation.
- Background process functionality with `pystray` system tray integration.
- Custom interactive GUI using `tkinter` for setting daily reminders.
- Dynamic reminder scheduler that triggers full-screen pop-ups and custom animations.
- Typist tracking: the pet notices when you are actively typing and rewards you.
- Smooth borderless window handling and transparency layer using `Pillow`.
