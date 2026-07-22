using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSUpdateActionSlotPacket : GamePacket
    {
        public CSUpdateActionSlotPacket() : base(CSOffsets.CSUpdateActionSlotPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var packetStart = stream.Pos;
            var packetBytes = System.BitConverter.ToString(stream.Buffer, packetStart, stream.LeftBytes);
            var slot = stream.ReadByte();
            var type = (ActionSlotType)stream.ReadByte();
            ulong actionId = 0;

            switch (type)
            {
                case ActionSlotType.None:
                    Connection.ActiveChar.SetAction(slot, ActionSlotType.None, 0);
                    break;
                case ActionSlotType.ItemType:
                case ActionSlotType.Spell:
                case ActionSlotType.RidePetSpell:
                case ActionSlotType.BattlePetSpell:
                    actionId = stream.ReadUInt32();
                    Connection.ActiveChar.SetAction(slot, type, (uint)actionId);
                    break;
                case ActionSlotType.ItemId:
                    actionId = stream.ReadUInt64();
                    Connection.ActiveChar.SetAction(slot, type, actionId);
                    break;
                default:
                    _log.Error("[ActionBar8] C2G unknown type={0}, slot={1}, payload={2}", (byte)type, slot, packetBytes);
                    break;
            }

            _log.Info(
                "[ActionBar8] C2G char={0} slot={1} type={2}({3}) actionId={4} consumed={5} remaining={6} payload={7}",
                Connection.ActiveChar?.Name ?? "<none>", slot, type, (byte)type, actionId,
                stream.Pos - packetStart, stream.LeftBytes, packetBytes);
        }
    }
}
