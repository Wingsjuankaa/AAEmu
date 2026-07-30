from __future__ import annotations

import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import canonical_json


DECODED_TABLES = ("actor_models", "models", "npcs")

APPEARANCE_SPECS: dict[str, dict[str, Any]] = {
    "face_decal_assets": {
        "columns": (
            "id asset_path category_id defaultX defaultY display_order icon_id "
            "is_new item_id model_id movable npc_only odd_eye_info"
        ).split(),
        "layout": "68 78 68 68 68 68 68 38 68 68 38 38 78".split(),
        "start": 0x56A25EB,
        "done": 0x56CB359,
        "rows": 1797,
        "first_string_reference": 245780,
        "next_string_reference": 246990,
        "loader": "x2game.dll FUN_39a3f9d0",
        "sql_address": "0x39df84d0",
    },
    "custom_face_presets": {
        "columns": (
            "id display_order face_morph_type_id icon_id model_id modifier"
        ).split(),
        "layout": "68 68 68 68 68 blob:128".split(),
        "start": 0x56CB35F,
        "done": 0x56DBFB8,
        "rows": 449,
        "first_string_reference": None,
        "next_string_reference": None,
        "loader": "x2game.dll FUN_39a3fde0",
        "sql_address": "0x39e00690",
    },
    "total_character_customs": {
        "columns": (
            "id body_normal_map_id body_normal_map_weight body_id deco_color "
            "default_hair_color display_order eyebrow_color face_diffuse_map_id "
            "face_eyelash_map_id face_fixed_decal_asset_0_id "
            "face_fixed_decal_asset_0_weight face_fixed_decal_asset_1_id "
            "face_fixed_decal_asset_1_weight face_fixed_decal_asset_2_id "
            "face_fixed_decal_asset_2_weight face_fixed_decal_asset_3_id "
            "face_fixed_decal_asset_3_weight face_fixed_decal_asset_4_id "
            "face_fixed_decal_asset_4_weight face_fixed_decal_asset_5_id "
            "face_fixed_decal_asset_5_weight face_movable_decal_asset_id "
            "face_movable_decal_move_x face_movable_decal_move_y "
            "face_movable_decal_rotate face_movable_decal_scale "
            "face_movable_decal_weight face_normal_map_id face_normal_map_weight "
            "face_id hair_color_id hair_id horn_color_id horn_id icon_id "
            "left_pupil_color lip_color model_id modifier npcOnly owner_type_id "
            "right_pupil_color skin_color_id two_tone_first_width "
            "two_tone_hair_color two_tone_second_width"
        ).split(),
        "layout": (
            "68 68 60 68 68 68 68 68 68 68 68 60 68 60 68 60 68 60 "
            "68 60 68 60 68 68 68 60 60 60 68 60 68 68 68 68 68 68 "
            "68 68 68 blob:128 38 68 68 68 60 68 60"
        ).split(),
        "start": 0x56DBFBE,
        "done": 0x576620A,
        "rows": 1546,
        "first_string_reference": None,
        "next_string_reference": None,
        "loader": "x2game.dll FUN_39a400d0",
        "sql_address": "0x39e007a0",
    },
}

