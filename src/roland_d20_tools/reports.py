"""Read-only, record-safe diagnostic reports for Roland D-20 DT1 dumps."""

from __future__ import annotations

from pathlib import Path

from .core import D20Error, assemble_partial, load_dt1, note_name, printable_text, user_tone_names


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


def _value(table: tuple[str, ...], value: int) -> str:
    return table[value] if 0 <= value < len(table) else f"Unknown({value})"


def _load(path: Path):
    messages = load_dt1(path)
    if not messages:
        raise D20Error("No valid Roland D-20 DT1 messages were found.")
    return messages


def _area(messages, area: int, size: int, label: str):
    image = assemble_partial(messages, area, size, label)
    if not image.coverage():
        raise D20Error(f"No {label} (address {area:02X}H) was found in this file.")
    return image


def _tone_label(group: int, number: int, names: dict[int, str]) -> str:
    if group == 0:
        return f"a{number + 1:02d} ({_value(PRESET_A, number)})"
    if group == 1:
        return f"b{number + 1:02d} ({_value(PRESET_B, number)})"
    if group == 2:
        return f"i{number + 1:02d} ({names.get(number, 'User Tone')})"
    if group == 3:
        return f"r{number + 1:02d} ({_value(RHYTHM_TONES, number)})"
    return f"unknown group {group}, tone {number + 1}"


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


def patch(path: Path, number: int | None = None) -> str:
    messages = _load(path)
    image = _area(messages, 0x07, 128 * 38, "Patch data")
    names = user_tone_names(messages)
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
    return "\n".join((
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


def _slot(index: int) -> str:
    bank = "I" if index < 64 else "C"
    item = index if index < 64 else index - 64
    return f"{bank}-{item // 8 + 1}{item % 8 + 1}"


def timbre(path: Path, slot: str | None = None) -> str:
    messages = _load(path)
    image = _area(messages, 0x05, 128 * 8, "Timbre data")
    names = user_tone_names(messages)
    if slot is None:
        lines = ["Slot   Source      Tone"]
        for index in range(128):
            start = index * 8
            if image.complete(start, 8):
                group, number = image.data[start], image.data[start + 1]
                source = ("Preset A", "Preset B", "User", "Rhythm")[group] if group < 4 else "Unknown"
                lines.append(f"{_slot(index):<6} {source:<11} {_tone_label(group, number, names)}")
        return "\n".join(lines)
    target = slot.upper().strip()
    choices = {_slot(index): index for index in range(128)}
    if target not in choices:
        raise D20Error("--slot must be I-11 through I-88 or C-11 through C-88.")
    start = choices[target] * 8
    if not image.complete(start, 8):
        raise D20Error(f"Timbre slot {target} is incomplete; no values were guessed.")
    data = image.data[start : start + 8]
    return "\n".join((
        f"Timbre slot {target}", f"Tone: {_tone_label(data[0], data[1], names)}", f"Key shift: {data[2] - 24:+d}; fine tune: {data[3] - 50:+d}",
        f"Bender range: {data[4]}; assign mode: {data[5] + 1}; reverb: {'ON' if data[6] == 1 else 'OFF'}",
    ))


def _partial(data: bytes, offset: int, source: str) -> list[str]:
    value = lambda index: data[offset + index]
    waveform = ("Saw" if value(4) else "Square") if source == "S" else f"PCM bank {1 if value(4) else 0}, wave {value(5) + 1}"
    return [
        f"  Wave generator: pitch {note_name(value(0), d20_octaves=True)}, fine {value(1) - 50:+d}, key follow {_value(WG_KF, value(2))}, bender {'ON' if value(3) else 'OFF'}",
        f"  Wave: {waveform}; pulse width {value(6)}; pulse-width velocity {value(7) - 7:+d}",
        f"  LFO: rate {value(20)}, depth {value(21)}, modulation {value(22)}",
        f"  Pitch envelope: depth {value(8)}, velocity {value(9)}, time key follow {_value(TKF, value(10))}; times {list(data[offset + 11:offset + 15])}",
        f"  TVF: cutoff {value(23)}, resonance {value(24)}, key follow {_value(TVF_KF, value(25))}, bias {note_name(value(26), d20_octaves=True)} / {value(27) - 7:+d}",
        f"  TVA: level {value(41)}, velocity {value(42) - 50:+d}; bias 1 {note_name(value(43), d20_octaves=True)} / {value(44) - 7:+d}; bias 2 {note_name(value(45), d20_octaves=True)} / {value(46) - 7:+d}",
    ]


def tone(path: Path, number: int | None = None) -> str:
    messages = _load(path)
    permanent = assemble_partial(messages, 0x08, 64 * 256, "Tone data")
    temporary = assemble_partial(messages, 0x04, 64 * 256, "Temporary Tone data")
    image, area = (permanent, "08H") if permanent.coverage() else (temporary, "04H")
    if not image.coverage():
        raise D20Error("No Tone data was found in address 08H or 04H.")
    if number is None:
        lines = [f"Tone names (address {area})", "ID   Name"]
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
    lines = [f"Tone {number}: {printable_text(data[:10])} (address {area})", f"Structure 1/2: {structures[0]} ({STRUCTURES.get(structures[0], 'Unknown')}); structure 3/4: {structures[1]} ({STRUCTURES.get(structures[1], 'Unknown')})", f"Envelope mode: {'No Sustain' if data[13] == 1 else 'Normal'}"]
    for partial, offset in enumerate((14, 72, 130, 188)):
        active = bool(data[12] & (1 << partial))
        lines.append(f"\nPartial {partial + 1} [{source_pairs[partial]}]: {'ACTIVE' if active else 'MUTED'}")
        if active:
            lines.extend(_partial(data, offset, source_pairs[partial]))
    return "\n".join(lines)


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
