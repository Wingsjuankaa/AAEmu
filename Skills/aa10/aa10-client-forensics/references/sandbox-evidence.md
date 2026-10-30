# Evidencia del sandbox AA10

El laboratorio aceptado vive en E:\AAEmu\rama_10\runtime\sandbox-aa10.
Zone411 aa10_sandbox_lab, actor Sandbox1001/cuenta1, cuatro dummies y cuatro
NPCs de servicios. Cliente español, +locale en_us. El usuario maneja el cliente;
no controlar su escritorio. Su existencia no autoriza lifecycle desde forensics.

Separar fuentes:

- Full autoritativa y compact principal siguen siendo la autoridad estática.
- client/game_pak y zone/game_pak del sandbox son derivados físicos privados;
  zone411-installed.json registra identidades, manifiesto y aceptación.
- Zone411 es custom: deriva terreno/colisiones/modelos de retail406. MainWorld0
  privado fue reducido a2×2 celdas; no atribuir ese world.xml al continente retail.
- Los catálogos añaden identidad/localización de411. Native usa +db_location
  al catálogo full privado; el packed game.sqlite3 cifrado permanece opaco.
- captures/, logs/, profile/ArcheAge.log y zone-save/ son observaciones de runtime,
  no pruebas automáticas de que el contrato nativo completo está cerrado.

La reconstrucción puede editar C# real bajo dotnet watch y conservar sesión.
La evidencia debe mostrar contador CLR aumentado, PID/sesión conservados,
efecto observado y aceptación del usuario. Una build o el flag de soporte no
equivalen a esa prueba. El caso23592 aceptó daño a30 y44–45 m tras Hot Reload;
no cierra todos sus combos ni toda la selección del servidor nativo.

Consultar en E:\AAEmu\rama_10\server\AAEmu:
Docs/AA10SandboxSeparateZone_es.md, AA10SandboxHotReload_es.md,
AA10PrecisionShotRange_es.md y checkpoints homónimos. Outputs forenses bajo
forensics/output/aa10-client-forensics/sandbox-zone-separate-20261029 y
precision-shot-range-20261029. Continuar desde estos artefactos sin volver a
extraer archivos idénticos. No operar Docker, DB, clientes ni editar C# desde
esta skill; esa fase pertenece a aaemu10-native-reconstruction. Todo nuevo en E.
