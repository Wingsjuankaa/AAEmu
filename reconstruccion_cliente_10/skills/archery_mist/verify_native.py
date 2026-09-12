"""Verify exported Ghidra body ranges against the effective AA10 release PE.

Requires pefile. Usage: python verify_native.py <archery-mist-repair-output>
The corpus export uses Aa10WorldLevelNativeAudit.java in read-only/noanalysis mode.
"""
import hashlib
import json
import sys
from pathlib import Path
import pefile

binary = Path('E:/AAEmu/rama_10/client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/Bin64/x2game.dll')
output = Path(sys.argv[1])
with binary.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
if digest != '405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734':
    raise SystemExit('Release identity changed; re-audit rather than reusing RVAs.')
pe = pefile.PE(str(binary))
if pe.FILE_HEADER.Machine != 0x8664:
    raise SystemExit('Expected x64 PE.')
results = []
for path in sorted(output.glob('client-*/*.bytes')):
    matches = []
    for line in path.read_text().splitlines():
        rva, hex_bytes = line.split()
        body = bytes.fromhex(hex_bytes)
        matches.append(pe.get_data(int(rva), len(body)) == body)
    results.append({'file': str(path.relative_to(output)), 'match': bool(matches) and all(matches), 'ranges': len(matches)})
if not results or not all(r['match'] for r in results):
    raise SystemExit('Missing corpus or byte mismatch.')
manifest = {'binary': str(binary), 'sha256': digest, 'architecture': 'x64',
            'image_base': hex(pe.OPTIONAL_HEADER.ImageBase), 'results': results}
(output / 'native-reanchor.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
print(f'{len(results)} functions match the effective release PE.')
