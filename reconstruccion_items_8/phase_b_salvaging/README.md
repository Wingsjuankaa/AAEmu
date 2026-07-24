# B6 — salvaging y conversión de objetos AA8

La clausura `item_conv_*` fue recuperada completa desde `game11`, con layouts
confirmados en `x2game.dll`. También se recuperaron 96 relaciones de smelting y
32 definiciones de operación.

La mutación sigue bloqueada: falta cerrar el formato nativo de
`item_smelting_probs`, resolver algunas cadenas internadas y confirmar el
protocolo de solicitud/resultado. No se usa ningún dato 3.0 como sustituto.
