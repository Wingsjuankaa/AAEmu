using System;

namespace AAEmu.Game.Models.Game.Items.Templates
{
    public class WeaponTemplate : EquipItemTemplate
    {
        public override Type ClassType => typeof(Weapon);

        public bool BaseEnchantable { get; set; }
        public Holdable HoldableTemplate { get; set; }
        public bool BaseEquipment { get; set; }
        public uint AssetId { get; set; }
        public uint FixedAttackedSoundId { get; set; }
        public uint FixedVisualEffectId { get; set; }
        public float DrawnScale { get; set; }
        public float WornScale { get; set; }
    }
}
