"""Fail closed on vendor dependencies; retain PE/import correspondence."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import pefile

wheel, report = map(Path, sys.argv[1:3])
allowed = {'decord.dll', 'avcodec-62.dll', 'avformat-62.dll', 'avfilter-11.dll',
           'avutil-60.dll', 'avdevice-62.dll', 'swscale-9.dll', 'swresample-6.dll'}
result = {'wheel': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
          'dlls': [], 'errors': [], 'crt_policy': 'external Microsoft runtime prerequisite; no CRT copied from toolchain'}
with zipfile.ZipFile(wheel) as z:
    dlls = {Path(n).name.lower(): n for n in z.namelist() if n.lower().endswith('.dll')}
    for name, member in dlls.items():
        data = z.read(member)
        pe = pefile.PE(data=data)
        imports = sorted({entry.dll.decode().lower() for attr in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT') for entry in getattr(pe, attr, [])})
        row = {'name': name, 'member': member, 'sha256': hashlib.sha256(data).hexdigest(),
               'machine': hex(pe.FILE_HEADER.Machine), 'imports': imports, 'resolved': {}}
        result['dlls'].append(row)
        if name not in allowed:
            result['errors'].append('unapproved DLL: ' + name)
        if pe.FILE_HEADER.Machine != 0xAA64:
            result['errors'].append('non ARM64: ' + name)
        row['origin'] = 'decord2@1b4cfbd5d2964d411341ccf252051e516845430e' if name == 'decord.dll' else 'stock ffmpeg-8.1.1.tar.xz SHA256 b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3'
        row['license'] = 'Apache-2.0 plus pinned dlpack/dmlc header notices' if name == 'decord.dll' else 'LGPL-2.1-or-later configured; see stock LICENSE.md and retained COPYING texts'
        if name not in allowed:
            row['origin'] = row['license'] = 'not classified by this clean-build policy; see original inventory'
        for dep in imports:
            if dep in dlls:
                row['resolved'][dep] = 'wheel:' + dlls[dep]
            elif dep.startswith(('api-ms-win-', 'ext-ms-win-')):
                row['resolved'][dep] = 'Windows API-set contract (OS provided)'
            elif os.name == 'nt' and (p := Path(os.environ['SystemRoot']) / 'System32' / dep).is_file():
                row['resolved'][dep] = {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'machine': hex(pefile.PE(str(p)).FILE_HEADER.Machine)}
            elif os.name != 'nt':
                row['resolved'][dep] = 'not runtime verified on non-Windows audit host'
            else:
                result['errors'].append('unresolved import: ' + name + ' -> ' + dep)
    if 'decord.dll' not in dlls:
        result['errors'].append('missing decord.dll')
report.write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result, indent=2))
assert not result['errors'], result['errors']
