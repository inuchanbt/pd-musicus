"""PD musicus: saved USB-PD / ASD logs to music and a visual-ready timeline."""
import argparse
from bisect import bisect_left
import csv
import hashlib
import json
import math
from pathlib import Path

import avs_music
import cts_music
import pd_music
import power_music

VERSION = "0.2.0"


def reset_kind(event):
    row = event["row"]
    label = "".join(c for c in " ".join(row.get(k, "") for k in ("Message", "SOP", "Ok")).upper() if c.isalnum())
    if "HARDRESET" in label:
        return "hard_reset"
    if "SOFTRESET" in label:
        return "soft_reset"
    return None


def resolve_mode(path, mode, asd):
    if mode != "auto":
        return mode
    with path.open(encoding="utf-8-sig", newline="") as f:
        fields = next(csv.reader(f), [])
    if "cts_like_case_id" in fields:
        return "cts"
    return "power" if asd else "duet"


def protocol_item(event, at, kind=None, timing="arranged"):
    row = event["row"]
    return dict(kind=kind or reset_kind(event) or "protocol", at_s=at,
                source_row=row["Sno"], source_time_us=event["time_us"],
                label=row["Message"], status=row["Ok"], role=row["Power Role"],
                sop=row["SOP"], timing=timing)


def reset_notes(kind, at):
    # Different punctuation: soft reset is a rewind, hard reset a low crash.
    pitches = (76, 72, 67) if kind == "soft_reset" else (40, 41, 28)
    return [dict(at=at + i * .075, pitch=pitch, duration=.3 if kind == "soft_reset" else .6,
                 gain=.12, pan=0, voice="bell" if kind == "soft_reset" else "guitar",
                 layer=kind) for i, pitch in enumerate(pitches)]


