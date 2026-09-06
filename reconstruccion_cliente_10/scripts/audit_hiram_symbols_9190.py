"""Read-only r575 quest/buff chain and native crash evidence for quest 9190."""
import hashlib
import json
import sqlite3
import struct
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/hiram-symbols-9190'
OUT.mkdir(parents=True, exist_ok=True)
DB = ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3'
ZONE = ROOT / 'server/AAEmu/.server_files/AAEmu.ZoneHost/zone-350'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


catalogs = {}
for label, path in [('full', DB), ('runtime', ROOT / 'server/AAEmu/.server_files/AAEmu.Game/Data/compact.sqlite3')]:
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    queries = {
        'objectives': 'select * from quest_act_obj_effect_fires where id in (89,90,91)',
        'dagger_objective': 'select * from quest_act_obj_item_gathers where id=4247',
        'supply': 'select * from quest_act_supply_items where id=8280',
        'symbol_effects': 'select skill_id,effect_id,application_method_id from skill_effects where skill_id in (40092,40093,40094)',
        'effects': 'select * from effects where id in (73148,73151,73152,73153,73154,73155,73156)',
        'buff_effects': 'select * from buff_effects where id in (28072,28073,28074)',
        'buffs': 'select id,duration,stack_rule_id,max_stack,transform_buff_id from buffs where id in (23137,23652,23653)',
        'timeout': 'select * from buff_triggers where buff_id=23653',
        'gain_item': 'select * from special_effects where id=38819',
        'accept_reset': 'select * from dispel_effects where id=3635',
    }
    catalogs[label] = {key: [dict(row) for row in db.execute(sql)] for key, sql in queries.items()}
    db.close()

dump = ZONE / '14c5f2ee-36fc-4d78-9a3e-cfc1275806a7.dmp'
raw = dump.read_bytes()
count, directory = struct.unpack_from('<II', raw, 8)
modules = []
exception = {}
for index in range(count):
    kind, size, offset = struct.unpack_from('<III', raw, directory + index * 12)
    if kind == 4:
        for i in range(struct.unpack_from('<I', raw, offset)[0]):
            base, length, _, _, name = struct.unpack_from('<QIIII', raw, offset + 4 + i * 108)
            name = raw[name+4:name+4+struct.unpack_from('<I', raw, name)[0]].decode('utf-16le')
            modules.append({'base': hex(base), 'size': hex(length), 'path': name})
    elif kind == 6:
        _, context = struct.unpack_from('<II', raw, offset + 160)
        exception = {name: hex(struct.unpack_from('<Q', raw, context + 120 + i * 8)[0])
                     for i, name in enumerate(['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15','rip'])}

files = [DB, dump, ZONE / 'zone-350.crash', ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575/Bin64/x2game-dev_dedicate.dll']
report = {'quest': 9190, 'zone': 350, 'catalogs': catalogs, 'crash_registers': exception,
          'modules': modules, 'sha256': {str(p): digest(p) for p in files},
          'native_chain': {'receiver_rva': '0x364DE0', 'unit_lookup_rva': '0x35C830',
                           'buff_destroy_rva': '0x450420', 'fault_rva': '0x450A7A'},
          'observed': {'utc': '2026-09-04T14:54:31Z', 'doodad_obj_id': 101263,
                       'doodad_template_id': 13443, 'temporary_buff': 23137,
                       'temporary_buff_index': 2, 'quest_progress': [1,1,1,0],
                       'note': 'Heap packet absent from minidump; owner correlation uses Game warning at 14:54:25 and 5000ms buff duration.'}}
(OUT / 'catalog-and-crash.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'output': str(OUT / 'catalog-and-crash.json'), 'quest': 9190}, ensure_ascii=True))