APPEARANCE_AUXILIARY_SPECS: dict[str, dict[str, Any]] = {
    "body_diffuse_maps": {
        "columns": "id diffuse model_id name".split(),
        "layout": "68 78 68 78".split(),
        "header": 138013916,
        "start": 138013921,
        "done": 138014120,
        "rows": 2,
        "loader": "x2game.dll FUN_39a065d0",
        "task": "body_diffuse_maps@defb78",
        "asset_columns": ("diffuse",),
    },
    "body_normal_maps": {
        "columns": (
            "id display_order icon_id is_new model_id name normal npc_only specular"
        ).split(),
        "layout": "68 68 68 38 68 78 78 38 78".split(),
        "header": 138014121,
        "start": 138014126,
        "done": 138017774,
        "rows": 27,
        "loader": "x2game.dll FUN_39a06880",
        "task": "body_normal_maps@defbc0",
        "asset_columns": ("normal", "specular"),
    },
    "face_diffuse_maps": {
        "columns": "id diffuse model_id name npc_only".split(),
        "layout": "68 78 68 78 38".split(),
        "header": 138017775,
        "start": 138017780,
        "done": 138017780,
        "rows": 0,
        "loader": "x2game.dll FUN_39a06c20",
        "task": "face_diffuse_maps@defc30",
        "asset_columns": ("diffuse",),
    },
    "face_normal_maps": {
        "columns": (
            "id display_order icon_id is_new model_id name normal npc_only specular"
        ).split(),
        "layout": "68 68 68 38 68 78 78 38 78".split(),
        "header": 138017781,
        "start": 138017786,
        "done": 138033146,
        "rows": 138,
        "loader": "x2game.dll FUN_39a06f20",
        "task": "face_normal_maps@defc80",
        "asset_columns": ("normal", "specular"),
    },
    "face_eyelash_maps": {
        "columns": "id eyelash model_id name npc_only".split(),
        "layout": "68 78 68 78 38".split(),
        "header": 138033147,
        "start": 138033152,
        "done": 138033152,
        "rows": 0,
        "loader": "x2game.dll FUN_39a072c0",
        "task": "face_eyelash_maps@defcf0",
        "asset_columns": ("eyelash",),
    },
    "customizing_item_assets": {
        "columns": (
            "item_id category_id display_order is_new model_id two_tone use_pallet"
        ).split(),
        "layout": "68 68 68 38 68 38 38".split(),
        "header": 138664626,
        "start": 138664632,
        "done": 138673352,
        "rows": 436,
        "loader": "x2game.dll FUN_39a12910",
        "task": "customizing_item_assets@df4ed0",
        "asset_columns": (),
    },
    "custom_hair_textures": {
        "columns": (
            "id diffuse_texture mask_texture normal_texture specular_texture"
        ).split(),
        "layout": "68 78 78 78 78".split(),
        "header": 138704600,
        "start": 138704606,
        "done": 138706066,
        "rows": 5,
        "loader": "x2game.dll FUN_39a01ca0",
        "task": "custom_hair_textures@df00a0",
        "asset_columns": (
            "diffuse_texture",
            "mask_texture",
            "normal_texture",
            "specular_texture",
        ),
        "first_string_reference": 394516,
        "next_string_reference": 394532,
    },
}

ABSENT_APPEARANCE_SPECS: dict[str, dict[str, Any]] = {
    "customizing_item_asset_colors": {
        "columns": (
            "id asset_id category_id default_hair_color display_order "
            "hair_base_color_r hair_base_color_g hair_base_color_b icon_id "
            "material model_id two_tone_first_width two_tone_hair_color "
            "two_tone_second_width"
        ).split(),
        "layout": "68 68 68 68 68 68 68 68 68 78 68 60 68 60".split(),
        "loader": "x2game.dll FUN_39952f80",
        "task": "customizing_item_asset_colors@dd0600",
        "call_index": 273,
    },
    "skin_colors": {
        "columns": (
            "id bright_skin_color_r bright_skin_color_g bright_skin_color_b "
            "comment custom_postfix diffuse_color_r diffuse_color_g "
            "diffuse_color_b display_order glossness icon_id "
            "middle_skin_color_r middle_skin_color_g middle_skin_color_b "
            "model_id npc_only specular_color_r specular_color_g "
            "specular_color_b specular_level"
        ).split(),
        "layout": (
            "68 68 68 68 78 78 68 68 68 68 68 68 68 68 68 68 38 "
            "68 68 68 60"
        ).split(),
        "loader": "x2game.dll FUN_399533d0",
        "task": "skin_colors@dd0700",
        "call_index": 274,
    },
}

_APPEARANCE_MAP_BOOTSTRAP = {
    "columns": "id comments farm_group_id guard_time name".split(),
    "layout": "68 78 68 68 78".split(),
    "header": 138011833,
    "start": 138011838,
    "done": 138013915,
    "rows": 46,
    "first_string_reference": 392878,
    "next_string_reference": 392923,
}