def build_plan(path, mode="auto", asd=None, bpm=None):
    path = Path(path)
    asd = Path(asd) if asd else None
    mode = resolve_mode(path, mode, asd)
    if asd and mode != "power":
        raise ValueError("--asd is only used by power mode (or auto with a PD input)")
    if mode == "power" and not asd:
        raise ValueError("power mode requires --asd from the same sweep session")
    default_bpm = {"conversation": 100, "duet": 104, "avs": 112, "power": 112, "cts": 144}[mode]
    target_bpm = bpm if bpm is not None else default_bpm
    if not math.isfinite(target_bpm) or not 30 <= target_bpm <= 240:
        raise ValueError("BPM must be between 30 and 240")
    timeline, notices = [], []
    if mode == "cts":
        points = cts_music.load_points(path)
        notes = cts_music.compose(points)
        for p in points:
            timeline.append(dict(kind="measurement", at_s=p["audio_time_s"], label=p["case"],
                                 source_lines=p["csv_lines"], data=p, timing="one_beat_per_case"))
        notices.append("ASD measurements only; protocol resets cannot be inferred from this input.")
    else:
        events = pd_music.read_events(path)
        by_row = {e["row"]["Sno"]: e for e in events}
        if len(by_row) != len(events):
            raise ValueError("PD CSV Sno values must be unique for timeline references")
        if mode in ("conversation", "duet"):
            arranger = pd_music.arrange if mode == "conversation" else pd_music.arrange_song
            notes, score = arranger(events, default_bpm)
            for e, s in zip(events, score):
                timeline.append(protocol_item(e, s["audio_time_s"]))
                kind = reset_kind(e)
                if kind:
                    # Replace the old generic motif with explicit reset punctuation.
                    starts = s["note_times_s"]
                    notes = [n for n in notes if not any(abs(n["at"] - t) < 1e-5 for t in starts)]
                    notes.extend(reset_notes(kind, s["audio_time_s"]))
            notices.append("Generic protocol motifs; extended PDO reassembly and PPS/SPR AVS voltage decoding are not implemented.")
        else:
            points = avs_music.extract(events)
            if mode == "power":
                power_music.match_measurements(points, asd)
                notes = power_music.orchestrate(points)
                # Make increasing power audible through the guitar as well as drums.
                for n in notes:
                    if n["voice"] == "drive":
                        n.update(voice="guitar", gain=n["gain"] * 2.6)
                notices.append("ASD/PD matching uses ordered target voltage/current, not synchronized clocks; use the same session.")
            else:
                notes = avs_music.compose(points)
            for p in points:
                at = p["audio_time_s"]
                for key, offset in (("request_row", 0), ("accept_row", 1), ("ready_row", 2)):
                    if p[key] is not None:
                        item = protocol_item(by_row[p[key]], at + offset * 60 / default_bpm)
                        if key == "request_row":
                            item["data"] = p
                        timeline.append(item)
            # Resets are not silently discarded by the sweep-focused arrangement.
            anchors = sorted((x["source_time_us"], x["at_s"]) for x in timeline)
            times = [a[0] for a in anchors]
            for e in events:
                kind = reset_kind(e)
                if not kind:
                    continue
                t = e["time_us"]
                idx = bisect_left(times, t)
                if idx == 0:
                    at = max(0, anchors[0][1] - .5)
                elif idx == len(anchors):
                    at = anchors[-1][1] + .5
                else:
                    t0, a0 = anchors[idx - 1]
                    t1, a1 = anchors[idx]
                    at = a0 + (a1 - a0) * (t - t0) / max(1, t1 - t0)
                timeline.append(protocol_item(e, at, kind, "interpolated_between_arranged_events"))
                notes.extend(reset_notes(kind, at))
            notices.append("Sweep focus omits setup, GoodCRC and KeepAlive; resets are retained with approximate arranged timing.")
    ratio = default_bpm / target_bpm
    for n in notes:
        n["at"] *= ratio
        n["duration"] *= ratio
    for item in timeline:
        item["at_s"] *= ratio
        if "data" in item:
            item["data"]["audio_time_s"] *= ratio
    timeline.sort(key=lambda x: x["at_s"])
    notes.sort(key=lambda x: x["at"])
    for i, item in enumerate(timeline):
        item["id"] = f"event-{i+1:05d}"
    for i, n in enumerate(notes):
        n["id"] = f"note-{i+1:06d}"
    duration = max(n["at"] + n["duration"] for n in notes) + 1
    return dict(schema_version=1, app_version=VERSION, mode=mode, bpm=target_bpm,
                inputs=[dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                        for p in (path, asd) if p],
                duration_s=duration, sample_rate=44100, channels=2,
                timebase="arranged_audio_seconds", timeline=timeline, notes=notes,
                notices=notices + ["Synthetic instruments and authored backing; music is not a compliance verdict."])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"PD musicus {VERSION}")
    parser.add_argument("input", type=Path, nargs="?", help="CY4500 Utility PD CSV or ASD CTS-like CSV")
    parser.add_argument("--player", action="store_true", help="Open the local synchronized audio/protocol player")
    parser.add_argument("--port", type=int, default=8765, help="Local player port (default 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Start the player without opening a browser")
    parser.add_argument("--mode", choices=("auto", "conversation", "duet", "avs", "power", "cts"), default="auto")
    parser.add_argument("--asd", type=Path, help="Matching ASD AVS sweep CSV for power mode")
    parser.add_argument("--bpm", type=float)
    parser.add_argument("--out", type=Path, help="WAV path; defaults to output/<input>_musicus.wav")
    parser.add_argument("--plan-only", action="store_true", help="Write the timeline/score without rendering audio")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=180, help="Reject longer arrangements; maximum 600")
    args = parser.parse_args(argv)
    if args.player:
        if args.input or args.asd or args.out or args.plan_only or args.mode != "auto" or args.bpm is not None:
            parser.error("--player cannot be combined with arrangement arguments")
        if not 1 <= args.port <= 65535:
            parser.error("--port must be between 1 and 65535")
        from pd_musicus_player import run
        try:
            run(args.port, not args.no_browser)
        except OSError as exc:
            parser.exit(1, f"Could not start player: {exc}\n")
        return
    if args.input is None:
        parser.error("Provide an input CSV or use --player")
    out = args.out or Path("output") / (args.input.stem + "_musicus.wav")
    score_path = out.with_suffix(".score.json")
    try:
        if out.suffix.lower() != ".wav":
            raise ValueError("--out must end in .wav")
        if not math.isfinite(args.max_seconds) or not 0 < args.max_seconds <= 600:
            raise ValueError("--max-seconds must be greater than 0 and at most 600")
        for dest in (out, score_path):
            if dest.resolve() in [p.resolve() for p in (args.input, args.asd) if p]:
                raise ValueError("Output must not replace an input")
            if dest.exists() and not args.overwrite:
                raise ValueError(f"Output exists: {dest}; choose another name or use --overwrite")
        plan = build_plan(args.input, args.mode, args.asd, args.bpm)
        if plan["duration_s"] > args.max_seconds:
            raise ValueError(f"Arrangement is {plan['duration_s']:.1f}s, above --max-seconds {args.max_seconds:g}; use a shorter capture or increase the limit")
        out.parent.mkdir(parents=True, exist_ok=True)
        if not args.plan_only:
            plan.update(pd_music.render(plan["notes"], out))
        plan["audio"] = None if args.plan_only else out.name
        score_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(f"PD musicus {VERSION} | {plan['mode']} | {plan['duration_s']:.1f}s | {len(plan['timeline'])} events")
        print(f"Score: {score_path.resolve()}")
        if not args.plan_only:
            print(f"WAV: {out.resolve()}")
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
