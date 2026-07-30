from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .schema import open_read_only


STRONG_STATES = {"confirmed", "tombstone"}
NON_RESOLVING_AUTHORITIES = {
    "client_reference",
    "historical_structure",
    "server_observed",
    "wiki_visible",
}
NATIVE_RELATION_PROVENANCE = {
    "client_compact_8",
    "game11_native",
    "x2game_confirmed",
}
ASSET_REFERENCE_PROVENANCE = {
    "client_filesystem",
    "game_pak",
    "gamepak_lua_decompiled",
    "gamepak_xml_extracted",
}


@dataclass(frozen=True)
class EntityObservation:
    stage: int
    state: str
    lifecycle: str
    authority: str
    provenance: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "authority": self.authority,
            "lifecycle": self.lifecycle,
            "provenance": self.provenance,
            "stage": self.stage,
            "state": self.state,
        }


@dataclass(frozen=True)
class EntityResolution:
    entity_key: str
    state: str
    observations: tuple[EntityObservation, ...]

    @property
    def stages(self) -> tuple[int, ...]:
        return tuple(sorted({value.stage for value in self.observations}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "observations": [value.as_dict() for value in self.observations],
            "resolved_state": self.state,
            "stages": list(self.stages),
        }


def relation_can_close_from_destination(
    *,
    authority: str,
    provenance: str,
) -> bool:
    return (
        authority == "client_native"
        or provenance in NATIVE_RELATION_PROVENANCE
    )


def relation_is_asset_corroboration(
    *,
    authority: str,
    provenance: str,
) -> bool:
    return (
        authority in {"client_asset", "client_reference"}
        and provenance in ASSET_REFERENCE_PROVENANCE
    )


def _candidate_entity_keys(source: sqlite3.Connection) -> set[str]:
    keys = {
        str(row[0])
        for row in source.execute(
            """
            SELECT entity_key FROM gaps
            WHERE blocker_code IN (
                'referenced_endpoint_not_in_decoded_stages',
                'referenced_endpoint_not_in_prior_stages'
            )
            """
        )
    }
    keys.update(
        str(row[0])
        for row in source.execute(
            """
            SELECT DISTINCT dst_entity_key FROM relations
            WHERE state IN ('blocked','missing','opaque','unknown')
            """
        )
    )
    keys.update(
        str(row[0])
        for row in source.execute(
            """
            SELECT entity_key FROM entities
            WHERE state IN ('blocked','missing','opaque','unknown')
              AND lifecycle NOT IN ('localization_only','tombstone')
            """
        )
    )
    return keys


def _observation_is_strong(row: sqlite3.Row) -> bool:
    return (
        str(row["state"]) in STRONG_STATES
        and str(row["authority"]) not in NON_RESOLVING_AUTHORITIES
    )


class CrossStageResolver:
    def __init__(
        self,
        resolutions: dict[str, EntityResolution],
        *,
        candidate_count: int,
    ) -> None:
        self._resolutions = resolutions
        self.candidate_count = candidate_count

    @classmethod
    def from_stage_databases(
        cls,
        source: sqlite3.Connection,
        stage_paths: Iterable[tuple[int, Path]],
    ) -> "CrossStageResolver":
        candidates = _candidate_entity_keys(source)
        observations: dict[str, list[EntityObservation]] = defaultdict(list)
        for stage, path in sorted(stage_paths):
            connection = open_read_only(path)
            try:
                rows = connection.execute(
                    """
                    SELECT entity_key,state,lifecycle,authority,provenance
                    FROM entities
                    WHERE state IN ('confirmed','tombstone')
                    ORDER BY entity_key
                    """
                )
                for row in rows:
                    entity_key = str(row["entity_key"])
                    if (
                        entity_key not in candidates
                        or not _observation_is_strong(row)
                    ):
                        continue
                    observations[entity_key].append(
                        EntityObservation(
                            stage=stage,
                            state=str(row["state"]),
                            lifecycle=str(row["lifecycle"]),
                            authority=str(row["authority"]),
                            provenance=str(row["provenance"]),
                        )
                    )
            finally:
                connection.close()

        resolutions: dict[str, EntityResolution] = {}
        for entity_key, values in sorted(observations.items()):
            states = {value.state for value in values}
            if len(states) != 1:
                raise RuntimeError(
                    "Conflicting strong cross-stage states for "
                    f"{entity_key}: {sorted(states)}"
                )
            ordered = tuple(
                sorted(
                    values,
                    key=lambda value: (
                        value.stage,
                        value.authority,
                        value.lifecycle,
                        value.provenance,
                    ),
                )
            )
            resolutions[entity_key] = EntityResolution(
                entity_key=entity_key,
                state=next(iter(states)),
                observations=ordered,
            )
        return cls(resolutions, candidate_count=len(candidates))

    def resolve(self, entity_key: str) -> EntityResolution | None:
        return self._resolutions.get(entity_key)

    @property
    def resolved_candidate_count(self) -> int:
        return len(self._resolutions)
