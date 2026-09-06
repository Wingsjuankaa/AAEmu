#!/usr/bin/env python3
"""Disable only r575 World Level through its native system_feature_controls gate.

Never edits the input. Unknown input/output identities fail closed. The original
forensic databases remain intact. No EXP, quests, dates or localization edits.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

PROFILES = {
    'FFEE421EAFA5617FF844D9DEE12F33ABD24CCCC0DC035C2E029E72ED073646E5': 'embedded',
    'F61B6B6ED23AD83403D0E45F7D72F7CDF33553BCDE03535E800ACBB84639165B': 'loose',
}
PATCHED = {
    '8F39B0672B60F77B4027259BDFFB714810BF9392045BA81686A028203ADB5223': 'embedded',
    '90E5C12A451F1334FF5C1B949982BEE3F1A9E4258F0EFC5FD3FF9D0478591E3C': 'loose',
}
IDENTITY = (1, 1, 1001, 'World Level System - Opens at player level 30')


def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest().upper()


def transform(db):
    rows = db.execute('SELECT id, control_type, condition_type, describe, state '
                      'FROM system_feature_controls WHERE control_type=1 OR id=1').fetchall()
    if len(rows) != 1 or tuple(rows[0][:4]) != IDENTITY or rows[0][4] not in (0, 1):
        raise ValueError('Unknown or ambiguous World Level native control identity')
    if rows[0][4] == 0:
        return 0
    with db:
        db.execute('UPDATE system_feature_controls SET state=0 WHERE id=1 AND control_type=1')
    return 1


def build(source, output):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output.exists() or output == source:
        raise ValueError('Output must be a new file distinct from input')
    before = sha256(source)
    profile = PROFILES.get(before) or PATCHED.get(before)
    if profile is None:
        raise ValueError(f'Unknown SQLite SHA-256: {before}')
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    try:
        with closing(sqlite3.connect(output)) as db:
            if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise ValueError('Source integrity failed')
            changed = transform(db)
            if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise ValueError('Output integrity failed')
        after = sha256(output)
        if output.stat().st_size != source.stat().st_size:
            raise ValueError('Fixed-size entry grew')
        expected = [h for h, p in PATCHED.items() if p == profile]
        if expected and after not in expected:
            raise ValueError(f'Output is not deterministic: {after}')
        return dict(profile=profile, source=str(source), output=str(output),
                    size=output.stat().st_size, before=before, after=after, changed=changed)
    except Exception:
        output.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), indent=2))
