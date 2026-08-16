using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Packets.G2C.UnitState;

/// <summary>Position, scale, level pairs, four slot selectors, and model reference.</summary>
internal static class UnitStatePlacementSerializer
{
    private const sbyte UnsetSlot = -1;

    public static void Write(PacketStream stream, UnitStateWireContext context)
    {
        var unit = context.Unit;
        // Only client packets ground World-owned NPCs. A Zone placement override is already local.
        if (context.PlacementOverride is null)
            GroundWorldNpc(unit, context);

        var position = context.PlacementOverride ?? unit.Transform.Local.Position;
        stream.WritePosition(position);
        stream.Write(unit.Scale);
        stream.Write(checked((sbyte)unit.Level));
        stream.Write(checked((sbyte)unit.HeirLevel));

        WriteLevelBlock(stream, context);
        WriteSlotSelectors(stream);
        stream.Write(unit.ModelId);
    }

    private static void GroundWorldNpc(Unit unit, UnitStateWireContext context)
    {
        if (context.Npc is null || context.Npc.IsZoneMirror)
            return;

        var position = unit.Transform.Local.Position;
        var height = WorldManager.Instance.GetReferenceHeight(
            context.Npc, position.X, position.Y, position.Z, unit.Transform.ZoneId);
        unit.Transform.Local.SetHeight(height);
    }

    private static void WriteLevelBlock(PacketStream stream, UnitStateWireContext context)
    {
        // This is the native secondary level override, not a duplicate of the display level pair
        // written immediately above.  For a Character, x2game r575 stores its first byte at
        // Unit+0x42 and treats any non-zero value as an instruction to skip equipment-derived
        // modifiers while building the local attribute aggregate.  Repeating Unit.Level here
        // therefore leaves appearance/gear score intact but suppresses weapon DPS, armor and base
        // item attributes in X2Unit:UnitInfo("player").  No override is required for normal units.
        if (context.BaseUnitType is BaseUnitType.Character or BaseUnitType.Npc)
        {
            stream.Write((sbyte)0);
            stream.Write((sbyte)0);
            return;
        }

        stream.Write(checked((sbyte)context.Unit.Level));
        stream.Write((sbyte)0);
    }

    private static void WriteSlotSelectors(PacketStream stream)
    {
        // r575 deserializes these as four signed bytes named "slot".  Its character-stat
        // aggregator treats every non-negative value as an equipment slot to exclude.  Zero is
        // therefore not an empty/default selector: it disables the Head slot and suppresses the
        // helmet's base armor and socket modifiers.  The AA8 implementation also uses -1, but the
        // width and exclusion semantics here are independently confirmed in the AA10 x2game.
        for (var index = 0; index < 4; index++)
            stream.Write(UnsetSlot);
    }
}
