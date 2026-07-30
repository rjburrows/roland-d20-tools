# Architecture

```mermaid
flowchart TD
    CLI[d20-tools CLI] --> I[SysEx inspector]
    CLI --> D[Detailed diagnostic reports]
    CLI --> S[Sound converter]
    CLI --> R[Rhythm converter]
    CLI --> W[Song / All placeholders]
    S --> Core[Shared D-20 validation core]
    R --> Core
    D --> Core
    Core --> Native[Native .333 / .444 files]
    Core --> Midi[Standard MIDI .mid]
    Core --> Syx[Raw SysEx .syx]
    Tests[Unit and regression tests] --> CLI
    Tests --> Core
    Local[Optional local fixtures\nDemoDump.mid + TESTSND.333] --> Tests
```

`core.py` owns file safety, DT1 checksum validation, address-aware assembly,
text and note helpers, and atomic output replacement. `sound.py` and
`rhythm.py` own only the rules for their respective native containers.
`reports.py` decodes complete records only; it never substitutes missing bytes.
The CLI dispatches one explicit subcommand and never guesses a file type. See
the [memory-address reference](memory-map.md) for the layouts used by each
module.
