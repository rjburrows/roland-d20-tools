# Architecture

```mermaid
flowchart TD
    CLI[d20-tools CLI] --> I[Compact inspector]
    CLI --> F[Named-sound finder]
    CLI --> H[Doctor support summary]
    CLI --> D[Detailed diagnostic reports]
    CLI --> S[Sound converter]
    CLI --> R[Rhythm converter]
    CLI --> W[Song / All placeholders]
    S --> Core[Shared D-20 validation core]
    R --> Core
    D --> Core
    F --> Core
    Core --> Native[Native .333 / .444 files]
    Core --> Midi[Standard MIDI .mid]
    Core --> Syx[Raw SysEx .syx]
    Tests[Unit and regression tests] --> CLI
    Tests --> Core
    Local[Optional local fixtures\nDemoDump.mid + TESTSND.333 + TESTRHY.444 + D1020ORIG.MID] --> Tests
```

`core.py` owns file safety, DT1 checksum validation, address-aware assembly,
text and note helpers, atomic output replacement, and native-file adaptation
for the read-only inspector and reports. `sound.py` and `rhythm.py` own only
the rules for their respective native containers.
`reports.py` decodes complete records only; it never substitutes missing bytes.
The CLI dispatches one explicit subcommand and never guesses a file type. See
the [memory-address reference](memory-map.md) for the layouts used by each
module.
