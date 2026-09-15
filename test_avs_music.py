import unittest
from avs_music import extract, compose


def event(name, words=(), role="SRC", row="1"):
    return dict(row={"Ok": "OK", "SOP": "SOP", "Message": name,
                     "Power Role": role, "Sno": row}, words=words, time_us=0)


class AVSMusicTests(unittest.TestCase):
    def test_known_requests_and_acknowledgement(self):
        points = extract([
            event("EPR_REQUEST", [0xB046900A, 0xD3C096F0], "SNK", "1"),
            event("ACCEPT", row="2"), event("PS_RDY", row="3"),
            event("EPR_REQUEST", [0xB04F000A, 0xD3C096F0], "SNK", "4"),
            event("REJECT", row="5"), event("PS_RDY", row="6")])
        self.assertEqual([t["voltage_V"] for t in points], [21, 48])
        self.assertEqual(points[0]["current_A"], .5)
        self.assertEqual(points[0]["ready_row"], "3")
        self.assertIsNone(points[1]["ready_row"])
        notes = compose(points)
        self.assertLess(points[0]["pitch"], points[1]["pitch"])
        self.assertEqual(sum(n["layer"] == "ready" for n in notes), 3)

    def test_fixed_epr_request_is_not_avs(self):
        with self.assertRaisesRegex(ValueError, "No EPR AVS"):
            extract([event("EPR_REQUEST", [0x1044B12C, 0x0881912C], "SNK")])


if __name__ == "__main__":
    unittest.main()
