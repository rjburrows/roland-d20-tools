"""Read-only, record-safe diagnostic reports for Roland D-20 DT1 dumps."""

from __future__ import annotations

from pathlib import Path

from .core import D20Error, assemble_partial, load_report_messages, note_name, printable_text, user_tone_names


PRESET_A = (
    "AcouPiano 1", "AcouPiano 2", "AcouPiano 3", "Honky Tonk", "Elec Piano 1", "Elec Piano 2", "Elec Piano 3", "Elec Piano 4",
    "Elec Organ 1", "Elec Organ 2", "Elec Organ 3", "Elec Organ 4", "Pipe Organ 1", "Pipe Organ 2", "Pipe Organ 3", "Accordion",
    "Harpsi 1", "Harpsi 2", "Harpsi 3", "Clav 1", "Clav 2", "Clav 3", "Celesta 1", "Celesta 2", "Violin 1", "Violin 2",
    "Cello 1", "Cello 2", "Contrabass", "Pizzicato", "Harp 1", "Harp 2", "Strings 1", "Strings 2", "Strings 3", "Strings 4",
    "Brass 1", "Brass 2", "Brass 3", "Brass 4", "Trumpet 1", "Trumpet 2", "Trombone 1", "Trombone 2", "Horn", "Fr Horn",
    "Engl Horn", "Tuba", "Flute 1", "Flute 2", "Piccolo", "Recorder", "Pan Pipes", "Bottleblow", "Breathpipe", "Whistle",
    "Sax 1", "Sax 2", "Sax 3", "Clarinet 1", "Clarinet 2", "Oboe", "Bassoon", "Harmonica",
)
PRESET_B = (
    "Fantasy", "Harmo Pan", "Chorale", "Glasses", "Soundtrack", "Atmosphere", "Warm Bell", "Space Horn", "Echo Bell", "Ice Rains",
    "Oboe 2002", "Echo Pan", "Bell Swing", "Reso Synth", "Steam Pad", "VibeString", "Syn Lead 1", "Syn Lead 2", "Syn Lead 3",
    "Syn Lead 4", "Syn Bass 1", "Syn Bass 2", "Syn Bass 3", "Syn Bass 4", "AcouBass 1", "AcouBass 2", "ElecBass 1",
    "ElecBass 2", "SlapBass 1", "SlapBass 2", "Fretless 1", "Fretless 2", "Vibe", "Glock", "Marimba", "Xylophone", "Guitar 1",
    "Guitar 2", "Elec Gtr 1", "Elec Gtr 2", "Koto", "Shamisen", "Jamisen", "Sho", "Shakuhachi", "WadaikoSet", "Sitar",
    "Steel Drum", "Tech Snare", "Elec Tom", "Revrse Cym", "Ethno Hit", "Timpani", "Triangle", "Wind Bell", "Tube Bell", "Orche Hit",
    "Bird Tweet", "OneNoteJam", "Telephone", "Typewriter", "Insect", "WaterBells", "Jungle Tune",
)
RHYTHM_TONES = (
    "Closed High Hat-1", "Closed High Hat-2", "Open High Hat-1", "Open High Hat-2", "Crash Cymbal", "Crash Cymbal (short)",
    "Crash Cymbal (mute)", "Ride Cymbal", "Ride Cymbal (short)", "Ride Cymbal (mute)", "Cup", "Cup (mute)", "China Cymbal",
    "Splash Cymbal", "Bass Drum-1", "Bass Drum-2", "Bass Drum-3", "Bass Drum-4", "Snare Drum-1", "Snare Drum-2", "Snare Drum-3",
    "Snare Drum-4", "Snare Drum-5", "Snare Drum-6", "Rim Shot", "Brush-1", "Brush-2", "High Tom Tom-1", "Middle Tom Tom-1",
    "Low Tom Tom-1", "High Tom Tom-2", "Middle Tom Tom-2", "Low Tom Tom-2", "High Tom Tom-3", "Middle Tom Tom-3", "Low Tom Tom-3",
    "High Pitch Tom 1", "High Pitch Tom 2", "Hand Clap", "Tambourine", "Cowbell", "High Bongo", "Low Bongo", "High Conga (mute)",
    "High Conga", "Low Conga", "High Timbale", "Low Timbale", "High Agogo", "Low Agogo", "Cabasa", "Maracas", "Short Whistle",
    "Long Whistle", "Quijada", "Claves", "Castanets", "Triangle", "Wood Block", "Bell", "Native Drum-1", "Native Drum-2", "Native Drum-3", "OFF",
)