_ATTACH_ANIMS_STRING_SEED = {
    "columns": "owner_type owner_id anim_action_id attach_point_id".split(),
    "layout": "78 68 68 68".split(),
    "start": 0x3D6B679,
    "done": 0x3D6CABE,
    "rows": 287,
    "first_string_reference": 150126,
    "next_string_reference": 150128,
    "loader": "x2game.dll FUN_39a46b50",
}


@dataclass(frozen=True)
class DecodedResult:
    table: str
    rows: list[dict[str, Any]]
    start: int
    done: int
    digest: str
    token_counts: dict[str, int]
    unresolved_references: dict[int, int]
    resolution_evidence: dict[str, Any]


@dataclass(frozen=True)
class FaceTargetProfile:
    profile_key: str
    race: str
    gender: str
    code: str
    relative_path: str
    assets: tuple[dict[str, Any], ...]
    targets: tuple[dict[str, Any], ...]


_ACTOR_FACE_PROFILE = re.compile(
    r"(?:^|/)objects/characters/(?P<race>[^/]+)/(?P<gender>[^/]+)/",
    re.IGNORECASE,
)


def face_profile_key_from_model_file(model_file: str) -> str | None:
    """Derive the native face-target profile from an ActorModel CDF path."""

    normalized = model_file.replace("\\", "/").lower()
    match = _ACTOR_FACE_PROFILE.search(normalized)
    if match is None:
        return None
    return f"{match.group('race')}/{match.group('gender')}"


def _xml_scalar(value: str) -> int | float | str:
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def load_face_target_profiles(xml_root: Path) -> dict[str, FaceTargetProfile]:
    """Load every race/gender face-target profile from extracted game_pak XML."""

    base = xml_root / "game" / "objects" / "characters"
    paths = sorted(
        base.glob("*/*/face/*_targets.xml"),
        key=lambda value: value.as_posix().lower(),
    )
    if len(paths) != 12:
        raise ValueError(f"Expected 12 face-target profiles, got {len(paths)}")
    profiles: dict[str, FaceTargetProfile] = {}
    for path in paths:
        race = path.parent.parent.parent.name.lower()
        gender = path.parent.parent.name.lower()
        profile_key = f"{race}/{gender}"
        root = ET.parse(path).getroot()
        if root.tag != "FaceMaker":
            raise ValueError(f"Unexpected face-target root in {path}: {root.tag}")
        assets: list[dict[str, Any]] = []
        for child in root:
            if not child.tag.startswith("Asset"):
                continue
            assets.append(
                {
                    "slot": int(child.tag[5:]),
                    **{
                        key: _xml_scalar(value)
                        for key, value in sorted(child.attrib.items())
                    },
                }
            )
        targets: list[dict[str, Any]] = []
        target_root = root.find("Targets")
        if target_root is None:
            raise ValueError(f"Missing Targets element in {path}")
        for child in target_root.findall("Target"):
            target = {
                key: _xml_scalar(value)
                for key, value in sorted(child.attrib.items())
            }
            if "Idx" not in target or "Name" not in target:
                raise ValueError(f"Target without Idx/Name in {path}")
            index = int(target["Idx"])
            if not 1 <= index < 128:
                raise ValueError(f"Target index {index} outside int8[128] in {path}")
            targets.append(target)
        targets.sort(key=lambda value: int(value["Idx"]))
        indices = [int(value["Idx"]) for value in targets]
        if len(indices) != len(set(indices)):
            raise ValueError(f"Duplicate target index in {path}")
        if profile_key in profiles:
            raise ValueError(f"Duplicate face-target profile {profile_key}")
        profiles[profile_key] = FaceTargetProfile(
            profile_key=profile_key,
            race=race,
            gender=gender,
            code=path.stem.removesuffix("_targets"),
            relative_path=path.relative_to(xml_root).as_posix(),
            assets=tuple(assets),
            targets=tuple(targets),
        )
    return dict(sorted(profiles.items()))


