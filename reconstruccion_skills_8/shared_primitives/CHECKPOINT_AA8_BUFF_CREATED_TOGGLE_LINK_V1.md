# Checkpoint AA8 — vínculo de skill en `SCBuffCreated` V1

Fecha: 2026-08-09
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Estado: **cerrado en pruebas, Mechanics Lab y cliente AA8 real**

## Problema de referencia

Charge/Cargar `11918` comenzaba su cooldown correctamente, pero volvía a
mostrar 12 segundos cuando desaparecían los buffs creados por el lanzamiento.
La primera coincidencia ocurría al salir `7543` y la segunda al salir `11344`.
El servidor no iniciaba, reducía ni reseteaba el cooldown en esos instantes.

El defecto no pertenecía a Charge ni al reductor de Behind Enemy Lines. Era
una regresión transversal del estado publicado previamente por
`SCBuffCreated 0x36C`.

## Regresión localizada

El checkpoint `835b42e1` cambió el campo compacto `s` de `SCBuffCreated`:

- antes: `skillId` sólo cuando la skill era propietaria del buff toggle;
- después: ID de la skill origen para cualquier buff creado por una skill.

La implementación anterior ya advertía que poblar ese campo con la skill
equivocada aplicaba cooldown a otra skill. El comparador Modern conserva la
misma condición toggle-only, pero se usa aquí sólo como corroboración
estructural. La autoridad de cierre es el A/B histórico y la aceptación viva
con el cliente AA8.

Charge `11918` declara `toggle_buff_id=0`. Aun así, la regresión publicaba sus
buffs `7543`, `11344` y `22627` con `skillId=11918`. El cliente conservaba esa
relación y, al procesar la retirada posterior del buff, volvía a materializar
el cooldown base de Charge.

## Evidencia protocolaria y negativa

- `SCBuffCreated` pertenece al opcode AA8 `0x36C`, nivel cifrado 5.
- Stage 15 x64 confirma el serializer
  `FUN_399b2960 -> FUN_399b10a0`; este último contiene el campo compacto `s`
  antes de `stack`.
- El serializer confirma layout y anchura. Su semántica toggle-only se cierra
  por comportamiento histórico conocido funcional, A/B de la regresión y
  aceptación viva; no se deduce sólo del nombre de un campo.
- Las capturas live mostraron los buffs ligados a `11918` y sus retiradas a
  aproximadamente 4 y 9 segundos.
- En cada salto estaban ausentes un segundo `CSStartSkill`,
  `SCSkillCooldownReset`, `SCSkillCooldownReduce`, `SCCooldowns` y cualquier
  mutación de `UnitCooldowns`.
- Retirar snapshots de fin de plot y corregir el layout independiente de
  `SCBuffRemoved 0x023` no eliminó el salto. Ambas correcciones tenían
  evidencia propia, pero quedaron falsificadas como causa de este síntoma.

## Contrato corregido

`SCBuffCreated` debe separar dos conceptos:

- `originSkill`: procedencia interna útil para efectos, logs y diagnóstico;
- `toggleSkill`: relación funcional que el cliente consume para administrar
  el ciclo de una skill toggle.

Regla de serialización:

```text
if originSkill != null
   and originSkill.toggle_buff_id != 0
   and originSkill.toggle_buff_id == buff.id:
    s = originSkill.id
else:
    s = 0
```

No se elimina `Buff.Skill` ni se pierde la procedencia. El trace registra
`originSkill` y `toggleSkill` por separado. El `stack` nativo AA8 continúa
serializándose sin cambios.

## Reglas para futuras ramas

1. No usar un campo opcional de relación como contenedor genérico de
   procedencia sólo porque el dato está disponible en el servidor.
2. Antes de poblar un ID opcional de packet, identificar qué ciclo de UI o
   estado cliente controla su consumidor.
3. Ante un fallo que aparece al retirar un buff, inspeccionar también el
   `SCBuffCreated` original: la retirada puede activar una relación inválida
   almacenada varios segundos antes.
4. Comparar primero con la última revisión conocida funcional y localizar el
   commit de regresión antes de inventar paquetes de refresco.
5. Mantener separados inicio, reducción y reset de cooldown; ninguno corrige
   una relación toggle publicada erróneamente.
6. No añadir excepciones por skill ID. La regla depende únicamente de
   `toggle_buff_id == buff.id`.
7. Probar como mínimo:
   - skill no-toggle que crea un buff: `s=0`;
   - skill toggle y su buff propietario: `s=skillId`;
   - skill toggle creando otro buff: `s=0`;
   - `stack`, duraciones y cuerpo restante sin desplazamientos de wire.
8. Exigir aceptación viva esperando todas las expiraciones relevantes sin
   relog; un cast que parece correcto durante el primer segundo no cierra el
   lifecycle.

## Validación

- regresiones focales .NET 3.1: `9/9 PASS`;
- suite completa .NET 3.1: `619/619 PASS`;
- Mechanics Lab Charge: PASS, `originSkill=11918`, `toggleSkill=0`, resultado
  SHA-256
  `09EE2A88924E9369F0E4F71DF98D86ED15C21D7E35AC0AB2F5A46B112871B622`;
- Mechanics Lab Behind Gale: PASS, `12000 -> 10000 -> 8000 -> 6000`, resultado
  SHA-256
  `75A1FCAB81D08F2D72969797C4BD1E338952D117A6AC6100404EE11CBFA409EE`;
- cliente AA8 real: **PASS**; el usuario confirmó que las salidas de los buffs
  ya no reinician el cooldown de Charge.

## Implementación y despliegue de referencia

- código: `AAEmu.Game/Core/Packets/G2C/SCBuffCreatedPacket.cs`;
- regresiones: `AAEmu.Tests/CombatStatTests.cs`;
- dossier de origen:
  `reconstruccion_skills_8/battlerage/BATTLERAGE_COOLDOWN_TIMING_V5_AA8.md`;
- imagen desplegada:
  `sha256:6e7f05407ff5b76670960c03b5217686917fa185bb9761738e3b198621548a71`;
- `AAEmu.Game.dll` SHA-256:
  `C350439F3D0877946E9216A4AB1C559E70AA589755EF1B5AC688E1F82C6111B8`;
- compact V5 montada SHA-256:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- sólo se recreó `game`; scripts `0 errors`, puertos `2239/2250`, registro en
  LoginServer correcto y `RestartCount=0`.
