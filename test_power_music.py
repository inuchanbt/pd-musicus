import csv
import tempfile
import unittest
from pathlib import Path
from power_music import match_measurements, orchestrate


class PowerMusicTests(unittest.TestCase):
    def test_density_follows_measured_power(self):
        points = [dict(voltage_V=v, actual_power_W=p, accept_row="2", ready_row="3")
                  for v, p in [(21, 105), (48, 239), (21, 105)]]
        orchestrate(points)
        self.assertEqual([p["rhythm_subdivisions"] for p in points], [4, 16, 4])
        self.assertEqual(points[0]["intensity"], points[2]["intensity"])
        quiet = [dict(voltage_V=48, actual_power_W=24, accept_row="2", ready_row="3")]
        self.assertFalse(any(n["voice"] == "drive" for n in orchestrate(quiet)))

    def test_mismatched_log_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "asd.csv"
            with path.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["mode", "target_voltage_v", "target_load_current_a", "actual_voltage_v", "actual_current_a", "sweep_leg"])
                w.writerow(["avs-continuous", 24, 5, 23.9, 5, "outbound"])
            with self.assertRaisesRegex(ValueError, "mismatch"):
                match_measurements([dict(voltage_V=21, current_A=5)], path)


if __name__ == "__main__":
    unittest.main()
