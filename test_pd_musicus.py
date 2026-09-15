import csv
import json
from pathlib import Path
import tempfile
import unittest

from pd_musicus import build_plan, main


def fixture(path):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Sno", "Ok", "SOP", "Message", "Power Role", "Data", "Start Time"])
        w.writerows([
            [1, "OK", "SOP", "EPR_REQUEST", "SNK", "0x2089 0xB046900A 0xD3C096F0", 100],
            [2, "OK", "SOP", "ACCEPT", "SRC", "0x3", 200],
            [3, "HARD_RESET", "SOP", "HARD_RESET", "SRC", "0x0", 300],
            [4, "OK", "SOP", "PS_RDY", "SRC", "0x6", 400],
            [5, "OK", "SOP", "SOFT_RESET", "SNK", "0xd", 500],
            [6, "OK", "SOP", "EPR_REQUEST", "SNK", "0x2089 0xB04F000A 0xD3C096F0", 600],
            [7, "OK", "SOP", "ACCEPT", "SRC", "0x3", 700],
            [8, "OK", "SOP", "PS_RDY", "SRC", "0x6", 800],
        ])


class MusicusTests(unittest.TestCase):
    def test_reset_retention_and_no_ready_across_reset(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pd.csv"
            fixture(p)
            plan = build_plan(p, "avs")
            self.assertEqual(sum(x["kind"] == "hard_reset" for x in plan["timeline"]), 1)
            self.assertEqual(sum(x["kind"] == "soft_reset" for x in plan["timeline"]), 1)
            self.assertNotIn("4", [x["source_row"] for x in plan["timeline"]])
            self.assertIn("8", [x["source_row"] for x in plan["timeline"]])
            self.assertEqual({n["layer"] for n in plan["notes"]} & {"hard_reset", "soft_reset"}, {"hard_reset", "soft_reset"})

    def test_tempo_scales_audio_and_timeline_together(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pd.csv"
            fixture(p)
            a, b = build_plan(p, "avs", bpm=112), build_plan(p, "avs", bpm=56)
            for x, y in zip(a["notes"], b["notes"]):
                self.assertAlmostEqual(y["at"], 2*x["at"])
            for x, y in zip(a["timeline"], b["timeline"]):
                self.assertAlmostEqual(y["at_s"], 2*x["at_s"])
            self.assertEqual(a["schema_version"], 1)

    def test_cli_plan_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as d:
            p, out = Path(d)/"pd.csv", Path(d)/"song.wav"
            fixture(p)
            args = [str(p), "--mode", "avs", "--out", str(out), "--plan-only"]
            main(args)
            self.assertFalse(out.exists())
            report = json.loads(out.with_suffix(".score.json").read_text())
            self.assertIsNone(report["audio"])
            with self.assertRaises(SystemExit) as ctx:
                main(args)
            self.assertEqual(ctx.exception.code, 1)

    def test_missing_measurements_and_excess_duration_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"pd.csv"
            fixture(p)
            with self.assertRaisesRegex(ValueError, "requires --asd"):
                build_plan(p, "power")
            with self.assertRaises(SystemExit):
                main([str(p), "--out", str(Path(d)/"a.wav"), "--plan-only", "--max-seconds", "1"])
            self.assertFalse((Path(d)/"a.score.json").exists())


if __name__ == "__main__":
    unittest.main()
