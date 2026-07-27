from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import TOOL_NAME, TOOL_VERSION
from .candidates import generate_family, verify_candidate
from .config import ForensicsConfig, load_config
from .db import create_database, finalize_database, open_database, set_metadata
from .native_closure import generate_native_closure_audit
from .pipeline import (
    artifact_map,
    audit_server,
    build_manifest,
    decode_cache,
    register_artifacts,
    run_pipeline,
    scan_client,
)
from .reporting import explain_item, generate_report
from .surfaces import scan_reviewed_surfaces
from .util import canonical_json, open_sqlite_read_only, write_text_atomic
from .wiki import (
    DEFAULT_BASE_URL,
    DEFAULT_CRAWL_DELAY,
    DEFAULT_LOCALE,
    ENTITY_KINDS,
    audit_wiki,
    scan_wiki,
    wiki_edge_ids,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m item_forensics",
        description=(
            "Forensic AA8 item inventory. It never imports historical 3.0 "
            "gameplay data and never deploys generated candidates."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--research-root", type=Path)
    parser.add_argument("--client-compact", type=Path)
    parser.add_argument("--streams-root", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--legacy-item-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sql-manifest", type=Path)
    parser.add_argument("--surface-manifest", type=Path)
    parser.add_argument("--gamepak-index", type=Path)
    parser.add_argument("--x2game", type=Path, action="append")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scan-client", help="Create the base client item inventory")
    decode = commands.add_parser("decode-cache", help="Decode registered native cached results")
    decode.add_argument(
        "--deep",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Locate results by native anchors when a prior range is unavailable",
    )
    commands.add_parser("audit-server", help="Compare item capabilities with the AAEmu runtime")
    commands.add_parser(
        "audit-native-closure",
        help="Rebuild the deterministic audit for unresolved native item consumers",
    )
    run_all = commands.add_parser("run-all", help="Rebuild the complete inventory and reports")
    run_all.add_argument(
        "--deep",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Locate results by native anchors when a prior range is unavailable",
    )
    explain = commands.add_parser("explain", help="Explain evidence and gaps for one item")
    explain.add_argument("item_id", type=int)
    explain.add_argument("--json", action="store_true", dest="as_json")
    commands.add_parser("report", help="Regenerate deterministic HTML/CSV/JSON reports")
    wiki_scan = commands.add_parser(
        "scan-wiki",
        help="Freeze robots-aware ArcheRage wiki corroboration outside the native baseline",
    )
    wiki_scan.add_argument(
        "--kind",
        choices=sorted(ENTITY_KINDS),
        default="items",
        dest="entity_kind",
    )
    wiki_scan.add_argument(
        "--scope",
        choices=("unresolved", "catalog-only", "all"),
        default="unresolved",
        help="Native item IDs used as crawl seeds when --id is not supplied",
    )
    wiki_scan.add_argument("--id", type=int, action="append", dest="entity_ids")
    wiki_scan.add_argument(
        "--from-audit",
        action="store_true",
        help="Use distinct outgoing IDs of --kind from the current wiki audit",
    )
    wiki_scan.add_argument("--limit", type=int)
    wiki_scan.add_argument("--refresh", action="store_true")
    wiki_scan.add_argument("--delay", type=float, default=DEFAULT_CRAWL_DELAY)
    wiki_scan.add_argument("--base-url", default=DEFAULT_BASE_URL)
    wiki_scan.add_argument("--locale", default=DEFAULT_LOCALE)
    wiki_audit = commands.add_parser(
        "audit-wiki",
        help="Build a deterministic, non-authoritative SQLite audit from frozen pages",
    )
    wiki_audit.add_argument("--cache-dir", type=Path)
    wiki_audit.add_argument("--database", type=Path, dest="wiki_database")
    generate = commands.add_parser(
        "generate-family",
        help="Generate a review-only candidate family package",
    )
    generate.add_argument("family")
    verify = commands.add_parser("verify", help="Verify a candidate package")
    verify.add_argument("candidate", type=Path)
    return parser


def _config(options: argparse.Namespace) -> ForensicsConfig:
    if options.research_root is not None:
        os.environ["AAEMU_RESEARCH"] = str(options.research_root.resolve())
    config = load_config(options.config)
    return config.with_overrides(
        client_compact=options.client_compact,
        streams_root=options.streams_root,
        runtime=options.runtime,
        repo_root=options.repo_root,
        legacy_item_root=options.legacy_item_root,
        output_dir=options.output_dir,
        sql_manifest=options.sql_manifest,
        surface_manifest=options.surface_manifest,
        gamepak_index=options.gamepak_index,
        x2game=options.x2game,
    )


def _refresh_manifest(config: ForensicsConfig, quick: str, integrity: str) -> dict[str, Any]:
    connection = open_sqlite_read_only(config.database)
    try:
        manifest = build_manifest(
            config.database,
            connection,
            config,
            {"quick_check": quick, "integrity_check": integrity},
        )
    finally:
        connection.close()
    write_text_atomic(config.manifest, canonical_json(manifest, pretty=True))
    return manifest


def _scan(config: ForensicsConfig) -> dict[str, Any]:
    config.validate()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    connection = create_database(config.database)
    set_metadata(
        connection,
        {
            "client_build": config.client_build,
            "historical_3_0_gameplay_rows": 0,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        },
    )
    artifacts = register_artifacts(connection, config)
    result = scan_client(connection, config)
    surfaces = scan_reviewed_surfaces(connection, config)
    quick, integrity = finalize_database(connection)
    connection.close()
    manifest = _refresh_manifest(config, quick, integrity)
    return {
        **result,
        "surfaces": surfaces,
        "artifacts": len(artifacts),
        "database": config.database,
        "database_sha256": manifest["database"]["sha256"],
    }


def _decode(config: ForensicsConfig, deep: bool) -> dict[str, Any]:
    connection = open_database(config.database)
    try:
        result = decode_cache(
            connection,
            config,
            artifact_map(connection),
            deep=deep,
        )
        quick, integrity = finalize_database(connection)
    finally:
        connection.close()
    manifest = _refresh_manifest(config, quick, integrity)
    return {**result, "database_sha256": manifest["database"]["sha256"]}


def _audit(config: ForensicsConfig) -> dict[str, Any]:
    config.validate()
    connection = open_database(config.database)
    try:
        result = audit_server(connection, config)
        quick, integrity = finalize_database(connection)
    finally:
        connection.close()
    manifest = _refresh_manifest(config, quick, integrity)
    closure = generate_native_closure_audit(config)
    manifest["native_closure"] = {
        "json": config.native_closure_report.resolve().as_posix(),
        "json_sha256": closure["json_sha256"],
        "csv": config.native_closure_csv.resolve().as_posix(),
        "csv_sha256": closure["csv_sha256"],
        "summary": {
            "unresolved_descriptors": closure["unresolved_descriptors"],
            "closure_states": closure["closure_states"],
            "consumer_roles": closure["consumer_roles"],
        },
    }
    write_text_atomic(config.manifest, canonical_json(manifest, pretty=True))
    return {
        **result,
        "database_sha256": manifest["database"]["sha256"],
        "native_closure": closure,
    }


def _print_explanation(value: dict[str, Any]) -> None:
    summary = value["summary"]
    client = value["client_item"]
    coverage = value["runtime_coverage"] or {}
    print(
        f"item={client['item_id']} impl={client['impl_id']} "
        f"family={summary['family']} name={client.get('name') or ''}"
    )
    print(
        f"runtime_coverage={coverage.get('coverage', 'unknown')} "
        f"provenance={coverage.get('provenance', '')}"
    )
    print("capabilities:")
    for capability in value["capabilities"]:
        print(f"  {capability['dimension']}: {capability['state']}")
    print("gaps:")
    if not value["gaps"]:
        print("  none")
    for gap in value["gaps"]:
        print(
            f"  severity={gap['severity']} {gap['dimension']}: "
            f"{gap['blocker_code']} ({gap['state']})"
        )
    print("dependencies:")
    if not value["dependencies"]:
        print("  none")
    for edge in value["dependencies"]:
        print(
            f"  {edge['relation']} -> {edge['dst_kind']}:{edge['dst_id']} "
            f"[{edge['state']}]"
        )
    print("reviewed surface references:")
    if not value["surface_references"]:
        print("  none")
    for reference in value["surface_references"][:50]:
        print(
            f"  {reference['source_kind']}:{reference['path']} "
            f"[{reference['token_kind']}, {reference['state']}]"
        )


def _display(value: Any) -> None:
    def convert(item: Any) -> Any:
        if isinstance(item, Path):
            return item.resolve().as_posix()
        if isinstance(item, dict):
            return {key: convert(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [convert(child) for child in item]
        return item

    print(canonical_json(convert(value), pretty=True), end="")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = _parser()
    options = parser.parse_args(argv)
    try:
        if options.command == "verify":
            result = verify_candidate(options.candidate)
            _display(result)
            return 0 if result["ok"] else 2
        config = _config(options)
        if options.command == "scan-client":
            result = _scan(config)
        elif options.command == "decode-cache":
            result = _decode(config, options.deep)
        elif options.command == "audit-server":
            result = _audit(config)
        elif options.command == "audit-native-closure":
            result = generate_native_closure_audit(config)
        elif options.command == "run-all":
            pipeline = run_pipeline(config, deep=options.deep)
            report = generate_report(config)
            result = {"pipeline": pipeline, "report": report}
        elif options.command == "explain":
            result = explain_item(config.database, options.item_id)
            if options.as_json:
                _display(result)
            else:
                _print_explanation(result)
            return 0
        elif options.command == "report":
            result = generate_report(config)
        elif options.command == "scan-wiki":
            if options.from_audit and options.entity_ids:
                raise ValueError("--from-audit cannot be combined with --id")
            closure_ids = ()
            if options.from_audit:
                if not config.wiki_database.is_file():
                    raise FileNotFoundError(
                        f"Run audit-wiki before --from-audit: "
                        f"{config.wiki_database}"
                    )
                closure_ids = wiki_edge_ids(
                    config.wiki_database,
                    entity_kind=options.entity_kind,
                    limit=options.limit,
                )
            if (
                options.entity_kind != "items"
                and not options.entity_ids
                and not options.from_audit
            ):
                raise ValueError("--id is required when --kind is not items")
            result = scan_wiki(
                config,
                entity_kind=options.entity_kind,
                scope=options.scope,
                explicit_ids=closure_ids or options.entity_ids or (),
                limit=None if options.from_audit else options.limit,
                refresh=options.refresh,
                delay=options.delay,
                base_url=options.base_url,
                locale=options.locale,
                progress=lambda value: print(value, file=sys.stderr, flush=True),
            )
        elif options.command == "audit-wiki":
            result = audit_wiki(
                config,
                cache_dir=options.cache_dir,
                output_database=options.wiki_database,
            )
        elif options.command == "generate-family":
            result = generate_family(config, options.family)
        else:
            parser.error(f"Unsupported command: {options.command}")
            return 2
        _display(result)
        return 0
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        print(f"{TOOL_NAME}: {exc}", file=sys.stderr)
        return 1
