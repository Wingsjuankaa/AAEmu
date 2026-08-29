using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// AA10 r575 SC_WORLD_INTERACTION_SKILL_LIST (0xAC).
///
/// The release x2game.dll serializer is FUN_39ab6c90 and its nested interaction-list
/// serializer is FUN_39ab1bf0. Object handles are 24-bit BC values and the native
/// consumer caps the interaction array at ten entries.
/// </summary>
public sealed class SCWorldInteractionSkillListPacket : GamePacket
{
    private const uint BcMask = 0x00FF_FFFF;

    private readonly uint _targetObjId;
    private readonly uint _sourceObjId;
    private readonly uint _interactionType;
    private readonly uint _pickObjId;
    private readonly int _extraInfo;
    private readonly byte _mouseButton;
    private readonly int _modifierKeys;
    private readonly uint[] _interactions;

    public SCWorldInteractionSkillListPacket(
        uint targetObjId,
        uint sourceObjId,
        int extraInfo,
        int pickId,
        byte mouseButton,
        int modifierKeys,
        IEnumerable<uint> interactions,
        uint interactionType = 0)
        : base(SCOffsets.SCWorldInteractionSkillListPacket, 1)
    {
        _targetObjId = ToBcHandle(targetObjId);
        _sourceObjId = ToBcHandle(sourceObjId);
        _interactionType = interactionType;
        _pickObjId = unchecked((uint)pickId) & BcMask;
        _extraInfo = extraInfo;
        _mouseButton = mouseButton;
        _modifierKeys = modifierKeys;
        _interactions = (interactions ?? []).Take(10).ToArray();
    }

    public override PacketStream Write(PacketStream stream)
    {
        stream.WriteBc(_targetObjId);
        stream.WriteBc(_sourceObjId);

        stream.WriteBc(_sourceObjId);
        stream.WriteBc(_targetObjId);
        stream.Write(_interactionType);
        stream.WriteBc(_pickObjId);
        stream.Write(_interactions.Length);
        stream.Write(_extraInfo);
        foreach (var interaction in _interactions)
            stream.Write(interaction);

        stream.Write(_mouseButton);
        stream.Write(_modifierKeys);
        return stream;
    }

    private static uint ToBcHandle(uint value) => value <= BcMask ? value : 0;
}
