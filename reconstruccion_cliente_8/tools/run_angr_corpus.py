from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

import angr


def canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--binary-key", required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    options = arguments()
    anchors = json.loads(options.anchors.read_text(encoding="utf-8"))
    selected = sorted(
        {
            int(item["entry_rva"])
            for item in anchors["anchors"]
            if item["binary_key"] == options.binary_key
        }
    )
    project = angr.Project(str(options.binary), auto_load_libs=False)
    cfg = project.analyses.CFGFast(
        normalize=True,
        data_references=True,
        resolve_indirect_jumps=True,
    )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=f".{options.output.name}.",
        dir=options.output.parent,
    )
    os.close(handle)
    temporary = Path(name)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for rva in selected:
                address = project.loader.main_object.mapped_base + rva
                function = cfg.kb.functions.get(address)
                started = time.monotonic()
                row = {
                    "record": "function",
                    "binary_key": options.binary_key,
                    "entry_rva": rva,
                    "address": address,
                    "status": "failed",
                    "prototype": None,
                    "calling_convention": None,
                    "pseudocode": None,
                    "error": None,
                }
                try:
                    if function is None:
                        raise ValueError("CFGFast did not recover the anchor")
                    decompilation = project.analyses.Decompiler(
                        function,
                        cfg=cfg.model,
                    )
                    if decompilation.codegen is None:
                        raise ValueError("angr produced no code generator")
                    row["pseudocode"] = str(decompilation.codegen.text).replace(
                        "\r\n", "\n"
                    ).replace("\r", "\n")
                    row["prototype"] = (
                        str(function.prototype)
                        if function.prototype is not None
                        else None
                    )
                    row["calling_convention"] = (
                        type(function.calling_convention).__name__
                        if function.calling_convention is not None
                        else None
                    )
                    row["status"] = "confirmed"
                except Exception as exc:  # retain one explicit row per anchor
                    row["error"] = f"{type(exc).__name__}: {exc}"
                row["duration_ms"] = int((time.monotonic() - started) * 1000)
                if row["duration_ms"] > options.timeout * 1000:
                    row["status"] = "timeout"
                    row["error"] = (
                        f"Elapsed {row['duration_ms']} ms exceeded the "
                        f"{options.timeout} second policy"
                    )
                stream.write(canonical(row) + "\n")
        temporary.replace(options.output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
