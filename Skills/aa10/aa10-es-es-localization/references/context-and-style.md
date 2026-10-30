# Contexto, estilo y terminología

## Español objetivo

Usar español internacional comprensible en Hispanoamérica y España. Preferir oraciones breves en HUD y botones, infinitivos en acciones cuando encaje (`Aceptar`, `Cancelar`, `Equipar`) y segunda persona neutral en tutoriales. Evitar modismos locales.

## Política de contexto

Clasificar la unidad antes de traducir:

- `ui`: ventana, control, estado anterior/siguiente, límite visible y tecla asociada.
- `item`: tipo, categoría, receta, habilidad, buff, misión y obtención.
- `skill`: efecto, buff/debuff, recurso, alcance, objetivo y especialización.
- `quest`: cadena, etapa, NPC, objetos, lugar, burbujas y condiciones.
- `system`: funcionalidad completa, paquetes y valores dinámicos.
- `lore`: personaje, facción, cronología y registro de nombres propios.

Guardar enlaces de evidencia o claves relacionadas en `context_refs`. Si falta el consumidor y la frase admite sentidos distintos, usar estado `blocked`.

## Autoridad de fuentes

1. Función demostrada por el consumidor y datos mecánicos r575.
2. Coreano o chino nativo r575.
3. Traducciones coherentes coincidentes entre francés, alemán y ruso.
4. Inglés r575 como fuente de trabajo, nunca como verdad única.
5. Versiones anteriores o fuentes externas solo como corroboración registrada.

## Glosario inicial

El archivo versionado `glossary/terms.yaml` es la autoridad. Cada término incluye dominio, traducción preferida, alternativas prohibidas, estado, razón y evidencia. No fijar nombres propios ni vocabulario propio de ArcheAge por memoria sin contrastarlo.

Reglas iniciales aprobadas:

- `Patron` → `Patrón` cuando se refiera a la membresía.
- `Labor` → `Labor` como recurso del juego, sujeto a revisión visual del corpus completo.
- `Loyalty Token` → `Ficha de lealtad`.
- `World Level` → `Nivel del mundo` solo en evidencia y documentación; la función permanece desactivada en la build base actual.
- `EXP` → `EXP` en espacios compactos; `experiencia` en prosa.

## Nombres propios

Mantener el nombre inglés si no existe una forma canónica demostrada. Registrar por separado nombres de personajes, lugares, facciones, objetos únicos y monedas. Una decisión sobre un nombre no autoriza traducir palabras iguales usadas como sustantivos comunes.
