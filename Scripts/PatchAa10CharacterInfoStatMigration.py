#!/usr/bin/env python3
"""Build the AA10 r575 Character Info Stat Migration client patch.

The retail client already registers the current ``bless_uthstin`` window, but
its Character Info script does not expose that content.  This tool validates
the exact r575 Lua source and compiled entry, appends the missing Character
Info button integration, compiles a stripped Lua 5.1 chunk, restores the
ArcheAge bytecode header marker, and pads it to the original PAK entry size.

It only creates a replacement ALB.  Reinsertion into ``game_pak`` remains an
explicit, hash-guarded operation performed with ``PakEntryReplace``.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path


EXPECTED_SOURCE_SHA256 = "D33E3B0843585D03A12343EDCABB12DACF5DF8F0123D81AA84D5197C70B4CAEA"
EXPECTED_ALB_SHA256 = "598B7C84E5E383FAF447501B1873D9BEF419DA8638E1BBDB647C67AEAFB370E5"
EXPECTED_ALB_SIZE = 54_793

INTEGRATION = r'''

-- AAEmu AA10 r575: restore the native Stat Migration entry inside Character Info.
if X2Player:GetFeatureSet()["bless_uthstin"] then
    local migrationLabel = characterInfo.subtitle[19]
    local migrationButton = migrationLabel:CreateChildWidget("button", "blessUthstinPopupBtn", 0, true)
    migrationButton:AddAnchor("LEFT", characterInfo.window[25], "RIGHT", 0, 0)
    migrationButton:SetStyle("character_info_change")
    migrationButton:SetExtent(20, 20)
    migrationButton:Enable(UIParent:GetPermission(UIC_BLESS_UTHSTIN))

    function migrationButton:OnClick()
        ADDON:ToggleContent(UIC_BLESS_UTHSTIN)
    end
    migrationButton:SetHandler("OnClick", migrationButton.OnClick)

    function migrationButton:OnEnter()
        SetTooltip(GetUIText(WINDOW_TITLE_TEXT, "bless_uthstin"), self)
    end
    migrationButton:SetHandler("OnEnter", migrationButton.OnEnter)
end
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_exact(path: Path, expected_hash: str, expected_size: int | None = None) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if expected_size is not None and path.stat().st_size != expected_size:
        raise RuntimeError(
            f"{path}: expected {expected_size} bytes, got {path.stat().st_size}"
        )
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise RuntimeError(f"{path}: expected SHA-256 {expected_hash}, got {actual_hash}")


def build(source: Path, original_alb: Path, luac: Path, output: Path) -> None:
    require_exact(source, EXPECTED_SOURCE_SHA256)
    require_exact(original_alb, EXPECTED_ALB_SHA256, EXPECTED_ALB_SIZE)
    if not luac.is_file():
        raise FileNotFoundError(luac)

    source_text = source.read_text(encoding="utf-8-sig")
    if "AAEmu AA10 r575: restore the native Stat Migration" in source_text:
        raise RuntimeError(f"{source}: integration is already present")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa10-stat-migration-") as tmp_name:
        tmp = Path(tmp_name)
        patched_source = tmp / "character_info.lua"
        compiled = tmp / "character_info.alb"
        patched_source.write_text(source_text.rstrip() + INTEGRATION, encoding="utf-8", newline="\n")
        subprocess.run(
            [str(luac), "-s", "-o", str(compiled), str(patched_source)],
            check=True,
        )

        data = bytearray(compiled.read_bytes())
        if data[:12] != b"\x1bLua\x51\x00\x01\x04\x08\x04\x08\x00":
            raise RuntimeError(f"{compiled}: unexpected Lua 5.1 header {data[:12].hex()}")
        data[11] = 8
        if len(data) > EXPECTED_ALB_SIZE:
            raise RuntimeError(
                f"compiled patch is {len(data)} bytes; entry limit is {EXPECTED_ALB_SIZE}"
            )
        data.extend(b"\x00" * (EXPECTED_ALB_SIZE - len(data)))
        output.write_bytes(data)

    if output.stat().st_size != EXPECTED_ALB_SIZE:
        raise RuntimeError(f"{output}: invalid output size")
    print(f"source SHA-256:      {sha256(source)}")
    print(f"original ALB SHA-256:{sha256(original_alb)}")
    print(f"patched ALB SHA-256: {sha256(output)}")
    print(f"patched ALB size:    {output.stat().st_size}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the exact AA10 r575 Character Info Stat Migration ALB patch."
    )
    parser.add_argument("source", type=Path, help="extracted game/scripts/.../character_info.lua")
    parser.add_argument("original_alb", type=Path, help="extracted scriptsbin64 character_info.alb")
    parser.add_argument("luac", type=Path, help="64-bit-size_t Lua 5.1 compiler")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(
        args.source.resolve(),
        args.original_alb.resolve(),
        args.luac.resolve(),
        args.output.resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
