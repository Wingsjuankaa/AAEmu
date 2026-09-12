using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.PrivateAlpha;
using AAEmu.Game.Models.Game.BugReports;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSJoinUserChatChannelPacket() : GamePacket(CSOffsets.CSJoinUserChatChannelPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var name = stream.ReadString();
        var pwd = stream.ReadString();
        var create = stream.ReadBoolean();
        if (BugReportTransport.IsReserved(name))
        {
            if (Connection.ActiveChar is { } reporter)
                BugReportService.For(reporter).Receive(reporter, name, pwd, create);
            return;
        }
        if (AlphaTransport.IsReserved(name))
        {
            if (Connection.ActiveChar is { } character)
                AlphaService.For(character).Receive(character, name, pwd, create);
            return;
        }
        if (EquipSlotReinforceBatchTransport.IsReserved(name))
        {
            Connection.ActiveChar?.EquipSlotReinforce?.ReceiveBatchFragment(name, pwd, create);
            return;
        }
        Logger.Debug("JoinUserChatChannel, Name: {0}, Create: {1}", name, create);
    }
}