STRUCTURES = {
    1: "S-S (Mix)", 2: "S-S (Ring)", 3: "P-S (Mix)", 4: "P-S (Ring)", 5: "S-P (Ring)", 6: "P-P (Mix)",
    7: "P-P (Ring)", 8: "S-S (Ring)", 9: "P-P (Ring)", 10: "S-S (Ring/Mix)", 11: "P-S (Ring/Mix)",
    12: "S-P (Ring/Mix)", 13: "P-P (Ring/Mix)",
}
WG_KF = ("-1", "-1/2", "0", "1/8", "1/4", "3/8", "1/2", "5/8", "3/4", "7/8", "1", "5/4", "3/2", "2", "s1", "s2")
TVF_KF = ("0", "1/8", "1/4", "3/8", "1/2", "5/8", "3/4", "7/8", "1", "1.5", "2", "s1", "s2")
TKF = ("0", "1", "2", "3", "4")
REVERB = ("Room 1", "Room 2", "Hall 1", "Hall 2", "Plate", "Delay 1", "Delay 2", "Delay 3", "OFF")

# The D-20 reference chart calls these Bank 1 and Bank 2, with PCM numbers
# 1..128. DT1 stores the same values as bank 0/1 and waveform index 0..127.
PCM_BANKS = (
    (
        "Bass Drum-1", "Bass Drum-2", "Bass Drum-3", "Snare Drum-1", "Snare Drum-2", "Snare Drum-3", "Snare Drum-4", "Tom Tom-1",
        "Tom Tom-2", "High-Hat", "High-Hat (Loop)", "Crash Cymbal-1", "Crash Cymbal-2 (Loop)", "Ride Cymbal-1", "Ride Cymbal-2 (Loop)", "Cup",
        "China Cymbal-1", "China Cymbal-2 (Loop)", "Rim Shot", "Hand Clap", "Mute High Conga", "Conga", "Bongo", "Cowbell", "Tambourine", "Agogo",
        "Claves", "Timbale High", "Timbale Low", "Cabasa", "Timpani Attack", "Timpani", "Acoustic Piano High", "Acoustic Piano Low", "Piano Forte Jump",
        "Organ Percussion", "Trumpet", "Lips", "Trombone", "Clarinet", "Flute High", "Flute Low", "Steamer", "Indian Flute", "Breath", "Vibraphone High",
        "Vibraphone Low", "Marimba", "Xylophone High", "Xylophone Low", "Kalimba", "Wind Bell", "Chime Bar", "Hammer", "Guiro", "Chink", "Nails",
        "Fretless Bass", "Pull Bass", "Slap Bass", "Thump Bass", "Acoustic Bass", "Electric Bass", "Gut Guitar", "Steel Guitar", "Dirty Guitar", "Pizzicato",
        "Harp", "Contrabass", "Cello", "Violin-1", "Violin-2", "Koto", "Draw Bars (Loop)", "High Organ (Loop)", "Low Organ", "Trumpet (Loop)",
        "Trombone (Loop)", "Sax-1 (Loop)", "Sax-2 (Loop)", "Reed (Loop)", "Slap Bass (Loop)", "Acoustic Bass (Loop)", "Electric Bass-1 (Loop)",
        "Electric Bass-2 (Loop)", "Gut Guitar (Loop)", "Steel Guitar (Loop)", "Electric Guitar (Loop)", "Clav (Loop)", "Cello (Loop)", "Violin (Loop)",
        "Electric Piano-1 (Loop)", "Electric Piano-2 (Loop)", "Harpsichord-1 (Loop)", "Harpsichord-2 (Loop)", "Telephone Bell (Loop)",
        "Female Voice-1 (Loop)", "Female Voice-2 (Loop)", "Male Voice-1 (Loop)", "Male Voice-2 (Loop)", "Spectrum-1 (Loop)", "Spectrum-2 (Loop)",
        "Spectrum-3 (Loop)", "Spectrum-4 (Loop)", "Spectrum-5 (Loop)", "Spectrum-6 (Loop)", "Spectrum-7 (Loop)", "Spectrum-8 (Loop)",
        "Spectrum-9 (Loop)", "Spectrum-10 (Loop)", "Noise (Loop)", "Shot-1", "Shot-2", "Shot-3", "Shot-4", "Shot-5", "Shot-6", "Shot-7",
        "Shot-8", "Shot-9", "Shot-10", "Shot-11", "Shot-12", "Shot-13", "Shot-14", "Shot-15", "Shot-16", "Shot-17",
    ),
    (
        "Bass Drum-1", "Bass Drum-2", "Bass Drum-3", "Snare Drum-1", "Snare Drum-2", "Snare Drum-3", "Snare Drum-4", "Tom Tom-1",
        "Tom Tom-2", "High-Hat", "High-Hat (Loop)", "Crash Cymbal-1", "Crash Cymbal-2 (Loop)", "Ride Cymbal-1", "Ride Cymbal-2 (Loop)", "Cup",
        "China Cymbal-1", "China Cymbal-2 (Loop)", "Rim Shot", "Hand Clap", "Mute High Conga", "Conga", "Bongo", "Cowbell", "Tambourine", "Agogo",
        "Claves", "Timbale High", "Timbale Low", "Cabasa", *tuple(f"Loop-{index}" for index in range(1, 65)), *tuple(f"Jam-{index} (Loop)" for index in range(1, 35)),
    ),
)


