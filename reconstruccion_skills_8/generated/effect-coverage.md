# Battlerage effect coverage — ArcheAge 8.0

This matrix describes the effect types reachable through the relationships currently loaded by the runtime. It does not claim those historical relationships are the native 8.0 definitions.

| Effect type | Relations | Skills | Native concrete | Backend | Relation sources |
|---|---:|---:|---:|---|---|
| AggroEffect | 1 | 1 | 0 | backend_present_source_unconfirmed | runtime_server_reference |
| BuffEffect | 66 | 24 | 22 | backend_present_native_source_confirmed | client_8_game11, runtime_server_reference |
| ConversionEffect | 1 | 1 | 1 | backend_present_source_unconfirmed | client_8_game11 |
| DamageEffect | 49 | 23 | 16 | backend_present_source_unconfirmed | client_8_game11, runtime_server_reference |
| DispelEffect | 4 | 3 | 0 | backend_present_source_unconfirmed | runtime_server_reference |
| PhysicalExplosionEffect | 3 | 3 | 3 | backend_present_source_unconfirmed | client_8_game11 |
| SpecialEffect | 15 | 13 | 8 | backend_present_source_unconfirmed | client_8_game11, runtime_server_reference |

Unresolved effect relationships: 0.

`backend_present_missing_concrete_8_data` means the native relationship is recovered and AAEmu has a class/loader, but one or more referenced concrete rows are absent from the runtime compact.
`backend_present_missing_native_buff_templates` means native BuffEffect rows are recovered, but the client stream has not yet yielded the referenced `buffs` rows.
`backend_present_native_source_confirmed` means both the native BuffEffect row and its referenced 8.0 buff template were recovered.
