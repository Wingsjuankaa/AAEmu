from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _base_variables(repo_root: Path) -> dict[str, str]:
    workspace = repo_root.parent
    values = dict(os.environ)
    values.setdefault("AAEMU_REPO", str(repo_root))
    values.setdefault("AAEMU_WORKSPACE", str(workspace))
    values.setdefault("AAEMU_CLIENT", str(workspace / "client_kakao"))
    if "AAEMU_RESEARCH" not in values:
        manifest = (
            repo_root
            / "reconstruccion_character_8"
            / "generated"
            / "global-client-surfaces-v1-manifest.json"
        )
        if manifest.is_file():
            try:
                document = json.loads(manifest.read_text(encoding="utf-8-sig"))
                streams = document.get("cached_result_streams", [])
                first = Path(str(streams[0]["path"]))
                # .../AAEmu-Research/output/compact-8.0-extracted/gameN
                values["AAEMU_RESEARCH"] = str(first.parents[2])
            except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
    return values


def _expand(value: str, variables: dict[str, str]) -> str:
    missing: set[str] = set()

    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            missing.add(name)
            return match.group(0)
        return variables[name]

    expanded = VARIABLE.sub(substitute, value)
    if missing:
        raise ValueError(
            "Missing configuration environment variable(s): "
            + ", ".join(sorted(missing))
        )
    return expanded


def _path(value: str | None, variables: dict[str, str]) -> Path | None:
    if value is None:
        return None
    return Path(_expand(value, variables)).expanduser().resolve()


def read_dotenv_value(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return None


@dataclass(frozen=True)
class ForensicsConfig:
    client_build: str
    client_compact: Path
    streams_root: Path
    repo_root: Path
    legacy_item_root: Path
    output_dir: Path
    runtime_env: Path
    runtime: Path
    sql_manifest: Path | None
    surface_manifest: Path | None
    gamepak_index: Path | None
    x2game: tuple[Path, ...]

    @property
    def database(self) -> Path:
        return self.output_dir / "aa8-item-forensics.sqlite"

    @property
    def manifest(self) -> Path:
        return self.output_dir / "manifest.json"

    @property
    def wiki_cache_dir(self) -> Path:
        return self.output_dir / "wiki-cache"

    @property
    def wiki_database(self) -> Path:
        return self.output_dir / "aa8-wiki-corroboration.sqlite"

    @property
    def wiki_audit_report(self) -> Path:
        return self.output_dir / "wiki-audit.json"

    @property
    def wiki_audit_csv(self) -> Path:
        return self.output_dir / "wiki-audit.csv"

    @property
    def native_closure_report(self) -> Path:
        return self.output_dir / "native-closure-audit.json"

    @property
    def native_closure_csv(self) -> Path:
        return self.output_dir / "native-closure-audit.csv"

    def with_overrides(self, **overrides: Any) -> "ForensicsConfig":
        values = {
            key: value
            for key, value in overrides.items()
            if value is not None
        }
        if "x2game" in values:
            values["x2game"] = tuple(Path(p).resolve() for p in values["x2game"])
        for key in (
            "client_compact",
            "streams_root",
            "repo_root",
            "legacy_item_root",
            "output_dir",
            "runtime_env",
            "runtime",
            "sql_manifest",
            "surface_manifest",
            "gamepak_index",
        ):
            if key in values:
                values[key] = Path(values[key]).resolve()
        return replace(self, **values)

    def validate(self, require_runtime: bool = True) -> None:
        required_files = {
            "client compact": self.client_compact,
            "runtime .env": self.runtime_env,
        }
        if require_runtime:
            required_files["runtime compact"] = self.runtime
        for label, path in required_files.items():
            if not path.is_file():
                raise FileNotFoundError(f"{label} not found: {path}")
        if not self.streams_root.is_dir():
            raise FileNotFoundError(f"cached-result root not found: {self.streams_root}")
        if not self.repo_root.is_dir():
            raise FileNotFoundError(f"repository root not found: {self.repo_root}")


def load_config(path: Path | None = None) -> ForensicsConfig:
    repo = repository_root()
    config_path = (
        path.resolve()
        if path
        else Path(__file__).resolve().parent / "config" / "kakao-r558734.json"
    )
    document = json.loads(config_path.read_text(encoding="utf-8"))
    variables = _base_variables(repo)
    resolved_repo = _path(document["repo_root"], variables)
    assert resolved_repo is not None
    variables.update(_base_variables(resolved_repo))
    runtime_env = _path(document["runtime_env"], variables)
    assert runtime_env is not None
    runtime_text = read_dotenv_value(runtime_env, "COMPACT_DB")
    if not runtime_text:
        raise ValueError(f"COMPACT_DB is missing from {runtime_env}")
    runtime = Path(runtime_text)
    if not runtime.is_absolute():
        runtime = (resolved_repo / runtime).resolve()
    return ForensicsConfig(
        client_build=str(document["client_build"]),
        client_compact=_path(document["client_compact"], variables),  # type: ignore[arg-type]
        streams_root=_path(document["streams_root"], variables),  # type: ignore[arg-type]
        repo_root=resolved_repo,
        legacy_item_root=_path(document["legacy_item_root"], variables),  # type: ignore[arg-type]
        output_dir=_path(document["output_dir"], variables),  # type: ignore[arg-type]
        runtime_env=runtime_env,
        runtime=runtime.resolve(),
        sql_manifest=_path(document.get("sql_manifest"), variables),
        surface_manifest=_path(document.get("surface_manifest"), variables),
        gamepak_index=_path(document.get("gamepak_index"), variables),
        x2game=tuple(
            _path(value, variables)  # type: ignore[arg-type]
            for value in document.get("x2game", [])
        ),
    )
