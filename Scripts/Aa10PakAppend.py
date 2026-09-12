"""WIBO append boundary. Preserve existing encrypted records byte for byte.

Only the old FAT/footer suffix is replaced; all existing payload offsets stay
fixed. The caller must pin the full package, hold exclusive lifecycle control,
back up the old suffix, and verify consumers before accepting the change.
Requires cryptography. Layout authority: AAEmu.Commons/Utils/AAPak/AAPak.cs.
"""
import hashlib
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY=bytes.fromhex('321f2aeeaa584ab49a6c9e09d59e9c6f')
RECORD=336

def aes(data, encrypt=False):
    cipher=Cipher(algorithms.AES(KEY),modes.CBC(bytes(16)))
    op=cipher.encryptor() if encrypt else cipher.decryptor()
    return op.update(data)+op.finalize()

def aligned(n): return (n+511)//512*512
def sha(data): return hashlib.sha256(data).hexdigest().upper()

def read_tail(stream):
    stream.seek(0,2);size=stream.tell()
    if size<512 or size%512: raise ValueError('Unaligned package')
    stream.seek(size-512);footer=stream.read(512)
    header=aes(footer[:32])
    if header[:8]!=b'WIBO\0\0\0\0': raise ValueError('Only pinned WIBO layout supported')
    count,extras=struct.unpack_from('<II',header,8)
    start=size-512-aligned((count+extras)*RECORD)
    if count==0 or start<0: raise ValueError('Invalid file table counts')
    stream.seek(start);tail=stream.read()
    return start,tail,count,extras

def prepare(stream,name,payload):
    if not name.startswith('game/ui/custom/aaemu/') or '\\' in name or '..' in name:
        raise ValueError('Only custom AAEmu UI assets allowed')
    encoded=name.encode('ascii')
    if len(encoded)>=264 or not payload: raise ValueError('Invalid asset')
    start,tail,count,extras=read_tail(stream)
    # Read every live record to reject duplicate names and out-of-bounds payloads.
    for i in range(count):
        record=aes(tail[i*RECORD:(i+1)*RECORD])
        existing=record[:264].split(b'\0',1)[0]
        offset,size,duplicate,padding=struct.unpack_from('<qqqi',record,264)
        if min(offset,size,padding)<0 or size!=duplicate or offset+size+padding>start:
            raise ValueError(f'Invalid existing entry {i}')
        if existing==encoded:
            stream.seek(offset);current=stream.read(size)
            if current!=payload: raise ValueError('Asset already exists with different bytes')
            return dict(already=True,offset=start,before=tail,after=tail,count=count,extras=extras)
    record=bytearray(RECORD);record[:len(encoded)]=encoded
    struct.pack_into('<qqqi',record,264,start,len(payload),len(payload),aligned(len(payload))-len(payload))
    record[292:308]=hashlib.md5(payload).digest()
    # Fixed FILETIME (2026-09-11 UTC) makes builds deterministic.
    struct.pack_into('<qq',record,312,134336448000000000,134336448000000000)
    live_end=count*RECORD; records_end=(count+extras)*RECORD
    records=tail[:live_end]+aes(bytes(record),True)+tail[live_end:records_end]
    footer=bytearray(tail[-512:]);header=bytearray(aes(footer[:32]))
    struct.pack_into('<I',header,8,count+1);footer[:32]=aes(bytes(header),True)
    after=payload+bytes(aligned(len(payload))-len(payload))+records+bytes(aligned(len(records))-len(records))+footer
    return dict(already=False,offset=start,before=tail,after=after,count=count,extras=extras)

def write_suffix(path,offset,expected,replacement):
    # Caller backs up BEFORE opening writable and ensures the client is closed.
    # Re-read to refuse drift. Restore the exact original tail on write failure.
    with path.open('r+b') as stream:
        stream.seek(offset)
        if stream.read()!=expected: raise ValueError('Package suffix drift')
        import os
        try:
            stream.seek(offset);stream.write(replacement);stream.truncate();stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            stream.seek(offset);stream.write(expected);stream.truncate();stream.flush()
            os.fsync(stream.fileno())
            raise
