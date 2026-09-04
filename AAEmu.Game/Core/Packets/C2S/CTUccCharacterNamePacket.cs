using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Stream;
using AAEmu.Game.Core.Packets.S2C;

namespace AAEmu.Game.Core.Packets.C2S;

public class CTUccCharacterNamePacket() : StreamPacket(CTOffsets.CTUccCharacterNamePacket)
{
    public override void Read(PacketStream stream)
    {
        if (stream.Count - stream.Pos != sizeof(ulong))
        {
            Logger.Warn("Invalid r575 UccCharacterName request size: {0}", stream.Count - stream.Pos);
            return;
        }

        // r575 serializes the owner id as uint64 (native serializer slot +0x98).
        var id = stream.ReadUInt64();

        // The local character registry uses uint32; never alias a foreign/wide id
        // to a different local character by truncating its high bits.
        if (id > uint.MaxValue)
            return;

        var name = NameManager.Instance.GetCharacterName((uint)id);
        if (name != null)
            Connection.SendPacket(new TCUccCharNamePacket(id, name));

        Logger.Debug("UccCharacterName, Id: {0}, Name: {1}", id, name);
    }
}