def decode_signed_modifier(blob: dict[str, Any]) -> tuple[int, ...]:
    """Decode the exact CustomModel modifier payload as signed int8[128]."""

    if int(blob.get("bytes", 0)) != 128 or blob.get("encoding") != "hex":
        raise ValueError("Expected a 128-byte hexadecimal modifier payload")
    payload = bytes.fromhex(str(blob["value"]))
    if len(payload) != 128:
        raise ValueError(f"Expected 128 modifier bytes, got {len(payload)}")
    return tuple(value if value < 128 else value - 256 for value in payload)


class CachedResultReader:
    """Strict reader for the primitive cached-result ABI used by game11."""

    def __init__(self, data: bytes, first_string_reference: int | None):
        self.data = data
        self.cache: dict[int, str] = {}
        self.next_reference = first_string_reference
        self.tokens: Counter[str] = Counter()
        self.unresolved: Counter[int] = Counter()

    def _string(self, offset: int) -> tuple[str | None, int]:
        tag = self.data[offset]
        offset += 1
        if tag == 2:
            self.tokens["null"] += 1
            return None, offset
        if tag == 0:
            end = self.data.index(0, offset)
            self.tokens["literal"] += 1
            return self.data[offset:end].decode("utf-8", "replace"), end + 1
        reference = struct.unpack_from("<I", self.data, offset)[0]
        offset += 4
        if reference == 0xFFFFFFFF:
            end = self.data.index(0, offset)
            value = self.data[offset:end].decode("utf-8", "replace")
            self.tokens["insert"] += 1
            if self.next_reference is not None:
                self.cache[self.next_reference] = value
                self.next_reference += 1
            return value, end + 1
        self.tokens["reference"] += 1
        if reference in self.cache:
            self.tokens["resolved_reference"] += 1
            return self.cache[reference], offset
        self.tokens["unresolved_reference"] += 1
        self.unresolved[reference] += 1
        return f"<ref:{reference}>", offset

    def row(self, offset: int, layout: list[str]) -> tuple[list[Any], int]:
        if self.data[offset] != 100:
            raise ValueError(f"Expected SQLITE_ROW at 0x{offset:X}")
        offset += 1
        values: list[Any] = []
        for field_type in layout:
            if field_type == "38":
                values.append(self.data[offset])
                offset += 1
            elif field_type == "68":
                values.append(struct.unpack_from("<i", self.data, offset)[0])
                offset += 4
            elif field_type in {"40", "70"}:
                values.append(struct.unpack_from("<q", self.data, offset)[0])
                offset += 8
            elif field_type == "60":
                values.append(struct.unpack_from("<d", self.data, offset)[0])
                offset += 8
            elif field_type == "78":
                value, offset = self._string(offset)
                values.append(value)
            elif field_type.startswith("blob:"):
                expected = int(field_type.split(":", 1)[1])
                length = struct.unpack_from("<I", self.data, offset)[0]
                offset += 4
                if length != expected:
                    raise ValueError(
                        f"Expected {expected}-byte blob, got {length} "
                        f"at 0x{offset - 4:X}"
                    )
                value = self.data[offset : offset + length]
                if len(value) != length:
                    raise ValueError(f"Truncated blob at 0x{offset:X}")
                offset += length
                values.append(
                    {
                        "bytes": length,
                        "encoding": "hex",
                        "sha256": hashlib.sha256(value).hexdigest().upper(),
                        "value": value.hex().upper(),
                    }
                )
            else:
                raise ValueError(f"Unsupported cached-result field type {field_type}")
        return values, offset


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _decode_attach_anims_string_seed(
    data: bytes,
) -> tuple[dict[int, str], dict[str, Any]]:
    """Recover the two model subtype strings from their native producer."""

    spec = _ATTACH_ANIMS_STRING_SEED
    reader = CachedResultReader(data, int(spec["first_string_reference"]))
    cursor = int(spec["start"])
    rows = 0
    while cursor < len(data) and data[cursor] == 100:
        _, cursor = reader.row(cursor, list(spec["layout"]))
        rows += 1
    if cursor != int(spec["done"]) or data[cursor] != 101:
        raise ValueError(
            "attach_anims string seed has an unexpected SQLITE_DONE boundary"
        )
    if rows != int(spec["rows"]):
        raise ValueError(
            f"attach_anims string seed expected {spec['rows']} rows, got {rows}"
        )
    if reader.next_reference != int(spec["next_string_reference"]):
        raise ValueError("attach_anims string seed endpoint mismatch")
    expected = {150126: "VehicleModel", 150127: "ShipModel"}
    actual = {key: reader.cache.get(key) for key in expected}
    if actual != expected:
        raise ValueError(f"attach_anims string seed changed: {actual}")
    if reader.unresolved:
        raise ValueError(
            f"attach_anims string seed has unresolved refs: {reader.unresolved}"
        )
    return expected, {
        "source_table": "attach_anims",
        "loader": spec["loader"],
        "start": spec["start"],
        "done": spec["done"],
        "rows": rows,
        "first_reference": spec["first_string_reference"],
        "next_reference": spec["next_string_reference"],
        "self_references_resolved": reader.tokens["resolved_reference"],
        "values": expected,
    }


