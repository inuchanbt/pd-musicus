"""Short EPR AVS sweep composition from CY4500 Utility CSV.

EPR_REQUEST includes the selected PDO, so AVS units can be identified without
guessing from the object position or reassembling extended capabilities.
"""
import argparse
import json
from pathlib import Path
from pd_music import read_events, render, SCALE


def extract(events):
    transactions = []
    pending = None
    for e in events:
        r = e["row"]
        reset_label = "".join(c for c in " ".join(r.get(k, "") for k in ("Message", "SOP", "Ok")).upper() if c.isalnum())
        if "HARDRESET" in reset_label or "SOFTRESET" in reset_label:
            pending = None
        if r["Ok"] != "OK" or r["SOP"] != "SOP":
            continue
        name = r["Message"].replace("_", "").upper()
        if name in ("REQUEST", "EPRREQUEST", "SOFTRESET", "HARDRESET"):
            pending = None
        if name == "EPRREQUEST" and r["Power Role"] == "SNK" and len(e["words"]) == 2:
            rdo, pdo = e["words"]
            if pdo >> 28 != 0xD:  # augmented PDO, subtype 1: EPR AVS
                continue
            pending = dict(voltage_V=((rdo >> 9) & 0xfff) * .025,
                           current_A=(rdo & 0x7f) * .05,
                           request_row=r["Sno"], time_us=e["time_us"],
                           accept_row=None, ready_row=None)
            transactions.append(pending)
        elif pending is not None and r["Power Role"] == "SRC":
            if name == "ACCEPT":
                pending["accept_row"] = r["Sno"]
            elif name == "PSRDY":
                if pending["accept_row"] is not None:
                    pending["ready_row"] = r["Sno"]
                pending = None
            elif name in ("REJECT", "WAIT", "NOTSUPPORTED"):
                pending = None
    if not transactions:
        raise ValueError("No EPR AVS requests with echoed AVS PDO found")
    return transactions


def compose(transactions, bpm=112):
    beat = 60 / bpm
    voltages = sorted({t["voltage_V"] for t in transactions})
    pitches = {v: 60 + 12 * (i // 5) + SCALE[i % 5] for i, v in enumerate(voltages)}
    notes = []

    def add(at, pitch, length, gain, pan, voice, layer):
        notes.append(dict(at=at * beat, pitch=pitch, duration=length * beat,
                          gain=gain, pan=pan, voice=voice, layer=layer))

    for i, pitch in enumerate((48, 55, 60, 64)):
        add(i * .5, pitch, 1.5, .09, -.25, "piano", "authored")
    for i, t in enumerate(transactions):
        at = 2 + i * 4
        pitch = pitches[t["voltage_V"]]
        t.update(audio_time_s=at * beat, pitch=pitch)
        # Sink asks; source answers only if the corresponding message exists.
        add(at, pitch, 1.2, .21, .5, "marimba", "request")
        add(at + .5, pitch + 12, .7, .085, .5, "marimba", "request_ornament")
        if t["accept_row"] is not None:
            add(at + 1, pitch, 1.8, .16, -.5, "piano", "accept")
            add(at + 1.5, pitch + 7, 1, .07, -.5, "piano", "accept_ornament")
        if t["ready_row"] is not None:
            for p in (pitch - 12, pitch, pitch + 7):
                add(at + 2, p, 1.9, .08, -.35, "piano", "ready")
        # Open fifths follow the requested pitch; backing is an authored layer.
        add(at, pitch - 24, 1.7, .11, 0, "bass", "authored")
        add(at + 2.5, pitch - 17, 1.2, .07, 0, "bass", "authored")
        for p in (pitch - 12, pitch - 5):
            add(at, p, 3.9, .035, 0, "pad", "authored")
    end = 2 + len(transactions) * 4
    for p in (36, 48, 60, 64, 67):
        add(end, p, 4, .075, 0, "piano", "authored")
    return notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("output/delta_avs_duet.wav"))
    args = parser.parse_args()
    if args.out.suffix.lower() != ".wav":
        parser.error("--out must end in .wav")
    events = read_events(args.input)
    transactions = extract(events)
    notes = compose(transactions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    info = render(notes, args.out)
    report = dict(input=str(args.input.resolve()), bpm=112, source_events=len(events),
                  transactions=transactions, arrangement=notes, **info,
                  mapping="Sorted unique requested voltages -> consecutive C pentatonic notes; relative to this capture",
                  timing="Each request occupies four beats; response latency is not reproduced",
                  omitted="Setup, GoodCRC, KeepAlive and unrelated traffic")
    args.out.with_suffix(".score.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(dict(**info, requests=len(transactions),
                         voltages=[t["voltage_V"] for t in transactions],
                         accepted=sum(t["accept_row"] is not None for t in transactions),
                         ready=sum(t["ready_row"] is not None for t in transactions)), indent=2))


if __name__ == "__main__":
    main()
