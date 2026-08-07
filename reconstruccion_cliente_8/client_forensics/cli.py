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
from .quest_item_crosswalk import (
    build_quest_item_crosswalk,
    freeze_quest_item_wiki,
    validate_quest_item_crosswalk,
)
from .nuia_story_graph import (
    build_nuia_story_quest_graph,
    freeze_nuia_story_wiki,
    validate_nuia_story_quest_graph,
)
from .nuia_story_graph_v2 import (
    build_nuia_story_quest_graph_v2,
    freeze_nuia_story_wiki_v2,
    validate_nuia_story_quest_graph_v2,
)
from .native_code import (
    build_anchor_inventory,
    build_stage_15,
    diff_native_architectures,
    export_native_anchor_dossiers,
    export_native_function,
    inventory_native_code,
    load_native_code_config,
    native_code_status,
    normalize_drcov_trace,
    register_dynamic_coverage,
    run_native_batch,
    run_native_decompiler,
    serve_native_code,
    validate_native_code_database,
)
from .native_semantics import (
    build_native_semantic_index,
    export_native_closure,
    load_native_semantic_config,
    native_semantic_status,
    validate_native_semantic_index,
)
from .specialization_graph import (
    build_specialization_graph_suite,
    build_specialization_graph,
    freeze_specialization_wiki_suite,
    freeze_specialization_wiki,
    validate_specialization_graph_suite,
    validate_specialization_graph,
)
from .aa10_crosswalk import build_aa10_crosswalk, validate_aa10_crosswalk


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
    parser.add_argument("--native-code-config", type=Path)
    parser.add_argument("--native-semantic-config", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("build-stage-00")
    commands.add_parser("build-stage-10")
    commands.add_parser("inventory-native-code")
    native_status = commands.add_parser("native-code-status")
    native_status.add_argument("--wave")
    native_status.add_argument("--verify-outputs", action="store_true")
    commands.add_parser("select-native-anchors")
    native_run = commands.add_parser("run-native-decompiler")
    native_run.add_argument("--engine", required=True)
    native_run.add_argument("--binary", required=True)
    native_run.add_argument("--architecture", choices=("x86", "x64"))
    native_run.add_argument("--scope", choices=("full", "anchors"), default="full")
    native_run.add_argument("--resume", action="store_true")
    native_batch = commands.add_parser("run-native-batch")
    native_batch.add_argument("--wave", required=True)
    native_batch.add_argument("--engines", default="ghidra,rizin")
    native_batch.add_argument("--resume", action="store_true")
    stage_15_build = commands.add_parser("build-stage-15")
    stage_15_build.add_argument(
        "--performance",
        choices=("balanced", "max"),
        default="balanced",
    )
    stage_15_build.add_argument("--workers", type=int)
    stage_15_build.add_argument("--memory-mb", type=int)
    stage_15_build.add_argument("--progress-file", type=Path)
    stage_15_build.add_argument("--no-resume", action="store_true")
    stage_15_build.add_argument(
        "--console-progress",
        action="store_true",
        help="Show the progress bar even when stderr is redirected.",
    )
    commands.add_parser("validate-stage-15")
    commands.add_parser("diff-native-architectures")
    native_server = commands.add_parser("serve-native-code")
    native_server.add_argument("--bind", default="127.0.0.1")
    native_server.add_argument("--port", type=int, default=8765)
    native_export = commands.add_parser("export-native-function")
    native_export.add_argument("binary")
    native_export.add_argument("rva", type=lambda value: int(value, 0))
    native_export.add_argument("--architecture", choices=("x86", "x64"))
    commands.add_parser("export-native-anchors")
    semantic_build = commands.add_parser("build-native-semantic-index")
    semantic_build.add_argument("--resume", action="store_true")
    commands.add_parser("validate-native-semantic-index")
    semantic_status = commands.add_parser("native-semantic-status")
    semantic_status.add_argument("--domain")
    semantic_status.add_argument("--tier")
    semantic_export = commands.add_parser("export-native-closure")
    semantic_export.add_argument("root_kind")
    semantic_export.add_argument("root_key")
    native_coverage = commands.add_parser("register-native-coverage")
    native_coverage.add_argument("manifest", type=Path)
    native_drcov = commands.add_parser("normalize-native-drcov")
    native_drcov.add_argument("trace", type=Path)
    native_drcov.add_argument("--scenario", required=True)
    native_drcov.add_argument(
        "--architecture",
        required=True,
        choices=("x86", "x64"),
    )
    native_drcov.add_argument("--output", type=Path, required=True)
    native_drcov.add_argument(
        "--network-scope",
        choices=("offline", "local_only"),
        default="offline",
    )
    native_drcov.add_argument("--tool-version", default="11.3.0")
    commands.add_parser("import-items")
    commands.add_parser("build-stage-30")
    commands.add_parser("build-stage-40")
    commands.add_parser("build-stage-50")
    commands.add_parser("build-stage-60")
    freeze_wiki = commands.add_parser("freeze-stage-70-wiki")
    freeze_wiki.add_argument("--refresh", action="store_true")
    freeze_wiki.add_argument("--delay", type=float, default=1.0)
    freeze_quest_items = commands.add_parser("freeze-quest-item-wiki")
    freeze_quest_items.add_argument("--resume", action="store_true")
    freeze_quest_items.add_argument("--delay", type=float, default=1.0)
    commands.add_parser("build-quest-item-crosswalk")
    commands.add_parser("validate-quest-item-crosswalk")
    freeze_nuia_story = commands.add_parser("freeze-nuia-story-wiki")
    freeze_nuia_story.add_argument("--resume", action="store_true")
    freeze_nuia_story.add_argument("--delay", type=float, default=1.0)
    commands.add_parser("build-nuia-story-quest-graph")
    commands.add_parser("validate-nuia-story-quest-graph")
    freeze_nuia_story_v2 = commands.add_parser("freeze-nuia-story-wiki-v2")
    freeze_nuia_story_v2.add_argument("--resume", action="store_true")
    freeze_nuia_story_v2.add_argument("--delay", type=float, default=1.0)
    commands.add_parser("build-nuia-story-quest-graph-v2")
    commands.add_parser("validate-nuia-story-quest-graph-v2")
    freeze_specialization = commands.add_parser("freeze-specialization-wiki")
    freeze_specialization.add_argument("specialization")
    freeze_specialization.add_argument("--resume", action="store_true")
    freeze_specialization.add_argument("--delay", type=float, default=1.0)
    build_specialization = commands.add_parser("build-specialization-graph")
    build_specialization.add_argument("specialization")
    validate_specialization = commands.add_parser("validate-specialization-graph")
    validate_specialization.add_argument("specialization")
    freeze_specialization_suite = commands.add_parser("freeze-specialization-suite-wiki")
    freeze_specialization_suite.add_argument("--specializations", default="all")
    freeze_specialization_suite.add_argument("--resume", action="store_true")
    freeze_specialization_suite.add_argument("--delay", type=float, default=1.0)
    build_specialization_suite = commands.add_parser("build-specialization-suite")
    build_specialization_suite.add_argument("--specializations", default="all")
    build_specialization_suite.add_argument("--reuse-graphs", action="store_true")
    validate_specialization_suite = commands.add_parser("validate-specialization-suite")
    validate_specialization_suite.add_argument("--specializations", default="all")
    build_aa10 = commands.add_parser("build-aa10-crosswalk")
    build_aa10.add_argument("--aa10-database", type=Path)
    build_aa10.add_argument("--database", type=Path)
    validate_aa10 = commands.add_parser("validate-aa10-crosswalk")
    validate_aa10.add_argument("--database", type=Path)
    commands.add_parser("build-stage-70")
    commands.add_parser("build-stage-90")
    commands.add_parser("consolidate")
    commands.add_parser("finalize")
    run_all_parser = commands.add_parser("run-all")
    run_all_parser.add_argument("--refresh-native-code", action="store_true")
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
        config.stage_15,
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
        native_config = load_native_code_config(options.native_code_config)
        semantic_config = load_native_semantic_config(options.native_semantic_config)
        if options.command == "status":
            result = _status(config)
        elif options.command == "inventory-native-code":
            result = inventory_native_code(native_config)
        elif options.command == "native-code-status":
            result = native_code_status(
                native_config,
                wave=options.wave,
                verify_outputs=options.verify_outputs,
            )
        elif options.command == "select-native-anchors":
            result = build_anchor_inventory(native_config)
        elif options.command == "run-native-decompiler":
            result = run_native_decompiler(
                native_config,
                engine=options.engine,
                binary=options.binary,
                architecture=options.architecture,
                scope=options.scope,
                resume=options.resume,
            )
        elif options.command == "run-native-batch":
            result = run_native_batch(
                native_config,
                wave=options.wave,
                engines=options.engines.split(","),
                resume=options.resume,
            )
        elif options.command == "build-stage-15":
            result = build_stage_15(
                native_config,
                performance_profile=options.performance,
                workers=options.workers,
                memory_mb=options.memory_mb,
                resume=not options.no_resume,
                progress_path=options.progress_file,
                console_progress=True if options.console_progress else None,
            )
        elif options.command == "validate-stage-15":
            result = validate_native_code_database(native_config.stage_database)
        elif options.command == "diff-native-architectures":
            result = diff_native_architectures(native_config)
        elif options.command == "register-native-coverage":
            result = register_dynamic_coverage(native_config, options.manifest)
        elif options.command == "normalize-native-drcov":
            result = normalize_drcov_trace(
                native_config,
                options.trace,
                scenario=options.scenario,
                architecture=options.architecture,
                output_path=options.output,
                network_scope=options.network_scope,
                tool_version=options.tool_version,
            )
        elif options.command == "serve-native-code":
            serve_native_code(
                native_config,
                bind=options.bind,
                port=options.port,
                semantic_database=semantic_config.database,
            )
            result = {"status": "stopped"}
        elif options.command == "export-native-function":
            result = export_native_function(
                native_config,
                options.binary,
                options.rva,
                architecture=options.architecture,
            )
        elif options.command == "export-native-anchors":
            result = export_native_anchor_dossiers(native_config)
        elif options.command == "build-native-semantic-index":
            result = build_native_semantic_index(
                semantic_config,
                native_config,
                config,
                resume=options.resume,
            )
        elif options.command == "validate-native-semantic-index":
            result = validate_native_semantic_index(
                semantic_config,
                native=native_config,
                forensics=config,
            )
        elif options.command == "native-semantic-status":
            result = native_semantic_status(
                semantic_config,
                domain=options.domain,
                tier=options.tier,
            )
        elif options.command == "export-native-closure":
            result = export_native_closure(
                semantic_config,
                native_config,
                options.root_kind,
                options.root_key,
            )
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
        elif options.command == "freeze-quest-item-wiki":
            result = freeze_quest_item_wiki(
                config,
                resume=options.resume,
                delay=options.delay,
                progress=lambda value: print(value, file=sys.stderr),
            )
        elif options.command == "build-quest-item-crosswalk":
            result = build_quest_item_crosswalk(config)
        elif options.command == "validate-quest-item-crosswalk":
            result = validate_quest_item_crosswalk(config)
        elif options.command == "freeze-nuia-story-wiki":
            result = freeze_nuia_story_wiki(
                config,
                resume=options.resume,
                delay=options.delay,
                progress=lambda value: print(value, file=sys.stderr),
            )
        elif options.command == "build-nuia-story-quest-graph":
            result = build_nuia_story_quest_graph(config)
        elif options.command == "validate-nuia-story-quest-graph":
            result = validate_nuia_story_quest_graph(config)
        elif options.command == "freeze-nuia-story-wiki-v2":
            result = freeze_nuia_story_wiki_v2(
                config,
                resume=options.resume,
                delay=options.delay,
                progress=lambda value: print(value, file=sys.stderr),
            )
        elif options.command == "build-nuia-story-quest-graph-v2":
            result = build_nuia_story_quest_graph_v2(config)
        elif options.command == "validate-nuia-story-quest-graph-v2":
            result = validate_nuia_story_quest_graph_v2(config)
        elif options.command == "freeze-specialization-wiki":
            result = freeze_specialization_wiki(
                config,
                options.specialization,
                resume=options.resume,
                delay=options.delay,
                progress=lambda value: print(value, file=sys.stderr),
            )
        elif options.command == "build-specialization-graph":
            result = build_specialization_graph(config, options.specialization)
        elif options.command == "validate-specialization-graph":
            result = validate_specialization_graph(config, options.specialization)
        elif options.command == "freeze-specialization-suite-wiki":
            result = freeze_specialization_wiki_suite(
                config,
                options.specializations,
                resume=options.resume,
                delay=options.delay,
                progress=lambda value: print(value, file=sys.stderr),
            )
        elif options.command == "build-specialization-suite":
            result = build_specialization_graph_suite(
                config,
                options.specializations,
                build_graphs=not options.reuse_graphs,
                progress=lambda value: print(value, file=sys.stderr),
            )
        elif options.command == "validate-specialization-suite":
            result = validate_specialization_graph_suite(
                config, options.specializations
            )
        elif options.command == "build-aa10-crosswalk":
            result = build_aa10_crosswalk(
                config,
                aa10_database=options.aa10_database,
                database=options.database,
            )
        elif options.command == "validate-aa10-crosswalk":
            result = validate_aa10_crosswalk(config, database=options.database)
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
                # Stage 90 materializes blocker_roots consumed by the native
                # semantic sidecar.  Bootstrap its source graph without the
                # sidecar to avoid a circular freshness dependency; the
                # subsequent full consolidation remains strict.
                consolidate(
                    context,
                    include_stage_90=False,
                    include_native_semantic=False,
                )
                result = build_stage_90(context)
            elif options.command == "consolidate":
                result = consolidate(context)
            elif options.command == "finalize":
                result = finalize_outputs(config)
            elif options.command == "run-all":
                if options.refresh_native_code:
                    inventory_native_code(native_config)
                    build_anchor_inventory(native_config)
                    build_stage_15(native_config)
                validate_native_code_database(native_config.stage_database)
                validate_native_semantic_index(
                    semantic_config,
                    native=native_config,
                    forensics=config,
                )
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
