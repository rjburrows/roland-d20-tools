# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-30

### Added

- Safe local conversion between native D-20 Sound (`.333`) and Rhythm (`.444`)
  files and standard MIDI or raw SysEx.
- Read-only inspection and detailed System, Patch, Timbre, Tone, and Rhythm
  reports for D-20 dumps and compatible native files.
- A recursive `d20-tools find` command for Patch, Timbre, and Tone names.
- Explicit detection of native Song (`.222`) and All (`.111`) containers.
- Public automated tests, optional private regression checks, and CI release
  verification.

### Known limitations

- Song and All conversion commands are placeholders. They do not write files.
- The tool does not send or receive data through a live MIDI interface.
