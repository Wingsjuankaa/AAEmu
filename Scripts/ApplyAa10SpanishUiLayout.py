#!/usr/bin/env python3
"""Dry-run/apply the Spanish r575 layout with exact hashes and entry rollback."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

import PatchAa10SpanishUiLayout as patch

ROOT = Path("E:/AAEmu/rama_10")
REPO = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview"
LUAC = Path("E:/AAEmu-Research/work/lua-5.1.5-msvc/lua-5.1.5/src/luac51.exe")
EXTRACT = REPO / "reconstruccion_cliente_10/tools/PakEntryExtract/bin/Release/net10.0/PakEntryExtract.dll"
BATCH = REPO / "reconstruccion_cliente_10/tools/PakBatchExtract/bin/Release/net10.0/PakBatchExtract.dll"
REPLACE = REPO / "Tools/PakEntryReplace/bin/Release/net10.0/PakEntryReplace.dll"
X2_HASH = "405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734"
SENTINELS = ["game/ui/icon/achievement/icon_achieve_0001.dds",
             "game/ui/map/map_resources/arche_mall/en_us/world.dds",
             "game/scriptsbin64/x2ui/crafting/crafting_view.alb"]


def run(*args):
    result = subprocess.run([str(x) for x in args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def preflight(client: Path, apply: bool):
    # A layout task must never mutate the English base client, another build,
    # or a shared hardlink. Locale preview identity is deliberate and exact.
    if client.resolve() != CLIENT.resolve():
        raise RuntimeError(f"Only the Spanish full-preview distribution is supported: {CLIENT}")
    pak = client / "game_pak"
    if pak.stat().st_nlink != 1:
        raise RuntimeError("game_pak has multiple hardlinks")
    original = ROOT / "client/ArcheAge-Returns-10.0.2.13-r575/game_pak"
    if os.path.samefile(pak, original):
        raise RuntimeError("Spanish package aliases the original")
    patch.v1.require_exact(client / "Bin64/x2game.dll", X2_HASH)
    if apply:
        command = "Get-CimInstance Win32_Process -Filter \"Name = 'archeage.exe'\" | Select-Object -ExpandProperty ExecutablePath"
        paths = run("powershell.exe", "-NoProfile", "-Command", command).splitlines()
        if any(str(client).lower() in path.lower() for path in paths):
            raise RuntimeError("Close the Spanish archeage.exe before applying")
    return pak


def extract(pak: Path, entry: str, destination: Path):
    run("dotnet", EXTRACT, pak, entry, destination)
    return patch.v1.sha256(destination)


def transaction(entries, write, verify, restore):
    """Track attempted writes too: the native writer may fail after writing."""
    attempted = []
    try:
        for entry in entries:
            if entry["before"] == entry["after"]:
                continue
            attempted.append(entry)
            write(entry)
        verify()
    except Exception:
        failures = []
        for entry in reversed(attempted):
            try:
                restore(entry)
            except Exception as error:
                failures.append(str(error))
        if failures:
            raise RuntimeError("Rollback requires inspection: " + "; ".join(failures))
        raise


def main(patch_module=None, backup_prefix="aa10-spanish-ui-v2"):
    patch = patch_module or globals()["patch"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, default=CLIENT)
    parser.add_argument("--luac", type=Path, default=LUAC)
    parser.add_argument("--backup-root", type=Path, default=ROOT / "backups/client-patches")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    pak = preflight(args.client, args.apply)
    contracts = json.loads(patch.CONTRACTS.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    work = args.backup_root / now.strftime(backup_prefix + "-%Y%m%d-%H%M%S-%fZ")
    work.mkdir(parents=True, exist_ok=False)
    effective = work / "effective"
    names = []
    for entry in contracts["entries"]:
        names += [f"game/scripts/x2ui/{entry['name']}.lua",
                  f"game/scriptsbin64/x2ui/{entry['name']}.alb"]
    names += SENTINELS
    listing = work / "entries.txt"
    listing.write_text("\n".join(names) + "\n", encoding="utf-8")
    run("dotnet", BATCH, pak, listing, effective)
    entries = patch.build(effective, work / "replacements", args.luac)
    for entry in entries:
        entry["entry"] = f"game/scriptsbin64/x2ui/{entry['name']}.alb"
        entry["rollback"] = str(effective / entry["entry"].removeprefix("game/"))
        # No loose shadow is present in this distribution. Refuse to silently
        # install an ineffective patch if that changes in a future deployment.
        if (args.client / entry["entry"]).exists():
            raise RuntimeError(f"Loose ALB shadows package: {entry['entry']}")
    sentinels = {name: patch.v1.sha256(effective / name.removeprefix("game/"))
                 for name in SENTINELS}
    size = pak.stat().st_size
    print("Hashing complete game_pak before operation...", flush=True)
    before = patch.v1.sha256(pak)
    manifest = {"schema_version": 1, "patch_id": contracts["patch_id"],
                "time_utc": now.isoformat(), "applied": False,
                "repository_head": run("git", "-C", REPO, "rev-parse", "HEAD"),
                "game_pak": str(pak), "size_before": size, "sha256_before": before,
                "x2game_sha256": X2_HASH, "entries": entries, "sentinels": sentinels,
                "retail_visual_acceptance": "pending"}
    manifest_path = work / "manifest.json"

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def write(entry):
        print(run("dotnet", REPLACE, pak, entry["entry"], entry["replacement"], entry["before"]), flush=True)

    def verify():
        for entry in entries:
            output = work / "verified" / f"{entry['name']}.alb"
            actual = extract(pak, entry["entry"], output)
            if actual != entry["after"] or output.stat().st_size != entry["size"]:
                raise RuntimeError(f"Reextraction failed: {entry['entry']}")
            entry["verified_sha256"] = actual
        for name, expected in sentinels.items():
            if extract(pak, name, work / "verified" / name) != expected:
                raise RuntimeError(f"Unrelated entry changed: {name}")
        if pak.stat().st_size != size:
            raise RuntimeError("Package size changed")

    def restore(entry):
        output = work / "rollback-inspect" / f"{entry['name']}.alb"
        current = extract(pak, entry["entry"], output)
        if current == entry["before"]:
            return
        if current != entry["after"]:
            raise RuntimeError(f"Unknown post-failure entry: {entry['entry']}")
        run("dotnet", REPLACE, pak, entry["entry"], entry["rollback"], entry["after"])
        restored = extract(pak, entry["entry"], work / "rollback-verified" / f"{entry['name']}.alb")
        if restored != entry["before"]:
            raise RuntimeError(f"Rollback hash mismatch: {entry['entry']}")

    save()  # durable rollback plan before any package write
    try:
        if args.apply:
            transaction(entries, write, verify, restore)
            manifest["applied"] = True
        changed = args.apply and any(e["before"] != e["after"] for e in entries)
        print("Hashing complete game_pak after operation..." if changed else "No package bytes changed.", flush=True)
        manifest["sha256_after"] = patch.v1.sha256(pak) if changed else before
        manifest["size_after"] = pak.stat().st_size
        manifest["state"] = "applied" if changed else "already_patched" if args.apply else "dry_run"
    except Exception as error:
        manifest["state"] = "failed"
        manifest["error"] = str(error)
        raise
    finally:
        save()
    print(f"{manifest['state']}: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
