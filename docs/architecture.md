# Architecture

```mermaid
flowchart TD
    CLI[d20-tools CLI] --> I[SysEx inspector]
    CLI --> S[Sound converter]
    CLI --> R[Rhythm converter]
    CLI --> W[Song / All placeholders]
    S --> Core[Shared D-20 validation core]
    R --> Core
    Core --> Native[Native .333 / .444 files]
    Core --> Midi[Standard MIDI .mid]
    Core --> Syx[Raw SysEx .syx]
    Tests[Unit and regression tests] --> CLI
    Tests --> Core
    Local[Optional local fixtures\nAwkward.mid + TESTSND.333] --> Tests
```

`core.py` owns file safety, DT1 checksum validation, address-aware assembly,
and atomic output replacement. `sound.py` and `rhythm.py` own only the rules
for their respective native containers. The CLI dispatches one explicit
subcommand and never guesses a file type.
