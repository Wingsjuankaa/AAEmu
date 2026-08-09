# AA8 Character Slots - candidato de port selectivo V1

Fecha: 2026-08-09

## Hallazgo vivo

La integración temporal con código moderno habilitó correctamente slots de
personaje adicionales en el cliente AA8. Al restaurar el checkpoint AA8 se
recuperaron los contratos visuales y de entrada al mundo ya aprobados, pero los
slots volvieron a aparecer como no disponibles.

Esto es evidencia positiva de una mejora moderna compatible y separable. No
forma parte de la reparación de desconexión al morir un NPC y no debe mezclarse
con ella.

## Frontera candidata

La comparación debe empezar por:

- `AAEmu.Commons/Models/CharacterSlotPolicy.cs`;
- `CharacterManager.cs`;
- `SCAccountInfoPacket`;
- `SCInitialConfigPacket`;
- `SCLevelRestrictionConfigPacket`;
- `SCTrionConfigPacket`;
- `FinishStatePacket`;
- la respuesta de join del LoginServer y su modelo de cuenta.

## Regla de promoción

Portar solamente la política de cantidad/desbloqueo y los campos cuya anchura,
orden y semántica hayan sido confirmados para AA8. Los serializers modernos no
se copiarán completos. La aceptación requiere:

1. conservar selección y render correcto de personajes existentes;
2. mostrar el número configurado de slots creables;
3. crear un personaje sin `serializer size mismatch`;
4. persistir la disponibilidad tras relog;
5. no alterar Login, selección de servidor ni entrada al mundo.

Estado: candidato documentado; no implementado en el runtime V1.17 de muerte.
