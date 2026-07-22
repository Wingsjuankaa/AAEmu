using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills.Plots;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCPlotEventPacket : GamePacket
    {
        private readonly ushort _tl;
        private readonly uint _eventId;
        private readonly uint _skillId;
        private readonly PlotObject _caster;
        private readonly PlotObject _target;
        private readonly uint _unkId;
        private readonly ushort _castingTime;
        private readonly byte _flag;
        private readonly ulong _itemId;
        private readonly byte _targetUnitCount;
        private readonly byte _inputDirection;

        public SCPlotEventPacket(
            ushort tl, uint eventId, uint skillId, PlotObject caster, PlotObject target, uint unkId,
            ushort castingTime, byte flag, byte inputDirection, ulong itemId = 0L, byte targetUnitCount = 1)
            : base(SCOffsets.SCPlotEventPacket, 5)
        {
            _tl = tl;
            _eventId = eventId;
            _skillId = skillId;
            _caster = caster;
            _target = target;
            _unkId = unkId;
            _castingTime = castingTime;
            _flag = flag;
            _itemId = itemId;
            _targetUnitCount = targetUnitCount;
            _inputDirection = inputDirection;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_tl);
            stream.Write(_eventId); // type(id), eventId?
            stream.Write(_skillId);
            stream.Write(_caster);  // PlotObj
            stream.Write(_target);  // PlotObj
            stream.Write(_itemId);  // itemId
            stream.WriteBc(_unkId);
            stream.Write(_castingTime); // msec, castingTime / 10
            stream.WriteBc(0);      // objId
            stream.Write((short)0); // msec
            stream.Write(_targetUnitCount); // targetUnitCount // TODO if aoe, list of units
            if (_targetUnitCount > 0)
            {
                for (var i = 0; i < _targetUnitCount; i++)
                {
                    stream.WriteBc(_target.UnitId); // TODO targetUnitCount > 0 -> do->while() stream.WriteBc(0);
                }
            }
            stream.Write(_flag);

            if (((_flag >> 3) & 1) == 1)
            {
                for (var i = 0; i < 13; i++)
                    stream.Write(0); // v
            }

            // Kakao 8.0 r558734 always reads inputDirection after the flags
            // and their optional 13-value block (x2game.dll FUN_399a38b0).
            stream.Write(_inputDirection);

            return stream;
        }
    }
}
