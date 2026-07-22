using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCActionSlotsPacket : GamePacket
    {
        private readonly ActionSlot[] _slots;

        public SCActionSlotsPacket(ActionSlot[] slots) : base(SCOffsets.SCActionSlotsPacket, 5)
        {
            _slots = slots;
        }

        public override PacketStream Write(PacketStream stream)
        {
            var packetStart = stream.Count;
            var nonEmpty = 0;

            //foreach (var slot in _slots)
            //{
            //    stream.Write((byte)slot.Type);
            //    if (slot.Type != ActionSlotType.None)
            //        stream.Write(slot.ActionId);
            //}

            foreach (var s in _slots)
            {
                var slot = (byte)s.Type;
                stream.Write(slot);
                switch (s.Type)
                {
                    case ActionSlotType.None:
                        break;
                    case ActionSlotType.ItemType:
                    case ActionSlotType.Spell:
                    case ActionSlotType.RidePetSpell:
                    case ActionSlotType.BattlePetSpell:
                        nonEmpty++;
                        stream.Write((uint)s.ActionId);
                        break;
                    case ActionSlotType.ItemId:
                        nonEmpty++;
                        stream.Write(s.ActionId); // itemId
                        break;
                    default:
                        _log.Error("SCActionSlotsPacket, Unknown ActionSlotType!");
                        break;
                }
            }

            _log.Info(
                "[ActionBar8] G2C slots={0} nonEmpty={1} encodedBytes={2}",
                _slots.Length, nonEmpty, stream.Count - packetStart);

            return stream;
        }
    }
}
