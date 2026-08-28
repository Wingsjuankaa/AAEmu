#!/usr/bin/env python3
"""Build the AA10 r575 Housing calendar-date client patch.

The Returns Housing maintenance UI formats absolute tax dates with the generic
duration formatter.  In en_us that renders values such as ``2026 yr Month:``
and makes a calendar year look like a protection duration.  This builder keeps
the server wire contract untouched and changes only the two Housing consumers:

* maintenance due dates use the native simple calendar-date formatter;
* the redundant localized ``until`` suffix is omitted because the row title
  already states "Protected Until" / "Demolition Date";
* the prepay ownership date uses the same native calendar-date formatter.

The inputs are exact AA10 r575 source/ALB entries extracted from ``game_pak``.
The generated stripped Lua 5.1 chunks restore ArcheAge's 64-bit string-size
marker and are zero-padded to the original entry sizes for safe replacement.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScriptContract:
    name: str
    source_sha256: str
    alb_sha256: str
    patched_sha256: str
    alb_size: int


MAINTAIN = ScriptContract(
    name="maintain_window",
    source_sha256="C74333D534643DEADA4C47A779A9204501FCF0531093C2343780610EC2AB8A15",
    alb_sha256="CA446A2D1FA6DB2F3C96AEB73AD206B93707FF637C09A75082129D6DE5677736",
    patched_sha256="CA19CCE55ECBCB1C8C165BD28B762905FB98C3F99172639580742CD559A789CD",
    alb_size=16_432,
)

MAINTAIN_VIEW = ScriptContract(
    name="maintain_window_view",
    source_sha256="D5EAF8B045DE4D56BCC0FDF16F67C491A92D21A1B4624378FC9ED0054602F36A",
    alb_sha256="A946192136A542998B5AE12C989B774D2DBEE47FB024F39A26F33B55A304E105",
    patched_sha256="8C6F73F36B827C4072D8078ABA649F7E51B5D44A19F9A7DC20F97FF4AFFC416E",
    alb_size=39_389,
)

LUA_51_HEADER = b"\x1bLua\x51\x00\x01\x04\x08\x04\x08\x00"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


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


def patch_maintain_source(source: str) -> str:
    patched = replace_once(
        source,
        "local dueStr = locale.time.GetDateToDateFormat(taxInfo.dueTime)",
        "local dueStr = locale.time.GetDateToSimpleDateFormat(taxInfo.dueTime)",
        "maintenance date formatter",
    )
    patched = replace_once(
        patched,
        'dueDate = string.format("%s%s%s|r", redHexColor, dueStr, locale.housing.untilTerm)',
        'dueDate = string.format("%s%s|r", redHexColor, dueStr)',
        "overdue suffix",
    )
    patched = replace_once(
        patched,
        'dueDate = string.format("%s%s", dueStr, locale.housing.untilTerm)',
        "dueDate = dueStr",
        "protected-until suffix",
    )
    return patched


def patch_maintain_view_source(source: str) -> str:
    return replace_once(
        source,
        "local prepayTimeStr = locale.time.GetDateToDateFormat(window.taxInfo.prepayTime)",
        "local prepayTimeStr = locale.time.GetDateToSimpleDateFormat(window.taxInfo.prepayTime)",
        "prepay date formatter",
    )


def compile_patch(
    contract: ScriptContract,
    source_path: Path,
    alb_path: Path,
    luac: Path,
    output: Path,
    patcher,
) -> tuple[str, str]:
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

    if output.stat().st_size != contract.alb_size:
        raise RuntimeError(f"{output}: invalid output size")
    output_hash = sha256(output)
    if output_hash != contract.patched_sha256:
        raise RuntimeError(
            f"{output}: expected patched SHA-256 {contract.patched_sha256}, got {output_hash}"
        )
    return sha256(source_path), output_hash


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build exact AA10 r575 Housing calendar-date ALB replacements."
    )
    parser.add_argument("--maintain-source", required=True, type=Path)
    parser.add_argument("--maintain-alb", required=True, type=Path)
    parser.add_argument("--view-source", required=True, type=Path)
    parser.add_argument("--view-alb", required=True, type=Path)
    parser.add_argument("--luac", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    results = []
    results.append(
        (
            MAINTAIN,
            *compile_patch(
                MAINTAIN,
                args.maintain_source.resolve(),
                args.maintain_alb.resolve(),
                args.luac.resolve(),
                output_dir / "maintain_window.alb",
                patch_maintain_source,
            ),
        )
    )
    results.append(
        (
            MAINTAIN_VIEW,
            *compile_patch(
                MAINTAIN_VIEW,
                args.view_source.resolve(),
                args.view_alb.resolve(),
                args.luac.resolve(),
                output_dir / "maintain_window_view.alb",
                patch_maintain_view_source,
            ),
        )
    )

    for contract, source_hash, patched_hash in results:
        print(contract.name)
        print(f"  source SHA-256:  {source_hash}")
        print(f"  original SHA-256:{contract.alb_sha256}")
        print(f"  patched SHA-256: {patched_hash}")
        print(f"  size:             {contract.alb_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
