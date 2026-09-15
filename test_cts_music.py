import unittest
from cts_music import compose


class CTSMusicTests(unittest.TestCase):
    def test_power_density_and_failed_marker(self):
        points = [dict(actual_power_W=w, target_voltage_V=48, statuses=[s])
                  for w, s in [(24, "observed-pass"), (239, "observed-pass"), (0, "failed-end-state")]]
        notes = compose(points)
        beat = 60 / 144
        count = lambda i: sum(n["layer"] == "power_riff" and (4+i)*beat <= n["at"] < (5+i)*beat for n in notes)
        self.assertGreater(count(1), count(0))
        self.assertEqual(count(2), 0)
        self.assertEqual(sum(n["layer"] == "failed_state_accent" for n in notes), 2)


if __name__ == "__main__":
    unittest.main()
