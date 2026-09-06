#!/usr/bin/env python3
"""Build the AA10 r575 Western-language UI layout patch.

The Returns client keeps Folio category buttons and equipment item tooltips at
compact East-Asian-language widths.  This builder makes two scoped changes:

* the Folio uses a 900 px window and stretches its category buttons to the
  available page width, preserving the artwork reservation;
* equipment item tooltips use a 360 px minimum width while non-equipment item,
  buff, skill and map tooltips keep their native sizes.

Inputs are exact r575 source and effective Bin64 ALB entries.  Generated Lua
5.1 chunks are stripped, marked with ArcheAge's x64 header byte and padded to
the original entry size for safe in-place replacement.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


FOLIO_WIDTH = 900
EQUIPMENT_TOOLTIP_WIDTH = 360
LUA_51_HEADER = b"\x1bLua\x51\x00\x01\x04\x08\x04\x08\x00"


@dataclass(frozen=True)
class ScriptContract:
    name: str
    source_sha256: str
    alb_sha256: str
    alb_size: int
    patched_sha256: str = ""


CRAFTING_VIEW = ScriptContract(
    name="crafting_view",
    source_sha256="E5E2D64596DD2D4B66EF8C37A9967FD1D5319D52E04CB868B73395A4DD6E0955",
    alb_sha256="0B65638618E3F588C8EDDF98832BC076ABD8DD0159DF6F736AC94BFA429C7AF6",
    alb_size=51_452,
    patched_sha256="067B69FA6664CACC3D0239F31405A743D958C0BD7811D6B604F8AA93B35756F7",
)

TOOLTIP = ScriptContract(
    name="tooltip",
    source_sha256="2C66A3039B85CA1C86C892E191E4A6B10FAB549072B72A6E7B8651C2CFED9C4E",
    alb_sha256="F725001F508C86DC8579333830964CFE7CE673A86F5FC301864C996929A040AF",
    alb_size=266_870,
    patched_sha256="3215CAC0947058F6C47715EAF55C85DC9029C49E6248D593DF2147DF2EE4ED91",
)


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


def require_exact_alb(path: Path, contract: ScriptContract) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != contract.alb_size:
        raise RuntimeError(
            f"{path}: expected {contract.alb_size} bytes, got {path.stat().st_size}"
        )
    actual_hash = sha256(path)
    allowed = (contract.alb_sha256, contract.patched_sha256)
    if actual_hash not in allowed:
        raise RuntimeError(
            f"{path}: expected original/patched SHA-256 {allowed}, got {actual_hash}"
        )


def replace_once(source: str, old: str, new: str, description: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{description}: expected one exact source match, found {count}")
    return source.replace(old, new, 1)


def patch_crafting_source(source: str) -> str:
    patched = replace_once(
        source,
        "            ApplyButtonSkin(button, BUTTON_STYLE.EQUIPMENT)\n            \n            local width = button:GetWidth() - 280",
        "            ApplyButtonSkin(button, BUTTON_STYLE.EQUIPMENT)\n            button:SetWidth(window:GetWidth())\n            \n            local width = button:GetWidth() - 280",
        "equipment category button width",
    )
    patched = replace_once(
        patched,
        "            ApplyButtonSkin(button, BUTTON_STYLE.DEFAULT)\n            \n            local width = button:GetWidth() - 100",
        "            ApplyButtonSkin(button, BUTTON_STYLE.DEFAULT)\n            button:SetWidth((window:GetWidth() - 4) / 2)\n            \n            local width = button:GetWidth() - 100",
        "default category button width",
    )
    return replace_once(
        patched,
        '    local windowWidth = GetLayoutSetCrafting()["windowWidth"]',
        f"    local windowWidth = {FOLIO_WIDTH}",
        "Folio window width",
    )


def equipment_width_expression(prefix: str) -> str:
    return (
        f'{prefix}(impl == "weapon" or impl == "armor" or '
        f'impl == "mate_armor" or impl == "butler_armor" or '
        f'impl == "accessory") and {EQUIPMENT_TOOLTIP_WIDTH} or 250'
    )


def patch_tooltip_source(source: str) -> str:
    patched = replace_once(
        source,
        "    local tooltipWnd = tooltip.tooltipWindows[tipNum]\n    tooltipWnd.minWindowWidth = 250",
        "    local tooltipWnd = tooltip.tooltipWindows[tipNum]\n"
        "    local impl = tipInfo[\"item_impl\"]\n"
        + equipment_width_expression("    tooltipWnd.minWindowWidth = "),
        "comparison/effect item tooltip width",
    )
    return replace_once(
        patched,
        "function PrepareTooltip(tipInfo, tipNum, equipped)\n"
        "    local impl = tipInfo[\"item_impl\"]\n\n"
        "    tooltip.tooltipWindows[tipNum].minWindowWidth = 250",
        "function PrepareTooltip(tipInfo, tipNum, equipped)\n"
        "    local impl = tipInfo[\"item_impl\"]\n\n"
        + equipment_width_expression(
            "    tooltip.tooltipWindows[tipNum].minWindowWidth = "
        ),
        "direct item tooltip width",
    )


def compile_patch(
    contract: ScriptContract,
    source_path: Path,
    alb_path: Path,
    luac: Path,
    output: Path,
    patcher: Callable[[str], str],
) -> str:
    require_exact(source_path, contract.source_sha256)
    require_exact_alb(alb_path, contract)
    if not luac.is_file():
        raise FileNotFoundError(luac)

    source_text = source_path.read_text(encoding="utf-8-sig")
    patched_text = patcher(source_text)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"aa10-{contract.name}-") as temp_name:
        temp = Path(temp_name)
        patched_source = temp / f"{contract.name}.lua"
        compiled = temp / f"{contract.name}.alb"
        patched_source.write_text(patched_text, encoding="utf-8", newline="\n")
        subprocess.run(
            [str(luac), "-s", "-o", str(compiled), str(patched_source)],
            check=True,
        )

        data = bytearray(compiled.read_bytes())
        if data[:12] != LUA_51_HEADER:
            raise RuntimeError(f"{compiled}: unexpected Lua 5.1 header {data[:12].hex()}")
        data[11] = 8
        if len(data) > contract.alb_size:
            raise RuntimeError(
                f"{compiled}: {len(data)} bytes exceeds entry size {contract.alb_size}"
            )
        data.extend(b"\x00" * (contract.alb_size - len(data)))
        output.write_bytes(data)

    output_hash = sha256(output)
    if contract.patched_sha256 and output_hash != contract.patched_sha256:
        raise RuntimeError(
            f"{output}: expected patched SHA-256 {contract.patched_sha256}, got {output_hash}"
        )
    return output_hash


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build exact AA10 r575 Western-language UI ALB replacements."
    )
    parser.add_argument("--crafting-source", required=True, type=Path)
    parser.add_argument("--crafting-alb", required=True, type=Path)
    parser.add_argument("--tooltip-source", required=True, type=Path)
    parser.add_argument("--tooltip-alb", required=True, type=Path)
    parser.add_argument("--luac", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    outputs = (
        (
            CRAFTING_VIEW,
            compile_patch(
                CRAFTING_VIEW,
                args.crafting_source.resolve(),
                args.crafting_alb.resolve(),
                args.luac.resolve(),
                output_dir / "crafting_view.alb",
                patch_crafting_source,
            ),
        ),
        (
            TOOLTIP,
            compile_patch(
                TOOLTIP,
                args.tooltip_source.resolve(),
                args.tooltip_alb.resolve(),
                args.luac.resolve(),
                output_dir / "tooltip.alb",
                patch_tooltip_source,
            ),
        ),
    )

    for contract, output_hash in outputs:
        print(contract.name)
        print(f"  original SHA-256: {contract.alb_sha256}")
        print(f"  patched SHA-256:  {output_hash}")
        print(f"  size:              {contract.alb_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