def _value(table: tuple[str, ...], value: int) -> str:
    return table[value] if 0 <= value < len(table) else f"Unknown({value})"


def _raw(value: int, minimum: int, maximum: int) -> str:
    """Format a documented unsigned parameter without hiding bad stored data."""
    return str(value) if minimum <= value <= maximum else f"Invalid({value}; expected {minimum}..{maximum})"


def _signed(value: int, zero: int, minimum: int, maximum: int) -> str:
    """Format a signed parameter whose stored value is offset from zero."""
    if not minimum <= value <= maximum:
        return f"Invalid({value}; expected {minimum}..{maximum})"
    return f"{value - zero:+d}"


def _negative(value: int, maximum: int) -> str:
    """Format a stored 0..maximum parameter that represents 0..-maximum."""
    if not 0 <= value <= maximum:
        return f"Invalid({value}; expected 0..{maximum})"
    return f"{-value:+d}"


def _one_based(value: int, maximum: int) -> str:
    """Format a zero-based enumerated value using its displayed number."""
    if not 0 <= value <= maximum:
        return f"Invalid({value}; expected 0..{maximum})"
    return str(value + 1)


def _series(values: bytes, formatter) -> str:
    """Format a compact parameter series without concealing invalid values."""
    return "[" + ", ".join(formatter(value) for value in values) + "]"


def _bias_point(value: int) -> str:
    """Decode the D-20's 7-bit, directional bias-point representation.

    Values 0..63 mean <A1..<C7 and 64..127 mean >A1..>C7.  The lower
    six bits advance chromatically from A1, rather than using MIDI's C-based
    note zero.  This is distinct from Wave Generator pitch values.
    """
    if not 0 <= value <= 127:
        return f"Invalid({value})"
    note_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    pitch = value & 0x3F
    note_index = pitch + 9  # Stored 0 is A1; stored 3 is C2.
    direction = "<" if value < 64 else ">"
    return f"{direction}{note_names[note_index % 12]}{note_index // 12 + 1}"


def _load(path: Path):
    messages = load_report_messages(path)
    if not messages:
        raise D20Error("No valid Roland D-20 DT1 messages were found.")
    return messages


def _area(messages, area: int, size: int, label: str):
    image = assemble_partial(messages, area, size, label)
    if not image.coverage():
        raise D20Error(f"No {label} (address {area:02X}H) was found in this file.")
    return image


def _tone_label(group: int, number: int, names: dict[int, str], *, parenthesize_name: bool = True) -> str:
    def label(identifier: str, name: str) -> str:
        return f"{identifier} ({name})" if parenthesize_name else f"{identifier} {name}"

    if group == 0:
        return label(f"a{number + 1:02d}", _value(PRESET_A, number))
    if group == 1:
        return label(f"b{number + 1:02d}", _value(PRESET_B, number))
    if group == 2:
        return label(f"i{number + 1:02d}", names.get(number, "User Tone"))
    if group == 3:
        return label(f"r{number + 1:02d}", _value(RHYTHM_TONES, number))
    return f"unknown group {group}, tone {number + 1}"


def _pcm_wave_name(selector: int, index: int) -> str:
    """Format PCM values using the two-bank, one-based reference chart.

    Factory Tone data uses selector values 0, 2, and 3. The D-20's two PCM
    banks are selected as 0 (manual Bank 1) or non-zero (manual Bank 2).
    """
    bank_index = 0 if selector == 0 else 1
    bank_number = bank_index + 1
    if not 0 <= index < len(PCM_BANKS[bank_index]):
        return f"Unknown waveform (PCM Bank {bank_number}, Wave {index + 1})"
    return f"{PCM_BANKS[bank_index][index]} (PCM Bank {bank_number}, Wave {index + 1})"


