from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import TOOL_NAME, TOOL_VERSION
from .build import (
    BuildContext,
    build_stage_00,
    build_stage_10,
    build_stage_20,
    build_stage_30,
    build_stage_40,
    build_stage_50,
    build_stage_60,
    build_stage_70,
    build_stage_90,
    consolidate,
    finalize_outputs,
    run_all,
)
from .config import ForensicsConfig, load_config
from .closure import (
    build_reconstruction_dossier,
    default_dossier_paths,
    write_reconstruction_dossier,
)
from .util import canonical_json, sha256_file
from .validate import explain_entity, validate_database
from .wiki70 import freeze_stage_70_wiki


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m client_forensics",
        description=(
            "Build the staged AA8 client knowledge graph. "
            "This tool never mutates AAEmu or a runtime compact."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-items", type=Path)
    parser.add_argument("--source-item-manifest", type=Path)
    parser.add_argument("--source-item-tool-root", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("build-stage-00")
    commands.add_parser("build-stage-10")
    commands.add_parser("import-items")
    commands.add_parser("build-stage-30")
    commands.add_parser("build-stage-40")
    commands.add_parser("build-stage-50")
    commands.add_parser("build-stage-60")
    freeze_wiki = commands.add_parser("freeze-stage-70-wiki")
    freeze_wiki.add_argument("--refresh", action="store_true")
    freeze_wiki.add_argument("--delay", type=float, default=1.0)
    commands.add_parser("build-stage-70")
    commands.add_parser("build-stage-90")
    commands.add_parser("consolidate")
    commands.add_parser("finalize")
    commands.add_parser("run-all")
    validate = commands.add_parser("validate")
    validate.add_argument("database", type=Path, nargs="?")
    explain = commands.add_parser("explain")
    explain.add_argument("kind")
    explain.add_argument("native_id")
    closure = commands.add_parser("explain-closure")
    closure.add_argument("kind")
    closure.add_argument("native_id")
    _add_closure_arguments(closure)
    dossier = commands.add_parser("export-dossier")
    dossier.add_argument("kind")
    dossier.add_argument("native_id")
    dossier.add_argument("--json", type=Path, dest="json_path")
    dossier.add_argument("--html", type=Path, dest="html_path")
    _add_closure_arguments(dossier)
    return parser


def _add_closure_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        default="auto",
        help="Perfil declarativo; auto usa quest/item/skill o generic.",
    )
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--max-nodes", type=int)
    parser.add_argument("--max-edges-per-node", type=int)
    parser.add_argument(
        "--no-properties",
        action="store_true",
        help="Omite propiedades detalladas; conserva entidades y relaciones.",
    )


def _config(options: argparse.Namespace) -> ForensicsConfig:
    return load_config(options.config).with_overrides(
        output_dir=options.output_dir,
        source_item_database=options.source_items,
        source_item_manifest=options.source_item_manifest,
        source_item_tool_root=options.source_item_tool_root,
    )


def _convert(value: Any) -> Any:
    if isinstance(value, Path):
        return value.resolve().as_posix()
    if isinstance(value, dict):
        return {key: _convert(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert(child) for child in value]
    return value


def _display(value: Any) -> None:
    print(canonical_json(_convert(value), pretty=True), end="")


def _status(config: ForensicsConfig) -> dict[str, Any]:
    outputs = []
    for path in (
        config.stage_00,
        config.stage_10,
        config.stage_20,
        config.stage_30,
        config.stage_40,
        config.stage_50,
        config.stage_60,
        config.stage_70,
        config.stage_90,
        config.consolidated,
        config.manifest,
    ):
        outputs.append(
            {
                "path": path.resolve().as_posix(),
                "present": path.is_file(),
                "bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return {
        "client_build": config.client_build,
        "mode": "forensics_only",
        "server_mutation": "forbidden",
        "source_item_database": {
            "path": config.source_item_database.resolve().as_posix(),
            "present": config.source_item_database.is_file(),
            "sha256": (
                sha256_file(config.source_item_database)
                if config.source_item_database.is_file()
                else None
            ),
        },
        "outputs": outputs,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = _parser()
    options = parser.parse_args(argv)
    try:
        config = _config(options)
        if options.command == "status":
            result = _status(config)
        elif options.command == "validate":
            database = (options.database or config.consolidated).resolve()
            result = validate_database(
                database,
                consolidated=(database == config.consolidated.resolve()),
            )
        elif options.command == "explain":
            result = explain_entity(
                config.consolidated,
                options.kind,
                options.native_id,
            )
        elif options.command in {"explain-closure", "export-dossier"}:
            dossier = build_reconstruction_dossier(
                config.consolidated,
                options.kind,
                options.native_id,
                profile=options.profile,
                policy_path=options.policy,
                max_depth=options.max_depth,
                max_nodes=options.max_nodes,
                max_edges_per_node=options.max_edges_per_node,
                include_properties=not options.no_properties,
            )
            if options.command == "explain-closure":
                result = dossier
            else:
                default_json, default_html = default_dossier_paths(
                    config.output_dir,
                    options.kind,
                    options.native_id,
                )
                result = write_reconstruction_dossier(
                    dossier,
                    (options.json_path or default_json).resolve(),
                    (options.html_path or default_html).resolve(),
                )
        elif options.command == "finalize":
            result = finalize_outputs(config)
        elif options.command == "freeze-stage-70-wiki":
            result = freeze_stage_70_wiki(
                config,
                refresh=options.refresh,
                delay=options.delay,
                progress=lambda value: print(value, file=sys.stderr),
            )
        else:
            context = BuildContext.create(config)
            if options.command == "build-stage-00":
                result = build_stage_00(context)
            elif options.command == "build-stage-10":
                result = build_stage_10(context)
            elif options.command == "import-items":
                result = build_stage_20(context)
            elif options.command == "build-stage-30":
                result = build_stage_30(context)
            elif options.command == "build-stage-40":
                result = build_stage_40(context)
            elif options.command == "build-stage-50":
                result = build_stage_50(context)
            elif options.command == "build-stage-60":
                result = build_stage_60(context)
            elif options.command == "build-stage-70":
                result = build_stage_70(context)
            elif options.command == "build-stage-90":
                consolidate(context, include_stage_90=False)
                result = build_stage_90(context)
            elif options.command == "consolidate":
                result = consolidate(context)
            elif options.command == "run-all":
                result = run_all(config)
            else:
                parser.error(f"Unsupported command: {options.command}")
                return 2
        _display(result)
        return 0
    except (FileNotFoundError, KeyError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"{TOOL_NAME}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
