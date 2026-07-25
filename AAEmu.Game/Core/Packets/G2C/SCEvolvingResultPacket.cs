using System;
using System.Collections.Generic;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public sealed class EvolvingModifierResult
    {
        public ushort UnitModifierTypeId { get; set; }
        public byte GradeId { get; set; }
        public int Value { get; set; }
    }

    /// <summary>
    /// Native AA8 synthesis result (x2game.dll, opcode 0x0C6).
    ///
    /// PTR_FUN_39cfa228 / FUN_399a1e60 confirms the complete wire layout.
    /// The client consumes this packet after ItemTask reason 100 to build the
    /// synthesis result notice and refresh the active Gear Upgrade state.
    /// </summary>
    public sealed class SCEvolvingResultPacket : GamePacket
    {
        private const int MaximumModifierCount = 5;

        private readonly ulong _itemId;
        private readonly byte _beforeGradeId;
        private readonly byte _afterGradeId;
        private readonly int _addedExperience;
        private readonly int _bonusExperience;
        private readonly int _addedChance;
        private readonly IReadOnlyList<EvolvingModifierResult> _modifiers;

        public SCEvolvingResultPacket(
            ulong itemId,
            byte beforeGradeId,
            byte afterGradeId,
            int addedExperience,
            int bonusExperience,
            int addedChance,
            IReadOnlyList<EvolvingModifierResult> modifiers)
            : base(SCOffsets.SCEvolvingResultPacket, 5)
        {
            _itemId = itemId;
            _beforeGradeId = beforeGradeId;
            _afterGradeId = afterGradeId;
            _addedExperience = addedExperience;
            _bonusExperience = bonusExperience;
            _addedChance = addedChance;
            _modifiers = modifiers ?? Array.Empty<EvolvingModifierResult>();
        }

        public override PacketStream Write(PacketStream stream)
        {
            if (_modifiers.Count > MaximumModifierCount)
                throw new InvalidOperationException(
                    $"AA8 synthesis supports at most {MaximumModifierCount} " +
                    "new modifier results.");

            stream.Write(_itemId);

            // The AA8 serializer writes memory field +0x19 before +0x18.
            stream.Write(_afterGradeId);
            stream.Write(_beforeGradeId);
            stream.Write((byte)_modifiers.Count);
            stream.Write(_addedExperience);
            stream.Write(_bonusExperience);
            stream.Write(_addedChance);
            foreach (var modifier in _modifiers)
            {
                stream.Write(modifier.UnitModifierTypeId);
                stream.Write(modifier.GradeId);
                stream.Write(modifier.Value);
            }
            return stream;
        }
    }
}
