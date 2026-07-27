# Patrón AA8 nativo para reconstruir modelos de NPC

Fecha de validación: 2026-07-26
Autoridad: cliente Kakao 8.0.3.12 r558734
Caso de aceptación: Lucius, NPC `3597`

## Resultado validado en juego

La reconstrucción visual de Lucius quedó completa:

- identidad y nombre correctos;
- ropa, capa, armadura y tocado correctos;
- cabello correcto;
- rostro humano completo, sin el placeholder blanco.

Evidencia visual de aceptación:

- captura original:
  `C:\Users\juank\AppData\Local\Temp\codex-clipboard-4c2e5bff-ee75-4f81-9a8a-1ffb93e8ae26.png`;
- dimensiones: `861x892`;
- SHA-256:
  `4FCC81F2D57AEDFAF26F2500CBBE2B52B8F51CD5291C019E3766A0F4350F7690`.

## Cadena de reconstrucción confirmada

La apariencia de un NPC humano no sale de una sola fila. Debe cerrarse esta
cadena completa:

1. `npcs.id -> npcs.model_id`;
2. `characters.model_id -> characters.face_item_id`;
3. `face_item_id -> items + item_body_parts`;
4. `total_character_customs` aporta identidad visual, cabello, decal y otras
   personalizaciones del modelo;
5. `equip_pack_cloths` y `equip_pack_weapons` seleccionan el equipo;
6. cada item del equipo debe tener su definición general y su descriptor
   concreto (`item_armors`, `item_weapons`, `item_body_parts`, etc.);
7. cada descriptor debe conservar el `asset_id` nativo que resuelve el recurso
   gráfico del cliente.

## Fallo que reveló Lucius

Para el modelo humano masculino `10`, AA8 declara explícitamente
`characters.face_item_id = 19838`.

El servidor escogía la última fila compatible de `item_body_parts`, que era
`48541` (`nu_m_mannequin_face`). Esa selección ordinal producía el rostro
blanco aun cuando el rostro correcto sí existía en el cliente.

Regla reutilizable:

> Nunca elegir rostro, cabello o pieza corporal por posición, por máximo ID ni
> por “última coincidencia”. Se debe seguir la referencia explícita declarada
> por el modelo nativo.

## Criterio de cierre para futuros NPC

Un modelo de NPC sólo se considera reconstruido cuando:

- todas las referencias anteriores existen en el runtime;
- no quedan items o descriptores huérfanos;
- los `asset_id` coinciden con el cliente AA8;
- el servidor selecciona las piezas explícitas del modelo;
- una prueba dentro del juego confirma cuerpo, rostro, cabello y equipo.

Lucius es el caso patrón para automatizar en el futuro la reconstrucción del
resto de los modelos de NPC.
