using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Char;

public sealed record EquipSlotReinforceProgress(sbyte Level = 1, int Experience = 0);
public readonly record struct EquipSlotReinforceEffectKey(byte Slot, sbyte Level);

/// <summary>Immutable operation snapshot. Unstored slots have native level 1 and zero EXP.</summary>
public sealed class EquipSlotReinforceState
{
    public IReadOnlyDictionary<byte, EquipSlotReinforceProgress> Slots { get; }
    public IReadOnlyDictionary<EquipSlotReinforceEffectKey, uint> Effects { get; }

    public EquipSlotReinforceState(
        IReadOnlyDictionary<byte, EquipSlotReinforceProgress> slots = null,
        IReadOnlyDictionary<EquipSlotReinforceEffectKey, uint> effects = null)
    {
        Slots = new System.Collections.ObjectModel.ReadOnlyDictionary<byte, EquipSlotReinforceProgress>(
            slots?.ToDictionary(x => x.Key, x => x.Value) ?? []);
        Effects = new System.Collections.ObjectModel.ReadOnlyDictionary<EquipSlotReinforceEffectKey, uint>(
            effects?.ToDictionary(x => x.Key, x => x.Value) ?? []);
    }

    public EquipSlotReinforceProgress Get(byte slot) => Slots.GetValueOrDefault(slot) ?? new();

    public EquipSlotReinforceState With(byte slot, EquipSlotReinforceProgress progress,
        EquipSlotReinforceEffectKey? key = null, uint modifier = 0)
    {
        var slots = Slots.ToDictionary(x => x.Key, x => x.Value);
        var effects = Effects.ToDictionary(x => x.Key, x => x.Value);
        slots[slot] = progress;
        if (key.HasValue)
            effects[key.Value] = modifier;
        return new(slots, effects);
    }

    /// <summary>RVA A41200/A43710: map counts u32; slot map key i32, level u8, EXP i32;
    /// effect map key u8 slot+i8 milestone, value u32 modifier descriptor.</summary>
    public PacketStream Write(PacketStream stream)
    {
        stream.Write((uint)Slots.Count);
        foreach (var (slot, value) in Slots.OrderBy(x => x.Key))
        {
            stream.Write((int)slot);
            stream.Write((byte)value.Level);
            stream.Write(value.Experience);
        }
        stream.Write((uint)Effects.Count);
        foreach (var (key, value) in Effects.OrderBy(x => x.Key.Slot).ThenBy(x => x.Key.Level))
        {
            stream.Write(key.Slot);
            stream.Write(key.Level);
            stream.Write(value);
        }
        return stream;
    }
}
