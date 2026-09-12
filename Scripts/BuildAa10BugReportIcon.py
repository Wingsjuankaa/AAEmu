"""Convert the generated transparent PNG into the pinned runtime DDS (Pillow required)."""
from pathlib import Path
import hashlib
import json
import struct
from PIL import Image

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/bug-report'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def build():
    source=ASSETS/'report-icon-source.png'
    manifest=json.loads((ASSETS/'icon.json').read_text(encoding='utf-8'))
    if digest(source)!=manifest['source_sha256']: raise ValueError('Source PNG drift')
    convert_icon(source,ASSETS/'report-icon-64.png',ASSETS/'report-icon.dds')
    print(json.dumps({n:digest(ASSETS/n) for n in ['report-icon-source.png','report-icon-64.png','report-icon.dds']}))

def convert_icon(source,preview,dds):
    image=Image.open(source)
    if image.mode!='RGBA' or image.getextrema()[3]!=(0,255): raise ValueError('Real alpha required')
    # Format conversion only; premultiplied resampling avoids dark fringes at alpha edges.
    small=image.convert('RGBa').resize((64,64),Image.Resampling.LANCZOS).convert('RGBA')
    small.save(preview)
    # Match r575 ui/common/default.dds: legacy BGRA8, full mip chain,
    # DDSD_LINEARSIZE | DDSD_MIPMAPCOUNT, DDSCAPS_COMPLEX | MIPMAP | TEXTURE.
    # Pillow's DXT5 writer emitted an invalid top-level linear size (268 vs 4096).
    header=struct.pack('<31I',124,0xA1007,64,64,64*64*4,0,7,*([0]*11),
                       32,0x41,0,32,0xff0000,0xff00,0xff,0xff000000,
                       0x401008,0,0,0,0)
    levels=[]
    for size in (64,32,16,8,4,2,1):
        mip=small if size==64 else small.convert('RGBa').resize((size,size),Image.Resampling.LANCZOS).convert('RGBA')
        levels.append(mip.tobytes('raw','BGRA'))
    dds.write_bytes(b'DDS '+header+b''.join(levels))
    result=Image.open(dds)
    if result.size!=(64,64) or result.getextrema()[3]!=(0,255): raise ValueError('DDS alpha lost')
if __name__=='__main__': build()
