# Corroboración histórica y regional

Usar fuentes web para distinguir contenido retail persistente, contenido de
evento, variantes regionales, IDs reutilizados y datos realmente obsoletos.
Este paso es obligatorio cuando full/compact/consumer dejan una entidad
bloqueada o aparentemente incompleta y existe una posibilidad razonable de que
fuera utilizable en la versión del juego.

## Fuentes y captura

Priorizar, en orden:

1. notas oficiales y archivos oficiales de la época;
2. catálogos versionados que separen contenido activo y `unused`, como
   ArcheAge Codex, comprobando versión, fecha y locale;
3. wikis regionales con relaciones de receta, workbench, skill o doodad;
4. foros o guías contemporáneas sólo como indicio auxiliar.

Registrar URL, título, fecha de publicación o actualización, versión declarada,
región/locale, ID consultado y campos observados. No considerar una coincidencia
por ID como identidad suficiente: comparar nombre, producto, materiales,
workbench, labor/coste, skill y período para detectar reutilización del ID.

## Clasificación

Mantener la evidencia externa en un namespace separado y asignar una de estas
clases antes de decidir:

- `persistent_candidate`: aparece como receta normal en la época y región;
- `event_conditional`: fue craftable sólo mientras existían evento y consumer;
- `regional_conflict`: regiones publican contratos o disponibilidad distintos;
- `id_reuse_conflict`: el mismo ID representa otra receta/contrato;
- `external_unused`: el catálogo versionado la marca explícitamente sin uso;
- `external_unresolved`: la web no aporta evidencia bastante precisa.

La web no eleva por sí sola una receta a ejecutable. Sirve para abrir o cerrar la
pregunta histórica y debe cruzarse con full AA10, compact retail, consumer,
cliente/Zone r575 y, cuando sea necesario, una prueba dinámica reproducible.

## Recetas intencionalmente sin materiales

No tratar `materials.Count == 0` como corrupción universal. Una receta sin
materiales puede ser válida si la evidencia AA10 y la corroboración histórica
demuestran que su pago real es labor, moneda, actability, una condición de
interacción o un recurso del consumer.

Promoverla únicamente cuando queden cerrados:

- producto y cantidad;
- labor/coste/actability y skill;
- estación o consumer y permisos;
- ausencia intencional de relaciones de materiales, no un loader incompleto;
- transacción y rechazo sin mutación parcial;
- comportamiento del cliente exacto antes/después y persistencia tras relog.

Una allowlist temporal debe ser cerrada, citar evidencia por receta y excluir
automáticamente IDs de evento, región conflictiva, test o reutilizados.

## Decisión

Un caso puede promocionarse cuando la fuente web corrobora un contrato ya
demostrado por AA10 o cuando una prueba dinámica del cliente exacto resuelve la
ambigüedad. Si las fuentes discrepan, conservar el bloqueo con su clase concreta
y no delegar al flujo legacy.
