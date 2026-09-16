"""Read-only inventory of normal Nuia sidequests and their interaction dependencies.

Normal/detail=1 is an explicit catalog scope, not an assertion that every row
is a currently offered yellow quest. Race stories, events and world-placeholders
must not silently become playable content merely because their zone is Nuia.
"""
import json
import sqlite3
from collections import Counter

import audit_hiram_onward_quests as spatial
from build_quest_stage40 import inspect_server

OUT = spatial.ROOT / 'forensics/output/aa10-client-forensics/nuia-sidequests-20260915'
SCOPE = ("detail_id=1 AND category_id NOT IN (3,8,93,131,45,174) AND (race & 13)!=0 AND "
         "zone_id IN (SELECT z.id FROM zones z JOIN zone_groups g ON z.group_id=g.id WHERE g.target_id=3)")


def main():
    spatial.OUT, spatial.SCOPE = OUT, SCOPE
    spatial.main(validate_overlay=False, include_item_spawns=True, strict_contracts=False)
    report = json.loads((OUT/'audit.json').read_text(encoding='utf-8'))
    full = sqlite3.connect((spatial.ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3').as_uri()+'?mode=ro',uri=True)
    full.row_factory = sqlite3.Row
    ids = ','.join(str(q['id']) for q in report['quests'])
    classes, loaders, _, stubs, _, _ = inspect_server(spatial.REPO)
    acts = spatial.rows(full, f'''SELECT a.*,c.quest_context_id FROM quest_acts a
        JOIN quest_components c ON a.quest_component_id=c.id
        WHERE a.enable='t' AND c.quest_context_id IN ({ids}) ORDER BY a.id''')
    unsupported = [a for a in acts if a['act_detail_type'] not in classes or a['act_detail_type'] not in loaders or a['act_detail_type'] in stubs]
    client = sqlite3.connect((spatial.ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/game/db/compact.sqlite3').as_uri()+'?mode=ro',uri=True)
    titles = dict(client.execute("SELECT idx,en_us FROM localized_texts WHERE tbl_name='quest_contexts' AND tbl_column_name='name'"))
    report['unsupported_acts'] = unsupported
    report['act_types'] = dict(sorted(Counter(a['act_detail_type'] for a in acts).items()))
    report['scope_limits'] = ['Normal detail1 + Nuia catalog zone + western race mask; not proof of availability.',
                              'Static placement absence does not prove a dynamic/plantable actor is broken.',
                              'No client interaction capture or retail completion is claimed.']
    for q in report['quests']:
        q['title_es'] = titles.get(q['id'])
    (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(quests=len(report['quests']),actors=len(report['actors']),unsupported=len(unsupported),
                         missing_templates=report['missing_npc_templates']+report['missing_item_templates'])))


if __name__=='__main__':
    main()
