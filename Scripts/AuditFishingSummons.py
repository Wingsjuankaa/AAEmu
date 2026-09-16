"""Read-only r575 fishing/summon closure; does not assert live-client acceptance."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    unavailable = []

    def rows(query):
        # Compact omits server-only tables; absence is not a broken gameplay reference.
        try:
            return [dict(row) for row in db.execute(query)]
        except sqlite3.OperationalError as error:
            if 'no such table:' not in str(error):
                raise
            unavailable.append({'query': query, 'reason': str(error)})
            return None

    rods = rows('''SELECT i.id,i.use_skill_id,i.level_requirement,i.actability_group_id,
        i.actability_requirement,w.recharge_buff_id,w.charge_lifetime
        FROM items i JOIN item_weapons w ON w.item_id=i.id WHERE w.holdable_id=17''')
    skills = rows('''SELECT s.id,s.plot_id,s.target_type_id,s.casting_cancelable,
        s.channeling_cancelable FROM skills s JOIN tagged_skills t ON t.skill_id=s.id
        WHERE t.tag_id=1024 AND s.target_type_id=6''')
    requirements = rows('''SELECT u.* FROM unit_reqs u WHERE u.owner_type='Skill'
        AND u.owner_id IN (SELECT s.id FROM skills s JOIN tagged_skills t ON t.skill_id=s.id
        WHERE t.tag_id=1024)''')
    boats = rows('''SELECT i.id,i.use_skill_id,ss.slave_id FROM items i
        JOIN item_summon_slaves ss ON ss.item_id=i.id JOIN slaves s ON s.id=ss.slave_id
        WHERE s.slave_kind_id=9''')
    checks = {
        'boat_missing_slave': rows('''SELECT ss.* FROM item_summon_slaves ss
            LEFT JOIN slaves s ON s.id=ss.slave_id WHERE s.id IS NULL'''),
        'school_missing_spawner': rows('''SELECT f.* FROM doodad_func_fish_schools f
            LEFT JOIN npc_spawners n ON n.id=f.npc_spawner_id WHERE n.id IS NULL'''),
        'school_missing_members': rows('''SELECT f.* FROM doodad_func_fish_schools f
            WHERE NOT EXISTS(SELECT 1 FROM npc_spawner_npcs n WHERE n.npc_spawner_id=f.npc_spawner_id)'''),
        'fish_missing_item': rows('''SELECT f.* FROM fish_details f
            LEFT JOIN items i ON i.id=f.item_id WHERE i.id IS NULL'''),
        'sale_missing_fish_details': rows('''SELECT f.* FROM doodad_func_buy_fish_items f
            LEFT JOIN fish_details d ON d.item_id=f.item_id WHERE d.id IS NULL'''),
        'trophy_missing_output': rows('''SELECT f.* FROM doodad_func_convert_fish_items f
            LEFT JOIN items i ON i.id=f.convert_item_id WHERE i.id IS NULL'''),
    }
    counts = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
              for table in ['fish_details', 'spawn_fish_effects', 'doodad_func_fish_schools',
                            'doodad_func_buy_fish_items', 'doodad_func_convert_fish_items']}
    result = {'path': str(path), 'sha256': digest(path), 'counts': counts,
              'rods': rods, 'rod_skills': skills, 'fishing_skill_requirements': requirements,
              'fishing_boats': boats, 'reference_gaps': checks, 'not_evaluated': unavailable,
              'live_acceptance': 'pending: summon, withdraw, relog, catch, sell and trophy'}
    db.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = [audit(path) for path in args.database]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for entry in result:
        print(entry['path'], entry['counts'],
              {key: len(rows) if rows is not None else 'not_evaluated'
               for key, rows in entry['reference_gaps'].items()})


if __name__ == '__main__':
    main()
