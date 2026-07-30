from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "kakao-r558734.json"
)


@dataclass(frozen=True)
class ForensicsConfig:
    client_build: str
    output_dir: Path
    source_item_database: Path
    source_item_manifest: Path
    source_item_tool_root: Path
    source_cached_streams_dir: Path
    source_game11: Path
    source_client_compact: Path
    source_npc_catalog_manifest: Path
    source_character_data: Path
    source_character_manifest: Path
    source_faction_data: Path
    source_faction_manifest: Path
    source_spawner_layers_manifest: Path
    source_spawner_absence_manifest: Path
    source_ghidra_sql_loaders_64: Path
    source_ghidra_sql_call_sequence: Path
    source_ghidra_loot_loaders_x86: Path
    source_loot_loader_tasks: Path
    source_ghidra_item_grade_order_x64: Path
    source_ghidra_item_grade_order_x86: Path
    source_ghidra_item_grade_descriptor_x64: Path
    source_ghidra_item_grade_descriptor_x86: Path
    source_item_grade_loader_tasks: Path
    source_ghidra_item_grade_secondary_x64: Path
    source_ghidra_item_grade_secondary_x86: Path
    source_item_grade_secondary_loader_tasks: Path
    source_ghidra_item_guide_x64: Path
    source_ghidra_item_guide_x86: Path
    source_item_guide_loader_tasks: Path
    source_ghidra_tag_loaders_x64: Path
    source_ghidra_tag_loaders_x86: Path
    source_ghidra_tag_layouts_x64: Path
    source_ghidra_tag_layouts_x86: Path
    source_tag_loader_tasks: Path
    source_sql_surface_manifest: Path
    source_ghidra_quest_loaders_x86: Path
    source_quest_loader_tasks: Path
    source_ghidra_enum_consumers_x64: Path
    source_ghidra_enum_consumers_x86: Path
    source_ghidra_quest_bubble_callbacks_x64: Path
    source_ghidra_quest_component_struct_x64: Path
    source_ghidra_quest_scalar_api_x64: Path
    source_ghidra_quest_scalar_consumers_x64: Path
    source_ghidra_quest_scalar_consumers_x86: Path
    source_ghidra_component_accessor_context_x64: Path
    source_ghidra_component_accessor_context_x86: Path
    source_ghidra_component_text_vector_trace_x64: Path
    source_ghidra_component_text_vector_trace_x86: Path
    source_ghidra_component_text_data_x64: Path
    source_ghidra_component_text_data_x86: Path
    source_ghidra_ui_event_core_x64: Path
    source_ghidra_ui_event_core_x86: Path
    source_component_text_surface_snapshot: Path
    source_ghidra_npc_ai_field_trace_x64: Path
    source_ghidra_npc_ai_field_trace_x86: Path
    source_ghidra_npc_ai_forwarded_helpers_x64: Path
    source_ghidra_npc_ai_forwarded_helpers_x86: Path
    source_ghidra_npc_ai_raw_vector_x64: Path
    source_ghidra_npc_ai_raw_vector_x86: Path
    source_ghidra_quest_component_copy_x86: Path
    source_ghidra_npc_ai_lua_bindings_x64: Path
    source_ghidra_npc_ai_lua_bindings_x86: Path
    source_ghidra_npc_ai_script_stubs_x64: Path
    source_ghidra_npc_ai_script_stubs_x86: Path
    source_npc_ai_surface_snapshot: Path
    source_quest_wiki_cache: Path
    source_item_wiki_cache: Path
    source_skills_tool_root: Path
    source_ghidra_skill_loaders_x86: Path
    source_skill_loader_tasks: Path
    source_ghidra_world_interaction_loader_x86: Path
    source_ghidra_world_interaction_enum_x64: Path
    source_ghidra_world_interaction_enum_x86: Path
    source_world_interaction_loader_tasks: Path
    source_skill_wiki_cache: Path
    source_ghidra_asset_loaders_x86: Path
    source_asset_loader_tasks: Path
    source_ghidra_custom_model_x64: Path
    source_ghidra_custom_model_x86: Path
    source_gamepak_index: Path
    source_gamepak_xml_root: Path
    source_gamepak_lua64_root: Path
    source_gamepak_lua32_root: Path
    wiki_base_url: str
    wiki_locale: str

    @property
    def stage_00(self) -> Path:
        return self.output_dir / "stage-00-artifacts.sqlite"

    @property
    def stage_10(self) -> Path:
        return self.output_dir / "stage-10-native-data.sqlite"

    @property
    def stage_20(self) -> Path:
        return self.output_dir / "stage-20-items.sqlite"

    @property
    def stage_30(self) -> Path:
        return self.output_dir / "stage-30-world-actors.sqlite"

    @property
    def stage_40(self) -> Path:
        return self.output_dir / "stage-40-quests.sqlite"

    @property
    def stage_50(self) -> Path:
        return self.output_dir / "stage-50-skills.sqlite"

    @property
    def stage_60(self) -> Path:
        return self.output_dir / "stage-60-assets.sqlite"

    @property
    def stage_70(self) -> Path:
        return self.output_dir / "stage-70-wiki.sqlite"

    @property
    def stage_90(self) -> Path:
        return self.output_dir / "stage-90-coverage-closure.sqlite"

    @property
    def stage_70_wiki_cache(self) -> Path:
        return self.output_dir / "stage70-wiki-cache"

    @property
    def consolidated(self) -> Path:
        return self.output_dir / "aa8-client-knowledge.sqlite"

    @property
    def manifest(self) -> Path:
        return self.output_dir / "manifest.json"

    def with_overrides(
        self,
        *,
        output_dir: Path | None = None,
        source_item_database: Path | None = None,
        source_item_manifest: Path | None = None,
        source_item_tool_root: Path | None = None,
    ) -> "ForensicsConfig":
        return replace(
            self,
            output_dir=(output_dir or self.output_dir).resolve(),
            source_item_database=(
                source_item_database or self.source_item_database
            ).resolve(),
            source_item_manifest=(
                source_item_manifest or self.source_item_manifest
            ).resolve(),
            source_item_tool_root=(
                source_item_tool_root or self.source_item_tool_root
            ).resolve(),
        )

    def validate(self) -> None:
        required_files = (
            self.source_item_database,
            self.source_item_manifest,
            self.source_game11,
            self.source_client_compact,
            self.source_npc_catalog_manifest,
            self.source_character_data,
            self.source_character_manifest,
            self.source_faction_data,
            self.source_faction_manifest,
            self.source_spawner_layers_manifest,
            self.source_spawner_absence_manifest,
            self.source_ghidra_sql_loaders_64,
            self.source_ghidra_sql_call_sequence,
            self.source_ghidra_loot_loaders_x86,
            self.source_loot_loader_tasks,
            self.source_ghidra_item_grade_order_x64,
            self.source_ghidra_item_grade_order_x86,
            self.source_ghidra_item_grade_descriptor_x64,
            self.source_ghidra_item_grade_descriptor_x86,
            self.source_item_grade_loader_tasks,
            self.source_ghidra_item_grade_secondary_x64,
            self.source_ghidra_item_grade_secondary_x86,
            self.source_item_grade_secondary_loader_tasks,
            self.source_ghidra_item_guide_x64,
            self.source_ghidra_item_guide_x86,
            self.source_item_guide_loader_tasks,
            self.source_ghidra_tag_loaders_x64,
            self.source_ghidra_tag_loaders_x86,
            self.source_ghidra_tag_layouts_x64,
            self.source_ghidra_tag_layouts_x86,
            self.source_tag_loader_tasks,
            self.source_sql_surface_manifest,
            self.source_ghidra_quest_loaders_x86,
            self.source_quest_loader_tasks,
            self.source_ghidra_enum_consumers_x64,
            self.source_ghidra_enum_consumers_x86,
            self.source_ghidra_quest_bubble_callbacks_x64,
            self.source_ghidra_quest_component_struct_x64,
            self.source_ghidra_quest_scalar_api_x64,
            self.source_ghidra_quest_scalar_consumers_x64,
            self.source_ghidra_quest_scalar_consumers_x86,
            self.source_ghidra_component_accessor_context_x64,
            self.source_ghidra_component_accessor_context_x86,
            self.source_ghidra_component_text_vector_trace_x64,
            self.source_ghidra_component_text_vector_trace_x86,
            self.source_ghidra_component_text_data_x64,
            self.source_ghidra_component_text_data_x86,
            self.source_ghidra_ui_event_core_x64,
            self.source_ghidra_ui_event_core_x86,
            self.source_component_text_surface_snapshot,
            self.source_ghidra_npc_ai_field_trace_x64,
            self.source_ghidra_npc_ai_field_trace_x86,
            self.source_ghidra_npc_ai_forwarded_helpers_x64,
            self.source_ghidra_npc_ai_forwarded_helpers_x86,
            self.source_ghidra_npc_ai_raw_vector_x64,
            self.source_ghidra_npc_ai_raw_vector_x86,
            self.source_ghidra_quest_component_copy_x86,
            self.source_ghidra_npc_ai_lua_bindings_x64,
            self.source_ghidra_npc_ai_lua_bindings_x86,
            self.source_ghidra_npc_ai_script_stubs_x64,
            self.source_ghidra_npc_ai_script_stubs_x86,
            self.source_npc_ai_surface_snapshot,
            self.source_ghidra_skill_loaders_x86,
            self.source_skill_loader_tasks,
            self.source_ghidra_world_interaction_loader_x86,
            self.source_ghidra_world_interaction_enum_x64,
            self.source_ghidra_world_interaction_enum_x86,
            self.source_world_interaction_loader_tasks,
            self.source_ghidra_asset_loaders_x86,
            self.source_asset_loader_tasks,
            self.source_ghidra_custom_model_x64,
            self.source_ghidra_custom_model_x86,
            self.source_gamepak_index,
        )
        for path in required_files:
            if not path.is_file():
                raise FileNotFoundError(path)
        if not self.source_item_tool_root.is_dir():
            raise FileNotFoundError(self.source_item_tool_root)
        if not self.source_cached_streams_dir.is_dir():
            raise FileNotFoundError(self.source_cached_streams_dir)
        if not self.source_quest_wiki_cache.is_dir():
            raise FileNotFoundError(self.source_quest_wiki_cache)
        if not self.source_item_wiki_cache.is_dir():
            raise FileNotFoundError(self.source_item_wiki_cache)
        if not self.source_skills_tool_root.is_dir():
            raise FileNotFoundError(self.source_skills_tool_root)
        if not self.source_skill_wiki_cache.is_dir():
            raise FileNotFoundError(self.source_skill_wiki_cache)
        for path in (
            self.source_gamepak_xml_root,
            self.source_gamepak_lua64_root,
            self.source_gamepak_lua32_root,
        ):
            if not path.is_dir():
                raise FileNotFoundError(path)
        if self.output_dir.resolve() == self.source_item_database.parent.resolve():
            raise ValueError("The transversal output must not overwrite the item baseline")


