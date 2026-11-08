# Bonus: Roland D-20 PCM samples

[Download all samples — D20_PCM_Samples.zip](https://github.com/rjburrows/roland-d20-tools/raw/refs/heads/main/bonus/D20_PCM_Samples.zip)

The ZIP contains **256 named WAV selections**, arranged in two banks of 128, extracted from the supplied **Roland D-20 ROMS (w-o control)** dump set. These are the D-20's factory PCM waveform regions, rather than recordings of complete tones or patches. Repeated and overlapping selections are retained: the set represents **168 unique address/length regions**.

## Copyright and intended use

**The original PCM waveform content is copyright Roland Corporation. These samples are shared for experimentation and non-commercial use only.** They are excluded from this project's MIT licence. All rights in the original content remain with Roland Corporation; this notice does not claim that Roland has granted a redistribution or other licence. This independent project is not affiliated with or endorsed by Roland Corporation. See [NOTICE.txt](NOTICE.txt), also included in the download.

## Where they came from

The extraction used these supplied ROM images (the raw ROM files are not included):

| ROM image | Role |
| --- | --- |
| `r15179878-3.BIN` | First PCM data segment, ordered by content hash |
| `r15179880-3.BIN` | Second PCM data segment, ordered by content hash |
| `r15179904-00-lh5310dj-full-3.BIN` | Tone metadata: selection boundaries, loop flags and pitch words |

Selection names were cross-checked against the PCM Sounds tables on PDF pages 167–168 of the [Roland D-20 Owner's Manual](https://cdn.roland.com/assets/media/pdf/D-20_OM.pdf). Decoding and table interpretation were informed by [Munt](https://github.com/munt/munt) and the related [Di-111 implementation](https://github.com/luginf/Di-111-synth). The included `provenance.json` records source hashes and implementation references; `sample_manifest.csv` maps each filename to its ROM offset, length and flags.

## Format and limitations

- Mono, signed 16-bit PCM WAV at a **32 kHz preview/export rate**, without normalization or added effects.
- Native note pitch, master tuning, envelopes, filtering, interpolation, output circuitry and reverb are not reconstructed. This is not a verified reproduction of physical D-20 playback.
- Looped regions are exported once; the WAVs contain no loop metadata. Loop flags and raw pitch words are retained in the manifest.
- `_FixedTune` represents an asterisk in the original drum selection name. Some selections therefore contain identical audio with different selection metadata.

The archive also includes the extraction script, name list, manifest, provenance, README and copyright notice. Re-running the script requires the original ROM images. WAV headers, frame counts and audio bytes were checked during extraction, and the ZIP's contents were checked before publication.

The download checksum is in [SHA256SUMS](SHA256SUMS).
