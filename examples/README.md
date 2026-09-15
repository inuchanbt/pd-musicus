# Example: one voltage sweep, two musical moods

These examples use measured EPR AVS sweeps from 21 V to 48 V and back to 21 V,
in 3 V steps (19 points), with 0.5 A and 5 A electronic loads.
The source was a Delta ADP-240LB B / Lenovo ADL240WY3AA-D.

| Load | Included audio | Input files |
| --- | --- | --- |
| 0.5 A | [avs_0p5a.wav](avs_0p5a.wav) | [PD](avs_0p5a_pd.csv), [ASD](avs_0p5a_asd.csv) |
| 5 A | [avs_5a.wav](avs_5a.wav) | [PD](avs_5a_pd.csv), [ASD](avs_5a_asd.csv) |

Both WAVs are approximately 45 seconds and use the v0.1.0 `power` arrangement at
112 BPM. Low power keeps the gentle base arrangement; higher measured power adds
guitar, percussion, and denser rhythms. The maximum recorded steady-point power
in the 5 A example is 238.905 W.

## Reproduce

From the repository root, with Python 3.10 or newer:

```sh
python pd_musicus.py examples/avs_0p5a_pd.csv --asd examples/avs_0p5a_asd.csv --out output/example_0p5a.wav
python pd_musicus.py examples/avs_5a_pd.csv --asd examples/avs_5a_asd.csv --out output/example_5a.wav
```

No equipment or third-party Python packages are required. The commands also produce
timeline JSON files. Those generated files contain local input paths and are not bundled here.
Minor floating-point differences across Python/platform implementations may affect PCM bytes.

## What is included

- PD CSV: the Utility-format packet/event table from each session.
- ASD CSV: only the 19 steady `avs-continuous` rows and the six columns needed by
  the music renderer. Local command lines, paths, device metadata, and initial
  load-ramp measurements have been omitted.
- WAV: synthesized audio produced from those files, not a microphone or instrument recording.

The sample CSVs are curated music inputs, not complete measurement reports or a
claim of USB-PD compliance. The hardware is identified for provenance, not endorsement.
Files in this directory are provided under the repository's [MIT license](../LICENSE).
