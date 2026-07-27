using System;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Quests;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCQuestContextUpdatedPacket : GamePacket
    {
        private readonly Quest _quest;
        private readonly uint _componentId;

        public SCQuestContextUpdatedPacket(Quest quest, uint componentId) : base(SCOffsets.SCQuestContextUpdatedPacket, 5)
        {
            _quest = quest;
            _componentId = componentId;
        }

        private static byte GetWidthCode(uint value)
        {
            if (value >= 0x1000000)
                return 3;
            if (value >= 0x10000)
                return 2;
            if (value >= 0x100)
                return 1;
            return 0;
        }

        private void WriteNativeUpdatedComponents(PacketStream stream)
        {
            // AA8 carries ten variable-width uint32 values after the quest
            // record. The first value identifies the changed component; the
            // remaining entries are empty for a single-component update.
            var components = new uint[10];
            components[0] = _componentId;

            for (var offset = 0; offset < components.Length; offset += 4)
            {
                var count = Math.Min(4, components.Length - offset);
                byte widthFlags = 0;
                for (var index = 0; index < count; index++)
                {
                    widthFlags |=
                        (byte)(GetWidthCode(components[offset + index]) << (index * 2));
                }

                stream.Write(widthFlags);
                for (var index = 0; index < count; index++)
                {
                    var value = components[offset + index];
                    switch (GetWidthCode(value))
                    {
                        case 0:
                            stream.Write((byte)value);
                            break;
                        case 1:
                            stream.Write((ushort)value);
                            break;
                        case 2:
                            stream.Write((byte)value);
                            stream.Write((ushort)(value >> 8));
                            break;
                        default:
                            stream.Write(value);
                            break;
                    }
                }
            }
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_quest);
            WriteNativeUpdatedComponents(stream);
            return stream;
        }
    }
}
