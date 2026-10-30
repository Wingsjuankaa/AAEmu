# Padre upstream y actualización segura

## Identidad obligatoria

- Target: `origin/rama_10` en `Wingsjuankaa/AAEmu`.
- Padre único: `upstream/client_version/zone-10.0.2_r575` en `AAEmu/AAEmu`.
- Ref prohibida por confusión: `upstream/client_version/10.0.2_r575`.

Comprobar URLs y refs antes de integrar. No asumir que un fetch previo está
actualizado.

## Procedimiento

1. Preservar el estado del usuario y registrar branch/HEAD/dirtiness.
2. Ejecutar fetch explícito del padre exacto:

   ```powershell
   git fetch upstream `
     +refs/heads/client_version/zone-10.0.2_r575:refs/remotes/upstream/client_version/zone-10.0.2_r575
   ```

3. Calcular merge-base y divergencia. Inventariar commits propios que deben
   sobrevivir.
4. Simular conflictos con `git merge-tree` cuando esté disponible.
5. Crear una rama backup local nombrada con fecha y SHA antes de una integración
   no trivial.
6. Integrar con merge normal en `rama_10` para preservar linaje. No rebasear,
   resetear ni force-pushear salvo petición explícita.
7. Verificar que el padre sea ancestro, el worktree quede limpio y los cambios
   propios sobrevivan.
8. Ejecutar restore, build Release y pruebas unitarias.
9. Publicar a `origin/rama_10` sólo con autorización del usuario y verificar el
   SHA remoto.

Si hay cambios locales solapados, no ocultarlos ni descartarlos. Detener la
integración o aislarla de forma recuperable. Nunca resolver un conflicto
seleccionando masivamente “theirs” o “ours”.
