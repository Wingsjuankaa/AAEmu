using System;

namespace AAEmu.Game.Models.Game.Items.Templates
{
    public sealed class SocketItemTemplate : ItemTemplate
    {
        public override Type ClassType => typeof(SocketItem);

        public uint NativeDefinitionId { get; set; }
        public string BuffModifierTooltip { get; set; }
        public uint EisetId { get; set; }
        public uint EquipItemTagId { get; set; }
        public uint EquipItemId { get; set; }
        public uint EquipSlotGroupId { get; set; }
        public bool Extractable { get; set; }
        public bool IgnoreEquipItemTag { get; set; }
        public uint ItemSocketChanceId { get; set; }
        public string SkillModifierTooltip { get; set; }
    }
}