def load_config(path: Path | None = None) -> ForensicsConfig:
    config_path = (path or DEFAULT_CONFIG).resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent

    def resolve(value: str) -> Path:
        candidate = Path(value)
        return (candidate if candidate.is_absolute() else base / candidate).resolve()

    return ForensicsConfig(
        client_build=str(raw["client_build"]),
        output_dir=resolve(raw["output_dir"]),
        source_item_database=resolve(raw["source_item_database"]),
        source_item_manifest=resolve(raw["source_item_manifest"]),
        source_item_tool_root=resolve(raw["source_item_tool_root"]),
        source_cached_streams_dir=resolve(raw["source_cached_streams_dir"]),
        source_game11=resolve(raw["source_game11"]),
        source_client_compact=resolve(raw["source_client_compact"]),
        source_npc_catalog_manifest=resolve(raw["source_npc_catalog_manifest"]),
        source_character_data=resolve(raw["source_character_data"]),
        source_character_manifest=resolve(raw["source_character_manifest"]),
        source_faction_data=resolve(raw["source_faction_data"]),
        source_faction_manifest=resolve(raw["source_faction_manifest"]),
        source_spawner_layers_manifest=resolve(raw["source_spawner_layers_manifest"]),
        source_spawner_absence_manifest=resolve(raw["source_spawner_absence_manifest"]),
        source_ghidra_sql_loaders_64=resolve(raw["source_ghidra_sql_loaders_64"]),
        source_ghidra_sql_call_sequence=resolve(
            raw["source_ghidra_sql_call_sequence"]
        ),
        source_ghidra_loot_loaders_x86=resolve(
            raw["source_ghidra_loot_loaders_x86"]
        ),
        source_loot_loader_tasks=resolve(raw["source_loot_loader_tasks"]),
        source_ghidra_item_grade_order_x64=resolve(
            raw["source_ghidra_item_grade_order_x64"]
        ),
        source_ghidra_item_grade_order_x86=resolve(
            raw["source_ghidra_item_grade_order_x86"]
        ),
        source_ghidra_item_grade_descriptor_x64=resolve(
            raw["source_ghidra_item_grade_descriptor_x64"]
        ),
        source_ghidra_item_grade_descriptor_x86=resolve(
            raw["source_ghidra_item_grade_descriptor_x86"]
        ),
        source_item_grade_loader_tasks=resolve(
            raw["source_item_grade_loader_tasks"]
        ),
        source_ghidra_item_grade_secondary_x64=resolve(
            raw["source_ghidra_item_grade_secondary_x64"]
        ),
        source_ghidra_item_grade_secondary_x86=resolve(
            raw["source_ghidra_item_grade_secondary_x86"]
        ),
        source_item_grade_secondary_loader_tasks=resolve(
            raw["source_item_grade_secondary_loader_tasks"]
        ),
        source_ghidra_item_guide_x64=resolve(
            raw["source_ghidra_item_guide_x64"]
        ),
        source_ghidra_item_guide_x86=resolve(
            raw["source_ghidra_item_guide_x86"]
        ),
        source_item_guide_loader_tasks=resolve(
            raw["source_item_guide_loader_tasks"]
        ),
        source_ghidra_tag_loaders_x64=resolve(
            raw["source_ghidra_tag_loaders_x64"]
        ),
        source_ghidra_tag_loaders_x86=resolve(
            raw["source_ghidra_tag_loaders_x86"]
        ),
        source_ghidra_tag_layouts_x64=resolve(
            raw["source_ghidra_tag_layouts_x64"]
        ),
        source_ghidra_tag_layouts_x86=resolve(
            raw["source_ghidra_tag_layouts_x86"]
        ),
        source_tag_loader_tasks=resolve(
            raw["source_tag_loader_tasks"]
        ),
        source_sql_surface_manifest=resolve(raw["source_sql_surface_manifest"]),
        source_ghidra_quest_loaders_x86=resolve(
            raw["source_ghidra_quest_loaders_x86"]
        ),
        source_quest_loader_tasks=resolve(raw["source_quest_loader_tasks"]),
        source_ghidra_enum_consumers_x64=resolve(
            raw["source_ghidra_enum_consumers_x64"]
        ),
        source_ghidra_enum_consumers_x86=resolve(
            raw["source_ghidra_enum_consumers_x86"]
        ),
        source_ghidra_quest_bubble_callbacks_x64=resolve(
            raw["source_ghidra_quest_bubble_callbacks_x64"]
        ),
        source_ghidra_quest_component_struct_x64=resolve(
            raw["source_ghidra_quest_component_struct_x64"]
        ),
        source_ghidra_quest_scalar_api_x64=resolve(
            raw["source_ghidra_quest_scalar_api_x64"]
        ),
        source_ghidra_quest_scalar_consumers_x64=resolve(
            raw["source_ghidra_quest_scalar_consumers_x64"]
        ),
        source_ghidra_quest_scalar_consumers_x86=resolve(
            raw["source_ghidra_quest_scalar_consumers_x86"]
        ),
        source_ghidra_component_accessor_context_x64=resolve(
            raw["source_ghidra_component_accessor_context_x64"]
        ),
        source_ghidra_component_accessor_context_x86=resolve(
            raw["source_ghidra_component_accessor_context_x86"]
        ),
        source_ghidra_component_text_vector_trace_x64=resolve(
            raw["source_ghidra_component_text_vector_trace_x64"]
        ),
        source_ghidra_component_text_vector_trace_x86=resolve(
            raw["source_ghidra_component_text_vector_trace_x86"]
        ),
        source_ghidra_component_text_data_x64=resolve(
            raw["source_ghidra_component_text_data_x64"]
        ),
        source_ghidra_component_text_data_x86=resolve(
            raw["source_ghidra_component_text_data_x86"]
        ),
        source_ghidra_ui_event_core_x64=resolve(
            raw["source_ghidra_ui_event_core_x64"]
        ),
        source_ghidra_ui_event_core_x86=resolve(
            raw["source_ghidra_ui_event_core_x86"]
        ),
        source_component_text_surface_snapshot=resolve(
            raw["source_component_text_surface_snapshot"]
        ),
        source_ghidra_npc_ai_field_trace_x64=resolve(
            raw["source_ghidra_npc_ai_field_trace_x64"]
        ),
        source_ghidra_npc_ai_field_trace_x86=resolve(
            raw["source_ghidra_npc_ai_field_trace_x86"]
        ),
        source_ghidra_npc_ai_forwarded_helpers_x64=resolve(
            raw["source_ghidra_npc_ai_forwarded_helpers_x64"]
        ),
        source_ghidra_npc_ai_forwarded_helpers_x86=resolve(
            raw["source_ghidra_npc_ai_forwarded_helpers_x86"]
        ),
        source_ghidra_npc_ai_raw_vector_x64=resolve(
            raw["source_ghidra_npc_ai_raw_vector_x64"]
        ),
        source_ghidra_npc_ai_raw_vector_x86=resolve(
            raw["source_ghidra_npc_ai_raw_vector_x86"]
        ),
        source_ghidra_quest_component_copy_x86=resolve(
            raw["source_ghidra_quest_component_copy_x86"]
        ),
        source_ghidra_npc_ai_lua_bindings_x64=resolve(
            raw["source_ghidra_npc_ai_lua_bindings_x64"]
        ),
        source_ghidra_npc_ai_lua_bindings_x86=resolve(
            raw["source_ghidra_npc_ai_lua_bindings_x86"]
        ),
        source_ghidra_npc_ai_script_stubs_x64=resolve(
            raw["source_ghidra_npc_ai_script_stubs_x64"]
        ),
        source_ghidra_npc_ai_script_stubs_x86=resolve(
            raw["source_ghidra_npc_ai_script_stubs_x86"]
        ),
        source_npc_ai_surface_snapshot=resolve(
            raw["source_npc_ai_surface_snapshot"]
        ),
        source_quest_wiki_cache=resolve(raw["source_quest_wiki_cache"]),
        source_item_wiki_cache=resolve(raw["source_item_wiki_cache"]),
        source_skills_tool_root=resolve(raw["source_skills_tool_root"]),
        source_ghidra_skill_loaders_x86=resolve(
            raw["source_ghidra_skill_loaders_x86"]
        ),
        source_skill_loader_tasks=resolve(raw["source_skill_loader_tasks"]),
        source_ghidra_world_interaction_loader_x86=resolve(
            raw["source_ghidra_world_interaction_loader_x86"]
        ),
        source_ghidra_world_interaction_enum_x64=resolve(
            raw["source_ghidra_world_interaction_enum_x64"]
        ),
        source_ghidra_world_interaction_enum_x86=resolve(
            raw["source_ghidra_world_interaction_enum_x86"]
        ),
        source_world_interaction_loader_tasks=resolve(
            raw["source_world_interaction_loader_tasks"]
        ),
        source_skill_wiki_cache=resolve(raw["source_skill_wiki_cache"]),
        source_ghidra_asset_loaders_x86=resolve(
            raw["source_ghidra_asset_loaders_x86"]
        ),
        source_asset_loader_tasks=resolve(raw["source_asset_loader_tasks"]),
        source_ghidra_custom_model_x64=resolve(
            raw["source_ghidra_custom_model_x64"]
        ),
        source_ghidra_custom_model_x86=resolve(
            raw["source_ghidra_custom_model_x86"]
        ),
        source_gamepak_index=resolve(raw["source_gamepak_index"]),
        source_gamepak_xml_root=resolve(raw["source_gamepak_xml_root"]),
        source_gamepak_lua64_root=resolve(raw["source_gamepak_lua64_root"]),
        source_gamepak_lua32_root=resolve(raw["source_gamepak_lua32_root"]),
        wiki_base_url=str(raw["wiki_base_url"]).rstrip("/"),
        wiki_locale=str(raw["wiki_locale"]),
    )
