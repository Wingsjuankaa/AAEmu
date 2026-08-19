using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSSellBackpackGoodsPacket() : GamePacket(CSOffsets.CSSellBackpackGoodsPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var npcObjId = stream.ReadBc();
        var characterObjId = stream.ReadBc();

        Logger.Debug(
            "CSSellBackpackGoods decoded npcObjId={0}, characterObjId={1}, activeCharacterId={2}, activeCharacterObjId={3}, unreadBytes={4}",
            npcObjId,
            characterObjId,
            Connection.ActiveChar?.Id ?? 0,
            Connection.ActiveChar?.ObjId ?? 0,
            stream.LeftBytes);

        SpecialtyManager.Instance.SellSpecialty(Connection.ActiveChar, npcObjId, characterObjId);
    }
}
