# PD musicus

Turn USB Power Delivery negotiations and load measurements into music.

Source capabilities become melodies, requests and responses become musical exchanges,
and higher measured power adds guitar distortion, drums, and denser rhythms.
Resets and failed measurement states have their own musical accents.

**Version 0.2.0** · [日本語README](README.ja.md)

## Watch the conversation

```sh
python pd_musicus.py --player
```

This opens a local browser player with the two included audio examples. It displays
the current protocol event, source/sink direction, surrounding events, and measured
voltage/current/power when available. Pause, seek, or click an event to jump to its sound.

Use **Open your recording** to select one WAV and its matching schema-1 `.score.json`
together. Files are processed in the browser and are not uploaded. CTS scores display
measurement cases; protocol scores distinguish Soft Reset and Hard Reset.

The player binds only to `127.0.0.1` and serves a fixed set of player/sample files,
not your private capture directories. Press Ctrl+C in the terminal to stop it.
Use `--port 18765` to request a different port, or `--no-browser` to print the URL
without opening a tab. If the requested port is unavailable, an available local port is used.
You can also open `player/index.html` directly for local WAV/JSON selection; bundled
sample buttons require the local server. A modern browser with WAV playback is required.

The view follows **arranged audio time**, not original wire timing. Measurements belong
to an arranged point, not a live meter. Animated bars illustrate playback/power rather
than an audio spectrum.

## Export a video

The optional offline exporter makes a 1280×720 MP4 with synchronized event labels,
Source/Sink direction, power-driven animation, and the WAV audio (encoded as AAC).
It renders frames directly, so no browser recording is needed.

Install [FFmpeg](https://ffmpeg.org/) with libx264/AAC support and make `ffmpeg`
available on PATH, then install the optional Python dependency:

```sh
python -m pip install -r requirements-video.txt
python pd_musicus.py examples/avs_5a_pd.csv --asd examples/avs_5a_asd.csv --mode power --plan-only --out output/avs_5a_video.wav
python pd_musicus_video.py examples/avs_5a.wav --score output/avs_5a_video.score.json --out output/avs_5a.mp4 --title "EPR AVS / 5 A"
```

The `--plan-only` command creates only the score, matching the included default-tempo WAV.
For your own recordings, use the WAV and score from the same rendering run.
Matching duration is checked; it does not prove that two files belong together.
Options: `--fps 24|30|60` (default 30), `--font path/to/font.ttf`,
`--ffmpeg path/to/ffmpeg`, and `--overwrite`. Videos are limited to 600 seconds.
The video follows the arranged timeline, including resets; CTS inputs show cases.
This is a separate CLI export, with no export button in the browser player.

### From your own measurement logs

Choose the audio arrangement for your input:

| Logs available | Arguments for `pd_musicus.py` |
| --- | --- |
| CY4500 Utility PD CSV: general conversation | `captures/pd.csv --mode duet` |
| CY4500 Utility PD CSV: EPR AVS sweep | `captures/pd.csv --mode avs` |
| PD CSV + ASD AVS CSV from the same test | `captures/pd.csv --asd captures/asd.csv --mode power` |
| ASD CTS-like measurement CSV | `captures/cts.csv --mode cts` |

For example, render a power-driven arrangement and then its video:

```sh
python pd_musicus.py "captures/pd.csv" --asd "captures/asd.csv" --mode power --out "output/my_session.wav"
python pd_musicus_video.py "output/my_session.wav" --score "output/my_session.score.json" --out "output/my_session.mp4" --title "My PD session"
```

Replace the capture paths with your files. The first command creates both the WAV
and matching score; the second creates the MP4. These single-line commands also
work in PowerShell. Add `--overwrite` to each command when replacing existing output.
Audio generation defaults to a 180-second limit; use `--max-seconds 600` on
`pd_musicus.py` for longer arrangements, up to 600 seconds.

Only the supported CSV formats are accepted, not arbitrary measurement exports.
CTS-only input shows measurement cases, without inferred PD messages. Actual measured
power requires the matching ASD data; PD requests alone are not power measurements.

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

- Python 3.10 or later; audio generation and the browser player need no third-party packages.
- Optional MP4 export: Pillow (`requirements-video.txt`) and FFmpeg with libx264/AAC support.
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
The local player and video exporter use this timeline; sampled instruments are not yet included.

## Development

```sh
python -m unittest -v
node player/test_timeline.cjs
```

Tests cover input validation, request/response mapping, resets, power-dependent
density, timeline tempo scaling, output protection, PCM generation, and local HTTP access/ranges.
The optional JavaScript test uses Node.js and checks timeline seeking, resets, and validation;
Node.js is not needed to run the player.

| File | Responsibility |
| --- | --- |
| `pd_musicus.py` | Unified CLI, mode selection, common timeline, output controls |
| `pd_musicus_player.py`, `player/` | Local HTTP server and synchronized browser player |
| `pd_musicus_video.py` | Optional offline MP4 renderer |
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
- Expand the synchronized protocol view and power-driven visual effects.
- Add more video layouts and visual effects.
- Expand input formats and PPS/SPR AVS decoding.

These are future directions beyond the current player.

## License

[MIT](LICENSE). The included example CSV files and synthesized WAV files are also
provided under the MIT license. No third-party instrument recordings are bundled.