def system(path: Path) -> str:
    data = _area(_load(path), 0x10, 50, "System data")
    if not data.complete(0, 50):
        raise D20Error(f"System data is incomplete ({data.coverage()}/50 bytes); no settings were decoded.")
    value = data.data
    lines = ["D-20 Global System Settings (10 00 00)", f"Master tune: {value[0]}", f"Global reverb: {_value(REVERB, value[1])} (time {value[2]}, level {value[3]})", "", "Part     Reserve  Level  Pan     Stored MIDI channel"]
    for index in range(8):
        pan = "Center" if value[42 + index] == 7 else f"L{7 - value[42 + index]}" if value[42 + index] < 7 else f"R{value[42 + index] - 7}"
        lines.append(f"Part {index + 1:<2}  {value[4 + index]:>7}  {value[33 + index]:>5}  {pan:<6}  {value[20 + index] + 1}")
    lines.append(f"Rhythm   {value[12]:>7}  {value[41]:>5}  Per-key  {value[13] + 1}")
    lines.append("Note: stored system MIDI channels are not the active temporary-part channels.")
    return "\n".join(lines)


def patch(path: Path, number: int | None = None, *, showtones: bool = False) -> str:
    messages = _load(path)
    image = _area(messages, 0x07, 128 * 38, "Patch data")
    names = user_tone_names(messages)
    if showtones and number is None:
        raise D20Error("--showtones requires --patch 1..128.")
    if number is None:
        lines = ["ID   Patch name         Layout"]
        for index in range(128):
            start = index * 38
            if image.complete(start, 38) and any(image.data[start : start + 38]):
                layout = ("Whole", "Dual", "Split")[image.data[start]] if image.data[start] < 3 else f"Unknown({image.data[start]})"
                lines.append(f"{index + 1:<4} {printable_text(image.data[start + 21 : start + 37]):<18} {layout}")
        return "\n".join(lines + (["(No populated complete patch records.)"] if len(lines) == 1 else []))
    if not 1 <= number <= 128:
        raise D20Error("--patch must be in the range 1..128.")
    start = (number - 1) * 38
    if not image.complete(start, 38):
        raise D20Error(f"Patch {number} is incomplete; no values were guessed.")
    data = image.data[start : start + 38]
    layout = ("Whole", "Dual", "Split")[data[0]] if data[0] < 3 else f"Unknown({data[0]})"
    report = "\n".join((
        f"Patch {number}: {printable_text(data[21:37])}", f"Layout: {layout}; split: {note_name(data[1])}",
        f"Level: {data[20]}; balance (lower/upper): {data[19]}", f"Reverb: {_value(REVERB, data[16])}; time: {data[17] + 1}; level: {data[18]}", "",
        "Parameter         Lower                              Upper",
        f"Tone              {_tone_label(data[2], data[3], names):<34} {_tone_label(data[4], data[5], names)}",
        f"Key shift         {data[6] - 24:+d}                                 {data[7] - 24:+d}",
        f"Fine tune         {data[8] - 50:+d}                                 {data[9] - 50:+d}",
        f"Bender range      {data[10]}                                  {data[11]}",
        f"Assign mode       {data[12] + 1}                                  {data[13] + 1}",
        f"Reverb switch     {'ON' if data[14] == 1 else 'OFF'}                                 {'ON' if data[15] == 1 else 'OFF'}",
    ))
    if not showtones:
        return report
    assignments = (("Lower Tone", data[2], data[3]), ("Upper Tone", data[4], data[5]))
    return f"{report}\n\n{_assigned_tone_reports(messages, assignments, names)}"


def _timbre_id(index: int) -> str:
    """Return the D-20's A/B panel-bank identifier for a Timbre record."""
    bank = "A" if index < 64 else "B"
    item = index if index < 64 else index - 64
    return f"{bank}-{item // 8 + 1}{item % 8 + 1}"


