# Sound finder (`d20-tools find`)

`d20-tools find` searches a folder and every subfolder for named D-20 Tones,
Timbres, and Patches. It accepts standard MIDI (`.mid` and `.midi`), raw SysEx
(`.syx`), native Sound (`.333`), and native All (`.111`) files. It only reads
files; no source file is changed.

```sh
d20-tools find ~/D20-library "Star Synth"
```

The default search is a case-insensitive literal substring search. Thus
`starsynth`, `StarSynth`, and `STAR` can all find a Tone named `StarSynth`.
Results are grouped by absolute filename and identify each matching object.
When a Tone name is in use by a Timbre or Patch, those assignments are also
reported, making it easy to find where the sound is used.

```text
/Users/you/D20-library/set-01.mid
  Tone i17: StarSynth
  Timbre A-11: i17 StarSynth
  Patch 1: Night Pad — i17 StarSynth / i17 StarSynth

Searched 12 supported file(s) for 'starsynth' (case-insensitive substring); found 3 match(es) in 1 file(s).
```

## Options

Limit the result kind when required:

```sh
d20-tools find ~/D20-library "Star Synth" --type patch
d20-tools find ~/D20-library "Star Synth" --type timbre
d20-tools find ~/D20-library "Star Synth" --type tone
```

Use `--exact` to require a complete, case-insensitive Tone or Patch name
match. This is useful where short names would otherwise produce too many
results:

```sh
d20-tools find ~/D20-library StarSynth --type tone --exact
```

Files which do not contain complete compatible D-20 name data are skipped and
counted in the final summary. Native Rhythm and Song files are intentionally
not searched: they do not store the editable Patch, Timbre, or Tone memories.
