"""Dry-run/apply/roll back the opt-in entry patch in the dedicated Spanish sandbox copy."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import struct

import PatchAa10SandboxAutoEntry as patch
import ApplyAa10SpanishUiLayout as tools

ROOT = patch.ROOT
REPO = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "runtime/sandbox-aa10/client"
PRIMARY = ROOT / "client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview"
SENTINELS = tools.SENTINELS


def entry_modify_times(pak: Path, names):
    """Read exact WIBO FILETIMEs; payload extractors do not retain this metadata."""
    from Aa10PakAppend import aes, read_tail, RECORD
    wanted, result = {name.encode("utf-8"): name for name in names}, {}
    with pak.open("rb") as stream:
        _, tail, count, _ = read_tail(stream)
    for index in range(count):
        record = aes(tail[index * RECORD:(index + 1) * RECORD])
        raw_name = record[:264].split(b"\0", 1)[0]
        if raw_name in wanted:
            name = wanted[raw_name]
            if name in result:
                raise RuntimeError("Duplicate WIBO entry")
            result[name] = struct.unpack_from("<q", record, 320)[0]
    if set(result) != set(wanted.values()):
        raise RuntimeError("Missing WIBO timestamp records")
    return result


def set_modify_time(path: Path, filetime: int):
    timestamp_ns = (filetime - 116444736000000000) * 100
    os.utime(path, ns=(timestamp_ns, timestamp_ns))


def verified_before_hash(pak: Path, marker_path: Path) -> str:
    """Reuse a prior full hash only while its physical file identity stays bound."""
    require_e(marker_path)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    identity = pak.stat()
    if (Path(marker["package_path"]).resolve() != pak.resolve()
            or marker.get("package_size") != identity.st_size
            or marker.get("package_mtime_ns") != identity.st_mtime_ns
            or marker.get("package_inode") != identity.st_ino):
        raise RuntimeError("Prior full-package verification no longer binds this exact file")
    digest = marker.get("package_sha256", "")
    if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
        raise RuntimeError("Prior marker has no complete SHA-256")
    return digest.upper()


def require_e(path: Path):
    if path.resolve().drive.upper() != "E:":
        raise RuntimeError(f"Sandbox output must stay on E: {path}")


def preflight(client: Path, apply: bool):
    if client.resolve() != CLIENT.resolve():
        raise RuntimeError(f"Only the dedicated sandbox client is writable: {CLIENT}")
    pak = client / "game_pak"
    if pak.stat().st_nlink != 1 or os.path.samefile(pak, PRIMARY / "game_pak"):
        raise RuntimeError("Sandbox package must be a physical independent copy")
    contracts = json.loads(patch.CONTRACTS.read_text(encoding="utf-8"))
    patch.lua.v1.require_exact(client / "Bin64/x2game.dll", contracts["x2game_sha256"])
    if apply:
        command = 'Get-CimInstance Win32_Process -Filter "Name = \'archeage.exe\'" | Select-Object -ExpandProperty ExecutablePath'
        paths = tools.run("powershell.exe", "-NoProfile", "-Command", command).splitlines()
        if any(str(client).lower() in path.lower() for path in paths):
            raise RuntimeError("Close only the sandbox archeage.exe before applying")
    return pak


def rollback(args, pak: Path):
    require_e(args.rollback_manifest)
    manifest = json.loads(args.rollback_manifest.read_text(encoding="utf-8"))
    contracts = json.loads(patch.CONTRACTS.read_text(encoding="utf-8"))
    expected = {e["name"]: e for e in contracts["entries"]}
    if manifest.get("patch_id") != contracts["patch_id"] or Path(manifest["game_pak"]).resolve() != pak.resolve():
        raise RuntimeError("Rollback manifest belongs to another target/patch")
    if len(manifest["entries"]) != len(expected) or {e["name"] for e in manifest["entries"]} != set(expected):
        raise RuntimeError("Unexpected rollback entry set")
    work = args.rollback_manifest.parent / datetime.now(timezone.utc).strftime("rollback-%Y%m%d-%H%M%S-%fZ")
    work.mkdir(parents=True, exist_ok=False)
    prepared = []
    results = []
    for entry in reversed(manifest["entries"]):
        contract = expected[entry["name"]]
        if entry["entry"] != f"game/scriptsbin64/x2ui/{entry['name']}.alb":
            raise RuntimeError("Rollback entry name disagrees with its contract")
        allowed = [contract["alb_sha256"], *contract.get("previous_patched_sha256", []), contract["patched_sha256"]]
        if entry["before"] not in allowed or entry["after"] != contract["patched_sha256"]:
            raise RuntimeError("Unknown rollback hashes")
        saved = Path(entry["rollback"])
        if not saved.resolve().is_relative_to(args.rollback_manifest.parent.resolve()):
            raise RuntimeError("Rollback source escaped its backup directory")
        patch.lua.v1.require_exact(saved, entry["before"], contract["size"])
        before_time = entry.get("modify_filetime_before")
        if before_time is None:
            # Intake apply produced before timestamp preservation was added.
            # Recover only that exact, fully hashed package snapshot.
            if manifest["sha256_before"] != contracts["initial_package_sha256"]:
                raise RuntimeError("Legacy rollback has no exact original timestamp")
            before_time = contract["original_modify_filetime"]
        set_modify_time(saved, before_time)
        destination = work / "before" / f"{entry['name']}.alb"
        current = tools.extract(pak, entry["entry"], destination)
        if current not in (entry["before"], entry["after"]):
            raise RuntimeError("Rollback refuses an entry modified by another patch")
        current_time = entry_modify_times(pak, [entry["entry"]])[entry["entry"]]
        set_modify_time(destination, current_time)
        prepared.append({"name": entry["name"], "entry": entry["entry"],
                         "before": current, "after": entry["before"],
                         "modify_filetime_before": current_time, "modify_filetime_after": before_time,
                         "replacement": str(saved), "rollback": str(destination)})
    # Validate every backup/hash before the first mutation.
    print("Hashing the sandbox package before rollback...", flush=True)
    before_hash = patch.lua.v1.sha256(pak)
    (work / "plan.json").write_text(json.dumps(prepared, indent=2) + "\n", encoding="utf-8")

    def write(entry):
        tools.run("dotnet", tools.REPLACE, pak, entry["entry"], entry["replacement"], entry["before"])

    def verify():
        actual_times = entry_modify_times(pak, [e["entry"] for e in prepared])
        for entry in prepared:
            if tools.extract(pak, entry["entry"], work / "verified" / f"{entry['name']}.alb") != entry["after"]:
                raise RuntimeError("Rollback reextraction mismatch")
            if actual_times[entry["entry"]] != entry["modify_filetime_after"]:
                raise RuntimeError("Rollback timestamp mismatch")
        for name, digest in manifest["sentinels"].items():
            if tools.extract(pak, name, work / "sentinels" / name) != digest:
                raise RuntimeError("Rollback unrelated map/icon/UI verification failed")

    def restore(entry):
        current = tools.extract(pak, entry["entry"], work / "failed-check" / f"{entry['name']}.alb")
        if current == entry["before"]:
            return
        if current != entry["after"]:
            raise RuntimeError("Unknown failed rollback entry; inspect its snapshot")
        tools.run("dotnet", tools.REPLACE, pak, entry["entry"], entry["rollback"], current)
        if tools.extract(pak, entry["entry"], work / "failed-restored" / f"{entry['name']}.alb") != entry["before"]:
            raise RuntimeError("Failed rollback compensation mismatch")

    if args.apply:
        tools.transaction(prepared, write, verify, restore)
    for entry in prepared:
        results.append({"name": entry["name"], "current": entry["before"], "restored": args.apply})
    if args.apply:
        print("Hashing the sandbox package after rollback...", flush=True)
    result = {"state": "rolled_back" if args.apply else "rollback_dry_run", "entries": results,
              "sha256_before": before_hash, "sha256_after": patch.lua.v1.sha256(pak) if args.apply else before_hash,
              "size_after": pak.stat().st_size}
    (work / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-root", type=Path, default=CLIENT)
    parser.add_argument("--luac", type=Path, default=Path("E:/AAEmu-Research/work/lua-5.1.5-msvc/lua-5.1.5/src/luac51.exe"))
    parser.add_argument("--backup-root", type=Path, default=ROOT / "backups/client-patches")
    parser.add_argument("--rollback-manifest", type=Path)
    parser.add_argument("--reuse-verified-marker", type=Path,
                        help="Reuse the previous complete package hash only for identical inode/size/mtime")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require_e(args.backup_root)
    temp = ROOT / "runtime/sandbox-aa10/temp"
    temp.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(temp)
    os.environ["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    os.environ["DOTNET_CLI_HOME"] = str(ROOT / "artifacts/sandbox/dotnet-home")
    os.environ["NUGET_PACKAGES"] = str(ROOT / "artifacts/cache/nuget")
    pak = preflight(args.client_root, args.apply)
    if args.rollback_manifest:
        rollback(args, pak)
        return
    now = datetime.now(timezone.utc)
    contracts = json.loads(patch.CONTRACTS.read_text(encoding="utf-8"))
    work = args.backup_root / now.strftime(contracts["patch_id"] + "-%Y%m%d-%H%M%S-%fZ")
    work.mkdir(parents=True, exist_ok=False)
    effective = work / "effective"
    names = []
    for entry in contracts["entries"]:
        names += [f"game/scripts/x2ui/{entry['name']}.lua", f"game/scriptsbin64/x2ui/{entry['name']}.alb"]
    names += SENTINELS
    listing = work / "entries.txt"
    listing.write_text("\n".join(names) + "\n", encoding="utf-8")
    tools.run("dotnet", tools.BATCH, pak, listing, effective)
    entries = patch.build(effective, work / "replacements", args.luac)
    times = entry_modify_times(pak, [f"game/scriptsbin64/x2ui/{e['name']}.alb" for e in entries])
    fixed_times = {e["name"]: e["original_modify_filetime"] for e in contracts["entries"]}
    for entry in entries:
        entry["entry"] = f"game/scriptsbin64/x2ui/{entry['name']}.alb"
        entry["rollback"] = str(effective / entry["entry"].removeprefix("game/"))
        entry["modify_filetime_before"] = times[entry["entry"]]
        entry["modify_filetime_after"] = fixed_times[entry["name"]]
        set_modify_time(Path(entry["rollback"]), entry["modify_filetime_before"])
        set_modify_time(Path(entry["replacement"]), entry["modify_filetime_after"])
        if (args.client_root / entry["entry"]).exists():
            raise RuntimeError(f"Loose ALB shadows the sandbox patch: {entry['entry']}")
    sentinels = {name: patch.lua.v1.sha256(effective / name.removeprefix("game/")) for name in SENTINELS}
    size = pak.stat().st_size
    print("Reusing the unchanged package's prior full SHA-256..." if args.reuse_verified_marker
          else "Hashing the sandbox package before operation...", flush=True)
    before = verified_before_hash(pak, args.reuse_verified_marker) if args.reuse_verified_marker else patch.lua.v1.sha256(pak)
    manifest = {"schema_version": 1, "patch_id": contracts["patch_id"],
                "time_utc": now.isoformat(), "state": "prepared", "applied": False,
                "game_pak": str(pak), "size_before": size, "sha256_before": before,
                "sha256_before_source": str(args.reuse_verified_marker) if args.reuse_verified_marker else "full_read",
                "repository_head": tools.run("git", "-C", REPO, "rev-parse", "HEAD"),
                "entries": entries, "sentinels": sentinels, "retail_acceptance": "pending"}
    manifest_path = work / "manifest.json"

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def write(entry):
        tools.run("dotnet", tools.REPLACE, pak, entry["entry"], entry["replacement"], entry["before"])

    def verify():
        actual_times = entry_modify_times(pak, [e["entry"] for e in entries])
        for entry in entries:
            target = work / "verified" / f"{entry['name']}.alb"
            if tools.extract(pak, entry["entry"], target) != entry["after"] or target.stat().st_size != entry["size"]:
                raise RuntimeError(f"Reextraction failed: {entry['entry']}")
            if actual_times[entry["entry"]] != entry["modify_filetime_after"]:
                raise RuntimeError(f"Non-deterministic package timestamp: {entry['entry']}")
        for name, digest in sentinels.items():
            if tools.extract(pak, name, work / "verified" / name) != digest:
                raise RuntimeError(f"Unrelated UI/map/icon changed: {name}")
        if pak.stat().st_size != size:
            raise RuntimeError("Sandbox package size changed")

    def restore(entry):
        target = work / "failed-check" / f"{entry['name']}.alb"
        current = tools.extract(pak, entry["entry"], target)
        if current == entry["before"]:
            return
        if current != entry["after"]:
            raise RuntimeError("Unknown partially written entry; inspect backup")
        tools.run("dotnet", tools.REPLACE, pak, entry["entry"], entry["rollback"], current)
        if tools.extract(pak, entry["entry"], work / "failed-restored" / f"{entry['name']}.alb") != entry["before"]:
            raise RuntimeError("Failure rollback verification mismatch")

    save()
    try:
        if args.apply:
            tools.transaction(entries, write, verify, restore)
            manifest["applied"] = True
        changed = args.apply and any(e["before"] != e["after"] for e in entries)
        print("Hashing the sandbox package after operation..." if changed else "No package bytes changed.", flush=True)
        manifest["sha256_after"] = patch.lua.v1.sha256(pak) if changed else before
        manifest["size_after"] = pak.stat().st_size
        manifest["state"] = "applied" if changed else "already_patched" if args.apply else "dry_run"
    except Exception as error:
        manifest["state"], manifest["error"] = "failed", str(error)
        raise
    finally:
        save()
    print(f"{manifest['state']}: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
