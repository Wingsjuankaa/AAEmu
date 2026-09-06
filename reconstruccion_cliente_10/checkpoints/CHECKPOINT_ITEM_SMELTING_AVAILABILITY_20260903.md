# Item Smelting — disponibilidad, no aceptación jugable

Estado vigente: DEPRECADO / FUERA DE ALCANCE por decisión explícita del usuario (2026-09-03).
Feature178 OFF. Código y evidencia conservados; sin aceptación funcional ni despliegue.
No continuar auditorías, reconstrucción o activación salvo petición explícita de reapertura.
La auditoría siguiente conserva los bloqueos históricos, no tareas pendientes del proyecto.
Target `rama_10`, base41570558459efad934065d3ea348bffc52f45162,
padre3cc280b14d7da0d874121d14ebbf409f5e032d1c.

Dossier: [AA10ItemSmeltingReconstruction_es.md](../../Docs/AA10ItemSmeltingReconstruction_es.md).

- Cuatro fuentes congeladas; integridad y quick_check correctos.
- Dos builds deterministas: SHA256 audit.json
  `0626fe423ad05610e3002b07f8998b0bdee1af9218d77f77ff3821552864e7a7`.
-32 recetas/96 outputs;43482/43489 ausentes en las cuatro fuentes.
-40000 existe en full y full-derived, no en compact retail ni actual.
-Corrección:35525→61510→SpecialEffect27384→151, no Anim34.
-Catalizador43445 obsoleto→37020→67866→31887/type100/value1=1400.
-Ghidra baseline2735819 no se identifica falsamente como405242e vigente.
  Selector98B9C0, iteradorAF6140 y caller121180 reanclados por igualdad de
  todos sus bytes contra el PE405242e. Primera coincidencia, no menorID garantizado.
-Notas históricas2017 corroboran desuso; no reemplazan fuente exacta Returns.

Reproducir desde repo:

```powershell
python reconstruccion_cliente_10/scripts/audit_item_smelting_availability.py --output E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/item-smelting-frontier/availability-20260903-a
python reconstruccion_cliente_10/scripts/audit_item_smelting_availability.py --output E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/item-smelting-frontier/availability-20260903-b
```

Script nativo `Aa10SmeltingSelectorAudit.java`, Ghidra12.1.3/JDK21,
proyecto AA10X2GameRelease, `-process x2game.dll -readOnly -noanalysis`.
Log `item-smelting-frontier/selector-reanchored-20260903.log`.
El gate fallido previo de identidad se conserva como evidencia, no resultado válido.

SHA256 de decoders ejecutados (bytes locales):

- Python:53C319E02186ADAE070DF01E3EE7F6EA3E2CD03E2DE4B6D3E9F06289810A8BE6.
- Java:854B49A812FE8D3124758231497873F17DBF91656243058936DD8B016AD3DB5C.

Verificación final: `git diff --check` correcto. En C# sólo se corrigieron
comentarios; no cambió código ejecutable, configuración ni datos. No se repitió
build/suite .NET ni se desplegó una imagen por esta auditoría. Game continúa
healthy; feature false en fuente, mount y ambos Features.json del contenedor.
No se operó Zone ni se entregó un kit con una receta no demostrada.

Siguiente punto activo: Housing H2/H5-B. Smelting no bloquea la cola y no tiene gate de trabajo
pendiente. Esta exclusión no modifica Lunagem, socketing o crafting ni autoriza borrarlos.
