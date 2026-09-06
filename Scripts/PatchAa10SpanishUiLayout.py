#!/usr/bin/env python3
"""Deterministic Spanish UI expansion for the exact Returns r575 consumers.

Contracts are frozen in Aa10SpanishUiLayout.contracts.json. Never regenerate
them during installation: an unknown source or effective ALB must fail closed.
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import tempfile
from pathlib import Path

import PatchAa10WesternUiLayout as v1

CONTRACTS = Path(__file__).with_name("Aa10SpanishUiLayout.contracts.json")
WINDOW_WIDTHS = {300: 360, 350: 430, 430: 510, 450: 540,
                 510: 600, 600: 720, 680: 800, 800: 900}
SKILL_WIDTH = 420
TEXT_WIDTH = 360


def replace(source: str, old: str, new: str, count: int = 1) -> str:
    if source.count(old) != count:
        raise RuntimeError(f"Expected {count} exact matches for {old!r}; got {source.count(old)}")
    return source.replace(old, new)


def patch_source(name: str, source: str) -> str:
    if name == "baselib/func_prefix_size":
        for old, new in WINDOW_WIDTHS.items():
            source = replace(source, f"[WINDOW_WIDTH_{old}] = {old},",
                             f"[WINDOW_WIDTH_{old}] = {new},")
        return source
    if name == "baselib/baselib":
        return replace(source, "TOOLTIP_MAX_WIDTH = 350,", "TOOLTIP_MAX_WIDTH = 420,")
    if name == "components/tooltip/tooltip":
        # Retain the user's C equipment fix, including both comparison paths.
        source = v1.patch_tooltip_source(source)
        expression = v1.equipment_width_expression("")
        source = replace(source, expression, "360", 2)
        source = replace(source, "minWindowWidth = 300", "minWindowWidth = 420", 2)
        source = replace(source, "minWindowWidth = 250", "minWindowWidth = 360", 4)
        # Native AddAnotherSideLine does not reserve space for both translated
        # strings. Give cooldown its own full-width line, preserving all data.
        source = replace(source,
            'tooltipItemAndSkill:AddAnotherSideLine(lastLineIndex, cooldown_str, "", FONT_SIZE.MIDDLE, ALIGN_RIGHT, 0)',
            'lastLineIndex = tooltipItemAndSkill:AddLine(cooldown_str, "", FONT_SIZE.MIDDLE, "left", ALIGN_LEFT, 0)')
        # Casting can also be a long translated channeling duration.
        source = replace(source,
            'tooltipItemAndSkill:AddAnotherSideLine(lastLineIndex, cast_str, "", FONT_SIZE.MIDDLE, ALIGN_RIGHT, 0)',
            'lastLineIndex = tooltipItemAndSkill:AddLine(cast_str, "", FONT_SIZE.MIDDLE, "left", ALIGN_LEFT, 0)')
        return source
    if name == "components/tooltip/tooltip_view":
        # Reflow BEFORE measuring text on the native small-screen fallback.
        return replace(source,
            '                    self.currentSections[i]:SetInfo(self.tooltipItemAndSkill, tipInfo, equiped)\n'
            '                    self.currentSections[i]:SetSectionWidth(self.minWindowWidth - 34)',
            '                    self.currentSections[i]:SetSectionWidth(self.minWindowWidth - 34)\n'
            '                    self.currentSections[i]:SetInfo(self.tooltipItemAndSkill, tipInfo, equiped)')
    if name == "option/option":
        source = replace(source, "frame:SetExtent(200, height)", "frame:SetExtent(250, height)")
        return replace(source, "restartTip:SetExtent(200, FONT_SIZE.MIDDLE)",
                       "restartTip:SetExtent(pageWindow:GetWidth() - 10, FONT_SIZE.MIDDLE)")
    if name == "skill/locale/layout_set":
        # 800 px window minus 60 px native margins; all five columns fit.
        return replace(source, "{ 130, 130, 125, 125, 110 }", "{ 160, 155, 145, 145, 135 }")
    if name == "store/common":
        source = replace(source, "window:SetExtent(279, 80)",
                         "window:SetExtent((parent:GetWidth() - 2) / STORE_MAX_DEFAULT_ITEM_COLUMN, 80)")
        return replace(source, "local width = 279",
                       "local width = (parent:GetWidth() - 2) / STORE_MAX_DEFAULT_ITEM_COLUMN")
    if name == "questcontext/locale/ko":
        # The default is effective in Returns; the en_us override is gated by
        # KAKAONA. Use the widths demonstrated by this same r575 Western layout.
        source = replace(source, "gridWidth = 260", "gridWidth = 390")
        source = replace(source, "titleDefaultWidth = 215", "titleDefaultWidth = 345")
        source = replace(source, "objectWidth = 215", "objectWidth = 340")
        return replace(source, "questLocale.questSelectButtonWidth = 443",
                       "questLocale.questSelectButtonWidth = 680")
    raise ValueError(f"Unknown consumer {name}")


class LuaChunk:
    """Read Lua 5.1 x64 bytecode, excluding debug-only fields from its identity."""
    def __init__(self, data: bytes):
        if data[:11] != v1.LUA_51_HEADER[:11] or data[11] not in (0, 8):
            raise RuntimeError("Not an AA10 / compiler Lua 5.1 x64 chunk")
        self.data, self.pos = data, 12

    def take(self, count):
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        if len(result) != count:
            raise RuntimeError("Truncated Lua chunk")
        return result

    def integer(self):
        return struct.unpack("<I", self.take(4))[0]

    def string(self):
        return self.take(struct.unpack("<Q", self.take(8))[0])

    def function(self):
        self.string()
        self.take(8)  # first and last source lines
        flags = self.take(4)
        code = self.take(self.integer() * 4)
        constants = []
        for _ in range(self.integer()):
            tag = self.take(1)[0]
            if tag == 0:
                value = b""
            elif tag == 1:
                value = self.take(1)
            elif tag == 3:
                value = struct.unpack("<d", self.take(8))[0]
            elif tag == 254:
                # r575's integer constant extension, also documented by the
                # local unluac LConstantType parser. Compare numeric value.
                tag = 3
                value = struct.unpack("<q", self.take(8))[0]
            elif tag == 4:
                value = self.string()
            else:
                raise RuntimeError(f"Unknown Lua constant tag {tag}")
            constants.append((tag, value))
        children = tuple(self.function() for _ in range(self.integer()))
        self.take(self.integer() * 4)
        for _ in range(self.integer()):
            self.string()
            self.take(8)
        for _ in range(self.integer()):
            self.string()
        return flags, code, tuple(constants), children


def semantic_chunk(data: bytes):
    reader = LuaChunk(data)
    result = reader.function()
    if any(data[reader.pos:]):
        raise RuntimeError("Unexpected nonzero trailing bytecode")
    return result


def compile_source(source: str, luac: Path) -> bytes:
    with tempfile.TemporaryDirectory(prefix="aa10-es-ui-") as directory:
        root = Path(directory)
        lua, alb = root / "source.lua", root / "compiled.alb"
        lua.write_text(source, encoding="utf-8", newline="\n")
        subprocess.run([str(luac), "-s", "-o", str(alb), str(lua)], check=True)
        data = bytearray(alb.read_bytes())
        if data[:12] != v1.LUA_51_HEADER:
            raise RuntimeError("Unexpected compiler ABI")
        data[11] = 8
        semantic_chunk(bytes(data))
        return bytes(data)


def build(effective: Path, output: Path, luac: Path):
    contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    v1.require_exact(luac, contracts["luac_sha256"])
    results = []
    for entry in contracts["entries"]:
        name = entry["name"]
        source_path = effective / f"scripts/x2ui/{name}.lua"
        alb_path = effective / f"scriptsbin64/x2ui/{name}.alb"
        v1.require_exact(source_path, entry["source_sha256"])
        actual = v1.sha256(alb_path)
        if alb_path.stat().st_size != entry["size"] or actual not in entry["accepted_sha256"]:
            raise RuntimeError(f"Unknown effective ALB {name}: {actual}")
        source = source_path.read_text(encoding="utf-8-sig")
        compiled = compile_source(patch_source(name, source), luac)
        if len(compiled) > entry["size"]:
            raise RuntimeError(f"ALB exceeds fixed entry capacity: {name}")
        replacement = output / f"{name}.alb"
        replacement.parent.mkdir(parents=True, exist_ok=True)
        replacement.write_bytes(compiled + b"\0" * (entry["size"] - len(compiled)))
        v1.require_exact(replacement, entry["patched_sha256"], entry["size"])
        results.append({"name": name, "before": actual, "after": entry["patched_sha256"],
                        "size": entry["size"], "replacement": str(replacement)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effective", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--luac", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.effective, args.output, args.luac), indent=2))


if __name__ == "__main__":
    main()
