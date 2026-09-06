# Consulta a Codex desde el editor — prueba 2026-09-04

Target rama_10; padre upstream/client_version/zone-10.0.2_r575. Usuario autorizó una prueba de consulta contextual y devolución directa al editor. No se aprobaron ni aplicaron traducciones.

Se añadió `scripts/contextual_codex.py`, el endpoint local autenticado `POST /api/suggest-codex` y el botón **Consultar a Codex**. El proveedor local continúa disponible. El CLI instalado estaba autenticado mediante ChatGPT; se conservó el modelo configurado `gpt-6-astra` y esfuerzo `medium`. Se usa `codex exec` efímero, sandbox read-only, sin shell/unified_exec/js_repl/apps y con web_search desactivado. El proceso conserva la autenticación existente; no se leen ni copian tokens. No hay permisos nuevos sobre el cliente.

Contexto: fuentes multilingües, datos y relaciones de la entidad, notas guardadas, traducción actual y nombres protegidos. Los textos se delimitan como datos y se instruye a no obedecer órdenes incluidas en ellos. Respuesta restringida a JSON Schema (translation, note, uncertain), revalidada por los controles de localización y por revisión vigente. El registro puede ser draft o blocked, nunca approved. No se manda la conversación completa ni se asume que el modelo la conoce.

## Prueba real

- Entrada `ui_texts/text/1033`, revisión 2, inglés `Melee Accuracy`.
- Consulta inicial desde el proveedor: 6,685 segundos, «Precisión cuerpo a cuerpo», sin dudas señaladas, sin errores estructurales y sin eventos de herramientas.
- Consulta completa desde el botón en navegador: 6,868 segundos, mismo texto; nota: «Se mantiene la traducción aprobada: las fuentes confirman que indica la probabilidad de acertar ataques cuerpo a cuerpo, no su daño.» La nota es una explicación del modelo, no una prueba adicional de la mecánica.
- Evidencias: `work/codex-translation/61218124018346338a4c73a7b02c5da5` y `work/codex-translation/72560868e5754ea8837b655cab2c7002`. Cada ejecución reportó 14.732 tokens de entrada; salida 53 y 55 respectivamente. Esto prueba conectividad, contexto y devolución al editor, no calidad semántica de todo el corpus ni latencia de misiones extensas.
- UI verificada: propuesta recibida con modelo, explicación, duración y **Usar como borrador**. No se pulsó guardar, aprobar ni aplicar.
- 37 pruebas Python correctas, incluyendo rechazo de esquemas/tipos, variables y nombres alterados, y ausencia de aprobación automática. JavaScript válido con `node --check`.

El servicio del editor fue reiniciado mediante barrera de mantenimiento sin trabajos en curso. Pestañas antiguas requieren recarga. Ningún servicio AAEmu ni Zone fue operado. Fuentes oficiales consultadas: https://learn.chatgpt.com/docs/non-interactive-mode y https://learn.chatgpt.com/docs/auth; además, ayuda del CLI instalado y `codex login status`.
