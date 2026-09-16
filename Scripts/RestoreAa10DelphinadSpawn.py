"""Restore the r575 Delphinad Mirage dungeon entry in server world_spawns.json.

Read-only unless --apply; preserves the JSON-with-comments file and backs it up.
No game_pak writes. Evidence: native world.xml origin=(1,1), spawn_point.g
local=(524.66,1045.13,282.607), zRot=-2.0944 rad, World conversion=1024/cell.
Native SHA256: world.xml 9969c75997520fb4e7e95b5f6733bf091f7f1632db6057eb0f2ee8eac86bed7e;
spawn_point.g f859b3f2bf673a47d011aca2f2592a91ec87eed72b77ad16b2938b83c1df1fb0.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ENTRY = {
    "Name": "instance_phantom_of_delphinad",
    "SpawnPosition": {
        "ZoneId": 384, "X": 1548.66, "Y": 2069.13, "Z": 282.607,
        "Yaw": math.degrees(-2.0944),
    },
}


def parse(text):
    # Keep string literals intact while removing // comments used by this catalog.
    clean = re.sub(r'"(?:\\.|[^"\\])*"|//[^\r\n]*',
                   lambda m: "" if m[0].startswith("//") else m[0], text)
    rows = json.loads(clean)
    if not isinstance(rows, list):
        raise ValueError("Expected world spawn array")
    return rows


def plan(path):
    before = path.read_bytes()
    text = before.decode("utf-8-sig")
    rows = parse(text)
    matches = [r for r in rows if r.get("Name") == ENTRY["Name"]]
    if matches:
        if matches != [ENTRY]:
            raise ValueError(f"{path}: existing Delphinad spawn differs; refusing overwrite")
        return before, before
    end = text.rfind("]")
    content = text[:end].rstrip()
    if rows:
        tokens = [m for m in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|[^\s]', content)
                  if not m[0].startswith("//")]
        last = tokens[-1].end()
        content = content[:last] + "," + content[last:]
    newline = "\r\n" if "\r\n" in text else "\n"
    entry = json.dumps(ENTRY, ensure_ascii=False, indent=4)
    entry = newline.join("    " + line for line in entry.splitlines())
    result = content + newline + entry + newline + text[end:]
    assert parse(result) == rows + [ENTRY]
    after = result.encode("utf-8")
    if before.startswith(b"\xef\xbb\xbf"):
        after = b"\xef\xbb\xbf" + after
    return before, after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world-spawns", type=Path, nargs="+", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plans = [(path, *plan(path)) for path in args.world_spawns]
    for path, before, after in plans:
        digest = hashlib.sha256(before).hexdigest()
        if args.apply and before != after:
            if path.read_bytes() != before:
                raise ValueError(f"{path}: changed after planning")
            backup = path.with_name(path.name + ".before-delphinad-" + digest[:12])
            if backup.exists() and backup.read_bytes() != before:
                raise ValueError("Backup collision")
            if not backup.exists():
                backup.write_bytes(before)
            path.write_bytes(after)
            assert plan(path) == (after, after)
        print(json.dumps({"path": str(path), "changed": before != after,
                          "applied": args.apply, "sha256": hashlib.sha256(after).hexdigest()}))


if __name__ == "__main__":
    main()
