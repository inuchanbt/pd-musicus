"""CTS-like ASD measurements -> short synthesized guitar arrangement."""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from statistics import median
from pd_music import render


def load_points(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(enumerate(csv.DictReader(f), 2))
    points = []
    for case, group in itertools.groupby(rows, lambda pair: pair[1]["cts_like_case_id"]):
        group = list(group)
        samples = [r for _, r in group]
        voltage = [float(r["actual_voltage_v"]) for r in samples]
        watts = [float(r["actual_voltage_v"]) * float(r["actual_current_a"]) for r in samples]
        if not all(math.isfinite(v) and v >= 0 for v in voltage + watts):
            raise ValueError(f"Invalid measured value in {case}")
        points.append(dict(case=case, csv_lines=[line for line, _ in group],
                           phase=samples[0]["cts_like_phase"],
                           target_voltage_V=float(samples[0]["target_voltage_v"]),
                           actual_voltage_V=median(voltage), actual_power_W=median(watts),
                           statuses=sorted({r["cts_like_status"] for r in samples})))
    if not points:
        raise ValueError("No CTS points")
    return points


def compose(points):
    beat = 60 / 144
    notes = []
    def add(at, pitch, duration, gain, pan, voice, layer):
        notes.append(dict(at=at * beat, pitch=pitch, duration=duration * beat,
                          gain=gain, pan=pan, voice=voice, layer=layer))
    # A short count-in, then each measured point occupies one beat.
    for i in range(4):
        add(i, 96, .15, .06, .1, "hat", "authored")
    for i, p in enumerate(points):
        at = 4 + i
        intensity = min(1, max(0, p["actual_power_W"] / 240))
        # Requested voltage selects a low E-minor riff register.
        degrees = (0, 2, 3, 5, 7, 10, 12)
        index = min(6, max(0, round(math.log2(max(5, p["target_voltage_V"]) / 5) * 2)))
        root = 40 + degrees[index]
        p.update(audio_time_s=at * beat, root_pitch=root, intensity=intensity)
        failed = any(s.startswith("failed") for s in p["statuses"])
        if failed:
            for pitch in (root, root + 1):
                add(at, pitch, .3, .12, 0, "guitar", "failed_state_accent")
            continue
        subdivisions = 4 if intensity >= .6 else (2 if intensity >= .2 else 1)
        for step in range(subdivisions):
            onset = at + step / subdivisions
            # Double-tracked power chords dominate the mix, with palm-muted spacing.
            for side in (-1, 1):
                for interval in (0, 7):
                    add(onset + (.012 if side == 1 else 0), root + interval + side * .025,
                        .19 if subdivisions == 4 else .34,
                        .09 + .10 * intensity, side * .75, "guitar", "power_riff")
            add(onset, root - 12, .22, .13 + .05 * intensity, 0, "bass", "power_bass")
        add(at, 36, .65, .17 + .10 * intensity, 0, "kick", "authored_drums")
        if i % 2:
            add(at, 48, .45, .18, -.1, "snare", "authored_drums")
        for step in range(4 if intensity >= .6 else 2):
            add(at + step / (4 if intensity >= .6 else 2), 96, .15,
                .045, .2, "hat", "authored_drums")
        if intensity >= .85:
            for step, interval in enumerate((12, 15, 19, 22)):
                add(at + step * .25, root + interval, .25, .075, .3, "guitar", "peak_lead")
    end = 4 + len(points)
    for pitch in (40, 47, 52):
        add(end, pitch, 3, .17, 0, "guitar", "authored_ending")
    add(end, 28, 2, .15, 0, "bass", "authored_ending")
    return notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.suffix.lower() != ".wav":
        parser.error("Output must end in .wav")
    points = load_points(args.input)
    notes = compose(points)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    info = render(notes, args.out)
    report = dict(input=str(args.input.resolve()), **info, bpm=144, points=points,
                  arrangement=notes, mapping="One beat per consecutive CTS case; median measured V*A sets riff density; target voltage sets E-minor register",
                  limitations="Authored synthetic guitar/drums, not recorded instruments or a PD packet replay. Uses ASD CSV only. Failed cases retain a dissonant marker.")
    args.out.with_suffix(".score.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(dict(**info, points=len(points), failed_points=sum(any(s.startswith("failed") for s in p["statuses"]) for p in points)), indent=2))


if __name__ == "__main__":
    main()
