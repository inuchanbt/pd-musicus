# PD musicus

Turn USB Power Delivery negotiations and load measurements into music.

Source capabilities become melodies, requests and responses become musical exchanges,
and higher measured power adds guitar distortion, drums, and denser rhythms.
Resets and failed measurement states have their own musical accents.

**Version 0.1.0** · [日本語README](README.ja.md)

## Listen first

The same 21 → 48 → 21 V EPR AVS sweep, at two loads:

| Sample | Sound | WAV |
| --- | --- | --- |
| 0.5 A, about 10–24 W | Gentle piano/marimba-style exchange | [Listen / download](examples/avs_0p5a.wav) |
| 5 A, about 105–239 W | Increasing guitar distortion, drums, and rhythmic density | [Listen / download](examples/avs_5a.wav) |

Both are about 45 seconds, rendered with the same power-aware mode and tempo.
Depending on your browser, open or download the WAV to play it.
[Example data and reproduction commands](examples/README.md) are included.

## Requirements

- Python 3.10 or later; no third-party packages required.
- A supported CSV capture (see below).

Keep the Python modules together and run commands from the repository root.
PD musicus works offline with saved files. It does not connect to test equipment.
Private captures and generated output are excluded from version control; the curated
files in `examples/` are deliberately included.

## Quick start

Convert a CY4500 Utility-format PD capture into a piano/marimba-style duet:

```sh
python pd_musicus.py captures/session_pd.csv --out output/duet.wav
```

Use measured power from an ASD AVS sweep to drive the instrumentation:

```sh
python pd_musicus.py captures/sweep_pd.csv --asd captures/sweep_asd.csv --out output/power.wav
```

Turn an ASD CTS-like measurement log into a guitar arrangement:

```sh
python pd_musicus.py captures/cts_asd.csv --mode cts --out output/guitar.wav
```

These paths are placeholders for your own captures. To try the included data immediately:

```sh
python pd_musicus.py examples/avs_5a_pd.csv --asd examples/avs_5a_asd.csv --out output/demo.wav
```

Tests use synthetic data and require no hardware.

## Arrangement modes

| Mode | Input | Arrangement |
| --- | --- | --- |
| `auto` (default) | CSV, optionally `--asd` | Selects `cts` for CTS-column input, `power` for PD plus ASD, otherwise `duet` |
| `conversation` | CY4500 Utility PD CSV | Electronic call and response, with expanded short gaps |
| `duet` | CY4500 Utility PD CSV | Piano/marimba-style motifs on a musical grid with accompaniment |
| `avs` | CY4500 Utility PD CSV | EPR AVS voltage requests mapped to a pentatonic scale |
| `power` | PD CSV plus matching ASD AVS CSV | Measured watts control guitar, drums, and rhythmic density |
| `cts` | ASD CTS-like CSV | Voltage and measured power control low-register guitar riffs |

Select explicitly with `--mode`. `--asd` is only supported for `power`, including automatic selection.

```sh
python pd_musicus.py captures/sweep_pd.csv --mode avs --bpm 120 --out output/avs.wav
python pd_musicus.py captures/session_pd.csv --plan-only --out output/preview.wav
python pd_musicus.py --help
python pd_musicus.py --version
```

### Output controls

- `--out`: WAV destination; defaults to `output/<input-stem>_musicus.wav`.
- `--bpm`: tempo from 30 to 240; defaults depend on the arrangement mode.
- `--plan-only`: write the score/timeline JSON without rendering audio.
- `--overwrite`: explicitly replace existing output files.
- `--max-seconds`: reject longer arrangements (default 180, maximum 600). This does not truncate the music.

## How data becomes music

- **Voltage** selects pitch or register.
- **Measured power** changes instrumentation and rhythmic density, rather than merely increasing volume.
  `power` adds no intensity-driven parts below 30 W and reaches maximum intensity at 240 W.
  `cts` maps 0–240 W to an intensity of 0–1.
- **Requests, Accept, and PS_RDY** create musical exchanges in protocol-focused modes.
- **Soft Reset** produces a descending bell motif; **Hard Reset** produces a low distorted accent.
- **Failed CTS measurement states** retain dissonant accents.

Melodies, accompaniment, and percussion patterns are authored interpretations.
Instruments are synthesized, not recordings of real instruments. Musical time is
compressed or rearranged and does not represent measured protocol latency.

## Supported inputs and limitations

### CY4500 PD captures

The parser accepts Utility-format CSV with fields including `Sno`, `Ok`, `SOP`,
`Message`, `Power Role`, `Data`, and `Start Time`. `Data` contains hexadecimal
header/object tokens; timestamps are in microseconds. `Sno` values must be unique.
The parser handles 32-bit timestamp rollover.

Legacy byte-oriented CLI CSV, JSONL, and scope CSV are not supported in this version.
The format matters more than whether the file was exported by a GUI or CLI.

EPR AVS decoding uses the PDO included in `EPR_REQUEST` to identify the RDO units.
PPS/SPR AVS voltage decoding and extended capability reassembly are not implemented.
Generic protocol modes can still assign motifs to those messages.

### ASD measurements

`power` uses `avs-continuous` rows and matches them to PD requests by count, order,
target voltage, and requested current. Initial load-ramp samples are omitted.
Use files from the **same session**: this does not synchronize device clocks or
prove that unrelated captures belong together.

`cts` groups consecutive rows by `cts_like_case_id` and uses median measured power
for each point. It reads the ASD log alone and does not infer protocol resets from
measurement failures. Missing or unsupported measurement data may reject the input.

Sweep-focused modes omit setup traffic, GoodCRC, and KeepAlive. Resets are retained,
with playback positions interpolated between arranged protocol events.
This is a music tool, not a compliance verdict or measurement-fault diagnosis tool.

## Audio and timeline output

Each render produces:

- A 44.1 kHz, 16-bit stereo WAV, peak-normalized to 0.82.
- A matching `.score.json` containing source references, input hashes, timed events,
  measurement values where available, and the complete note arrangement.

The pipeline separates **input parsing → arrangement → audio rendering**.
The versioned [timeline schema](docs/timeline-v1.md) provides a foundation for future
protocol highlighting, power-driven visual effects, and alternative instrument renderers.
The current version does not include a synchronized visual player or sampled instruments.

## Development

```sh
python -m unittest -v
```

Tests cover input validation, request/response mapping, resets, power-dependent
density, timeline tempo scaling, output protection, and PCM generation.

| File | Responsibility |
| --- | --- |
| `pd_musicus.py` | Unified CLI, mode selection, common timeline, output controls |
| `pd_music.py` | PD CSV parser, general arrangements, synthesizer/WAV renderer |
| `avs_music.py` | EPR AVS extraction and melodic arrangement |
| `power_music.py` | ASD sweep matching and power-dependent orchestration |
| `cts_music.py` | CTS-like measurement grouping and guitar arrangement |
| `test_*.py` | Hardware-independent tests |

Earlier module-level command lines remain available for compatibility.
Use `pd_musicus.py` for new workflows. See [CHANGELOG.md](CHANGELOG.md) for version history.
The Japanese README provides a public Japanese-language guide.

## Future directions

- Refine instrument sounds against a broader set of captures.
- Add sampled instruments and more expressive guitar articulation.
- Highlight the protocol event corresponding to the current playback position.
- Animate voltage, watts, resets, and musical intensity.
- Expand input formats and PPS/SPR AVS decoding.

These are future directions, not features included in v0.1.0.

## License

[MIT](LICENSE). The included example CSV files and synthesized WAV files are also
provided under the MIT license. No third-party instrument recordings are bundled.
