"""Match ordered AVS sweep points to ASD measurements and orchestrate by watts."""
import argparse
import csv
import json
import math
from pathlib import Path
from avs_music import extract, compose
from pd_music import read_events, render


def match_measurements(transactions, path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        points = [(line, row) for line, row in enumerate(csv.DictReader(f), 2)
                  if row.get("mode") == "avs-continuous"]
    if len(points) != len(transactions):
        raise ValueError("PD requests and ASD steady sweep points have different counts")
    for t, (line, row) in zip(transactions, points):
        target = float(row["target_voltage_v"])
        current = float(row["target_load_current_a"])
        voltage, amps = float(row["actual_voltage_v"]), float(row["actual_current_a"])
        if not all(math.isfinite(x) for x in (target, current, voltage, amps)) or min(voltage, amps) < 0:
            raise ValueError(f"Invalid ASD measurements on line {line}")
        if abs(target - t["voltage_V"]) > .026 or abs(current - t["current_A"]) > .051:
            raise ValueError(f"PD/ASD point mismatch on ASD line {line}")
        t.update(asd_line=line, actual_voltage_V=voltage, actual_current_A=amps,
                 actual_power_W=voltage * amps, sweep_leg=row["sweep_leg"])


def orchestrate(transactions):
    notes = compose(transactions)
    beat = 60 / 112
    def add(at, pitch, duration, gain, pan, voice):
        notes.append(dict(at=at * beat, pitch=pitch, duration=duration * beat,
                          gain=gain, pan=pan, voice=voice, layer="measured_power_authored"))
    for i, t in enumerate(transactions):
        intensity = max(0, min(1, (t["actual_power_W"] - 30) / 210))
        t["intensity"] = intensity
        if intensity == 0:
            continue
        at, pitch = 2 + i * 4, t["pitch"]
        count = 16 if intensity >= .8 else (8 if intensity >= .5 else 4)
        t["rhythm_subdivisions"] = count
        for step in range(count):
            when = at + step * 4 / count
            add(when, pitch - 12 + (7 if step % 4 == 3 else 0), .32,
                .055 * intensity, -.3 if step % 2 else .3, "drive")
            add(when, 96, .14, .038 * intensity, .25, "hat")
        for step in ((0, 1.5, 2, 2.75, 3.5) if intensity >= .8 else (0, 2)):
            add(at + step, 36, .6, .19 * intensity, 0, "kick")
        for step in (1, 3):
            add(at + step, 48, .4, .11 * intensity, -.12, "snare")
        if intensity >= .65:
            for step in range(8):
                add(at + step * .5, pitch + (0, 7, 12, 7)[step % 4], .4,
                    .045 * intensity, .5, "marimba")
    return notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pd_csv", type=Path)
    parser.add_argument("asd_csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.suffix.lower() != ".wav":
        parser.error("Output must be a WAV path")
    transactions = extract(read_events(args.pd_csv))
    match_measurements(transactions, args.asd_csv)
    notes = orchestrate(transactions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    info = render(notes, args.out)
    report = dict(pd_csv=str(args.pd_csv.resolve()), asd_csv=str(args.asd_csv.resolve()),
                  matching="Ordered steady sweep points, verified target voltage/current; no clock synchronization",
                  intensity_mapping="clamp((ASD measured V*A - 30 W)/210 W, 0, 1)",
                  timing="4 beats per request at 112 BPM; setup/load ramp omitted",
                  transactions=transactions, arrangement=notes, **info)
    args.out.with_suffix(".score.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(dict(**info, points=len(transactions),
                         peak_measured_W=max(t["actual_power_W"] for t in transactions)), indent=2))


if __name__ == "__main__":
    main()
