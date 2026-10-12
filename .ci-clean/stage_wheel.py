"""Repack only freshly built pinned-source DLLs, licenses and recipe."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

source, ffmpeg, prefix, work, reports, harness = map(Path, sys.argv[1:])
wheel = next((work / 'unrepaired').glob('*.whl'))
unpack = work / 'unpack'
subprocess.run([sys.executable, '-m', 'wheel', 'unpack', str(wheel), '-d', str(unpack)], check=True)
root = next(unpack.iterdir())
notice = root / 'decord' / 'third_party_notices'
notice.mkdir(parents=True)
origins = []
for dll in sorted((prefix / 'bin').glob('*.dll')):
    shutil.copy2(dll, root / 'decord' / dll.name)
    origins.append({'dll': dll.name, 'build_output': str(dll), 'sha256': hashlib.sha256(dll.read_bytes()).hexdigest(), 'source': 'https://ffmpeg.org/releases/ffmpeg-8.1.1.tar.xz', 'source_sha256': 'b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3', 'patches': []})
for component, base in [('decord', source), ('dlpack', source/'3rdparty/dlpack'), ('dmlc-core',source/'3rdparty/dmlc-core'), ('ffmpeg',ffmpeg)]:
    dest = notice/component
    dest.mkdir()
    for pattern in ('LICENSE*', 'COPYING*', 'NOTICE*', 'PATENTS*', 'AUTHORS*'):
        for p in base.glob(pattern):
            if p.is_file():
                shutil.copy2(p, dest / p.name)
for name in ['clean-native.yml']:
    shutil.copy2(harness/'.github/workflows'/name, notice/name)
shutil.copy2(harness/'.ci-clean/BUILD-NOTES.md', notice/'BUILD-NOTES.md')
shutil.copy2(ffmpeg/'ffbuild/config.mak', notice/'ffmpeg-config.mak')
shutil.copy2(ffmpeg/'config.h', notice/'ffmpeg-config.h')
(notice/'source-binary-map.json').write_text(json.dumps(origins, indent=2), encoding='utf8')
(reports/'source-binary-map.json').write_text(json.dumps(origins, indent=2), encoding='utf8')
# Public Python implementation must be byte-identical to the exact source pin.
for p in (source/'python/decord').rglob('*.py'):
    assert p.read_bytes() == (root/'decord'/p.relative_to(source/'python/decord')).read_bytes(), str(p)
subprocess.run([sys.executable, '-m', 'wheel', 'pack', str(root), '-d', str(work/'wheels')], check=True)
print('Staged source DLLs:', len(origins), 'Python implementation unchanged; external CRT prerequisite; no binary uploads.')