def decode_catalog(game11: Path, catalog_manifest: Path) -> dict[str, DecodedResult]:
    manifest = load_json(catalog_manifest)
    data = game11.read_bytes()
    external_seed, seed_evidence = _decode_attach_anims_string_seed(data)
    decoded: dict[str, DecodedResult] = {}
    for table in DECODED_TABLES:
        spec = manifest["tables"][table]
        columns = [str(value) for value in spec["columns"]]
        layout = [str(value) for value in spec["layout"]]
        cached = spec["cached_result"]
        start = int(str(cached["start_hex"]), 16)
        done = int(str(cached["done_hex"]), 16)
        expected_rows = int(cached["row_count"])
        reader = CachedResultReader(
            data,
            (
                int(spec["string_cache"]["first_reference"])
                if spec["string_cache"]["first_reference"] is not None
                else None
            ),
        )
        cursor = start
        rows: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        while cursor < len(data) and data[cursor] == 100:
            values, cursor = reader.row(cursor, layout)
            row = dict(zip(columns, values, strict=True))
            encoded = canonical_json(row).encode("utf-8")
            digest.update(encoded)
            digest.update(b"\n")
            rows.append(row)
        if cursor != done or data[cursor] != 101:
            raise ValueError(
                f"{table}: expected SQLITE_DONE at 0x{done:X}, got 0x{cursor:X}"
            )
        if len(rows) != expected_rows:
            raise ValueError(
                f"{table}: expected {expected_rows} rows, got {len(rows)}"
            )
        actual_digest = digest.hexdigest().upper()
        expected_digest = str(cached["canonical_rows_sha256"]).upper()
        if actual_digest != expected_digest:
            raise ValueError(
                f"{table}: canonical digest mismatch "
                f"{actual_digest} != {expected_digest}"
            )
        externally_resolved: Counter[int] = Counter()
        for row in rows:
            for column, value in tuple(row.items()):
                if not unresolved_reference(value):
                    continue
                reference = int(value[5:-1])
                if reference not in external_seed:
                    continue
                row[column] = external_seed[reference]
                externally_resolved[reference] += 1
        remaining_unresolved = Counter(reader.unresolved)
        remaining_unresolved.subtract(externally_resolved)
        remaining_unresolved = Counter(
            {
                key: value
                for key, value in remaining_unresolved.items()
                if value > 0
            }
        )
        token_counts = Counter(reader.tokens)
        token_counts["externally_resolved_reference"] += sum(
            externally_resolved.values()
        )
        decoded[table] = DecodedResult(
            table=table,
            rows=rows,
            start=start,
            done=done,
            digest=actual_digest,
            token_counts=dict(sorted(token_counts.items())),
            unresolved_references=dict(sorted(remaining_unresolved.items())),
            resolution_evidence=(
                {
                    "external_string_seed": seed_evidence,
                    "resolved_occurrences": dict(
                        sorted(externally_resolved.items())
                    ),
                }
                if externally_resolved
                else {}
            ),
        )
    return decoded