def timbre(path: Path, selection: str | None = None, *, showtones: bool = False) -> str:
    messages = _load(path)
    image = _area(messages, 0x05, 128 * 8, "Timbre data")
    names = user_tone_names(messages)
    if showtones and selection is None:
        raise D20Error("--showtones requires --timbre A-11..A-88 or B-11..B-88.")
    if selection is None:
        lines = ["Timbre  Source      Tone"]
        for index in range(128):
            start = index * 8
            if image.complete(start, 8):
                group, number = image.data[start], image.data[start + 1]
                source = ("Preset A", "Preset B", "User", "Rhythm")[group] if group < 4 else "Unknown"
                lines.append(f"{_timbre_id(index):<8} {source:<11} {_tone_label(group, number, names, parenthesize_name=False)}")
        return "\n".join(lines)
    target = selection.upper().strip()
    choices = {_timbre_id(index): index for index in range(128)}
    if target not in choices:
        raise D20Error("--timbre must be A-11 through A-88 or B-11 through B-88.")
    start = choices[target] * 8
    if not image.complete(start, 8):
        raise D20Error(f"Timbre {target} is incomplete; no values were guessed.")
    data = image.data[start : start + 8]
    report = "\n".join((
        f"Timbre {target}", f"Tone: {_tone_label(data[0], data[1], names, parenthesize_name=False)}", f"Key shift: {_signed(data[2], 24, 0, 48)}; fine tune: {_signed(data[3], 50, 0, 100)}",
        f"Bender range: {_raw(data[4], 0, 24)}; assign mode: {_one_based(data[5], 3)}; reverb: {'ON' if data[6] == 1 else 'OFF' if data[6] == 0 else _raw(data[6], 0, 1)}",
    ))
    if not showtones:
        return report
    assignments = ((f"Timbre {target}", data[0], data[1]),)
    return f"{report}\n\n{_assigned_tone_reports(messages, assignments, names)}"


def _partial(data: bytes, offset: int, source: str) -> list[str]:
    value = lambda index: data[offset + index]
    raw_100 = lambda item: _raw(item, 0, 100)
    signed_50 = lambda item: _signed(item, 50, 0, 100)
    waveform = ("Saw" if value(4) else "Square") if source == "S" else _pcm_wave_name(value(4), value(5))
    return [
        f"  Wave generator: pitch {note_name(value(0), d20_octaves=True) if value(0) <= 96 else _raw(value(0), 0, 96)}, fine {_signed(value(1), 50, 0, 100)}, key follow {_value(WG_KF, value(2))}, bender {'ON' if value(3) == 1 else 'OFF' if value(3) == 0 else _raw(value(3), 0, 1)}",
        f"  Wave: {waveform}; pulse width {_raw(value(6), 0, 100)}; pulse-width velocity {_signed(value(7), 7, 0, 14)}",
        f"  LFO: rate {_raw(value(20), 0, 100)}, depth {_raw(value(21), 0, 100)}, modulation {_raw(value(22), 0, 100)}",
        f"  Pitch envelope: depth {_raw(value(8), 0, 10)}, velocity {_raw(value(9), 0, 3)}, time key follow {_value(TKF, value(10))}",
        f"    Times T1–T4: {_series(data[offset + 11:offset + 15], raw_100)}; levels L0/L1/L2/Sustain/End: {_series(data[offset + 15:offset + 20], signed_50)}",
        f"  TVF: cutoff {_raw(value(23), 0, 100)}, resonance {_raw(value(24), 0, 30)}, key follow {_value(TVF_KF, value(25))}, bias {_bias_point(value(26))} / {_signed(value(27), 7, 0, 14)}",
        f"  TVF envelope: depth {_raw(value(28), 0, 100)}, velocity {_raw(value(29), 0, 100)}, depth key follow {_value(TKF, value(30))}, time key follow {_value(TKF, value(31))}",
        f"    Times T1–T5: {_series(data[offset + 32:offset + 37], raw_100)}; levels L1/L2/L3/Sustain: {_series(data[offset + 37:offset + 41], signed_50)}",
        f"  TVA: level {_raw(value(41), 0, 100)}, velocity {_signed(value(42), 50, 0, 100)}; bias 1 {_bias_point(value(43))} / {_negative(value(44), 12)}; bias 2 {_bias_point(value(45))} / {_negative(value(46), 12)}",
        f"  TVA envelope: time-1 velocity follow {_value(TKF, value(47))}, time key follow {_value(TKF, value(48))}",
        f"    Times T1–T5: {_series(data[offset + 49:offset + 54], raw_100)}; levels L1/L2/L3/Sustain: {_series(data[offset + 54:offset + 58], raw_100)}",
    ]


