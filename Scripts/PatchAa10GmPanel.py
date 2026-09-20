"""Append GM closures to pinned r575 ALBs, preserving all existing extensions."""
import hashlib
import json
from pathlib import Path
import PatchAa10SpanishUiLayout as codec
from Aa10LuaExtension import Reader, encode, append_extension
v1 = codec.v1
CONTRACTS = Path(__file__).with_name('Aa10GmPanel.contracts.json')

def digest(data):
    return hashlib.sha256(data).hexdigest().upper()

def build(effective, output, luac):
    contract = json.loads(CONTRACTS.read_text(encoding='utf-8'))
    v1.require_exact(luac, contract['luac_sha256'])
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for entry in contract['entries']:
        name = entry['name']
        data = (effective / 'scriptsbin64/x2ui' / (name + '.alb')).read_bytes()
        before = digest(data)
        if len(data) != entry['size'] or before not in (entry['baseline_sha256'], entry['patched_sha256']):
            raise ValueError('Unknown effective ALB: ' + name)
        v1.require_exact(effective / 'scripts/x2ui' / (name + '.lua'), entry['source_sha256'])
        extension = codec.compile_source((Path(__file__).parent / entry['extension']).read_text(encoding='utf-8'), luac)
        if digest(extension) != entry['extension_sha256']:
            raise ValueError('Extension drift: ' + name)
        root = Reader(data).function()
        if before == entry['patched_sha256']:
            root['children'].pop()
            root['code'] = root['code'][:-12] + root['code'][-4:]
            root['flags'] = root['flags'][:3] + bytes([root['flags'][3] - 1])
        preserved = data[:12] + encode(root)
        if digest(preserved) != entry['preserved_sha256']:
            raise ValueError('Native or previous extension changed: ' + name)
        candidate = append_extension(preserved, extension)
        if len(candidate) > entry['size']:
            raise ValueError('ALB capacity exceeded: ' + name)
        candidate += bytes(entry['size'] - len(candidate))
        if digest(candidate) != entry['patched_sha256']:
            raise ValueError('Candidate drift: ' + name)
        target = output / (name.replace('/', '_') + '.alb')
        target.write_bytes(candidate)
        results.append(dict(name=name, before=before, after=digest(candidate), size=entry['size'], replacement=str(target)))
    return results
