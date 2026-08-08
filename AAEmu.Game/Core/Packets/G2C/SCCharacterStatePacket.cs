using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// AA 8.0.3.12 character state sent while entering the world.
/// </summary>
public class SCCharacterStatePacket(Character character) : GamePacket(SCOffsets.SCCharacterStatePacket, 5)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write((uint)character.Transform.InstanceId);

        var guid = new byte[16];
        BitConverter.GetBytes((ulong)character.Id).CopyTo(guid, 0);
        BitConverter.GetBytes((ulong)character.Id ^ 0x5AA5_A55A_5AA5_A55AUL).CopyTo(guid, 8);
        stream.Write(guid, true);
        stream.Write(0u); // rwd
        stream.Write(0u); // srwd

        character.WriteLobby80312(stream);

        stream.Write(character.Transform.World.Position.X);
        stream.Write(character.Transform.World.Position.Y);
        stream.Write(character.Transform.World.Position.Z);

        stream.Write(character.Experience);
        stream.Write(character.HeirExp);
        stream.Write(character.RecoverableExp);
        stream.Write(0u); // penaltiedExp
        stream.Write(character.ReturnDistrictId);
        stream.Write(0u); // returnDistrict type
        stream.Write(character.ResurrectionDistrictId);

        for (var i = 0; i < 30; i++)
            stream.Write(0u); // abilityExp

        stream.Write(0); // totalSentMail
        stream.Write(0); // totalMail
        stream.Write(0); // totalMiaMail
        stream.Write(0); // totalCommercialMail
        stream.Write(0); // unreadMail
        stream.Write(0); // unreadMiaMail
        stream.Write(0); // unreadCommercialMail
        stream.Write(character.NumInventorySlots);
        stream.Write(character.NumBankSlots);
        stream.Write(character.Money);
        stream.Write(character.Money2);
        stream.Write(0L);
        stream.Write(0L);
        stream.Write(character.AutoUseAAPoint);

        stream.Write(0u); // equipment state list
        stream.Write(character.JuryPoint);
        stream.Write(0); // jailSeconds
        stream.Write(0); // reportedNo
        stream.Write(0); // suspectedNo
        stream.Write(0); // totalPlayTime
        stream.Write(character.ExpandedExpert);
        stream.Write(0); // remainBotCheckCnt
        stream.Write((short)0); // failedBotCheckAccumCnt

        for (var i = 0; i < 12; i++)
            stream.Write(0L); // instantTime

        stream.Write(0u); // dailyLeadershipPoint
        stream.Write(DateTime.MinValue);
        stream.Write(0u); // dailyHonorWarPoint
        stream.Write(DateTime.MinValue);
        stream.Write(0); // totalReportBadUser
        stream.Write((byte)0); // usableAbilSetSlotCount

        for (var i = 0; i < 5; i++)
            stream.Write(0u); // stats

        stream.Write(1u); // pageInfos count
        for (var i = 0; i < 5; i++)
            stream.Write(0); // page stats
        stream.Write(0u); // applyNormalCount
        stream.Write(0u); // applySpecialCount

        stream.Write(0u); // selectPageIndex
        stream.Write(0u); // extendMaxStats
        stream.Write(0u); // applyExtendCount
        stream.Write(0u); // type
        stream.Write(0); // appellationStamp

        stream.Write(0u); // equipSlotReinforces
        stream.Write(0u); // slotInfoList
        stream.Write(0u); // levelEffectList
        stream.Write((byte)0); // reservedQuestDropTarget
        return stream;
    }
}
