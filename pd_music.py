"""CY4500 Utility CSV -> deterministic stereo conversation music (stdlib only)."""
import argparse
from array import array
import csv
import json
import math
from pathlib import Path
import sys
import wave

RATE = 44100
SCALE = (0, 2, 4, 7, 9)


def voltage_note(voltage):
    step = max(0, min(14, round(5 * math.log2(max(voltage, 5) / 5))))
    return 60 + 12 * (step // 5) + SCALE[step % 5]


def read_events(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"Sno", "Ok", "SOP", "Message", "Power Role", "Data", "Start Time"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Expected CY4500 Utility-format PD CSV; scope/legacy CSV is unsupported.")
        events = []
        previous = None
        epoch = 0
        for line, row in enumerate(reader, 2):
            try:
                raw_time = int(row["Start Time"])
                if previous is not None and raw_time < previous:
                    if previous - raw_time > 2**31:
                        epoch += 2**32
                    else:
                        raise ValueError("timestamps are out of order")
                previous = raw_time
                tokens = [int(x, 16) for x in row["Data"].split()]
                events.append(dict(row=row, time_us=raw_time + epoch, words=tokens[1:]))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"CSV line {line}: {exc}") from exc
    if not events:
        raise ValueError("CSV contains no events")
    return events


def arrange(events, bpm=100):
    beat = 60 / bpm
    cursor = 0.5
    last_time = events[0]["time_us"]
    pdos = []
    selected = 60
    notes, score = [], []
    for event in events:
        row, words = event["row"], event["words"]
        name = row["Message"].upper().replace("_", "")
        status = row["Ok"].upper()
        gap = (event["time_us"] - last_time) / 1e6
        # Preserve order, expand fast replies, compress silence; this is musical time.
        cursor += min(2 * beat, max(beat / 8, gap * 3))
        last_time = event["time_us"]
        cable = row["SOP"] != "SOP"
        voice = "bell" if cable else ("pluck" if row["Power Role"] == "SRC" else "soft")
        pan = 0 if cable else (-0.65 if row["Power Role"] == "SRC" else 0.65)
        motif, length, gain = [67], beat * 0.65, 0.15
        explanation = "message motif (not payload decoding)"
        if status in ("VBUS_UP", "VBUS_DN"):
            motif = [48, 55, 60] if status == "VBUS_UP" else [60, 55, 48]
            voice, pan = "bell", 0
            pdos, selected = [], 60
            explanation = status
        elif status != "OK":
            motif, voice = [48, 49], "bell"
            explanation = "capture error/status"
        elif name == "SOURCECAPABILITIES" and not cable:
            pdos = words
            motif = [voltage_note(((p >> 10) & 1023) * 0.05)
                     if p >> 30 == 0 else 84 for p in pdos] or [60]
            explanation = "fixed PDO voltage -> pentatonic pitch; non-fixed PDO -> high accent"
        elif name in ("REQUEST", "EPRREQUEST"):
            pos = (words[0] >> 28) & 15 if words else 0
            pdo = pdos[pos - 1] if 0 < pos <= len(pdos) else None
            if pdo is not None and pdo >> 30 == 0:
                selected = voltage_note(((pdo >> 10) & 1023) * 0.05)
                motif = [selected + 12, selected]
                explanation = f"requested fixed PDO {pos}"
            else:
                motif = [72, 76]
                explanation = f"request PDO {pos}; voltage unresolved, generic motif"
        elif name == "GOODCRC":
            motif, length, gain, voice = [96], 0.045, 0.055, "click"
            explanation = "acknowledgement click"
        elif name == "ACCEPT":
            motif = [selected, selected + 4, selected + 7]
            explanation = "acceptance chord"
        elif name == "PSRDY":
            motif, length = [selected - 12, selected, selected + 7], beat * 2
            explanation = "ready resolution chord; pitch follows last resolved request"
        elif name == "EPRMODE":
            motif, voice = [72, 79, 84], "bell"
            explanation = "EPR mode message motif; action not decoded"
        elif name == "EPRSOURCECAPABILITIES":
            motif, voice = [79, 84, 88, 91], "bell"
            explanation = "EPR chunk motif; extended PDOs are not reassembled in this prototype"
        elif "RESET" in name or name in ("REJECT", "WAIT", "NOTSUPPORTED"):
            motif, voice = [48, 49, 55], "bell"
            explanation = "reset/refusal motif"
            if "RESET" in name:
                pdos, selected = [], 60
        chord = name in ("ACCEPT", "PSRDY")
        starts = []
        for i, pitch in enumerate(motif):
            at = cursor + (0 if chord else i * beat / 4)
            notes.append(dict(at=at, pitch=pitch, duration=length, gain=gain / math.sqrt(len(motif))
                              if chord else gain, pan=pan, voice=voice))
            starts.append(round(at, 6))
        score.append(dict(row=row["Sno"], source_time_us=event["time_us"],
                          audio_time_s=round(cursor, 6), message=row["Message"],
                          status=status, role=row["Power Role"], sop=row["SOP"],
                          pitches=motif, note_times_s=starts, mapping=explanation))
        if name != "GOODCRC":
            cursor += max(beat / 2, (len(motif) - 1) * beat / 4)
    return notes, score


def arrange_song(events, bpm=100):
    """Place protocol motifs on a sixteenth-note grid and add authored backing."""
    _, score = arrange(events, bpm)
    beat = 60 / bpm
    notes = []
    tick = 16  # One bar of introduction.
    roots = [(0, 60)]

    def add(at_beat, pitch, duration, gain, pan, voice, layer):
        notes.append(dict(at=at_beat * beat, pitch=pitch, duration=duration * beat,
                          gain=gain, pan=pan, voice=voice, layer=layer))

    for item in score:
        name = item["message"].upper().replace("_", "")
        click = name == "GOODCRC" and item["status"] == "OK"
        if not click:
            tick = math.ceil(tick / 2) * 2
        start = tick / 4
        motif = item["pitches"]
        chord = name in ("ACCEPT", "PSRDY")
        voice = "piano" if item["role"] == "SRC" else "marimba"
        pan = -.5 if item["role"] == "SRC" else .5
        if item["sop"] != "SOP" or item["status"].startswith("VBUS"):
            voice, pan = "marimba", 0
        starts = []
        for i, pitch in enumerate(motif):
            at = start + (0 if chord or click else i * .5)
            add(at, pitch, .10 if click else (2.5 if chord else 1.2),
                .032 if click else (.19 / math.sqrt(len(motif)) if chord else .19),
                pan, "click" if click else voice, "protocol")
            starts.append(round(at * beat, 6))
        item.update(audio_time_s=round(start * beat, 6), note_times_s=starts,
                    beat=start, instrument="click" if click else voice)
        if name == "PSRDY" and item["status"] == "OK":
            roots.append((start, motif[1]))
        tick += 1 if click else max(6, len(motif) * 2 if not chord else 8)

    ending = math.ceil(tick / 16) * 4
    # Authored C / Am / F / G colors, transposed by the latest mapped ready pitch.
    harmony = ((0, (0, 4, 7, 14)), (-3, (0, 3, 7, 10)),
               (-7, (0, 4, 7, 11)), (-5, (0, 7, 9, 14)))
    for bar in range(int(ending / 4)):
        at = bar * 4
        root = next(pitch for when, pitch in reversed(roots) if when <= at)
        offset, intervals = harmony[bar % 4]
        base = 48 + (root - 60) + offset
        for j, interval in enumerate(intervals):
            add(at + j * .025, base + interval, 3.9, .035, -.2 + j * .13, "pad", "authored")
        for step, interval in ((0, 0), (1.5, 7), (2, 12), (3, 7)):
            add(at + step, base - 12 + interval, .85, .105, -.08, "bass", "authored")
        for step in range(8):
            add(at + step * .5, base + 12 + intervals[step % 4], .55,
                .025, .25, "piano", "authored")
    root = roots[-1][1]
    for interval in (-24, -12, 0, 4, 7, 14):
        add(ending, root + interval, 4, .075, 0, "piano", "authored")
    return notes, score


def render(notes, path, rate=RATE):
    duration = max(n["at"] + n["duration"] for n in notes) + 1.0
    if duration > 600:
        raise ValueError("Arrangement exceeds 10 minutes; use a shorter capture excerpt")
    frames = math.ceil(duration * rate)
    left, right = array("f", [0]) * frames, array("f", [0]) * frames
    for n in notes:
        freq = 440 * 2 ** ((n["pitch"] - 69) / 12)
        start = round(n["at"] * rate)
        count = int(n["duration"] * rate)
        lg = math.cos((n["pan"] + 1) * math.pi / 4) * n["gain"]
        rg = math.sin((n["pan"] + 1) * math.pi / 4) * n["gain"]
        cabinet = 0.0
        for i in range(count):
            t = i / rate
            phase = 2 * math.pi * freq * t
            env = min(1, t / .008) * min(1, (count - i) / (rate * .04))
            if n["voice"] == "guitar":
                # Rich string partials -> saturated amplifier -> simple cabinet low-pass.
                string = (math.sin(phase) + .55 * math.sin(phase * 2.001)
                          + .33 * math.sin(phase * 3.003) + .2 * math.sin(phase * 4.006))
                amp = math.tanh(5 * string * math.exp(-2.2 * t))
                cabinet += .32 * (amp - cabinet)
                value = cabinet * math.exp(-1.6 * t)
            elif n["voice"] == "drive":
                value = math.tanh(2.8 * (math.sin(phase) + .35 * math.sin(phase * 2))) * math.exp(-3.5 * t)
            elif n["voice"] == "kick":
                value = math.sin(2 * math.pi * (48 * t + 7 * (1 - math.exp(-35 * t)))) * math.exp(-12 * t)
            elif n["voice"] in ("snare", "hat"):
                noise = 2 * ((math.sin((i + 1) * 12.9898) * 43758.5453) % 1) - 1
                value = (noise * .7 + .3 * math.sin(2 * math.pi * 180 * t)) * math.exp(-24 * t) if n["voice"] == "snare" else noise * math.exp(-65 * t)
            elif n["voice"] == "piano":
                value = (math.sin(phase) * math.exp(-1.9 * t)
                         + .42 * math.sin(phase * 2.001) * math.exp(-3.5 * t)
                         + .19 * math.sin(phase * 3.004) * math.exp(-5 * t)
                         + .09 * math.sin(phase * 4.009) * math.exp(-8 * t))
            elif n["voice"] == "marimba":
                value = (math.sin(phase) * math.exp(-5 * t)
                         + .45 * math.sin(phase * 4) * math.exp(-18 * t)
                         + .14 * math.sin(phase * 9.2) * math.exp(-30 * t))
            elif n["voice"] == "bass":
                value = (math.sin(phase) + .24 * math.sin(phase * 2)) * math.exp(-3 * t)
            elif n["voice"] == "pad":
                env *= min(1, t / .16) * min(1, (count - i) / (rate * .3))
                value = .6 * math.sin(phase) + .2 * math.sin(phase * 1.002) + .12 * math.sin(phase * 2)
            elif n["voice"] == "pluck":
                value = (math.sin(phase) + .32 * math.sin(phase * 2) + .12 * math.sin(phase * 3)) * math.exp(-4 * t / n["duration"])
            elif n["voice"] == "bell":
                value = (math.sin(phase) + .3 * math.sin(phase * 2.76)) * math.exp(-3 * t / n["duration"])
            elif n["voice"] == "click":
                value = math.sin(phase) * math.exp(-100 * t)
            else:
                value = (math.sin(phase) + .15 * math.sin(phase * 2)) * math.exp(-2 * t / n["duration"])
            left[start + i] += value * env * lg
            right[start + i] += value * env * rg
    # A single quiet stereo echo gives the otherwise dry synthesized voices some space.
    delay = int(.19 * rate)
    for i in range(frames - 1, delay - 1, -1):
        left[i] += .18 * right[i - delay]
        right[i] += .18 * left[i - delay]
    peak = max(max(abs(v) for v in left), max(abs(v) for v in right))
    scale = .82 * 32767 / max(peak, 1e-9)
    pcm = array("h")
    for l, r in zip(left, right):
        pcm.extend((round(l * scale), round(r * scale)))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as out:
        out.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        out.writeframes(pcm.tobytes())
    return dict(duration_s=frames / rate, sample_rate=rate, channels=2, peak_normalized=.82)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("output/pd_conversation.wav"))
    parser.add_argument("--bpm", type=float, default=100)
    parser.add_argument("--style", choices=("conversation", "song"), default="conversation")
    args = parser.parse_args()
    if not 30 <= args.bpm <= 240:
        parser.error("--bpm must be between 30 and 240")
    if args.out.suffix.lower() != ".wav" or args.out.resolve() == args.input.resolve():
        parser.error("--out must be a WAV path different from input")
    try:
        events = read_events(args.input)
        arranger = arrange_song if args.style == "song" else arrange
        notes, score = arranger(events, args.bpm)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        info = render(notes, args.out)
        report = dict(input=str(args.input.resolve()), bpm=args.bpm, events=len(events),
                      notes=len(notes), style=args.style,
                      timing="sixteenth-note grid with authored backing" if args.style == "song"
                      else "musical: expanded replies and compressed silences",
                      **info, score=score, arrangement=notes)
        args.out.with_suffix(".score.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k not in ("score", "arrangement")}, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
