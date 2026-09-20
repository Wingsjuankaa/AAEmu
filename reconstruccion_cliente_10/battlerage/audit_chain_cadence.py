"""Read-only AA10 Combo/GCD inventory. Missing compact rows remain explicit."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("""
            SELECT se.*, s.value1 AS next_skill, s.value2 AS window_ms,
                   s.value3, s.value4, s.value5, s.value6, s.value7,
                   k.casting_time, k.channeling_time, k.cooldown_time,
                   k.custom_gcd, k.default_gcd, k.ignore_global_cooldown,
                   k.plot_id, k.plot_only, k.fire_anim_id, k.twohand_fire_anim_id,
                   k.dual_wield_fire_anim_id, k.use_anim_time, k.effect_delay,
                   k.use_weapon_cooldown_time, k.weapon_gcd_id
            FROM skill_effects se
            JOIN effects e ON e.id=se.effect_id
            JOIN special_effects s ON s.id=e.actual_id
            JOIN skills k ON k.id=se.skill_id
            WHERE e.actual_type='SpecialEffect' AND s.special_effect_type_id=48
            ORDER BY se.id
        """)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('full', 'client', 'runtime', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    sources = {key: {'sha256': digest(getattr(args, key)), 'rows': extract(getattr(args, key))}
               for key in ('full', 'client', 'runtime')}
    full = {row['id']: row for row in sources['full']['rows']}
    client = {row['id']: row for row in sources['client']['rows']}
    summary = {
        'counts': {key: len(value['rows']) for key, value in sources.items()},
        'full_runtime_equal': sources['full']['rows'] == sources['runtime']['rows'],
        'client_different_rows': [key for key in sorted(full.keys() & client.keys()) if full[key] != client[key]],
        'full_only_rows': [full[key] for key in sorted(full.keys() - client.keys())],
        'client_only_rows': [client[key] for key in sorted(client.keys() - full.keys())],
        'timing_scope': 'Authored values only; windows are not inter-hit delays or a proof of runtime pacing.'
    }
    result = {'summary': summary, 'sources': sources}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if not key.endswith('_rows')}))
    if not full or not summary['full_runtime_equal'] or summary['client_different_rows'] or summary['client_only_rows']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
