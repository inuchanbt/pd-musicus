from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from pd_musicus_player import make_handler
from pd_musicus_player import run


class PlayerServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        (root/'player').mkdir()
        (root/'examples').mkdir()
        (root/'player/index.html').write_text('player', encoding='utf-8')
        (root/'examples/avs_5a.wav').write_bytes(b'0123456789')
        (root/'private.txt').write_text('private', encoding='utf-8')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_range_and_head(self):
        with urlopen(Request(self.url+'/examples/avs_5a.wav',headers={'Range':'bytes=2-5'})) as r:
            self.assertEqual(r.status,206)
            self.assertEqual(r.read(),b'2345')
            self.assertEqual(r.headers['Content-Range'],'bytes 2-5/10')
        with urlopen(Request(self.url+'/',method='HEAD')) as r:
            self.assertEqual(r.read(),b'')
            self.assertEqual(r.headers['Content-Length'],'6')

    def test_private_files_and_invalid_range(self):
        for path in ('/private.txt','/../private.txt','/captures/data.csv'):
            with self.assertRaises(HTTPError) as ctx:
                urlopen(self.url+path)
            self.assertEqual(ctx.exception.code,404)
        with self.assertRaises(HTTPError) as ctx:
            urlopen(Request(self.url+'/examples/avs_5a.wav',headers={'Range':'bytes=20-30'}))
        self.assertEqual(ctx.exception.code,416)


class PlayerStartupTests(unittest.TestCase):
    def test_unavailable_port_falls_back_to_loopback_ephemeral_port(self):
        server = MagicMock()
        server.__enter__.return_value = server
        server.server_port = 12345
        server.serve_forever.side_effect = KeyboardInterrupt
        with patch('pd_musicus_player.ThreadingHTTPServer', side_effect=[OSError('port blocked'), server]) as factory:
            run(8765, open_browser=False)
        self.assertEqual(factory.call_args_list[0].args[0], ('127.0.0.1',8765))
        self.assertEqual(factory.call_args_list[1].args[0], ('127.0.0.1',0))


if __name__=='__main__':
    unittest.main()
