using AAEmu.Game.Models.Game.Formulas;

namespace AAEmu.Game.Models.Game.Items
{
    public class Holdable
    {
        public uint Id { get; set; }
        public uint KindId { get; set; }
        public int Speed { get; set; }
        public int ExtraDamagePierceFactor { get; set; }
        public int ExtraDamageSlashFactor { get; set; }
        public int ExtraDamageBluntFactor { get; set; }
        public int MaxRange { get; set; }
        public int Angle { get; set; }
        public int EnchantedDps1000 { get; set; }
        public uint SlotTypeId { get; set; }
        public int DamageScale { get; set; }
        public int ElementId { get; set; }
        public Formula FormulaDps { get; set; }
        public Formula FormulaMDps { get; set; }
        public Formula FormulaArmor { get; set; }
        public Formula FormulaHDps { get; set; }
        public Formula FormulaMagicResistance { get; set; }
        public int MinRange { get; set; }
        public int SheathePriority { get; set; }
        public float DurabilityRatio { get; set; }
        public int RenewCategory { get; set; }
        public int ItemProcId { get; set; }
        public int StatMultiplier { get; set; }
        public int GearScoreMultiplier { get; set; }
        public int PoseId { get; set; }
        public int SoundMaterialId { get; set; }

        public int AnimRight1Ratio { get; set; }
        public uint AnimRight1Id { get; set; }
        public int AnimRight2Ratio { get; set; }
        public uint AnimRight2Id { get; set; }
        public uint AnimRight3Id { get; set; }

        public uint SelectRightAttackAnimation(int roll)
        {
            var normalizedRoll = roll < 0 ? 0 : roll > 99 ? 99 : roll;
            var firstWeight = AnimRight1Ratio < 0 ? 0 : AnimRight1Ratio;
            var secondWeight = AnimRight2Ratio < 0 ? 0 : AnimRight2Ratio;

            if (AnimRight1Id != 0 && normalizedRoll < firstWeight)
                return AnimRight1Id;
            if (AnimRight2Id != 0 && normalizedRoll < firstWeight + secondWeight)
                return AnimRight2Id;
            if (AnimRight3Id != 0)
                return AnimRight3Id;

            return AnimRight1Id != 0 ? AnimRight1Id : AnimRight2Id;
        }
    }
}
