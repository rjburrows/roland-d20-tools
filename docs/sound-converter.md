# Sound converter (`d20-tools sound`)

Converts a Roland D-20 Sound disk file (`.333`) to either a Standard MIDI file
(`.mid`) containing D-20 DT1 SysEx messages, or raw SysEx (`.syx`). It also
reconstructs a `.333` file from a complete compatible MIDI or SysEx dump.

```sh
d20-tools sound SOUND.333 SOUND.mid
d20-tools sound SOUND.mid SOUND.333 --name SOUND
d20-tools sound SOUND.333 SOUND.syx --device-id 0x10
```

The native file is exactly 24,576 bytes. Conversion validates the file header,
filename field, duplicated patch region, DT1 checksums, complete Tone/Timbre/
Patch coverage, and the ten native-unrepresentable trailing bytes of each Tone.
It refuses lossy input rather than quietly changing a sound bank.
