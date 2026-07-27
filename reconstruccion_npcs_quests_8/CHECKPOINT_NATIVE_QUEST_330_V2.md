# Checkpoint AA8 nativo — quest 330 v2

Fecha: 2026-07-26
Autoridad: ArcheAge Kakao 8.0.3.12 r558734

## Resultado

La primera prueba en cliente rechazó correctamente dos supuestos:

- Lucius estaba presente, pero la quest 330 no se publicaba.
- `model_id=10` sólo entregaba el cuerpo base; Lucius no tenía rostro,
  pelo ni ropa funcionales.

La v2 cierra ambos caminos sin importar datos históricos 3.0.

## Causa de la quest ausente

El cliente conserva el catálogo y las relaciones de quest en su compact, pero
necesita que el servidor sincronice el estado activo y completado del
personaje. En el port inicial AA8 ambas llamadas quedaron comentadas en
`CSSelectCharacterPacket`, por lo que el cliente no podía calcular la
disponibilidad ni el marcador de NPC.

La v2 envía al seleccionar personaje:

- `SCQuestsPacket`, opcode AA8 `0x1B4`, nivel 5.
- `SCCompletedQuestsPacket`, opcode AA8 `0x081`, nivel 5.

Para Wingsjuanka esto significa una instantánea activa vacía y sus grupos de
quests completadas reales. La quest 330 no está activa ni completada.

## Causa de la apariencia placeholder

La fila nativa de Lucius es:

- NPC `3597`
- modelo `10`
- total custom `419` (`nu_m_lucius`)
- pelo `25269` (`nu_m_hair002`)
- pack de ropa `1070`
- cosplay `16066` (`sk_lucius001`)

Había dos fallos:

1. `NpcManager` serializaba `CharRace=0` y `CharGender=0` porque sólo copiaba
   `model_id`. AA8 agregó ambos campos al modelo personalizado.
2. El runtime no contenía la definición base ni el descriptor de armadura del
   cosplay `16066`.

La v2 usa la identidad Nuian masculina ya resuelta por el modelo, corrige los
índices 4 y 5 de los decals faciales e incorpora desde `game11` las
definiciones nativas de apariencia.

También se cerró Parish (`11541`), NPC de entrega:

- pelo `24133`
- camisa `2722`
- pantalón `18490`
- zapatos `25017`

## Runtime desplegado

Archivo:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-quest330-v2.sqlite3`

SHA-256:

`B74262085120BC91FC7A9EA35D54DB42C020DADD0D77559DBD77E3EFBCAFF963`

Comprobaciones de cierre:

- quest contexts/components/acts: `1 / 3 / 8`
- rewards presentes: `5`
- ítems de apariencia presentes: `6`
- descriptores de armadura: `4`
- pelos nativos: `2`
- gates completos de reward/apariencia: `8`
- `PRAGMA quick_check`: `ok`
- `PRAGMA integrity_check`: `ok`

## Validación automatizada

- 16/16 pruebas Python del dominio NPC/quest.
- 229/229 pruebas C#.
- Build Docker del servidor de juego correcto.

## Prueba manual requerida

Hay que reconectar completamente a Wingsjuanka para ejecutar de nuevo la
selección de personaje. Validar:

1. Lucius aparece con rostro, pelo y traje.
2. Lucius muestra el marcador de quest disponible.
3. La conversación permite aceptar la quest 330.
4. Parish permite entregarla.
5. Se reciben 210 EXP, 33 cobre, los rewards fijos y una selección.
6. Parish ofrece después la quest 2531.

Esta validación manual sigue siendo el gate final del comportamiento real del
cliente Kakao.
