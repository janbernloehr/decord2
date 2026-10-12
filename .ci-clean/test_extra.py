"""Additional public decode API gates; independent fixtures."""
import functools
import http.server
import io
from pathlib import Path
import subprocess
import sys
import threading
import wave

import decord
import numpy as np
import pytest


def test_decord_h264_explicit_seek_resize_and_closed_input():
    data = (Path(__file__).parent/'known-rgb-h264.mp4').read_bytes()
    stream = io.BytesIO(data)
    reader = decord.VideoReader(stream, ctx=decord.cpu(), num_threads=1, width=32, height=24)
    stream.close()
    for i in (10, 0, 5, 2):
        reader.seek_accurate(i)
        frame = reader.next().asnumpy()
        expected = np.broadcast_to(np.array([i*17,255-i*13,i*23],np.uint8),(24,32,3))
        np.testing.assert_allclose(frame,expected,rtol=0,atol=1)
    held = reader[2]
    del reader
    np.testing.assert_allclose(held.asnumpy(),np.broadcast_to([34,229,46],(24,32,3)),rtol=0,atol=1)


def test_decord_audio_pcm_wav_file_and_bytesio(tmp_path):
    samples = np.tile(np.array([-16384,0,16384,8192],dtype='<i2'),2000)
    path = tmp_path/'audio.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(samples.tobytes())
    for source in (str(path),io.BytesIO(path.read_bytes())):
        reader = decord.AudioReader(source,ctx=decord.cpu(),sample_rate=8000,mono=True)
        assert reader.shape == (1,8000)
        np.testing.assert_allclose(reader[:].asnumpy()[0],samples.astype(np.float32)/32768,rtol=0,atol=1e-6)
        assert abs(reader.duration()-1)<1e-6


def test_decord_http_decode():
    directory = str(Path(__file__).parent)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,directory=directory)
    server = http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        url = f'http://127.0.0.1:{server.server_port}/known-rgb-h264.mp4'
        reader = decord.VideoReader(url,ctx=decord.cpu(),num_threads=1)
        assert len(reader)==12
        np.testing.assert_array_equal(reader[0].asnumpy(),np.broadcast_to([0,255,0],(48,64,3)))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize('payload',[b'',b'not a media file',b'RIFF\xff\xff\xff\xffAVI ',b'\x00\x00\x00\x20ftypisom'])
def test_decord_malformed_subprocess_timeout(payload):
    code = 'import decord,io\ntry:\n decord.VideoReader(io.BytesIO('+repr(payload)+'),ctx=decord.cpu(),num_threads=1)\nexcept Exception as e:\n print(type(e).__name__); raise SystemExit(0)\nraise SystemExit(3)'
    result = subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0,(result.returncode,result.stdout,result.stderr)
    assert result.stdout.strip()
