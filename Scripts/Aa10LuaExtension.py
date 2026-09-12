"""Preserve native Lua instructions/constants; strip debug and append an isolated closure."""
import struct
from copy import deepcopy
from PatchAa10SpanishUiLayout import LuaChunk, semantic_chunk

def u32(n): return struct.pack('<I', n)

class Reader(LuaChunk):
    def function(self):
        self.string(); self.take(8)
        flags = self.take(4)
        code = self.take(self.integer() * 4)
        constants = []
        for _ in range(self.integer()):
            start = self.pos; tag = self.take(1)[0]
            if tag == 1: self.take(1)
            elif tag in (3, 254): self.take(8)
            elif tag == 4: self.string()
            elif tag != 0: raise ValueError('Unknown constant')
            constants.append(self.data[start:self.pos])
        children = [self.function() for _ in range(self.integer())]
        self.take(self.integer() * 4)
        for _ in range(self.integer()): self.string(); self.take(8)
        for _ in range(self.integer()): self.string()
        return dict(flags=flags, code=code, constants=constants, children=children)

def encode(f):
    return (bytes(16) + f['flags'] + u32(len(f['code'])//4) + f['code'] +
            u32(len(f['constants'])) + b''.join(f['constants']) +
            u32(len(f['children'])) + b''.join(encode(c) for c in f['children']) + bytes(12))

def append_extension(native, extension):
    original = Reader(native).function(); root = deepcopy(original)
    child = Reader(extension).function()
    # Root chunks must have no upvalues. Use a fresh register without overwriting locals.
    if child['flags'][0] != 0: raise ValueError('Extension captures upvalues')
    tail = struct.unpack('<I',root['code'][-4:])[0]
    if tail != 0x0080001e: raise ValueError('Expected plain native root RETURN 0 1')
    register = root['flags'][3]
    if register >= 249: raise ValueError('Root register limit')
    index = len(root['children'])
    root['flags'] = root['flags'][:3] + bytes([register+1])
    # CLOSURE A Bx; CALL A 1 1; original RETURN. Original PC/jump targets stay stable.
    root['code'] = root['code'][:-4] + u32(36 | register<<6 | index<<14) + u32(28 | register<<6 | 1<<23 | 1<<14) + u32(tail)
    root['children'].append(child)
    data = native[:12] + encode(root)
    restored = deepcopy(root); restored['flags'] = original['flags']
    restored['code'] = root['code'][:-12] + u32(tail); restored['children'].pop()
    if semantic_chunk(native[:12]+encode(restored)) != semantic_chunk(native):
        raise ValueError('Native semantic preservation failed')
    semantic_chunk(data)
    return data
