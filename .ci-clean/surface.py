"""Enumerate an isolated FFmpeg DLL tree; never reclassify vendor licenses."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import sys

root, output = map(Path, sys.argv[1:3])
root = root.resolve()
directory = os.add_dll_directory(str(root))
os.environ['PATH'] = str(root) + os.pathsep + os.environ['PATH']
codec = C.CDLL(str(root/'avcodec-62.dll'))
fmt = C.CDLL(str(root/'avformat-62.dll'))
filters = C.CDLL(str(root/'avfilter-11.dll'))

def iterate(lib, fn, kind=None):
    f = getattr(lib, fn)
    f.argtypes = [C.POINTER(C.c_void_p)]
    f.restype = C.c_void_p
    opaque = C.c_void_p()
    names = []
    accept = None
    if kind:
        accept = getattr(lib, kind)
        accept.argtypes = [C.c_void_p]
        accept.restype = C.c_int
    while item := f(C.byref(opaque)):
        if accept is None or accept(item):
            names.append(C.cast(item, C.POINTER(C.c_char_p))[0].decode())
    return sorted(set(names))

def protocols(output):
    f = fmt.avio_enum_protocols
    f.argtypes = [C.POINTER(C.c_void_p), C.c_int]
    f.restype = C.c_char_p
    opaque = C.c_void_p()
    out = []
    while name := f(C.byref(opaque), output):
        out.append(name.decode())
    return sorted(set(out))

codec.avcodec_license.restype = C.c_char_p
codec.avcodec_configuration.restype = C.c_char_p
result = {'root':str(root), 'dlls':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.dll'))},
          'decoders':iterate(codec,'av_codec_iterate','av_codec_is_decoder'),
          'encoders':iterate(codec,'av_codec_iterate','av_codec_is_encoder'),
          'demuxers':iterate(fmt,'av_demuxer_iterate'),
          'muxers':iterate(fmt,'av_muxer_iterate'),
          'filters':iterate(filters,'av_filter_iterate'),
          'input_protocols':protocols(0), 'output_protocols':protocols(1),
          'emitted_license_not_legal_clearance':codec.avcodec_license().decode(),
          'configuration':codec.avcodec_configuration().decode()}
output.write_text(json.dumps(result,indent=2),encoding='utf8')
print({k:len(v) for k,v in result.items() if isinstance(v,list)})
