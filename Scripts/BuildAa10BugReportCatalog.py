"""Build searchable ES/EN entity names from pinned AA10 databases (read only)."""
import argparse
import json
import sqlite3
from pathlib import Path
from contextlib import closing
from PatchAa10PrivateAlpha import sha, require, NATIVE
from ApplyAa10SpanishUiLayout import CLIENT

TABLES = {'quest':'quest_contexts','item':'items','skill':'skills','npc':'npcs'}
def names(path, table):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        return dict(db.execute(f"SELECT i.id,COALESCE(NULLIF(l.en_us,''),i.name,'') FROM {table} i LEFT JOIN localized_texts l ON l.tbl_name=? AND l.tbl_column_name='name' AND l.idx=i.id ORDER BY i.id",(table,)))
def build(output):
    compact=CLIENT/'game/db/compact.sqlite3'
    original=CLIENT.parent/'ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3'
    require(sha(NATIVE)=='87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F','Native catalog drift')
    require(sha(compact)=='E5947F15726BF05C392CDC912BC778F2BFE6E407349A1F3A89BAA818B56C3187','Spanish catalog drift')
    require(sha(original)=='90E5C12A451F1334FF5C1B949982BEE3F1A9E4258F0EFC5FD3FF9D0478591E3C','English catalog drift')
    rows=[]
    for category,table in TABLES.items():
        native=names(NATIVE,table); english=names(original,table); spanish=names(compact,table)
        for id in sorted(native.keys()|english.keys()|spanish.keys()):
            if id<=0: continue
            en=english.get(id,''); display=spanish.get(id) or en or native.get(id) or f'{category} #{id}'
            rows.append(dict(Category=category,Id=id,Name=display,English=en))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({'path':str(output),'sha256':sha(output),'counts':{c:sum(r['Category']==c for r in rows) for c in TABLES}}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    build(p.parse_args().output)
