using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.FactionCompetition;

/// <summary>One AA10 faction-competition scoreboard row.</summary>
public readonly record struct FactionCompetitionPoint(int FactionId, uint Point)
{
    public void Write(PacketStream stream)
    {
        stream.Write(FactionId);
        stream.Write(Point);
    }
}
