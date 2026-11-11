# Doctor (`d20-tools doctor`)

`d20-tools doctor` is a read-only support command. It prints the installed
tool version, Python and Mido versions, the supported file types, ready
commands, and deliberately unavailable capabilities.

```sh
d20-tools doctor
```

Example output:

```text
D-20 Tools doctor
Version: 0.2.0
Python: 3.10.0 (Darwin 24.0.0)
Mido: 1.3.3
Supported input: .mid, .midi, .syx, .333, .444, .111, .222
Ready commands: inspect, find, report, sound, rhythm; experimental: d110
BETA note export: song, all, pattern, rhythm --notes (Song/All saved tempo supported; ROM preset notes undecoded)
Live MIDI input/output: not included
```

Use `d20-tools --version` when only the installed version is needed, for
example when including it in a bug report.