def _tone_report(messages, number: int | None = None) -> str:
    permanent = assemble_partial(messages, 0x08, 64 * 256, "Tone data")
    temporary = assemble_partial(messages, 0x04, 64 * 256, "Temporary Tone data")
    image, area = (permanent, "08H") if permanent.coverage() else (temporary, "04H")
    if not image.coverage():
        raise D20Error("No Tone data was found in address 08H or 04H.")
    if number is None:
        lines = [f"Internal/user Tone names (address {area})", "ID   Name"]
        for index in range(64):
            start = index * 256
            if image.complete(start, 10):
                name = printable_text(image.data[start : start + 10])
                if name:
                    lines.append(f"{index + 1:<4} {name}")
        return "\n".join(lines + (["(No complete named tone records.)"] if len(lines) == 2 else []))
    if not 1 <= number <= 64:
        raise D20Error("--tone must be in the range 1..64.")
    start = (number - 1) * 256
    if not image.complete(start, 256):
        raise D20Error(f"Tone {number} in address {area} is incomplete; no values were guessed.")
    data = bytes(image.data[start : start + 256])
    structures = (data[10] + 1, data[11] + 1)
    source_pairs = tuple(("S" if "S" in STRUCTURES.get(structure, "S-S").split(" ")[0].split("-")[part] else "P") for structure in structures for part in range(2))
    lines = [f"Internal/user Tone i{number:02d}: {printable_text(data[:10])} (address {area})", f"Structure 1/2: {structures[0]} ({STRUCTURES.get(structures[0], 'Unknown')}); structure 3/4: {structures[1]} ({STRUCTURES.get(structures[1], 'Unknown')})", f"Envelope mode: {'No Sustain' if data[13] == 1 else 'Normal'}"]
    for partial, offset in enumerate((14, 72, 130, 188)):
        active = bool(data[12] & (1 << partial))
        lines.append(f"\nPartial {partial + 1} [{source_pairs[partial]}]: {'ACTIVE' if active else 'MUTED'}")
        if active:
            lines.extend(_partial(data, offset, source_pairs[partial]))
    return "\n".join(lines)


def _assigned_tone_reports(messages, assignments: tuple[tuple[str, int, int], ...], names: dict[int, str]) -> str:
    """Append editable Tone details for one or more Patch/Timbre assignments."""
    sections = ["Underlying Tone configuration"]
    source_descriptions = {
        0: "a fixed Preset A ROM Tone; no editable Tone configuration is present in a DT1 dump.",
        1: "a fixed Preset B ROM Tone; no editable Tone configuration is present in a DT1 dump.",
        3: "a Rhythm Tone; no editable Tone configuration is present in a DT1 dump.",
    }
    for context, group, number in assignments:
        label = _tone_label(group, number, names, parenthesize_name=False)
        heading = f"{context}: {label}"
        if group in source_descriptions:
            sections.append(f"{heading}\n  This is {source_descriptions[group]}")
            continue
        if group != 2:
            sections.append(f"{heading}\n  This uses an unknown Tone group; no configuration can be decoded.")
            continue
        try:
            details = _tone_report(messages, number + 1)
        except D20Error as exc:
            sections.append(f"{heading}\n  Tone configuration unavailable: {exc}")
        else:
            sections.append(f"{heading}\n\n{details}")
    return "\n\n".join(sections)


def tone(path: Path, number: int | None = None) -> str:
    return _tone_report(_load(path), number)


def rhythm(path: Path) -> str:
    messages = _load(path)
    image = _area(messages, 0x09, 85 * 4, "Rhythm Setup data")
    if not image.complete(0, 85 * 4):
        raise D20Error(f"Rhythm Setup data is incomplete ({image.coverage()}/340 bytes); no values were guessed.")
    names = user_tone_names(messages)
    lines = ["D-20 Rhythm Setup (09 00 00)", "Note       Tone                              Level  Pan     Reverb"]
    for index in range(85):
        offset, tone_number = index * 4, image.data[index * 4]
        if tone_number == 127:
            continue
        label = _tone_label(2, tone_number, names) if tone_number < 64 else _tone_label(3, tone_number - 64, names)
        pan = image.data[offset + 2]
        pan_text = "Center" if pan == 7 else f"L{7 - pan}" if pan < 7 else f"R{pan - 7}"
        lines.append(f"{note_name(index + 24):<10} {label:<33} {image.data[offset + 1]:<6} {pan_text:<7} {'ON' if image.data[offset + 3] == 1 else 'OFF'}")
    return "\n".join(lines)
