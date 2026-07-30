from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable


def canonical_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + "\n"
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonicalize_json_text(value: str | None) -> str:
    if value in (None, ""):
        return "{}"
    try:
        return canonical_json(json.loads(value))
    except (TypeError, ValueError):
        return canonical_json({"opaque_text": value})


def sha256_file(path: Path, *, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def tree_digest(root: Path, patterns: tuple[str, ...] = ("*.py", "*.json")) -> str:
    entries: list[dict[str, str]] = []
    for pattern in patterns:
        for path in sorted(root.rglob(pattern), key=lambda item: item.as_posix()):
            if path.is_file():
                entries.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "sha256": sha256_file(path),
                    }
                )
    return sha256_text(canonical_json(entries))


def entity_key(kind: str, native_id: Any) -> str:
    return f"{str(kind).strip().lower()}:{str(native_id).strip()}"


def stable_key(namespace: str, *parts: Any) -> str:
    payload = canonical_json([namespace, *parts])
    return f"{namespace}:{sha256_text(payload)[:32].lower()}"


def typed_value(value: Any) -> tuple[str, str | None, int | None, float | None, int | None, str | None]:
    if value is None:
        return ("null", None, None, None, None, "null")
    if isinstance(value, bool):
        return ("boolean", None, None, None, int(value), None)
    if isinstance(value, int):
        return ("integer", None, value, None, None, None)
    if isinstance(value, float):
        return ("real", None, None, value, None, None)
    if isinstance(value, str):
        return ("text", value, None, None, None, None)
    return ("json", None, None, None, None, canonical_json(value))


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        temporary.write_text(value, encoding="utf-8", newline="\n")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def chunks(values: Iterable[Any], size: int = 5000) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for value in values:
        batch.append(value)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
