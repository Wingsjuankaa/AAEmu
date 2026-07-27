from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

from .util import canonical_json


ITEM_TABLE = re.compile(
    r"^(?:items?|item_|equip_|wearable|holdable|armor_grade_|gem_)",
    re.IGNORECASE,
)
NATIVE_DEPENDENCY_TABLES = {
    "actability_groups",
    "buffs",
    "craft_a_categories",
    "craft_b_categories",
    "craft_c_categories",
    "craft_d_categories",
    "craft_line_components",
    "craft_lines",
    "craft_materials",
    "craft_pack_crafts",
    "craft_packs",
    "craft_products",
    "crafts",
    "doodad_almighties",
    "tagged_items",
    "tags",
}
TABLE_FROM_SQL = re.compile(
    r"\bFROM\s+[`\"']?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QuerySpec:
    table_name: str
    source_module: str
    columns: tuple[str, ...]
    layout: tuple[str, ...]
    stream_name: str = "game11"
    start: int | None = None
    expected_rows: int | None = None
    anchor_id: int | None = None
    anchor_values: dict[str, Any] | None = None
    loader_consumer: str | None = None
    sql_text: str | None = None
    evidence: dict[str, Any] | None = None

    def stable_key(self) -> tuple[Any, ...]:
        return (
            self.table_name,
            self.source_module,
            self.stream_name,
            self.start,
            self.columns,
            self.layout,
        )


def _import_module(path: Path, ordinal: int) -> ModuleType:
    name = f"aa8_item_forensics_registry_{ordinal}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load extractor definitions from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _spec_mappings(module: ModuleType) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for variable_name, value in sorted(vars(module).items()):
        if not isinstance(value, dict):
            continue
        for table_name, candidate in sorted(value.items(), key=lambda item: str(item[0])):
            if (
                isinstance(table_name, str)
                and isinstance(candidate, dict)
                and isinstance(candidate.get("columns"), (list, tuple))
                and isinstance(candidate.get("layout"), (list, tuple))
            ):
                yield variable_name, table_name, candidate


def load_legacy_specs(item_root: Path) -> tuple[list[QuerySpec], list[dict[str, str]]]:
    specs: list[QuerySpec] = []
    failures: list[dict[str, str]] = []
    paths = sorted(item_root.rglob("extract_native*.py"))
    for ordinal, path in enumerate(paths):
        relative = path.relative_to(item_root.parent).as_posix()
        try:
            module = _import_module(path, ordinal)
        except Exception as exc:  # The failure itself is negative evidence.
            failures.append({"module": relative, "error": f"{type(exc).__name__}: {exc}"})
            continue
        for variable_name, table_name, value in _spec_mappings(module):
            anchor_values = value.get("anchor_values", value.get("anchor"))
            expected = value.get("expected_rows", value.get("expected"))
            evidence = {
                "registry_source": relative,
                "registry_variable": variable_name,
            }
            first_string_reference = value.get("first_string_reference")
            if first_string_reference is None and table_name == "holdables":
                first_string_reference = getattr(
                    module,
                    "HOLDABLE_FIRST_STRING_REFERENCE",
                    None,
                )
            if first_string_reference is not None:
                evidence["first_string_reference"] = int(first_string_reference)
            specs.append(
                QuerySpec(
                    table_name=table_name,
                    source_module=f"{relative}:{variable_name}",
                    columns=tuple(str(column) for column in value["columns"]),
                    layout=tuple(str(field) for field in value["layout"]),
                    stream_name=str(value.get("stream_name", "game11")),
                    start=_as_int(value.get("start")),
                    expected_rows=_as_int(expected),
                    anchor_id=_as_int(value.get("anchor_id")),
                    anchor_values=(
                        {str(key): item for key, item in anchor_values.items()}
                        if isinstance(anchor_values, dict)
                        else None
                    ),
                    loader_consumer=(
                        str(value["layout_source"])
                        if value.get("layout_source")
                        else None
                    ),
                    evidence=evidence,
                )
            )
    unique: dict[tuple[Any, ...], QuerySpec] = {}
    for spec in specs:
        unique[spec.stable_key()] = spec
    return [unique[key] for key in sorted(unique, key=str)], failures


def _walk_ranges(
    value: Any,
    path: tuple[str, ...] = (),
) -> Iterator[tuple[str, dict[str, Any], tuple[str, ...]]]:
    if isinstance(value, dict):
        if (
            "start" in value
            and ("end" in value or "rows" in value)
            and path
        ):
            yield path[-1], value, path
        for key, child in value.items():
            yield from _walk_ranges(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_ranges(child, path + (str(index),))


def load_manifest_ranges(item_root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(item_root.rglob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        for name, value, json_path in _walk_ranges(document):
            try:
                start = _as_int(value.get("start"))
                end = _as_int(value.get("end"))
                rows = _as_int(value.get("rows"))
            except (TypeError, ValueError):
                continue
            if start is None:
                continue
            result.setdefault(name, []).append(
                {
                    "start": start,
                    "end": end,
                    "rows": rows,
                    "manifest": path.relative_to(item_root.parent).as_posix(),
                    "json_path": ".".join(json_path),
                }
            )
    for values in result.values():
        values.sort(key=lambda entry: (
            entry["start"],
            entry["manifest"],
            entry["json_path"],
        ))
    return result


def _base_table(name: str) -> str:
    return name.removesuffix("_short")


def merge_ranges(
    specs: list[QuerySpec],
    ranges: dict[str, list[dict[str, Any]]],
) -> list[QuerySpec]:
    merged: list[QuerySpec] = []
    for spec in specs:
        if spec.start is not None:
            merged.append(spec)
            continue
        candidates = (
            ranges.get(spec.table_name)
            or ranges.get(_base_table(spec.table_name))
            or []
        )
        exact = [
            entry
            for entry in candidates
            if spec.expected_rows is None
            or entry.get("rows") in (None, spec.expected_rows)
        ]
        if len(exact) != 1:
            merged.append(spec)
            continue
        entry = exact[0]
        evidence = dict(spec.evidence or {})
        evidence["range_manifest"] = entry["manifest"]
        evidence["range_json_path"] = entry["json_path"]
        merged.append(
            QuerySpec(
                **{
                    **spec.__dict__,
                    "start": int(entry["start"]),
                    "evidence": evidence,
                }
            )
        )
    return merged


def load_item_sql(sql_manifest: Path | None) -> dict[str, list[dict[str, Any]]]:
    if sql_manifest is None or not sql_manifest.is_file():
        return {}
    document = json.loads(sql_manifest.read_text(encoding="utf-8-sig"))
    result: dict[str, list[dict[str, Any]]] = {}
    for binary in document.get("binaries", []):
        for statement in binary.get("statements", []):
            sql = str(statement.get("value", ""))
            match = TABLE_FROM_SQL.search(sql)
            if not match:
                continue
            table = match.group(1).lower()
            if not ITEM_TABLE.search(table) and table not in NATIVE_DEPENDENCY_TABLES:
                continue
            result.setdefault(table, []).append(
                {
                    "binary": binary.get("path"),
                    "binary_sha256": binary.get("sha256"),
                    "offset": statement.get("offset"),
                    "sha256": statement.get("sha256"),
                    "sql": sql,
                    "referenced_tables": sorted(
                        {
                            str(value).lower()
                            for value in statement.get("tables", [])
                        }
                    ),
                }
            )
    for values in result.values():
        values.sort(key=lambda entry: (
            str(entry.get("binary", "")),
            int(entry.get("offset") or 0),
            str(entry.get("sql", "")),
        ))
    return result


def load_static_layout_registry(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    shared_evidence = {
        "authority": document.get("authority"),
        "ghidra": document.get("ghidra", {}),
        "registry_path": path.resolve().as_posix(),
        "schema_version": document.get("schema_version"),
    }
    stream = str(document.get("stream", "game11"))
    result: dict[str, dict[str, Any]] = {}
    for table_name, raw in sorted(document.get("tables", {}).items()):
        value = dict(raw)
        value["stream"] = stream
        value["evidence"] = {
            **shared_evidence,
            **dict(raw.get("evidence") or {}),
        }
        result[str(table_name).lower()] = value
    return result


def columns_from_select(sql: str) -> tuple[str, ...]:
    match = re.search(r"^\s*SELECT\s+(.*?)\s+FROM\s", sql, re.I | re.S)
    if not match:
        return ()
    return tuple(part.strip() for part in match.group(1).split(","))


def static_query_specs(
    registry: dict[str, dict[str, Any]],
    sql_by_table: dict[str, list[dict[str, Any]]],
    existing_tables: set[str],
) -> list[QuerySpec]:
    specs: list[QuerySpec] = []
    for table_name, value in sorted(registry.items()):
        if table_name in existing_tables:
            continue
        if value.get("status") != "confirmed_native_result":
            continue
        candidates = sql_by_table.get(table_name, [])
        if not candidates:
            continue
        exact_sql = value.get("sql")
        if exact_sql is None:
            statement = candidates[0]
        else:
            statement = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate.get("sql") == exact_sql
                ),
                None,
            )
            if statement is None:
                continue
        sql = str(statement["sql"])
        evidence = {
            **dict(value.get("evidence") or {}),
            "embedded_sql": {
                key: item
                for key, item in statement.items()
                if key != "sql"
            },
            "native_result_status": value["status"],
            "native_result_header": {
                "start": int(value["start"]),
                "rows": int(value["rows"]),
            },
        }
        if value.get("termination"):
            evidence["termination"] = str(value["termination"])
        if value.get("string_cache_calibrations"):
            evidence["string_cache_calibrations"] = list(
                value["string_cache_calibrations"]
            )
        if value.get("unresolved_scope_exclusions"):
            evidence["unresolved_scope_exclusions"] = list(
                value["unresolved_scope_exclusions"]
            )
        for key in (
            "entity_kind",
            "id_column",
            "id_scope_authority",
            "result_absence_evidence",
        ):
            if value.get(key) is not None:
                evidence[key] = value[key]
        specs.append(
            QuerySpec(
                table_name=table_name,
                source_module=str(
                    (value.get("evidence") or {}).get(
                        "registry_path",
                        "item_forensics/config/static-layouts.json",
                    )
                ),
                columns=columns_from_select(sql),
                layout=tuple(str(value["layout"]).split()),
                stream_name=str(value["stream"]),
                start=int(value["start"]),
                expected_rows=int(value["rows"]),
                loader_consumer=f"x2game.dll FUN_{value['loader']}",
                sql_text=sql,
                evidence=evidence,
            )
        )
    return specs


def attach_sql(
    specs: list[QuerySpec],
    sql_by_table: dict[str, list[dict[str, Any]]],
) -> list[QuerySpec]:
    result: list[QuerySpec] = []
    for spec in specs:
        candidates = sql_by_table.get(_base_table(spec.table_name).lower(), [])
        sql_text = spec.sql_text
        evidence = dict(spec.evidence or {})
        if candidates:
            chosen = candidates[0]
            sql_text = str(chosen["sql"])
            evidence["embedded_sql"] = {
                key: value
                for key, value in chosen.items()
                if key != "sql"
            }
        result.append(
            QuerySpec(
                **{
                    **spec.__dict__,
                    "sql_text": sql_text,
                    "evidence": evidence,
                }
            )
        )
    return result


def serialize_spec(spec: QuerySpec) -> dict[str, Any]:
    return {
        "anchor": (
            {
                "id": spec.anchor_id,
                "values": spec.anchor_values or {},
            }
            if spec.anchor_id is not None
            else None
        ),
        "columns": list(spec.columns),
        "evidence": spec.evidence or {},
        "expected_rows": spec.expected_rows,
        "layout": list(spec.layout),
        "loader_consumer": spec.loader_consumer,
        "source_module": spec.source_module,
        "sql": spec.sql_text,
        "start": spec.start,
        "stream": spec.stream_name,
        "table": spec.table_name,
    }


def registry_digest(specs: list[QuerySpec]) -> str:
    import hashlib

    payload = canonical_json([serialize_spec(spec) for spec in specs]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()
