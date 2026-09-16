"""Read-only extraction of the LAN snapshot's approved client databases and UI."""
import json
from pathlib import Path
import sqlite3
import subprocess

from BuildAa10LanClient import DESTINATION, EVIDENCE, PINS, REPO, sha


def main():
    checkpoint = json.loads((REPO/'reconstruccion_cliente_10/checkpoints/PRIVATE_ALPHA_HUD_20260912.manifest.json').read_text(encoding='utf-8'))
    expected = dict(checkpoint['sentinels'])
    expected[checkpoint['asset']['entry']] = checkpoint['asset']['sha256']
    for entry in checkpoint['entries']:
        expected['game/scriptsbin64/x2ui/'+entry['name']+'.alb'] = entry['after']
    expected.update({
        'game/db/compact.sqlite3': PINS['game/db/compact.sqlite3'],
        'game/db/game.sqlite3': '1387EC6535270F99D9469F7F895306673827AFB0861E1B4E5F7BAAA503F605EB',
        'game/scriptsbin64/x2ui/loginstage_new/character_create/character_create_race.alb':
            '545FA08321F3159AEC4D4B4927FA6880330C8AB8CCDECD7293A9A9EFB79C1EA6',
    })
    manifest = json.loads((DESTINATION/'MANIFEST-SHA256.json').read_text(encoding='utf-8'))
    assert manifest['all_destination_hashes_verified'] and manifest['source_pak_sha256'] == PINS['game_pak']
    entries = EVIDENCE/'entries.txt'
    entries.write_text('\n'.join(sorted(expected))+'\n', encoding='utf-8')
    extracted = EVIDENCE/'extracted'
    batch = REPO/'reconstruccion_cliente_10/tools/PakBatchExtract/bin/Release/net10.0/PakBatchExtract.dll'
    result = subprocess.run(['dotnet', str(batch), str(DESTINATION/'game_pak'), str(entries), str(extracted)],
                            capture_output=True, text=True)
    (EVIDENCE/'package-extraction.log').write_text(result.stdout+result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    checks = []
    for entry, pinned in expected.items():
        path = extracted/entry.removeprefix('game/')
        actual = sha(path)
        assert actual == pinned, (entry, actual, pinned)
        checks.append(dict(entry=entry, sha256=actual, bytes=path.stat().st_size))
    assert sha(extracted/'db/compact.sqlite3') == sha(DESTINATION/'game/db/compact.sqlite3')
    sqlite_checks = {}
    for path in (extracted/'db/compact.sqlite3', DESTINATION/'game/db/game.sqlite3'):
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            check = db.execute('PRAGMA quick_check').fetchall()
            assert check == [('ok',)], (path, check)
            sqlite_checks[str(path)] = 'ok'
    report = dict(package_entries=checks, sqlite_quick_check=sqlite_checks,
                  compact_matches_loose=True, second_pc_acceptance='pending', pak_modified=False)
    (EVIDENCE/'package-verification.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(verified_entries=len(checks), compact_matches_loose=True, sqlite_quick_check='ok')))


if __name__ == '__main__':
    main()
