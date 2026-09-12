"""Append the isolated report UI; preserve native inventory bytecode exactly."""
import json
import hashlib
from pathlib import Path
import PatchAa10SpanishUiLayout as codec
from Aa10LuaExtension import Reader, encode, append_extension
v1 = codec.v1
CONTRACTS = Path(__file__).with_name('Aa10BugReports.contracts.json')
LUA = Path(__file__).with_name('lua')/'BugReportPanel.lua'
def digest(b): return hashlib.sha256(b).hexdigest().upper()
def build(effective, output, luac):
    contract=json.loads(CONTRACTS.read_text(encoding='utf-8'))
    v1.require_exact(luac,contract['luac_sha256'])
    extension=codec.compile_source(LUA.read_text(encoding='utf-8'),luac)
    if digest(extension)!=contract['extension_sha256']: raise ValueError('Extension hash drift')
    output.mkdir(parents=True,exist_ok=False); results=[]
    for e in contract['entries']:
        name=e['name']; source=effective/'scriptsbin64/x2ui'/f'{name}.alb'
        data=source.read_bytes(); before=digest(data)
        if len(data)!=e['size'] or before not in [e['baseline_sha256'],e['patched_sha256'],*e.get('previous_sha256',[])]: raise ValueError('Unknown effective ALB')
        v1.require_exact(effective/'scripts/x2ui'/f'{name}.lua',e['source_sha256'])
        root=Reader(data).function()
        if before!=e['baseline_sha256']:
            root['children'].pop();root['code']=root['code'][:-12]+root['code'][-4:]
            root['flags']=root['flags'][:3]+bytes([root['flags'][3]-1])
        native=data[:12]+encode(root)
        if digest(native)!=e['native_stripped_sha256']: raise ValueError('Native instructions/constants drift')
        candidate=append_extension(native,extension)
        if len(candidate)>e['size']: raise ValueError('ALB capacity exceeded')
        candidate+=bytes(e['size']-len(candidate))
        if digest(candidate)!=e['patched_sha256']: raise ValueError('Candidate hash drift')
        target=output/f'{Path(name).name}.alb';target.write_bytes(candidate)
        results.append(dict(name=name,before=before,after=digest(candidate),size=e['size'],replacement=str(target)))
    return results
