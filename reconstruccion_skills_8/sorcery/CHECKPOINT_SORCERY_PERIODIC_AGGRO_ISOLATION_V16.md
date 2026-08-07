# Checkpoint Sorcery V16: aislamiento de aggro periodico

Fecha: 2026-08-06  
Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`  
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Objetivo

Separar los dos payloads que siempre aparecian juntos en el primer tick de
Meteor Strike Lightning (`skill 36479`):

1. `SCUnitDamagedPacket` con `CastAction=Buff`;
2. `SCUnitAiAggroPacket` para el mismo NPC.

V14 y V15 demostraron que el servidor permanece sano y que ni el canal ni
`topFlags` explican por si solos la desconexion.

## Cambio diagnostico transversal

`DamageEffect` conserva el dano, eventos, procs, buffs, vida del objetivo y
`Npc.OnDamageReceived`. Esto significa que la IA y la tabla autoritativa de
aggro del servidor siguen actualizandose.

Se omite solamente `SCUnitAiAggroPacket` cuando el dano proviene de
`CastBuff`. Los impactos directos y de plot siguen enviando el paquete. La
politica es generica para DoT y pulsos periodicos; no contiene IDs de Meteor o
Sorcery.

## Verificacion automatica

- prueba focal de la politica: `1/1`;
- suite completa con SQLite activa montada: `519/519`;
- SQLite y grafo de Meteor sin cambios;
- despliegue exclusivo de Game y prueba viva pendientes.

Si el cliente permanece conectado, el fallo queda aislado a la retransmision
periodica de la tabla de aggro. Si vuelve a desconectarse, se descarta por
completo `SCUnitAiAggroPacket` y la frontera queda reducida al payload o a los
valores de `SCUnitDamagedPacket(CastBuff)`.
