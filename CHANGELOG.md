# Changelog

## Unreleased

### Added

- **BETA** saved-tempo extraction for Song and All exports and inspection.
  Header byte `0x36` gives `40 + 2 × code` BPM for codes `0x00..0x69`.
  Song/All export uses it by default and accepts `--tempo-bpm` as an override.
  The executed Ghidra trace documents the load path and timer reapplication.

- Documented the C and A/B ROM reverse mapping and published the Ghidra trace
  scripts and read-only disk probes. Added a 100% branch-aware coverage gate
  for the Song and rhythm pattern decoders.
- **BETA** expanded saved rhythm selection track in Song and All note MIDI
  exports, with explicit rejection of undecoded ROM preset pattern IDs and
  `--no-rhythm-track` for a Song-lanes-only export. The Rhythm command accepts
  `--notes pattern|all|track` to write note MIDI for one writable pattern,
  32 separate pattern tracks, or its saved pattern sequence. Note-off length
  is configurable with `--gate-ticks`.
- **BETA** individual writable rhythm-pattern note MIDI export from native
  Rhythm (`.444`), Song (`.222`), or All (`.111`) files. Keeps simultaneous
  saved hits, note numbers, velocities, pattern meter, and raw Rhythm Setup
  settings as MIDI text; requires an audition tempo and uses a configurable
  provisional note-off gate. Adds synthetic and optional saved-pattern tests.
- **BETA** one-way note-event MIDI export for native Song (`.222`) and All
  (`.111`) files, using their shared Song region. Exports Type-1 MIDI with
  96 positions per quarter, stored-status lanes, and validated pattern meter.
- Generated cross-format timing, running-status, error, and output-safety tests.

### Fixed

- Song inspection and MIDI export validate the first stored pattern's header
  fields, so valid saves with different first-pattern lengths and hit counts
  are accepted.

### Limitations

- Original routing/patches, ROM preset pattern notes, and
  hardware note-off policy are not yet decoded. Writable pattern chains are
  expanded. Standalone Rhythm and individual pattern exports require an
  explicit audition tempo. There is no native note-MIDI round trip.

## [0.2.0] - 2026-07-31

### Added

- **BETA** saved-tempo extraction for Song and All exports and inspection.
  Header byte `0x36` gives `40 + 2 × code` BPM for codes `0x00..0x69`.
  Song/All export uses it by default and accepts `--tempo-bpm` as an override.
  The executed Ghidra trace documents the load path and timer reapplication.

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

- **BETA** saved-tempo extraction for Song and All exports and inspection.
  Header byte `0x36` gives `40 + 2 × code` BPM for codes `0x00..0x69`.
  Song/All export uses it by default and accepts `--tempo-bpm` as an override.
  The executed Ghidra trace documents the load path and timer reapplication.

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
