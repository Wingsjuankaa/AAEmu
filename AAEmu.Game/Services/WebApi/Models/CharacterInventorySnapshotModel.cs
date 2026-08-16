using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Containers;

namespace AAEmu.Game.Services.WebApi.Models;

internal sealed record CharacterInventorySnapshotModel(
    uint CharacterId,
    string CharacterName,
    uint Level,
    bool IsOnline,
    DateTime CapturedAtUtc,
    IReadOnlyList<CharacterItemSnapshotModel> Equipment,
    IReadOnlyList<CharacterItemSnapshotModel> Backpack)
{
    public static CharacterInventorySnapshotModel Create(
        uint characterId,
        string characterName,
        uint level,
        bool isOnline,
        ItemContainer equipment,
        ItemContainer backpack,
        DateTime capturedAtUtc)
    {
        return new CharacterInventorySnapshotModel(
            characterId,
            characterName,
            level,
            isOnline,
            capturedAtUtc,
            Snapshot(equipment, true),
            Snapshot(backpack, false));
    }

    private static IReadOnlyList<CharacterItemSnapshotModel> Snapshot(ItemContainer container, bool equipment)
    {
        if (container == null)
            return [];

        lock (container.Items)
        {
            return container.Items
                .OrderBy(item => item.Slot)
                .ThenBy(item => item.Id)
                .Select(item => CharacterItemSnapshotModel.Create(item, equipment))
                .ToArray();
        }
    }
}

internal sealed record CharacterItemSnapshotModel(
    ulong Id,
    uint TemplateId,
    string TemplateName,
    string Container,
    int Slot,
    string SlotName,
    int Count,
    byte Grade,
    string Flags,
    ushort? TemperScaleId,
    byte? Durability,
    byte? MaxDurability,
    IReadOnlyList<uint> SocketAndSynthesisData)
{
    public static CharacterItemSnapshotModel Create(Item item, bool equipment)
    {
        var equipItem = item as EquipItem;
        var slotName = equipment && Enum.IsDefined(typeof(EquipmentItemSlot), (byte)item.Slot)
            ? ((EquipmentItemSlot)(byte)item.Slot).ToString()
            : item.Slot.ToString();

        return new CharacterItemSnapshotModel(
            item.Id,
            item.TemplateId,
            item.Template?.Name ?? $"Item {item.TemplateId}",
            item.SlotType.ToString(),
            item.Slot,
            slotName,
            item.Count,
            item.Grade,
            item.ItemFlags.ToString(),
            equipItem?.ScaledA,
            equipItem?.Durability,
            equipItem?.MaxDurability,
            equipItem?.GemData?.Where(value => value != 0).ToArray() ?? []);
    }
}