def decode_appearance(game11: Path) -> dict[str, DecodedResult]:
    data = game11.read_bytes()
    decoded: dict[str, DecodedResult] = {}
    for table, spec in APPEARANCE_SPECS.items():
        reader = CachedResultReader(data, spec["first_string_reference"])
        cursor = int(spec["start"])
        rows: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        while cursor < len(data) and data[cursor] == 100:
            values, cursor = reader.row(cursor, list(spec["layout"]))
            row = dict(zip(spec["columns"], values, strict=True))
            encoded = canonical_json(row).encode("utf-8")
            digest.update(encoded)
            digest.update(b"\n")
            rows.append(row)
        if cursor != int(spec["done"]) or data[cursor] != 101:
            raise ValueError(
                f"{table}: expected SQLITE_DONE at 0x{spec['done']:X}, "
                f"got 0x{cursor:X}"
            )
        if len(rows) != int(spec["rows"]):
            raise ValueError(
                f"{table}: expected {spec['rows']} rows, got {len(rows)}"
            )
        expected_next = spec["next_string_reference"]
        if expected_next is not None and reader.next_reference != expected_next:
            raise ValueError(
                f"{table}: string cache ended at {reader.next_reference}, "
                f"expected {expected_next}"
            )
        if reader.unresolved:
            raise ValueError(
                f"{table}: unresolved string references "
                f"{dict(sorted(reader.unresolved.items()))}"
            )
        decoded[table] = DecodedResult(
            table=table,
            rows=rows,
            start=int(spec["start"]),
            done=int(spec["done"]),
            digest=digest.hexdigest().upper(),
            token_counts=dict(sorted(reader.tokens.items())),
            unresolved_references={},
            resolution_evidence={},
        )
    return decoded


def _decode_exact_result(
    *,
    data: bytes,
    reader: CachedResultReader,
    table: str,
    spec: dict[str, Any],
) -> DecodedResult:
    token_before = Counter(reader.tokens)
    unresolved_before = Counter(reader.unresolved)
    cursor = int(spec["start"])
    rows: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, list(spec["layout"]))
        row = dict(zip(spec["columns"], values, strict=True))
        encoded = canonical_json(row).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        rows.append(row)
    if cursor != int(spec["done"]) or data[cursor] != 101:
        raise ValueError(
            f"{table}: expected SQLITE_DONE at 0x{spec['done']:X}, "
            f"got 0x{cursor:X}"
        )
    if len(rows) != int(spec["rows"]):
        raise ValueError(f"{table}: expected {spec['rows']} rows, got {len(rows)}")
    token_delta = Counter(reader.tokens)
    token_delta.subtract(token_before)
    unresolved_delta = Counter(reader.unresolved)
    unresolved_delta.subtract(unresolved_before)
    return DecodedResult(
        table=table,
        rows=rows,
        start=int(spec["start"]),
        done=int(spec["done"]),
        digest=digest.hexdigest().upper(),
        token_counts={
            key: value for key, value in sorted(token_delta.items()) if value
        },
        unresolved_references={
            key: value for key, value in sorted(unresolved_delta.items()) if value
        },
        resolution_evidence={},
    )


