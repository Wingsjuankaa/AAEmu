# Checkpoint Stage 80 - Reconstruction dossiers V1

## Alcance

Este entregable agrega una herramienta de lectura sobre
`aa8-client-knowledge.sqlite`. No modifica las SQLite canonicas, AAEmu, una
compact runtime, `.env`, MySQL ni Docker.

Su objetivo es producir, para cualquier raiz `(kind, native_id)`, una clausura
forense determinista que una IA pueda consumir antes de reconstruir una
familia. La herramienta no declara una mecanica implementada ni promueve
evidencia wiki a autoridad nativa.

## Implementacion

- Motor comun: `client_forensics/closure.py`.
- Politicas: `config/closure-profiles.json`.
- Formato de politica: `AA8_CLOSURE_POLICY_V1`.
- Formato de salida: `AA8_RECONSTRUCTION_DOSSIER_V1`.
- Perfiles incluidos: `generic`, `quest`, `item` y `skill`.
- CLI:

```powershell
python -B -m client_forensics explain-closure <kind> <id>
python -B -m client_forensics export-dossier <kind> <id>
```

El recorrido es BFS y conserva la direccion canonica de cada arista aunque se
alcance por su indice inverso. Las reglas declarativas deciden `expand`,
`terminal` o `skip`, y clasifican cada path como `required`, `structural` o
`contextual`. Un limite, una entidad desconocida o una arista opaca nunca se
resuelve por aproximacion.

Cada dossier incorpora:

- Entidades y relaciones alcanzadas.
- Paths, profundidad, regla y relevancia.
- Propiedades, localizaciones, coverage, gaps y consumers.
- Blocker roots e impactos.
- Evidencia wiki corroborativa asociada.
- Limites de profundidad, nodos, fan-out y exclusiones de politica.
- Readiness forense separado de auditorias de runtime y presentacion.
- SHA-256 del perfil, manifest fuente y consolidada fuente.

El visor HTML es estatico y autocontenido. Incluye busqueda, filtros por tipo y
estado, grafo SVG con zoom/pan, lista de nodos y panel de evidencia.

## Ejercicio real: quest 330

La raiz `quest:330` produce:

| metrica | valor |
| --- | ---: |
| nodos | 128 |
| aristas | 179 |
| profundidad maxima | 7 |
| nodos required/root | 34 |
| aristas required/structural | 33 |
| limites registrados | 70 |
| limites duros sobre paths required | 0 |

La clausura recupera componentes, acts, act details, NPCs, modelo/apariencia,
items de recompensa, descriptores y las skills de uso de las cajas. Tambien
expone lo que todavia impide una reconstruccion nativa cerrada:

- `quest_component:3543` es un endpoint referenciado aun desconocido.
- `skill:42205`, `skill:42209` y `skill:46956` no tienen proyectada su clausura
  de efecto, buff, plot o items producidos.
- El protocolo de los items 47868, 47869 y 51185 sigue como auditoria posterior.
- Las referencias visuales no resueltas se conservan como auditoria de
  presentacion y no se confunden con ausencia de gameplay.

Por esto el resultado correcto es `forensic=blocked` y
`reconstruction=blocked_by_native_evidence`.

## Reutilizacion demostrada

El mismo motor, sin ramas Python especificas por tipo, genero:

| raiz | perfil | nodos | aristas | bloqueo principal |
| --- | --- | ---: | ---: | --- |
| `quest:330` | quest | 128 | 179 | endpoint y skills sin clausura |
| `item:51185` | item | 14 | 13 | `skill:46956` sin clausura |
| `skill:46956` | skill | 7 | 6 | comportamiento no proyectado |

Una familia nueva se agrega extendiendo `generic` en el JSON de politicas. No
requiere duplicar el walker, el exportador, el modelo de readiness ni el visor.

## Artefactos y determinismo

Fuente:

```text
E:/AAEmu-Research/output/aa8-client-forensics/aa8-client-knowledge.sqlite
SHA-256 807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC
```

Salidas:

| archivo | bytes | SHA-256 |
| --- | ---: | --- |
| `quest-330.json` | 1,830,907 | `C47AAF43F7BBA5F16D31CD30EBCB9B60A5103C07E13DE39D382DECFBBE82CD68` |
| `quest-330.html` | 1,360,551 | `6E2C5035A8E4E1815940F630C9186730117E09E42ECEDDAE2E460D0D870B1648` |
| `item-51185.json` | 184,893 | `F336AE41BB9E12AEEA0B4D1A6460CCF638FCFF84F7C2D82F1BE0D73CAAC26842` |
| `item-51185.html` | 143,903 | `19AED0FD0085159567F10B18D86A6D976AA0F52970CDB8FFFAAD7AB4DC8EDDCE` |
| `skill-46956.json` | 122,531 | `7C67380BE4A25DE5043D78A073A75B7D34AF59B7FC0F6CA84C75B034B3564035` |
| `skill-46956.html` | 100,801 | `BD1C2AD0D64EC45B0F1FA44364C2E03BC2E13E48DC2EEC3880FAD7DB4CE0282C` |

Dos exportaciones consecutivas produjeron los mismos seis SHA-256.

## Validacion

- Fixtures del walker, perfiles item/skill, separacion de bloqueos y exportacion
  determinista: 5/5 pruebas.
- Suite completa de `client_forensics`: 47/47 pruebas.
- HTML quest 330 validado en navegador local:
  128 nodos, 179 aristas y cero warnings/errors.
- Busqueda `51185` y panel de detalle con propiedades, gaps y coverage validados.
- Los artefactos no cargan scripts, estilos ni datos desde la red.

## Siguiente frontera recomendada

Usar los dossiers de las tres cajas alcanzadas por quest 330 como cola
dirigida de descifrado. El primer objetivo no es implementar las cajas: es
recuperar la clausura conductual nativa de skills 42205, 42209 y 46956 hasta
que el dossier enumere efectos y destinos item exactos. El mismo comando
medira automaticamente si esos bloqueos desaparecen en la siguiente
consolidada.
