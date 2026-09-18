import json
from pathlib import Path
import tempfile
import unittest
import wave

from pd_musicus_video import Timeline, export_video, load_score


class VideoTests(unittest.TestCase):
    def test_carry_reset_and_backward_seek(self):
        data = {'actual_power_W': 238.9}
        timeline = Timeline({'timeline': [
            {'at_s': 1, 'label': 'Request', 'data': data},
            {'at_s': 2, 'label': 'Accept'},
            {'at_s': 3, 'label': 'Reset', 'kind': 'hard_reset'},
        ]})
        self.assertIsNone(timeline.at(0)[2])
        self.assertEqual(timeline.at(2)[2], data)
        self.assertIsNone(timeline.at(3)[2])
        self.assertEqual(timeline.at(1 - 0.5 / 44100)[2], data)

    def test_invalid_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'score.json'
            base = {'schema_version': 1, 'timebase': 'arranged_audio_seconds',
                    'duration_s': 4, 'timeline': []}
            for events in ([None], [{'at_s': 2, 'label': 'A'}, {'at_s': 1, 'label': 'B'}],
                           [{'at_s': 1, 'label': 'A', 'data': {'actual_power_W': float('nan')}}]):
                path.write_text(json.dumps(dict(base, timeline=events)), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_score(path)

    def test_duration_mismatch_before_encoder_and_output_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wav, score, out = root/'test.wav', root/'test.json', root/'test.mp4'
            with wave.open(str(wav), 'wb') as audio:
                audio.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0' * 16000)
            score.write_text(json.dumps({'schema_version': 1, 'timebase': 'arranged_audio_seconds',
                                         'duration_s': 4, 'timeline': []}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'duration'):
                export_video(wav, score, out, ffmpeg='missing-encoder')
            out.write_bytes(b'existing video')
            with self.assertRaisesRegex(ValueError, 'exists'):
                export_video(wav, score, out)
            self.assertEqual(out.read_bytes(), b'existing video')


if __name__ == '__main__':
    unittest.main()
