using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Game.World.Transform;

namespace AAEmu.Game.Models.Game.Skills.Plots
{
    public enum PlotObjectType : byte {
        UNIT = 0x1,
        POSITION = 0x2
    }

    public class PlotObject : PacketMarshaler
    {
        public PlotObjectType Type { get; set; }
        public uint UnitId { get; set; }
        public Transform Position { get; set; }
        public Transform LinePosition { get; set; }
        public uint ReferenceId1 { get; set; }
        public uint ReferenceId2 { get; set; }
        public uint ReferenceId3 { get; set; }

        public PlotObject(BaseUnit unit) 
        {
            Type = PlotObjectType.UNIT;
            UnitId = unit.ObjId;
        }

        public PlotObject(uint unitId) 
        {
            Type = PlotObjectType.UNIT;
            UnitId = unitId;
        }

        public PlotObject(
            Transform position,
            Transform linePosition = null,
            uint referenceId1 = 0,
            uint referenceId2 = 0,
            uint referenceId3 = 0)
        {
            Type = PlotObjectType.POSITION;
            Position = position.CloneDetached();
            // A point target has no independent line endpoint. Encoding it as
            // a degenerate line preserves the exact location for consumers of
            // either positional field without inventing a second coordinate.
            LinePosition = (linePosition ?? position).CloneDetached();
            ReferenceId1 = referenceId1;
            ReferenceId2 = referenceId2;
            ReferenceId3 = referenceId3;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write((byte)Type);

            switch (Type) {
                case PlotObjectType.UNIT:
                    stream.WriteBc(UnitId);
                    break;
                case PlotObjectType.POSITION:
                    stream.WritePosition(Position.Local.Position);
                    var ypr = Position.Local.ToRollPitchYawSBytes();
                    stream.Write(ypr.Item1);
                    stream.Write(ypr.Item2);
                    stream.Write(ypr.Item3);

                    // Kakao 8.0 r558734 reads a second positional transform
                    // named lineRot, followed by three BC object references
                    // (x2game.dll FUN_3999fd00). Omitting this tail shifts all
                    // remaining SCPlotEvent fields and suppresses Location FX.
                    stream.WritePosition(LinePosition.Local.Position);
                    var lineYpr = LinePosition.Local.ToRollPitchYawSBytes();
                    stream.Write(lineYpr.Item1);
                    stream.Write(lineYpr.Item2);
                    stream.Write(lineYpr.Item3);
                    stream.WriteBc(ReferenceId1);
                    stream.WriteBc(ReferenceId2);
                    stream.WriteBc(ReferenceId3);
                    break;
            }

            return stream;
        }
    }
}