def decode_appearance_auxiliary(game11: Path) -> dict[str, DecodedResult]:
    """Decode the exact native appearance-map and item-customization results."""

    data = game11.read_bytes()
    reader = CachedResultReader(
        data, _APPEARANCE_MAP_BOOTSTRAP["first_string_reference"]
    )
    bootstrap = _decode_exact_result(
        data=data,
        reader=reader,
        table="common_farms_string_cache_bootstrap",
        spec=_APPEARANCE_MAP_BOOTSTRAP,
    )
    if reader.next_reference != _APPEARANCE_MAP_BOOTSTRAP["next_string_reference"]:
        raise ValueError("Appearance-map string-cache bootstrap endpoint mismatch")
    if bootstrap.unresolved_references != {287446: 37, 287451: 8}:
        raise ValueError(
            "Appearance-map bootstrap references changed: "
            f"{bootstrap.unresolved_references}"
        )

    decoded: dict[str, DecodedResult] = {}
    for table in (
        "body_diffuse_maps",
        "body_normal_maps",
        "face_diffuse_maps",
        "face_normal_maps",
        "face_eyelash_maps",
    ):
        result = _decode_exact_result(
            data=data,
            reader=reader,
            table=table,
            spec=APPEARANCE_AUXILIARY_SPECS[table],
        )
        if result.unresolved_references:
            raise ValueError(
                f"{table}: unresolved references {result.unresolved_references}"
            )
        decoded[table] = result
    if reader.next_reference != 393140:
        raise ValueError(
            "Appearance-map string cache ended at "
            f"{reader.next_reference}, expected 393140"
        )

    asset_spec = APPEARANCE_AUXILIARY_SPECS["customizing_item_assets"]
    decoded["customizing_item_assets"] = _decode_exact_result(
        data=data,
        reader=CachedResultReader(data, None),
        table="customizing_item_assets",
        spec=asset_spec,
    )
    hair_spec = APPEARANCE_AUXILIARY_SPECS["custom_hair_textures"]
    hair_reader = CachedResultReader(data, hair_spec["first_string_reference"])
    decoded["custom_hair_textures"] = _decode_exact_result(
        data=data,
        reader=hair_reader,
        table="custom_hair_textures",
        spec=hair_spec,
    )
    if hair_reader.next_reference != hair_spec["next_string_reference"]:
        raise ValueError("Custom-hair string-cache endpoint mismatch")
    if decoded["custom_hair_textures"].unresolved_references:
        raise ValueError("Custom-hair textures contain unresolved references")
    return decoded


def audit_absent_appearance_results(stream_dir: Path) -> dict[str, Any]:
    """Prove that the two referenced color layouts have no non-empty result."""

    streams: dict[str, Any] = {}
    matches: dict[str, list[dict[str, int | str]]] = {
        table: [] for table in ABSENT_APPEARANCE_SPECS
    }
    for path in sorted(
        stream_dir.glob("game*"),
        key=lambda value: int(value.name[4:]),
    ):
        data = path.read_bytes()
        header_count = 0
        cursor = 0
        while True:
            header = data.find(b"\x65\x64", cursor)
            if header < 0:
                break
            cursor = header + 1
            if header + 7 > len(data):
                continue
            row_count = struct.unpack_from("<I", data, header + 2)[0]
            start = header + 6
            if row_count > 50000 or (
                row_count > 0 and data[start] != 100
            ) or (row_count == 0 and data[start] != 101):
                continue
            header_count += 1
            if row_count == 0:
                continue
            for table, spec in ABSENT_APPEARANCE_SPECS.items():
                reader = CachedResultReader(data, None)
                result_cursor = start
                try:
                    for _ in range(row_count):
                        _, result_cursor = reader.row(
                            result_cursor, list(spec["layout"])
                        )
                except (IndexError, ValueError, struct.error):
                    continue
                if result_cursor < len(data) and data[result_cursor] == 101:
                    matches[table].append(
                        {
                            "stream": path.name,
                            "header": header,
                            "start": start,
                            "done": result_cursor,
                            "rows": row_count,
                        }
                    )
        streams[path.name] = {
            "bytes": len(data),
            "non_empty": bool(data),
            "structural_result_headers": header_count,
        }
    return {
        "streams": streams,
        "tables": {
            table: {
                "exact_layout_matches": values,
                "exact_layout_match_count": len(values),
            }
            for table, values in sorted(matches.items())
        },
        "game11_execution_slot": {
            "previous_result": "character_equip_packs",
            "previous_done": 100995039,
            "next_result_header": 100995040,
            "next_result_start": 100995045,
            "next_result_rows": 12740,
            "missing_call_indices": [273, 274],
            "classification": "no cached result emitted between adjacent boundaries",
        },
    }


def unresolved_reference(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("<ref:") and value.endswith(">")
