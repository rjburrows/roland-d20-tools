# Changelog

## Unreleased

### Added

- **BETA** one-way note-event MIDI export for native Song (`.222`) and All
  (`.111`) files, using their shared Song region. Exports Type-1 MIDI with
  96 positions per quarter, stored-status lanes, and validated pattern meter.
- Generated cross-format timing, running-status, error, and output-safety tests.

### Limitations

- Saved tempo, original routing/patches and rhythm-pattern notes are not yet
  decoded. An explicit audition tempo is required; no native round trip.

## [0.2.0] - 2026-07-31

### Added

- Experimental one-way D-20 to D-110 SysEx conversion, with validated Tone,
  Timbre, and Rhythm Setup output plus Markdown, HTML, JSON, and CSV reports.
- Structured `inspect` reports in Markdown, HTML, JSON, and CSV, including
  mixed Sound/Rhythm captures and native Song-region inventory.

### Changed

- Expanded report tables for Tones, Timbres, Patches, Rhythm Setup, and
  incomplete-data visibility.
- Clarified that D-110 output requires real-hardware validation.

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
- Machine-readable JSON and CSV output for named-sound searches, plus
  `d20-tools --version` and the `d20-tools doctor` support summary.

### Known limitations

- Song and All conversion commands are placeholders. They do not write files.
- The tool does not send or receive data through a live MIDI interface.
