import csv
import tempfile
import unittest
import wave
from pathlib import Path
from array import array

from pd_music import arrange, arrange_song, read_events, render


class MusicTests(unittest.TestCase):
    def write_capture(self, folder, rows):
        path = Path(folder) / "capture.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Sno", "Ok", "SOP", "Message", "Power Role", "Data", "Start Time"])
            writer.writerows(rows)
        return path

    def test_request_answers_selected_voltage_and_wav_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.write_capture(d, [
                [1, "OK", "SOP", "SOURCE_CAPABILITIES", "SRC", "0x2001 0x1912c 0x2d12c", 100],
                [2, "OK", "SOP", "REQUEST", "SNK", "0x1002 0x20000000", 200],
                [3, "OK", "SOP", "PS_RDY", "SRC", "0x6", 300]])
            notes, score = arrange(read_events(path))
            self.assertEqual(score[1]["pitches"][-1], score[0]["pitches"][1])
            self.assertEqual(score[2]["pitches"][1], score[1]["pitches"][-1])
            self.assertLess(score[0]["audio_time_s"], score[1]["audio_time_s"])
            self.assertTrue(any(n["pan"] < 0 for n in notes))
            self.assertTrue(any(n["pan"] > 0 for n in notes))
            out = Path(d) / "test.wav"
            render(notes, out, rate=12000)
            with wave.open(str(out)) as f:
                self.assertEqual((f.getnchannels(), f.getsampwidth(), f.getframerate()), (2, 2, 12000))
                samples = array("h", f.readframes(f.getnframes()))
                self.assertGreater(max(samples), 1000)
                self.assertLess(max(abs(s) for s in samples), 32767)

    def test_empty_capture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "no events"):
                read_events(self.write_capture(d, []))

    def test_song_preserves_events_and_quantizes_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.write_capture(d, [
                [1, "OK", "SOP", "SOURCE_CAPABILITIES", "SRC", "0x1001 0x1912c", 100],
                [2, "OK", "SOP", "GOODCRC", "SNK", "0x1", 150],
                [3, "OK", "SOP", "REQUEST", "SNK", "0x1002 0x10000000", 200],
                [4, "OK", "SOP", "PS_RDY", "SRC", "0x6", 300]])
            notes, score = arrange_song(read_events(path), 104)
            self.assertEqual([s["row"] for s in score], ["1", "2", "3", "4"])
            self.assertTrue(all(a["beat"] < b["beat"] for a, b in zip(score, score[1:])))
            self.assertTrue(all(s["beat"] * 4 == round(s["beat"] * 4) for s in score))
            self.assertEqual(score[0]["pitches"][0], score[2]["pitches"][-1])
            self.assertEqual({n["voice"] for n in notes}, {"piano", "marimba", "click", "pad", "bass"})
            self.assertTrue(any(n["layer"] == "authored" for n in notes))

    def test_wrap_and_bad_order(self):
        with tempfile.TemporaryDirectory() as d:
            def rows(a, b):
                return [[i, "OK", "SOP", "GOODCRC", "SRC", "0x1", t]
                        for i, t in enumerate((a, b), 1)]
            events = read_events(self.write_capture(d, rows(2**32 - 10, 20)))
            self.assertEqual(events[1]["time_us"] - events[0]["time_us"], 30)
            with self.assertRaisesRegex(ValueError, "out of order"):
                read_events(self.write_capture(d, rows(100, 90)))


if __name__ == "__main__":
    unittest.main()
