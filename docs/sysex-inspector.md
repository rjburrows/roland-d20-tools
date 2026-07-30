# SysEx inspector (`d20-tools inspect`)

This is a read-only summary for standard MIDI (`.mid` / `.midi`) or raw SysEx
(`.syx`) D-20 dumps. It validates Roland D-20 DT1 framing and checksums, then
lists the recognised memory areas and their message counts.

```sh
d20-tools inspect D20BACKUP.mid
d20-tools inspect D20BACKUP.syx
```

It is useful whether the dump came from MIDI Data Transfer or was produced by
one of the file converters. It never changes the input file.

