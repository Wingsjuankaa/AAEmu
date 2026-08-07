# Corroboración externa Sorcery AA8 V1

Fecha de consulta: 2026-08-05  
Cliente objetivo: ArcheAge Kakao `8.0.3.12 r558734`

## Regla de autoridad

Este documento sólo registra corroboración externa posterior al cierre forense
AA8. No promueve filas, fórmulas, balance, tiempos, rangos, textos ni contenido
al runtime. La autoridad continúa siendo, en este orden:

1. SQLite y assets del cliente AA8;
2. corpus nativo AA8 (`x2game.dll`, `game_pak`, DLL y Stage 15);
3. crosswalk AA8→10.x clasificado;
4. evidencia viva del cliente AA8.

Las páginas externas son mutables, pueden corresponder a revisiones posteriores
o servidores custom y sólo se usan para comprobar identidad pública y UX cuando
coinciden con una relación ya demostrada internamente.

## Identidad pública del cierre

La página pública [Skills - Sorcery](https://wiki.archerage.to/na-en/db/skills/sorcery)
enumera 42 de los 43 IDs del cierre ejecutable V3. Confirma de forma
independiente los doce entrypoints base, las cadenas internas visibles de
Flamebolt y Gods' Whip, los doce sucesores Heir, Ice Shard y los tres retornos
contextuales de Magic Circle.

El único ID del cierre V3 que no aparece en ese catálogo es `15317`. Esto
concuerda con la clasificación forense AA8: `15317` es un hijo interno exacto
de Meteor Strike, no una skill pública aprendible. La ausencia externa no es
una fuente de propiedades, pero sí evidencia negativa compatible con `show=0`
y con su uso exclusivo dentro del closure de Meteor.

La misma página lista el ID `9000229`, ajeno al cierre AA8. Se descarta por ser
contenido externo/custom sin raíz, relación ni consumidor demostrado en AA8.
No fue importado a SQLite, código ni manifiestos.

## Magic Circle y acción contextual

La ficha pública [Magic Circle 43185](https://archeagecodex.com/us/skill/43185/?sl=1)
corrobora que el sucesor ofrece una segunda activación para volver a la posición
del círculo. Esto coincide con el grafo AA8 ya demostrado:

- `43185` crea el ancla;
- `43465` es la acción contextual de retorno;
- el retorno debe usar la posición capturada, respetar mundo/instancia y
  consumir el buff de ancla.

La noticia histórica
[ArcheAge PTS Patch Notes Feature New Ancestral Skills](https://www.mmorpg.com/news/archeage-pts-patch-notes-feature-new-ancestral-skills-2000117309)
también sitúa Magic Circle: Quake en el sistema Ancestral antes de la revisión
AA8. Sólo se conserva esa existencia histórica; sus cifras no son autoridad.

## Resultado operativo

- Ningún vacío estático nuevo fue descubierto.
- No se justificó ningún cambio adicional de runtime.
- La corroboración refuerza el cierre 43/43 y la naturaleza interna de `15317`.
- La frontera restante sigue siendo exclusivamente viva: ciclo del servidor,
  FX/sonido/animación, segundo uso y persistencia tras relog en el cliente AA8.

